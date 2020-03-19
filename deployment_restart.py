#!/bin/python
#coding=utf-8
import httplib, urllib
import MySQLdb

def restart_deployment(deployment):
    #定义一些文件头
    headers = {'accept':'application/json'}
    #请求服务,例如：www.baidu.com
    hostServer="10.210.110.224:8080"
    #接口
    requrl ="/openapi/v1/gateway/action/restart_deployment?deployment="+deployment+"&namespace=hq-namespace&cluster=yxops-test-k8s&apikey=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOjEwLCJleHAiOjE1ODQ0MzY5MjIsImlhdCI6MTU4NDQzNjkyMiwiaXNzIjoid2F5bmUifQ.NIWkkznWlxY8zgCA0am25VoXXCQHznVd7LlpIVX9utkaJFnEKi_6OMkWIIcwCjRKFx7WHVy1b_mZwfpxLZJecA"
    #连接服务器       
    conn = httplib.HTTPConnection(hostServer)
    #发送请求       
    conn.request(method="GET",url=requrl,headers=headers)
    #获取请求响应       
    response=conn.getresponse()
    #打印请求状态
    if response.status in range(200,300):
        body = response.read()
        print deployment+": "+body
        pass

def query_deployment():
    # 打开数据库连接
    db = MySQLdb.connect("10.210.110.221", "test", "test123", "wayne", charset='utf8' )
    # 使用cursor()方法获取操作游标 
    cursor = db.cursor()
    # 使用execute方法执行SQL语句
    cursor.execute("select name from wayne.deployment")
    # 使用 fetchone() 方法获取一条数据
    data = cursor.fetchall()

    #循环遍历
    deployment_list=[]
    for i in range(len(data)):
        deployment_list.append(data[i][0])
    #列表过滤
    deployment_list.remove('statmonitor-deployment')
    for deployment in deployment_list:
        restart_deployment(deployment)
    # 关闭数据库连接
    db.close()

if __name__ == '__main__':
    query_deployment()
