# -*- coding: utf-8 -*-

import httplib
import logging
import StringIO
import urllib
import openerp

_logger = logging.getLogger(__name__)
import sys

_logger.setLevel(logging.INFO)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
_logger.addHandler(ch)

def http_to_wsgi(http_dir):
    """
    Turn a BaseHTTPRequestHandler into a WSGI entry point.
    Actually the argument is not a bare BaseHTTPRequestHandler but is wrapped
    (as a class, so it needs to be instanciated) in a HTTPDir.
    This code is adapted from wbsrv_lib.MultiHTTPHandler._handle_one_foreign().
    It is a temporary solution: the HTTP sub-handlers (in particular the
    document_webdav addon) have to be WSGIfied.
    """
    def wsgi_handler(environ, start_response):

        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                key = key[5:].replace('_', '-').title()
                headers[key] = value
            if key == 'CONTENT_LENGTH':
                key = key.replace('_', '-').title()
                headers[key] = value
        if environ.get('Content-Type'):
            headers['Content-Type'] = environ['Content-Type']

        # if environ['REQUEST_METHOD'] == 'GET':
        #     headers['Content-Disposition'] = 'Attachment'

        path = urllib.quote(environ.get('PATH_INFO', ''))
        if environ.get('QUERY_STRING'):
            path += '?' + environ['QUERY_STRING']

        request_version = 'HTTP/1.1' # TODO
        request_line = "%s %s %s\n" % (environ['REQUEST_METHOD'], path, request_version)

        class Dummy(object):
            pass

        # Let's pretend we have a server to hand to the handler.
        server = Dummy()
        server.server_name = environ['SERVER_NAME']
        server.server_port = int(environ['SERVER_PORT'])

        # Initialize the underlying handler and associated auth. provider.
        con = openerp.service.websrv_lib.noconnection(environ['wsgi.input'])
        handler = http_dir.instanciate_handler(con, environ['REMOTE_ADDR'], server)

        # Populate the handler as if it is called by a regular HTTP server
        # and the request is already parsed.
        handler.wfile = StringIO.StringIO()
        handler.rfile = environ['wsgi.input']
        handler.headers = headers
        handler.command = environ['REQUEST_METHOD']
        handler.path = path
        handler.request_version = request_version
        handler.close_connection = 0
        handler.raw_requestline = request_line
        handler.requestline = request_line

        options_200 = []
        options_401 = []
        options_xxx = []

        options_xxx += [('Pragma', 'no-cache')]
        options_200 += [('X-dmUser', 'username')]
        options_200 += [('x-responding-server', 'server')]
        options_200 += [('DAV', '1,2, access-control, <http://apache.org/dav/propset/fs/1>')]
        options_200 += [('Access-Control-Allow-Headers', 'authorization,content-type')]
        options_200 += [('Access-Control-Allow-Credentials', 'true')]
        options_200 += [('Access-Control-Allow-Methods',
                         'GET,POST,OPTIONS,PUT,PROPFIND,DELETE,MKCOL,MOVE,COPY,HEAD,PROPPATCH,LOCK,UNLOCK')]

        options_200 += [('MS-Author-Via', 'DAV')]
        options_200 += [
            ('Allow:', 'GET, HEAD, OPTIONS, PUT, POST, COPY, PROPFIND, PROPPATCH, DELETE, LOCK, MKCOL, MOVE, UNLOCK')]

        # options_401 += [('MS-Author-Via', 'DAV')]
        # options_401 += [('Allow:', 'GET, HEAD, OPTIONS, PUT, POST, COPY, PROPFIND, DELETE, LOCK, MKCOL, MOVE, UNLOCK')]
        # options_200 += [('Access-Control-Allow-Methods',
        #                  'GET,POST,OPTIONS,PUT,PROPFIND,DELETE,MKCOL,MOVE,COPY,HEAD,LOCK,UNLOCK')]
        # options_200 += [('Access-Control-Allow-Credentials', 'true')]
        # options_200 += [('Access-Control-Allow-Headers', 'authorization,content-type')]
        # options_200 += [('Set-Cookie', 'testCookie=true')]
        options_200 += [('Content-Type', 'text/html')]
        options_200 += [('Connection', 'keep-alive')]

        options_401 += [('Connection', 'close')]
        options_401 += [('Content-Type', 'text/html')]
        options_401 += [('MS-Author-Via', 'DAV')]
        options_401 += [('WWW-Authenticate', 'Basic realm="Login Required"')]
        # options_200 += [('WWW-Authenticate', 'Basic realm="Login Required"')]

        # Handle authentication if there is an auth. provider associated to
        # the handler.
        if hasattr(handler, 'auth_provider'):
            try:
                handler.auth_provider.checkRequest(handler, path)
            except openerp.service.websrv_lib.AuthRequiredExc, ae:

                # Darwin 9.x.x webdav clients will report "HTTP/1.0" to us, while they support (and need) the
                # authorisation features of HTTP/1.1 
                if request_version != 'HTTP/1.1' and ('Darwin/9.' not in handler.headers.get('User-Agent', '')):
                    start_response("403 Forbidden", [] + options_xxx)
                    return []
                if environ['REQUEST_METHOD'] == "OPTIONS":
                    start_response("200 OK", [
                        ('Content-Length', 0),  # len(self.auth_required_msg)
                    ] + options_xxx + options_200)
                    return []
                elif environ['REQUEST_METHOD'] == "PROPFIND":
                    start_response("401 Unauthorized", [
                        # ('WWW-Authenticate', '%s realm="%s"' % (ae.atype, ae.realm)),
                        ('Content-Length', 12),  # len(self.auth_required_msg)
                    ] + options_xxx + options_401)
                    handler.close_connection = 1
                    return ['Unauthorized']  # self.auth_required_msg
                elif environ['REQUEST_METHOD'] == "HEAD":
                    start_response("401 Unauthorized", [
                        # ('WWW-Authenticate', '%s realm="%s"' % (ae.atype, ae.realm)),
                        ('Content-Length', 12),  # len(self.auth_required_msg)
                    ] + options_xxx + options_401)
                    handler.close_connection = 1
                    return ['Unauthorized']  # self.auth_required_msg
                else:
                    start_response("401 Unauthorized", [
                        # ('WWW-Authenticate', '%s realm="%s"' % (ae.atype,ae.realm)),
                        ('Content-Length', 12),  # len(self.auth_required_msg)
                    ] + options_xxx + options_401)
                    handler.close_connection = 1
                return ['Unauthorized']  # self.auth_required_msg
            except openerp.service.websrv_lib.AuthRejectedExc, e:
                start_response("403 %s" % (e.args[0],), [] + options_xxx)
                handler.close_connection = 1
                return []

        method_name = 'do_' + handler.command

        # Support the OPTIONS method even when not provided directly by the
        # handler. TODO I would prefer to remove it and fix the handler if
        # needed.
        if not hasattr(handler, method_name):
            if handler.command == 'OPTIONS':
                return return_options(environ, start_response)
            start_response("501 Unsupported method (%r)" % handler.command, [] + options_xxx)
            return []

        # Finally, call the handler's method.
        try:
            method = getattr(handler, method_name)
            method()
            # The DAV handler buffers its output and provides a _flush()
            # method.
            getattr(handler, '_flush', lambda: None)()
            response = parse_http_response(handler.wfile.getvalue())
            response_headers = response.getheaders()

            # try to get auth from cookie
            found = False
            cookiez = handler.headers.get('Cookie', '')  # response_headers
            cookies = cookiez.split(";")
            # if environ.get('Content-Type'):
            for ck in cookies:
                if ck.strip().startswith("odoo_auth"):
                    cv = ck.strip().replace("odoo_auth=", "")
                    auth_str = cv
                    found = True

            if not found:
                c = handler.headers.get('Authorization', '')
                response_headers += [('Set-Cookie', 'odoo_auth='+c)]

            body = response.read()
            start_response(str(response.status) + ' ' + response.reason, response_headers)
            return [body]
        except (openerp.service.websrv_lib.AuthRejectedExc, openerp.service.websrv_lib.AuthRequiredExc):
            raise
        except Exception, e:
            print e
            start_response("500 Internal error", [] + options_xxx)
            return []

    return wsgi_handler

