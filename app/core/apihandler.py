from flask import views, request, jsonify, make_response, session
from .basehandler import BaseHandler, AuthError, LogicError, ParamsError, Dict


class ApiHandler(views.View, BaseHandler):
    methods = frozenset(['get', 'post', 'head', 'options',
                         'delete', 'put', 'trace', 'patch'])

    def dispatch_request(self, *args, **kwargs):
        self.query_or_body = None
        self.request = request
        self.session = session
        self.set_header = {}
        self.set_cookie = {}
        self.delete_cookie = []

        # 反射获取请求处理函数
        handler = getattr(self, self.request.method.lower(), None)

        # 没有对应逻辑，返回405
        if not callable(handler):
            # head 处理方式
            if self.request.method == 'HEAD':
                return make_response('', 200)
            # 405
            return make_response('<h1>METHOD {0} NOT ALLOWED</h1>'.format(self.request.method), 405)

        return self.api_wrapper(handler, *args, **kwargs)

    def api_wrapper(self, handler, *args, **kwargs):

        self.http_origin = self.request.environ.get('HTTP_ORIGIN', '')

        code = 1000
        data = msg = None
        start_time = self.get_timestamp()
        try:
            data = handler(*args, **kwargs)
        except AuthError as e:
            code = e.code
            msg = str(e)
        except LogicError as e:
            code = e.code
            msg = str(e)
        except ParamsError as e:
            code = e.code
            msg = str(e)
        cost_time = self.get_timestamp() - start_time

        res = {'code': code, 'data': data, 'cost': "{0}ms".format(round(cost_time * 1000, 2))}
        if msg:
            res.update({'msg': msg})

        response = make_response(jsonify(res))

        # 隐藏 服务器信息
        response.headers['Server'] = 'Tengine'

        if self.set_header:
            for k, v in self.set_header.items():
                response.headers[k] = v

        if self.set_cookie:
            for k, v in self.set_cookie.items():
                response.set_cookie(k, v)

        if self.delete_cookie:
            for k in self.delete_cookie:
                response.delete_cookie(k)

        return response

    @property
    def all_query(self):
        d = Dict(self.request.args.items())
        d.update(self.request.json or {})
        d.update(self.request.form.items())
        d.update(self.request.files.items())
        return d

    # 通过 self.input.id 获取id参数
    @property
    def input(self):
        if self.query_or_body is None:
            self.query_or_body = self.all_query
        return self.query_or_body

