# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import logging
import threading
import time
import psycopg2
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz

import openerp
from openerp import SUPERUSER_ID, netsvc, api
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.modules import load_information_from_description_file

_logger = logging.getLogger(__name__)


def str2tuple(s):
    return eval('tuple(%s)' % (s or ''))


_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}
BASE_VERSION = load_information_from_description_file('base')['version']


class IrCron(osv.osv):
    _inherit = "ir.cron"
    _columns = {
        'num_of_failed_runs': fields.integer('Number of failed runs', default=0),
        'last_failed_date': fields.datetime('Last failed date', copy=False),
        'last_run_date': fields.datetime('Last run date', copy=False),
    }

    def _handle_callback_exception(self, cr, uid, model_name, method_name, args, job_id, job_exception):
        """ Method called when an exception is raised by a job.

        Simply logs the exception and rollback the transaction.

        :param model_name: model name on which the job method is located.
        :param method_name: name of the method to call when this job is processed.
        :param args: arguments of the method (without the usual self, cr, uid).
        :param job_id: job id.
        :param job_exception: exception raised by the job.

        """
        cr.rollback()
        _logger.exception(
            "Call of self.pool.get('%s').%s(cr, uid, *%r) failed in Job %s" % (model_name, method_name, args, job_id))

    def _callback_now(self, cr, uid, model_name, method_name, args, job_id, cron_cr, now):
        """ Run the method associated to a given job

        It takes care of logging and exception handling.

        :param model_name: model name on which the job method is located.
        :param method_name: name of the method to call when this job is processed.
        :param args: arguments of the method (without the usual self, cr, uid).
        :param job_id: job id.
        """
        try:
            args = str2tuple(args)
            openerp.modules.registry.RegistryManager.check_registry_signaling(cr.dbname)
            registry = openerp.registry(cr.dbname)
            if model_name in registry:
                model = registry[model_name]
                if hasattr(model, method_name):
                    log_depth = (None if _logger.isEnabledFor(logging.DEBUG) else 1)
                    netsvc.log(_logger, logging.DEBUG, 'cron.object.execute',
                               (cr.dbname, uid, '*', model_name, method_name) + tuple(args), depth=log_depth)
                    if _logger.isEnabledFor(logging.DEBUG):
                        start_time = time.time()
                    getattr(model, method_name)(cr, uid, *args)
                    if _logger.isEnabledFor(logging.DEBUG):
                        end_time = time.time()
                        _logger.debug('%.3fs (%s, %s)' % (end_time - start_time, model_name, method_name))
                    openerp.modules.registry.RegistryManager.signal_caches_change(cr.dbname)
                else:
                    # update num_of_failed_runs counter if method is not found
                    try:
                        cron_cr.execute(
                            "UPDATE ir_cron SET num_of_failed_runs = num_of_failed_runs + 1, last_failed_date = %s, last_run_date = %s WHERE id=%s;",
                            (now, now, job_id,))
                    except:
                        cron_cr.rollback()
                        print "Error 1"
                        pass
                    msg = "Method `%s.%s` does not exist." % (model_name, method_name)
                    _logger.warning(msg)
            else:
                # update num_of_failed_runs counter if method is not found
                try:
                    cron_cr.execute(
                        "UPDATE ir_cron SET num_of_failed_runs = num_of_failed_runs + 1, last_failed_date = %s, last_run_date = %s WHERE id=%s;",
                        (now, now, job_id,))
                except:
                    cron_cr.rollback()
                    print "Error 2"
                    pass
                msg = "Model `%s` does not exist." % model_name
                _logger.warning(msg)
        except Exception, e:
            # update num_of_failed_runs counter if method is not found
            try:
                cron_cr.execute(
                    "UPDATE ir_cron SET num_of_failed_runs = num_of_failed_runs + 1, last_failed_date = %s, last_run_date = %s WHERE id=%s;",
                    (now, now, job_id,))
            except:
                cron_cr.rollback()
                print "Error 3"
                pass
            self._handle_callback_exception(cr, uid, model_name, method_name, args, job_id, e)

    def _process_job_now(self, job_cr, job, cron_cr, now):
        """ Run a given job taking care of the repetition.

        :param job_cr: cursor to use to execute the job, safe to commit/rollback
        :param job: job to be run (as a dictionary).
        :param cron_cr: cursor holding lock on the cron job row, to use to update the next exec date,
            must not be committed/rolled back!
        """
        try:
            with api.Environment.manage():
                nnow = fields.datetime.context_timestamp(job_cr, job['user_id'], datetime.now())
                nextcall = fields.datetime.context_timestamp(job_cr, job['user_id'],
                                                             datetime.strptime(job['nextcall'],
                                                                               DEFAULT_SERVER_DATETIME_FORMAT))
                numbercall = job['numbercall']

                ok = False
                while nextcall < nnow and numbercall:
                    if numbercall > 0:
                        numbercall -= 1
                    if not ok or job['doall']:
                        self._callback_now(job_cr, job['user_id'], job['model'], job['function'], job['args'],
                                           job['id'], cron_cr, now)
                    if numbercall:
                        nextcall += _intervalTypes[job['interval_type']](job['interval_number'])
                    ok = True
                addsql = ''
                if not numbercall:
                    addsql = ', active=False'
                try:
                    cron_cr.execute(
                        "UPDATE ir_cron SET last_run_date=%s, nextcall=%s, numbercall=%s" + addsql + " WHERE id=%s",
                        (now, nextcall.astimezone(pytz.UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                         numbercall, job['id']))
                except:
                    pass
                    cron_cr.rollback()
                    cron_cr.execute(
                        "UPDATE ir_cron SET nextcall=%s, numbercall=%s" + addsql + " WHERE id=%s",
                        (nextcall.astimezone(pytz.UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                         numbercall, job['id']))

                finally:
                    cron_cr.commit()
                self.invalidate_cache(job_cr, SUPERUSER_ID)


        finally:
            job_cr.commit()

    # @api.onchange('active')
    # def _onchange_active(self):
    #     """Reset num_of_failed_runs counter when activating job."""
    #     if self.active:
    #         self.num_of_failed_runs = 0
    @classmethod
    def _acquire_job(cls, db_name):
        # TODO remove 'check' argument from addons/base_action_rule/base_action_rule.py
        """ Try to process one cron job.

        This selects in database all the jobs that should be processed. It then
        tries to lock each of them and, if it succeeds, run the cron job (if it
        doesn't succeed, it means the job was already locked to be taken care
        of by another thread) and return.

        If a job was processed, returns True, otherwise returns False.
        """

        has_columns = False

        db = openerp.sql_db.db_connect(db_name)
        threading.current_thread().dbname = db_name
        cr = db.cursor()

        query = "SELECT column_name FROM information_schema.columns WHERE table_name LIKE 'ir_cron'"
        cr.execute(query, ())
        columns = []
        for data in cr.fetchall():
            if data[0] == 'last_run_date':
                has_columns = True

        jobs = []
        try:
            # Make sure the database we poll has the same version as the code of base
            cr.execute("SELECT 1 FROM ir_module_module WHERE name=%s AND latest_version=%s", ('base', BASE_VERSION))
            if cr.fetchone():
                # Careful to compare timestamps with 'UTC' - everything is UTC as of v6.1.
                cr.execute("""SELECT * FROM ir_cron
                              WHERE numbercall != 0
                                  AND active AND nextcall <= (now() at time zone 'UTC')
                              ORDER BY priority""")
                jobs = cr.dictfetchall()
            else:
                _logger.warning('Skipping database %s as its base version is not %s.', db_name, BASE_VERSION)
        except psycopg2.ProgrammingError, e:
            if e.pgcode == '42P01':
                # Class 42 — Syntax Error or Access Rule Violation; 42P01: undefined_table
                # The table ir_cron does not exist; this is probably not an OpenERP database.
                _logger.warning('Tried to poll an undefined table on database %s.', db_name)
            else:
                raise
        except Exception:
            _logger.warning('Exception in cron:', exc_info=True)
        finally:

            if has_columns:
                # clear error counter if last run went ok, we only want sequential failures
                try:
                    cr.execute(
                        "UPDATE ir_cron SET num_of_failed_runs = 0 WHERE last_run_date != last_failed_date and active = True;")
                    cr.commit()
                except:
                    cr.rollback()
                    pass

                # clear error counter every once in a while (24h), just to make sure
                try:
                    cr.execute(
                        """UPDATE ir_cron SET active = True, num_of_failed_runs = 0
                        where
                        last_run_date is not null
                        and now() - interval '24 hours' > last_run_date
                        and active = False
                        and num_of_failed_runs > 0;
                        """)
                    cr.commit()
                except:
                    cr.rollback()
                    pass

            cr.close()

        for job in jobs:
            lock_cr = db.cursor()
            now = datetime.now()
            try:
                try:
                    if 'num_of_failed_runs' in job.keys():
                        num_of_failed_runs = int(job['num_of_failed_runs'])
                        # if number of failed runs for current job is higher than 3, disable this job,
                        # obviously something went terribly wrong
                        if num_of_failed_runs > 6:
                            if not "provision" in job['name'].lower():
                                lock_cr.execute("UPDATE ir_cron SET active = False WHERE id=%s;", (job['id'],))
                                lock_cr.commit()

                                lock_cr.execute("""SELECT id, name, num_of_failed_runs,
                                                    active FROM ir_cron WHERE id=%s;""", (job['id'],))
                                res = lock_cr.fetchone()
                except:
                    lock_cr.rollback()
                    print "UPDATE FAILED!!"
                    pass

                # Try to grab an exclusive lock on the job row from within the task transaction
                # Restrict to the same conditions as for the search since the job may have already
                # been run by an other thread when cron is running in multi thread
                lock_cr.execute("""SELECT *
                                   FROM ir_cron
                                   WHERE numbercall != 0
                                      AND active
                                      AND nextcall <= (now() at time zone 'UTC')
                                      AND id=%s
                                   FOR UPDATE NOWAIT""",
                                (job['id'],), log_exceptions=False)

                locked_job = lock_cr.fetchone()
                if not locked_job:
                    _logger.debug("Job `%s` already executed by another process/thread. skipping it", job['name'])
                    continue
                # Got the lock on the job row, run its code
                _logger.debug('Starting job `%s`.', job['name'])
                job_cr = db.cursor()
                try:
                    if not cls._name:
                        cls._name = "ir.cron"
                    registry = openerp.registry(db_name)
                    if has_columns:
                        registry[cls._name]._process_job_now(job_cr, job, lock_cr, now)
                    else:
                        registry[cls._name]._process_job(job_cr, job, lock_cr)
                except Exception:
                    _logger.exception('Unexpected exception while processing cron job %r', job)
                    if 'num_of_failed_runs' in job.keys():
                        print 'num_of_failed_runs in job.keys()'
                        try:
                            lock_cr.execute("""UPDATE ir_cron SET num_of_failed_runs = num_of_failed_runs + 1,
                                                last_run_date=%s, last_failed_date = %s WHERE id=%s;""",
                                            (now, now, job['id'],))
                        except:
                            lock_cr.rollback()
                            pass
                finally:
                    job_cr.close()

            except psycopg2.OperationalError, e:
                if e.pgcode == '55P03':
                    # Class 55: Object not in prerequisite state; 55P03: lock_not_available
                    _logger.debug('Another process/thread is already busy executing job `%s`, skipping it.',
                                  job['name'])
                    continue
                else:
                    # Unexpected OperationalError
                    raise
            finally:
                # we're exiting due to an exception while acquiring the lock
                lock_cr.close()

        if hasattr(threading.current_thread(), 'dbname'):  # cron job could have removed it as side-effect
            del threading.current_thread().dbname


IrCron()

openerp.addons.base.ir.ir_cron.ir_cron._acquire_job = IrCron._acquire_job
openerp.addons.base.ir.ir_cron.ir_cron._process_job_now = IrCron._process_job_now
openerp.addons.base.ir.ir_cron.ir_cron._callback_now = IrCron._callback_now
openerp.addons.base.ir.ir_cron.ir_cron._handle_callback_exception = IrCron._handle_callback_exception