def parse_http_response(s):
    """ Turn a HTTP response string into a httplib.HTTPResponse object."""
    class DummySocket(StringIO.StringIO):
        """
        This is used to provide a StringIO to httplib.HTTPResponse
        which, instead of taking a file object, expects a socket and
        uses its makefile() method.
        """
        def makefile(self, *args, **kw):
            return self
    response = httplib.HTTPResponse(DummySocket(s))
    response.begin()
    return response

def return_options(environ, start_response):
    # Microsoft specific header, see
    # http://www.ibm.com/developerworks/rational/library/2089.html
    # if 'Microsoft' in environ.get('User-Agent', ''):
    #     options = [('MS-Author-Via', 'DAV')]
    # else:
    #     options = []
    # options += [('DAV', '1,2, access-control, <http://apache.org/dav/propset/fs/1>'), ('Allow', 'GET HEAD PROPFIND POST PUT OPTIONS REPORT MKCOL LOCK UNLOCK')]
    # options += [('MS-Author-Via', 'DAV')]
    # options += [('Access-Control-Allow-Headers', 'authorization,content-type')]
    # options += [('Access-Control-Allow-Credentials', 'true')]
    # options += [('Access-Control-Allow-Methods', 'GET,POST,OPTIONS,PUT,PROPFIND,DELETE,MKCOL,MOVE,COPY,HEAD,PROPPATCH,LOCK,UNLOCK')]
    options = []

    # options += [('Set-Cookie', 'testCookie=true')]
    options += [('Pragma', 'no-cache')]
    options += [('X-dmUser', 'username')]
    options += [('x-responding-server', 'server')]
    options += [('DAV', '1,2, access-control, <http://apache.org/dav/propset/fs/1>')]
    options += [('Access-Control-Allow-Headers', 'authorization,content-type')]
    options += [('Access-Control-Allow-Credentials', 'true')]
    options += [('Access-Control-Allow-Methods',
                 'GET,POST,OPTIONS,PUT,PROPFIND,DELETE,MKCOL,MOVE,COPY,HEAD,PROPPATCH,LOCK,UNLOCK')]

    options += [('MS-Author-Via', 'DAV')]
    options += [
        ('Allow:', 'GET, HEAD, OPTIONS, PUT, POST, COPY, PROPFIND, PROPPATCH, DELETE, LOCK, MKCOL, MOVE, UNLOCK')]

    # options_401 += [('MS-Author-Via', 'DAV')]
    # options_401 += [('Allow:', 'GET, HEAD, OPTIONS, PUT, POST, COPY, PROPFIND, DELETE, LOCK, MKCOL, MOVE, UNLOCK')]
    # options_200 += [('Access-Control-Allow-Methods',
    #                  'GET,POST,OPTIONS,PUT,PROPFIND,DELETE,MKCOL,MOVE,COPY,HEAD,LOCK,UNLOCK')]
    # options_200 += [('Access-Control-Allow-Credentials', 'true')]
    # options_200 += [('Access-Control-Allow-Headers', 'authorization,content-type')]
    options += [('Content-Type', 'text/html')]
    options += [('Connection', 'keep-alive')]

    start_response("200 OK", [('Content-Length', str(0))] + options)
    return []


