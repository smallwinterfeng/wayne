#!/usr/local/python3.6.10/bin/python3
import tornado.web
import tornado.ioloop
from tornado.httpclient import HTTPRequest
import json
import base64
import subprocess
import os
_CONVERT_TOOL = '/root/k8s/optools_to_k8s'
_CONVERT_TOOL_TEST = '/root/test/optools_to_k8s'
_DIAMOND_TOOL = '/root/k8s/diamond_to_k8s'
_TOKEN_KEY = 'api:foB9ROmprZ6V0WdlHY9L'


class OpenApiOptoolToK8sHandler(tornado.web.RequestHandler):
    def initialize(self):
        global _CONVERT_TOOL,_TOKEN_KEY,_CONVERT_TOOL_TEST
        self.tool = _CONVERT_TOOL
        self.key = _TOKEN_KEY
        self.test_tool = _CONVERT_TOOL_TEST
        self.result = {'code':None,'message':None}

    def get(self):
        tag_name = self.get_argument('tagName',None)
        token = self.get_argument('token',None)
        stack_name = self.get_argument('stackName',None)
        stack_dir = self.get_argument('stackDir',None)
        service_name = self.get_argument('serviceName',None)
        action = self.get_argument('action',None)
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        if not authorization(token):
            self.result['message'] = 'Authorization Failed'
            self.result['code'] = 401
            self.write(json.dumps(self.result))
        elif not stack_name or not tag_name or not stack_dir:
            self.result['message'] = u'缺少必须参数'
            self.result['code'] = 401
            self.write(json.dumps(self.result,ensure_ascii=False))
        else:
            self.run_convert_tool(tag_name,stack_dir,stack_name,serviceName=service_name,action=action)

    def post(self):
        message = None
        json_data = self.request.body.decode('utf-8')
        try:
            json_data = json.loads(json_data)
        except Exception as e:
            message = u'提交的json数据格式有误'
            json_data = dict()
        tag_name = json_data.get('tagName',None)
        token = json_data.get('token',None)
        stack_name = json_data.get('stackName',None)
        stack_dir = json_data.get('stackDir',None)
        service_name = json_data.get('serviceName',None)
        action = json_data.get('action',None)
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        if message:
            self.result['message'] = message
            self.result['code'] = 403
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
            self.write(json.dumps(self.result))
        elif not authorization(token):
            self.result['message'] = 'Authorization Failed'
            self.result['code'] = 403
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
            self.write(json.dumps(self.result,ensure_ascii=False))
        elif not stack_name or not tag_name or not stack_dir:
            self.result['message'] = u'缺少必须参数'
            self.result['code'] = 401
            self.write(json.dumps(self.result,ensure_ascii=False))
        else:
            self.run_convert_tool(tag_name,stack_dir,stack_name,serviceName=service_name,action=action)

    def run_convert_tool(self,tagName,stackDir,stackName,serviceName=None,action='prod'):
        tool = None
        if not action:
            tool = self.tool
        else:
            tool = self.test_tool
        path = self.get_output_dir(tool)
        if serviceName:
            cmd = 'cd {5} && {0} -t {1} -d {2} -s {3} -S {4}'.format(tool,tagName,stackDir,stackName,serviceName,path)
        else:
            cmd = 'cd {4} && {0} -t {1} -d {2} -s {3}'.format(tool,tagName,stackDir,stackName,path)
        result,output = subprocess.getstatusoutput(cmd)
        self.result['message'] =[line for line in filter(lambda line: line != "", output.split('\n'))]
        self.result['code'] = 200
        self.write(json.dumps(self.result,ensure_ascii=False))

    def get_output_dir(self,tool):
        path = os.path.dirname(tool)
        return path






class OpenApiDiamondToK8sHandler(tornado.web.RequestHandler):
    def initialize(self):
        global _CONVERT_TOOL,_TOKEN_KEY,_CONVERT_TOOL_TEST
        self.tool = _DIAMOND_TOOL
        self.result = {'code':None,'message':None}

    def get(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        if True:
            self.result['message'] = 'Authorization Failed. Only Post Method is support'
            self.result['code'] = 403
            self.write(json.dumps(self.result))

    def post(self):
        message = None
        json_data = self.request.body.decode('utf-8')
        try:
            json_data = json.loads(json_data)
        except Exception as e:
            message = u'提交的json数据格式有误'
            json_data = dict()
        token = json_data.get('token',None)
        service_name = json_data.get('serviceName',None)
        name_space = json_data.get('nameSpace',None)
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        if message:
            self.result['message'] = message
            self.result['code'] = 401
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
            self.write(json.dumps(self.result))
        elif not authorization(token):
            self.result['message'] = 'Authorization Failed'
            self.result['code'] = 403
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
            self.write(json.dumps(self.result,ensure_ascii=False))
        elif not service_name:
            self.result['message'] = u'缺少必须参数'
            self.result['code'] = 401
            self.write(json.dumps(self.result,ensure_ascii=False))
        else:
            self.run_convert_tool(service_name,name_space)

    def run_convert_tool(self,serviceName,nameSpace):
        tool = self.tool
        path = self.get_output_dir(tool)
        if serviceName and nameSpace:
            cmd = 'cd {0} && {1} -s {2} -n {3}'.format(path,tool,serviceName,nameSpace)
        else:
            cmd = 'cd {0} && {1} -s {2} '.format(path,tool,serviceName)
        result,output = subprocess.getstatusoutput(cmd)
        self.result['message'] =[line for line in filter(lambda line: line != "", output.split('\n'))]
        self.result['code'] = 200
        self.write(json.dumps(self.result,ensure_ascii=False))

    def get_output_dir(self,tool):
        path = os.path.dirname(tool)
        return path






def authorization(token):
    global _TOKEN_KEY
    _key = _TOKEN_KEY
    try:
        key = str(base64.b64decode(token),'utf-8').replace('\n','')
        if key == _key:
            return True
    except Exception as e:
        print(str(e))
        pass
    return False


routes = [
        (r'/api/convert/v1',OpenApiOptoolToK8sHandler), #兼容旧接口
        (r'/api/optool2k8s/v1',OpenApiOptoolToK8sHandler),
        (r'/api/diamond2k8s/v1',OpenApiDiamondToK8sHandler),
        ]
application = tornado.web.Application(routes)
application.listen(8888)
tornado.ioloop.IOLoop.current().start()
