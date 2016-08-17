# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

__author__ = 'ivica'

import logging
import os
import pprint
import time
import simplejson
import werkzeug.contrib.sessions
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.wrappers
import werkzeug.wsgi

try:
    import psutil
except ImportError:
    psutil = None

import openerp
from openerp.service.server import memory_info
from openerp.http import WebRequest
from openerp.http import Response, AuthenticationError, SessionExpiredException, serialize_exception, HttpRequest, \
    JsonRequest

_logger = logging.getLogger(__name__)
rpc_request = logging.getLogger(__name__ + '.rpc.request')
rpc_response = logging.getLogger(__name__ + '.rpc.response')

import openerp.http


def _get_request(self, httprequest):

    if httprequest.path.startswith('/raw_json/'):
        return JsonRawRequest(httprequest)
    # deduce type of request
    if httprequest.args.get('jsonp'):
        return JsonRequest(httprequest)
    if httprequest.mimetype in ("application/json", "application/json-rpc"):
        return JsonRequest(httprequest)
    else:
        return HttpRequest(httprequest)

        # monkey patch get_request method to include new json object
openerp.http.Root.get_request = _get_request

# openerp.http.Root = NewRoot()


class JsonRawRequest(WebRequest):
    """ Request handler for `JSON-RPC 2
    <http://www.jsonrpc.org/specification>`_ over HTTP

    * ``method`` is ignored
    * ``params`` must be a JSON object (not an array) and is passed as keyword
      arguments to the handler method
    * the handler method's result is returned as JSON-RPC ``result`` and
      wrapped in the `JSON-RPC Response
      <http://www.jsonrpc.org/specification#response_object>`_

    Sucessful request::

      --> {"jsonrpc": "2.0",
           "method": "call",
           "params": {"context": {},
                      "arg1": "val1" },
           "id": null}

      <-- {"jsonrpc": "2.0",
           "result": { "res1": "val1" },
           "id": null}

    Request producing a error::

      --> {"jsonrpc": "2.0",
           "method": "call",
           "params": {"context": {},
                      "arg1": "val1" },
           "id": null}

      <-- {"jsonrpc": "2.0",
           "error": {"code": 1,
                     "message": "End user error message.",
                     "data": {"code": "codestring",
                              "debug": "traceback" } },
           "id": null}

    """
    _request_type = "json"

    def __init__(self, *args):
        super(JsonRawRequest, self).__init__(*args)

        self.jsonp_handler = None

        args = self.httprequest.args
        jsonp = args.get('jsonp')
        self.jsonp = jsonp
        request = None
        request_id = args.get('id')

        if jsonp and self.httprequest.method == 'POST':
            # jsonp 2 steps step1 POST: save call
            def handler():
                self.session['jsonp_request_%s' %
                             (request_id,)] = self.httprequest.form['r']
                self.session.modified = True
                headers = [('Content-Type', 'text/plain; charset=utf-8')]
                r = werkzeug.wrappers.Response(request_id, headers=headers)
                return r

            self.jsonp_handler = handler
            return
        elif jsonp and args.get('r'):
            # jsonp method GET
            request = args.get('r')
        elif jsonp and request_id:
            # jsonp 2 steps step2 GET: run and return result
            request = self.session.pop(
                'jsonp_request_%s' % (request_id,), '{}')
        else:
            # regular jsonrpc2
            request = self.httprequest.stream.read()

        # Read POST content or POST Form Data named "request"
        try:
            self.JsonRawRequest = simplejson.loads(request)
        except simplejson.JSONDecodeError:
            msg = 'Invalid JSON data: %r' % (request,)
            _logger.error('%s: %s', self.httprequest.path, msg)
            raise werkzeug.exceptions.BadRequest(msg)

        self.params = dict(self.JsonRawRequest.get("params", {}))
        self.context = self.params.pop('context', dict(self.session.context))

    def _json_response(self, result=None, error=None):
        response = {
        }
        if error is not None:
            response['error'] = error
        if result is not None:
            response = result

        if self.jsonp:
            # If we use jsonp, that's mean we are called from another host
            # Some browser (IE and Safari) do no allow third party cookies
            # We need then to manage http sessions manually.
            response['session_id'] = self.session_id
            mime = 'application/javascript'
            body = "%s(%s);" % (self.jsonp, simplejson.dumps(response),)
        else:
            mime = 'application/json'
            body = simplejson.dumps(response)

        return Response(
            body, headers=[('Content-Type', mime),
                           ('Content-Length', len(body))])

    def _handle_exception(self, exception):
        """Called within an except block to allow converting exceptions
           to arbitrary responses. Anything returned (except None) will
           be used as response."""
        try:
            return super(JsonRawRequest, self)._handle_exception(exception)
        except Exception:
            if not isinstance(exception, (openerp.exceptions.Warning, SessionExpiredException)):
                _logger.exception("Exception during JSON request handling.")
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': serialize_exception(exception)
            }
            if isinstance(exception, AuthenticationError):
                error['code'] = 100
                error['message'] = "Odoo Session Invalid"
            if isinstance(exception, SessionExpiredException):
                error['code'] = 100
                error['message'] = "Odoo Session Expired"
            return self._json_response(error=error)

    def dispatch(self):
        if self.jsonp_handler:
            return self.jsonp_handler()
        try:
            rpc_request_flag = rpc_request.isEnabledFor(logging.DEBUG)
            rpc_response_flag = rpc_response.isEnabledFor(logging.DEBUG)
            if rpc_request_flag or rpc_response_flag:
                endpoint = self.endpoint.method.__name__
                model = self.params.get('model')
                method = self.params.get('method')
                args = self.params.get('args', [])

                start_time = time.time()
                _, start_vms = 0, 0
                if psutil:
                    _, start_vms = memory_info(psutil.Process(os.getpid()))
                if rpc_request and rpc_response_flag:
                    rpc_request.debug('%s: %s %s, %s',
                                      endpoint, model, method, pprint.pformat(args))

            result = self._call_function(**self.params)

            if rpc_request_flag or rpc_response_flag:
                end_time = time.time()
                _, end_vms = 0, 0
                if psutil:
                    _, end_vms = memory_info(psutil.Process(os.getpid()))
                logline = '%s: %s %s: time:%.3fs mem: %sk -> %sk (diff: %sk)' % (
                    endpoint, model, method, end_time - start_time, start_vms / 1024, end_vms / 1024,
                    (end_vms - start_vms) / 1024)
                if rpc_response_flag:
                    rpc_response.debug('%s, %s', logline,
                                       pprint.pformat(result))
                else:
                    rpc_request.debug(logline)

            return self._json_response(result)
        except Exception, e:
            return self._handle_exception(e)

            #root = NewRoot()
            # openerp.service.wsgi_server.register_wsgi_handler(root)