def return_options_root(environ, start_response):
    # Microsoft specific header, see
    # http://www.ibm.com/developerworks/rational/library/2089.html
    if 'Microsoft' in environ.get('User-Agent', ''):
        options = [('MS-Author-Via', 'DAV')]
    else:
        options = []
    options += [('DAV', '1,2, access-control, <http://apache.org/dav/propset/fs/1>'),
                ('Allow', 'GET HEAD POST PUT OPTIONS REPORT MKCOL LOCK UNLOCK')]
    options += [('MS-Author-Via', 'DAV')]
    options += [('Access-Control-Allow-Headers', 'authorization,content-type')]
    options += [('Access-Control-Allow-Credentials', 'true')]
    options += [
        ('Access-Control-Allow-Methods', 'GET,POST,OPTIONS,PUT,DELETE,MKCOL,MOVE,COPY,HEAD,PROPPATCH,LOCK,UNLOCK')]
    start_response("200 OK", [('Content-Length', str(0))] + options)
    return []

def wsgi_webdav(environ, start_response):
    pi = environ['PATH_INFO']
    if environ['REQUEST_METHOD'] == 'PROPFIND' and pi in ['*', '/']:
        # start_response("401 Unauthorized", [('Content-Length', str(0)), ('WWW-Authenticate', 'Basic realm="OpenERP User"'), ('Connection', 'keep-alive')])
        # start_response("404", [('Content-Length', str(0)), ('WWW-Authenticate', 'Basic realm="OpenERP User"'), ('Connection', 'close')])
        # start_response("404", [('Content-Length', str(0)), ('WWW-Authenticate', 'Basic realm="OpenERP User"'), ('Connection', 'close')])
        # return []
        environ['PATH_INFO'] = '/webdav/'
        pi = '/webdav/'
        http_dir = openerp.service.websrv_lib.find_http_service(pi)
        if http_dir:
            path = pi[len(http_dir.path):]
            if path.startswith('/'):
                environ['PATH_INFO'] = path
            else:
                environ['PATH_INFO'] = '/' + path
            return http_to_wsgi(http_dir)(environ, start_response)

    elif environ['REQUEST_METHOD'] == 'OPTIONS':
        # if pi in ['*', '/']:
        #     return return_options_root(environ, start_response)
        # else:
        return return_options(environ, start_response)
    elif pi.startswith('/webdav'):
        http_dir = openerp.service.websrv_lib.find_http_service(pi)
        if http_dir:
            path = pi[len(http_dir.path):]
            if path.startswith('/'):
                environ['PATH_INFO'] = path
            else:
                environ['PATH_INFO'] = '/' + path

            return http_to_wsgi(http_dir)(environ, start_response)
    return None

openerp.service.wsgi_server.module_handlers.insert(0, wsgi_webdav)
# openerp.service.wsgi_server.register_wsgi_handler(wsgi_webdav)

