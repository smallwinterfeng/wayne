#!/usr/local/python3.6.10/bin/python3.6

import os
from datetime import datetime,date,timedelta
import yaml
import re
import random
import copy
import optparse
import sys
import requests
import json

'''
使用python3.6解释器运行,安装pyinstaller进行二进制编译
'''

#请自行添加hostname绑定和添加公钥以便能正常拉去代码
_WECHAT_WEBHOOK = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=7dc28dba-2f87-447e-9931-b0930504b7af'
_CHECKOUT_PATH = '/home/optools' #代码检出目录
_OPTOOLS_REPO = 'http://szgitlab.youxin.com/deploy/optools.git' #optools代码地址
_CURRENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),'yaml')
_NAMESPACE_PREFIX = 'hq-system-'
_CHECKOUT_PATH_HOME='/home/optools/base'

#k8s Deployment模板
_DEPLOYMENT_TMP = """---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example
  namespace: hq-system
  labels:
    wayne-app: hq-system
    wayne-ns: hq-system
    app: SERVICE_NAME
spec:
  selector:
    matchLabels:
      app: SERVICE_NAME
  replicas: COUNT
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: SERVICE_NAME
        wayne-app: hq-system
        wayne-ns: hq-system
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/hostname
                operator: In
                values:
                - HOST_NAME
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 70
            preference:
              matchExpressions:
              - key: app_type
                operator: In
                values:
                - hq
          - weight: 30
            preference:
              matchExpressions:
              - key: share_type
                operator: In
                values:
                - dedicated
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - SERVICE_NAME
            topologyKey: "kubernetes.io/hostname"
      containers:
        - name: SERVICE_NAME
          image: IMAGE_NAME
          imagePullPolicy: IfNotPresent
          env:
          - name: JVM_MEM
            value: "6144m"
          - name: settings
            value: "xx"
          readinessProbe:
            tcpSocket:
              port: 8802
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            tcpSocket:
              port: 8802
            initialDelaySeconds: 30
            periodSeconds: 30
          volumeMounts:
            - mountPath: /opt/logs
              name: log-path
      volumes:
        - name: log-path
          hostPath:
            path: /opt/apps/logs/t2-server
"""

#k8s Deployment模板
_DEPLOYMENT_TMP_ICE = """---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example
  namespace: hq-system
  labels:
    wayne-app: hq-system
    wayne-ns: hq-system
    app: SERVICE_NAME
spec:
  selector:
    matchLabels:
      app: SERVICE_NAME
  replicas: COUNT
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: SERVICE_NAME
        wayne-app: hq-system
        wayne-ns: hq-system
    spec:
      hostNetwork: true
      hostIPC: true
      dnsPolicy: ClusterFirstWithHostNet
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/hostname
                operator: In
                values:
                - HOST_NAME
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 70
            preference:
              matchExpressions:
              - key: app_type
                operator: In
                values:
                - ice
          - weight: 30
            preference:
              matchExpressions:
              - key: share_type
                operator: In
                values:
                - dedicated
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - SERVICE_NAME
            topologyKey: "kubernetes.io/hostname"
      tolerations:
        - key: node_type
          operator: Equal
          value: dt
          effect: NoSchedule
      containers:
        - name: SERVICE_NAME
          image: IMAGE_NAME
          imagePullPolicy: IfNotPresent
          env:
          - name: JVM_MEM
            value: "6144m"
          - name: settings
            value: "xx"
          readinessProbe:
            tcpSocket:
              port: 8802
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            tcpSocket:
              port: 8802
            initialDelaySeconds: 30
            periodSeconds: 30
          volumeMounts:
            - mountPath: /opt/logs
              name: log-path
      volumes:
        - name: log-path
          hostPath:
            path: /opt/apps/logs/t2-server
"""

#k8s负载均衡模板
_SERVICE_TMP="""
apiVersion: v1
kind: Service
metadata:
  name: SERVICE_NAME
  namespace: hq-system
  labels:
    app: SERVICE_NAME
    wayne-app: hq-system
    wayne-ns: hq-system
    kubernetes.io/cluster-service: 'true'
  annotations:
    consul.hashicorp.com/service-name: SERVICE_NAME
    consul.hashicorp.com/service-port: 'SERVICE_PORT'
    consul.hashicorp.com/service-sync: "true"
    consul.hashicorp.com/service-tags: SERVICE_TAGS
spec:
  selector:
    app: SERVICE_NAME
  ports:
  - name: tcp_SERVICE_PORT
    port: SERVICE_PORT
    protocol: TCP
    targetPort: SERVICE_PORT
  - name: udp_SERVICE_PORT
    port: SERVICE_PORT
    protocol: UDP
    targetPort: SERVICE_PORT
"""

"""
清除拉取代码的历史数据
"""
def clean_history_data():
    global _CHECKOUT_PATH
    clean_day = date.today() - timedelta(days=2)
    clean_day = clean_day.strftime("%Y%m%d")
    _path = os.path.join(_CHECKOUT_PATH,clean_day)
    clean_cmd = 'rm -rf {0}*'.format(_path)
    os.system(clean_cmd)

clean_history_data()


def sub_tag_name(tag_name):
    if isinstance(tag_name,str):
      tag_name = tag_name.split('-')
      if len(tag_name) > 1:
        return '-'.join([tag_name[-2],tag_name[-1]]) if len(tag_name[-1]) <= 4 else tag_name[-1]
    return tag_name

#增量拉取optools代码
def checkout_to_tag_incre(tag_name):
    global _CHECKOUT_PATH_HOME, _OPTOOLS_REPO,_CHECKOUT_PATH
    create_time = datetime.strftime(datetime.now(),'%Y%m%d%H%M%S')
    code_dir = os.path.join(_CHECKOUT_PATH_HOME,"optools")
    code_dir_real = os.path.join(_CHECKOUT_PATH,create_time)
    code_dir_real = os.path.join(code_dir_real,'optools')
    if not os.path.exists(code_dir):
        os.system('/usr/bin/mkdir -p {0}'.format(code_dir))
    result = os.system('which git &>/dev/null')
    if result != 0:
        print(u"请先安装git工具")
        return False
    if not os.path.exists(code_dir+"/.gitignore"):
        result = os.system('cd {0} && git clone {1} &>/dev/null'.format(_CHECKOUT_PATH_HOME, _OPTOOLS_REPO))
    if result != 0 :
        print(u"下载optools代码失败,请检查是否添加公钥")
        return False
    #result = os.system('cd {0} && git checkout {1}'.format(code_dir,tag_name))
    result = os.system('cd {0} && git fetch --all &>/dev/null && git reset --hard origin/master &>/dev/null && echo "q"|git checkout {1} &>/dev/null'.format(code_dir,tag_name))
    if result != 0:
        print(u"checkout 代码失败,请确认tag是否存在")
        return False
    os.system("mkdir -p {2} && cp -a {0} {1}/".format(code_dir,code_dir_real,code_dir_real))
    return code_dir_real



#替换需要注册到consul服务的信息
def replace_service_port(service_yml_file, port):
    replace_str = 'consul.hashicorp.com/service-port: '+str(port)
    target_str = "consul.hashicorp.com/service-port: '"+str(port)+"'"
    cmd = ''' sed -i "s#{0}#{1}#g" {2} '''.format(replace_str,target_str,service_yml_file)
    os.system(cmd)


#解析optools的发布服务
def get_service_file(service_dir,service_name):
    file_list = os.listdir(service_dir)
    for fileName in file_list:
        if '.yml' in fileName or '.yaml' in fileName:
            with open(os.path.join(service_dir,fileName),'r') as f:
                data = yaml.load(f,Loader=yaml.FullLoader)
                if service_name in data:
                    return os.path.join(service_dir,fileName)
    return False

def check_file_exist(stack_file,var_file,dispatcher_file,service_file=None):
    if service_file:
        if isinstance(service_file, str):
            if not os.path.exists(service_file):
                return False
        if isinstance(service_file, list):
            for k in service_file:
                if not os.path.exists(k):
                    return False
    if os.path.exists(stack_file) and os.path.exists(var_file) and os.path.exists(dispatcher_file):
        return True
    return False




def get_service_by_stack(stack_file, stack_name,service_name=None):
    try:
        with open(stack_file, 'r') as f:
            data = yaml.load(f,Loader=yaml.FullLoader)
        service_list = None
        for stack in data:
            if stack_name == stack['name'].replace(' ',''):
                service_list = stack['service']
                if service_name:
                    for service_info in service_list:
                        if service_name.replace(' ','') == service_info['name'].replace(' ',''):
                            return [service_info]
                break
        return service_list
    except Exception as e:
        print(str(e))
        return False

def get_service_name(stack_file, stack_name,service_name=None):
    service_list = get_service_by_stack(stack_file,stack_name,service_name=service_name)
    if service_list:
        service_names = [[service['name'],service['repl']] for service in service_list]
    else:
        service_names = None
    return service_names


#解析optools 的service文件里面的变量
def parser_var_file(var_file):
    kv_store = dict()
    with open(var_file, 'r') as f:
        for line in f.readlines():
            if not line.startswith(r'#'):
                if  not re.search(r'^\s+#.*', line, re.M|re.I):
                    flag = 0
                    if '"' in line:
                        flag = 1
                        line = line.replace('\n','').split('"')
                    elif "'" in line:
                        flag = 1
                        line = line.replace('\n','').split("'")
                    else:
                        line = line.replace('\n','').split(':')
                    if len(line) > 1:
                        if  len(line[1].replace(' ',''))<1:
                            value = ''
                        else:
                            value = line[1].lstrip(' ').rstrip(' ')
                        try:
                            tmp_v = int(value)
                        except Exception as e:
                            flag = 0
                        value=[value,flag]
                        key = line[0].replace(':','').replace(' ','')
                        kv_store.update({key:value})
    return kv_store if kv_store != {} else None

#解析optools里面的发布机器
def parser_dispatcher_file(dispatcher_file, stack_name):
    if os.path.exists(dispatcher_file):
        try:
            with open(dispatcher_file,'r') as f:
                stack_list  = yaml.load(f,Loader=yaml.FullLoader)
                for stack_info in stack_list:
                    stack_name_list = stack_info.get('stack', None)
                    stack_node_list = stack_info.get('node', None)
                    if stack_name in stack_name_list:
                        return  stack_node_list
        except Exception as e:
            print(str(e))
    return False


#optools的service文件变量解析实现
def replace_service_var_by_python(service_files, data):
    if isinstance(service_files, str):
        service_files = [service_files]
    try:
        for service_file in service_files :
            for key in data.keys():
                result = os.system('grep "{0}" {1} &>/dev/null'.format(key,service_file))
                if result == 0:
                    value = data[key]
                    with open(service_file, 'r+',encoding='utf-8') as f:
                        all_lines = f.readlines()
                        f.seek(0)
                        f.truncate()
                        for line in all_lines:
                            if is_replace(line,key):
                                pass
                            else:
                                #line = line.replace("$"+key,value)
                                if value[1] == 0:
                                    line = line.replace("$"+key,value[0])
                                else:
                                    line = line.replace("$"+key,'"'+value[0]+'"')
                            f.write(line)
    except Exception as e:
        print(str(e))
        return False
    return True


def is_replace(line,key):
    re_compile_letter='\$'+key+'[A-Z]'
    re_compile_underline='\$'+key+'_'
    result_1 = re.search(re_compile_letter,line)
    result_2 = re.search(re_compile_underline,line)
    if result_1 or result_2:
        return True
    return False


#查询注册服务信息，若optools里面的docker file没有标明映射端口协议，则负载均衡默认解析为tcp端口
def find_service_info(port,env,protocol='tcp'):
    key_name = 'SERVICE_'+ port + '_NAME'
    key_tag = 'SERVICE_' + port + '_TAGS'
    service_name = None
    service_tag = None
    if key_name in env:
        service_name = env.get(key_name)
    else:
        return None
    if key_tag in env:
        service_tag = env.get(key_tag)
    return [service_name,service_tag,port,protocol]


#解析端口
def parser_ports(ports,env):
    register_service = list()
    for port in ports:
        port = str(port)
        port_list = port.split(':')
        protocol = 'tcp'
        if len(port_list) == 1:
            _p_info = port_list[0].split('/')
            _p = _p_info[0]
            if len(_p_info) > 1:
                protocol = _p_info[1].replace(' ','').lower()
            result = find_service_info(_p,env,protocol=protocol)
            if result:
                register_service.append(result)
        elif len(port_list) == 2:
            _s_p = port_list[0]
            _t_p_info = port_list[1].split('/')
            _t_p = _t_p_info[0]
            if len(_t_p_info) > 1:
                protocol = _t_p_info[1].replace(' ','').lower()
            result = find_service_info(_s_p,env,protocol=protocol)
            if result:
                register_service.append(result)
            result = find_service_info(_t_p,env,protocol=protocol)
            if result:
                register_service.append(result)
    return register_service



#解析optools的docker file文件
def dockerfile_parser(service_name,docker_file):
    register_service = list()
    hostpath_volumes = list()
    is_listen = False
    try:
        with open(docker_file, 'r') as f:
            data = yaml.load(f,Loader=yaml.FullLoader)
            service_data = data.get(service_name,None)
            if not service_data:
                return {}
            _image = service_data.get('image',None)
            _ports = service_data.get('ports',None)
            _volumes = service_data.get('volumes',None)
            _enviroment = service_data.get('environment',None)
            if _ports:
                register_service = parser_ports(_ports,_enviroment)
                is_listen = True
            if _volumes:
                for volume in _volumes:
                    volume = volume.split(':')
                    volume_name = service_name+'-'+str(random.randint(0,1000000000))
                    hostpath_volumes.append([volume_name,volume[0],volume[1]])
        return {'image_name': _image,
                'register_service': register_service,
                'register_volumes': hostpath_volumes,
                'enviroment': _enviroment,
                'is_listen': is_listen
               }
    except Exception as e:
        print(str(e))
    return {}


#将optools里面的映射文件转换成k8s的hostpath
def to_k8s_volumes_format(volumes):
    volume_mounts = list()
    k8s_volumes = list()
    for volume in volumes:
        volume_name = volume[0]
        host_path = volume[1]
        docker_path = volume[2]
        volume_mounts.append({'mountPath':docker_path,'name':volume_name})
        k8s_volumes.append({'name':volume_name,'hostPath':{'path':host_path}})
    return volume_mounts, k8s_volumes

#将optools里面的容器转换成k8s的pod
def to_k8s_containers_format(service_name,image_name,volume_mounts,env,port=None,replicas=0,protocol='tcp',is_listen=True):
    containers = list()
    env_list = list()
    for key,value in env.items():
        env_list.append({'name':key,'value':value})
    image_name = image_name.replace('registry.yxzq.com','hub.yxzq.com:5000')
    container = {
        'name': service_name,
        'image': image_name,
        'imagePullPolicy': 'IfNotPresent',
        'env': env_list,
        'readinessProbe':None,
        'livenessProbe': None,
        'volumeMounts': None,
    }
    container['volumeMounts'] = volume_mounts
    if port and protocol == 'tcp':
        readinessProbe={
            'tcpSocket': {'port': int(port)
                         },
            'initialDelaySeconds': 10,
            'periodSeconds': 10,
            'timeoutSeconds': 15,
            'failureThreshold': 3
        }
        livenessProbe={
            'tcpSocket':{
                'port': int(port)
            },
            'initialDelaySeconds': 30,
            'periodSeconds': 30,
            'timeoutSeconds': 15,
            'failureThreshold': 3
        }
        container['readinessProbe'] = readinessProbe
        container['livenessProbe'] = livenessProbe
        containers.append(container)
    else:
        container.pop('readinessProbe')
        container.pop('livenessProbe')
        if replicas >= 1:
            if is_listen:
                replicas = 1
            for num in range(0,int(replicas)):
                service_name = service_name+str(num)
                container['name'] = service_name
                containers.append(copy.deepcopy(container))
        else:
            containers.append({})
    return containers




#将optools服务转换成k8s的deployment
def docker_to_k8s(stack_name, service_name, service_file, dispatcher_node,tag_name,replicas=0,tmp_type='normal'):
    global _DEPLOYMENT_TMP,_SERVICE_TMP,_DEPLOYMENT_TMP_ICE
    result = {'deployment':{},
              'service':{},
              'image_list': []
             }
    docker_data = dockerfile_parser(service_name,service_file)
    image_name = docker_data['image_name']
    volumes = docker_data['register_volumes']
    register_service = docker_data['register_service']
    enviroment = docker_data['enviroment']
    is_listen = docker_data['is_listen']
    volume_mounts, k8s_volumes =  to_k8s_volumes_format(volumes)
    if not dispatcher_node:
        raise Exception('No node to dispatch. please check your dispatcher.yml format !')
    if len(register_service) < 1:
        result['deployment'] = render_k8s_deployment_template(_DEPLOYMENT_TMP_ICE if tmp_type == "ice" else _DEPLOYMENT_TMP,stack_name,service_name,image_name,enviroment,volume_mounts,k8s_volumes,dispatcher_node,tag_name,replicas=replicas,is_listen=is_listen)
    else:
        result['service'] = render_k8s_service_template(_SERVICE_TMP,register_service,service_name)
        result['deployment'] = render_k8s_deployment_template(_DEPLOYMENT_TMP_ICE if tmp_type == "ice" else _DEPLOYMENT_TMP,stack_name,service_name,image_name,enviroment,volume_mounts,k8s_volumes,dispatcher_node,tag_name,port=register_service[0][2],replicas=replicas,protocol=register_service[0][3])
    result['image_list'].append(image_name)
    return result


def render_k8s_deployment_template(template_name,stack_name,service_name,image_name,enviroment,volume_mounts,k8s_volumes,dispatcher_node,tag_name,port=None,replicas=0,protocol='tcp',is_listen=True):
    global _CURRENT_DIR,_NAMESPACE_PREFIX
    result = dict()
    try:
        rand_num = str(random.randint(0,9000000000000000))
        with open('/tmp/.deployment_{0}'.format(rand_num), 'w+') as f:
            f.write(template_name)
        with open('/tmp/.deployment_{0}'.format(rand_num), 'r') as f:
            data = yaml.load(f,Loader=yaml.FullLoader)
        data['spec']['replicas'] = len(dispatcher_node)
        #data['metadata']['name'] = _NAMESPACE_PREFIX+service_name
        data['metadata']['name'] = service_name+'-deployment'
        #data['metadata']['labels']['app'] = _NAMESPACE_PREFIX+service_name
        data['metadata']['labels']['app'] = service_name+'-deployment'
        data['metadata']['labels']['wayne-app'] = service_name
        #data['spec']['selector']['matchLabels']['app'] = _NAMESPACE_PREFIX+service_name
        data['spec']['selector']['matchLabels']['app'] = service_name+'-deployment'
        #data['spec']['template']['metadata']['labels']['app'] = _NAMESPACE_PREFIX+service_name
        data['spec']['template']['metadata']['labels']['app'] = service_name + '-deployment'
        data['spec']['template']['metadata']['labels']['wayne-app'] = service_name
        #data['spec']['template']['spec']['nodeSelector']['stack_name'] = stack_name
        data['spec']['template']['spec']['affinity']['nodeAffinity']['requiredDuringSchedulingIgnoredDuringExecution']['nodeSelectorTerms'][0]['matchExpressions'][0]['values'] = dispatcher_node
        if dispatcher_node:
            data['spec']['template']['spec']['affinity']['nodeAffinity']['requiredDuringSchedulingIgnoredDuringExecution']['nodeSelectorTerms'][0]['matchExpressions'][0]['values'] = dispatcher_node
        else:
            data['spec']['template']['spec']['affinity']['nodeAffinity']['requiredDuringSchedulingIgnoredDuringExecution']['nodeSelectorTerms'][0]['matchExpressions'][0]['values'] = ['No_Node']
        #data['spec']['template']['spec']['affinity']['podAntiAffinity']['requiredDuringSchedulingIgnoredDuringExecution'][0]['labelSelector']['matchExpressions'][0]['values'] = [_NAMESPACE_PREFIX+service_name]
        data['spec']['template']['spec']['affinity']['podAntiAffinity']['requiredDuringSchedulingIgnoredDuringExecution'][0]['labelSelector']['matchExpressions'][0]['values'] = [service_name+'-deployment']
        containers = to_k8s_containers_format(service_name,image_name,volume_mounts,enviroment,port=port,replicas=replicas,protocol=protocol,is_listen=is_listen)
        if not containers:
            return {service_name:None}
        data['spec']['template']['spec']['containers'] = containers
        data['spec']['template']['spec']['volumes'] = k8s_volumes
        data = is_random_schedule(dispatcher_node,data)
        output_file = os.path.join(_CURRENT_DIR,'{0}_deployment_{1}.yml'.format(service_name,sub_tag_name(tag_name)))
        with open(output_file,'w') as f:
            yaml.dump(data,f,default_flow_style=False)
        result.update({service_name:output_file})
    except Exception as e:
        print(str(e))
        result.update({service_name:None})
    return result


#判断是否为随机调度机器
def is_random_schedule(dispatcher,json_for_yaml):
    #optools里面的dispatcher.yaml文件，如果指定节点的名字为ALL-4，则所有行情节点都可调度且初始化为4台
    default_replicas = 3
    if isinstance(dispatcher,list) and len(dispatcher) == 1:
        dispatcher = dispatcher[0]
        if dispatcher.startswith('ALL'):
            split_data = dispatcher.split('-')
            replicas = 0
            if len(split_data) == 2:
                try:
                    replicas = int(split_data[1])
                except Exception as e:
                    replicas = default_replicas
            json_for_yaml['spec']['replicas'] = replicas
            json_for_yaml['spec']['template']['spec']['affinity']['nodeAffinity'].pop('requiredDuringSchedulingIgnoredDuringExecution')
            json_for_yaml['spec']['template']['spec']['affinity'].pop('podAntiAffinity')
    return json_for_yaml



def render_k8s_service_template(template_name,register_service,service_name):
    global _CURRENT_DIR,_NAMESPACE_PREFIX
    result = dict()
    for service in register_service:
        try:
            register_service_name = service[0]
            register_service_tags = service[1]
            register_service_port = int(service[2])
            register_service_protocol = service[3]
            rand_num = str(random.randint(0,9000000000000000))
            with open('/tmp/.service_{0}'.format(rand_num), 'w+') as f:
                f.write(template_name)
            with open('/tmp/.service_{0}'.format(rand_num), 'r') as f:
                data = yaml.load(f,Loader=yaml.FullLoader)
            #data['metadata']['name'] = _NAMESPACE_PREFIX+register_service_name
            data['metadata']['name'] = register_service_name
            #data['metadata']['labels']['app'] =  _NAMESPACE_PREFIX+service_name
            data['metadata']['labels']['app'] =  service_name+"-service"
            data['metadata']['annotations']['consul.hashicorp.com/service-name'] = register_service_name
            data['metadata']['annotations']['consul.hashicorp.com/service-port'] = register_service_port
            data['metadata']['annotations']['consul.hashicorp.com/service-tags'] = register_service_tags if register_service_tags else 'hq-service'
            #data['spec']['selector']['app'] = _NAMESPACE_PREFIX+service_name
            data['spec']['selector']['app'] = service_name+"-deployment"
            tcp_port = {'name':'tcp-{0}'.format(str(register_service_port)),
                        'port':register_service_port,
                        'protocol':'TCP',
                        'targetPort':register_service_port,
                       }
            udp_port = {'name':'udp-{0}'.format(str(register_service_port)),
                        'port':register_service_port,
                        'protocol':'UDP',
                        'targetPort':register_service_port,
                       }
            if register_service_protocol == 'tcp':
                data['spec']['ports'] = [tcp_port]
            else:
                data['spec']['ports'] = [udp_port]
            output_file = os.path.join(_CURRENT_DIR,'{0}_service_{1}.yml'.format(service_name,str(register_service_port)))
            with open(output_file,'w') as f:
                yaml.dump(data,f,default_flow_style=False)
            replace_service_port(output_file,register_service_port)
            result.update({register_service_name:output_file})
        except Exception as e:
            print(str(e))
            result.update({register_service_name:[]})
    return result




def get_stack_service(tag_name, project, stack_name, service_name=None,env='live-hk'):
    #code_dir = checkout_to_tag(tag_name)
    code_dir = checkout_to_tag_incre(tag_name)
    result = list()
    if code_dir:
        stack_dir = os.path.join(os.path.join(code_dir, 'optools/yx-deploy'), project)
        stack_file = os.path.join(stack_dir, 'stack.yml')
        service_dir = os.path.join(stack_dir, 'service')
        service_files = None
        service_names = get_service_name(stack_file,stack_name,service_name=service_name)
        if not service_names:
            print(u'找不到stack下对应的service,请检查stack路径和stack名是否正确!')
            return False
        if service_name:
            service_files = get_service_file(service_dir,service_name)
            service_data = [[service_name, service_files,service_names[0][1]]]
        else:
            service_files = [get_service_file(service_dir, service_name[0]) for service_name in service_names ]
            service_data = [[service_name[0],get_service_file(service_dir,service_name[0]),service_name[1]] for service_name in service_names ]
        var_file = os.path.join(os.path.join(stack_dir, 'config-'+env), 'var.yml')
        dispatcher_file = os.path.join(os.path.join(stack_dir, 'config-'+env), 'dispatcher.yml')
        if check_file_exist(stack_file, var_file,dispatcher_file,service_file=service_files):
            dispatcher_node = parser_dispatcher_file(dispatcher_file,stack_name)
            if replace_service_var_by_python(service_files, parser_var_file(var_file)):
                for service in service_data:
                    if service[0] in ['usicequoteforward-master', 'usicequoteforward-slave', 'usiceparser-master', 'usiceparser-slave']:
                        result.append(docker_to_k8s(stack_name,service[0],service[1],dispatcher_node,tag_name,replicas=service[2],tmp_type="ice"))
                    else:
                        result.append(docker_to_k8s(stack_name,service[0],service[1],dispatcher_node,tag_name,replicas=service[2]))
                return result
        else:
            print(u'检测文件失败,请确认stack目录,stack名是否正确')
    return result


#格式化输出结果
def format_output(result):
    service_list = list()
    send_service = list()
    if result:
        print('\n*******K8s Deployment YAML********\n')
        for project in result:
            deployment_info =  project['deployment']
            service_list.append(project['service'])
            for project_name,file_path in deployment_info.items():
                send_service.append(project_name)
                print(u"服务: {0} 生成文件: {1}".format(project_name,file_path))
        print('\n*******K8s Service YAML********\n#注意,如果wayne平台不存在service,需要手动将下列生成的service文件在wayne平台进行创建\n')
        for service in service_list:
            if service:
                for s_name,s_file in service.items():
                    if s_file:
                        print(u'服务: {0} 生成文件: {1}'.format(s_name,s_file))
                    else:
                        print(u'服务: {0} 生成失败,请检查配置是否正确'.format(s_name))
    return send_service


def main_api(tag_name,stack_dir,stack_name,service_name=None,env='live-hk'):
    result = list()
    try:
        result = get_stack_service(tag_name,stack_dir,stack_name,service_name=service_name)
    except Exception as e:
        print(str(e))
    return result

def main_cmd():
    parser_obj = optparse.OptionParser(usage="convert optools stack service project into k8s deployment and service yaml file.")
    parser_obj.add_option('-t','--tag',action='store',type='string',help='project tag (Must)',dest='tag')
    parser_obj.add_option('-d','--stack-dir',action='store',type='string',help='''optools stack file relative  path.
                          Example: /home/repo/optools/yx-deploy/quote-core/shcalc/stack.yml
                              The stack dir is : quote-core/shcalc (Must)
                          ''',dest='stack_dir')
    parser_obj.add_option('-s','--stack',action='store',type='string',help='optools stack name (Must)',dest='stack_name')
    parser_obj.add_option('-S','--service',action='store',type='string',help='optools service name (Optional)',dest='service_name')
    opt,args=parser_obj.parse_args()
    tag = opt.tag
    stack_dir = opt.stack_dir
    stack_name = opt.stack_name
    service_name = opt.service_name
    if not tag or not stack_dir or not stack_name:
        parser_obj.print_help()
    else:
        tag = tag.replace(' ','')
        stack_dir = stack_dir.replace(' ','')
        stack_name = stack_name.replace(' ','')
        if service_name:
            service_name = opt.service_name.replace(' ','')
            result = get_stack_service(tag,stack_dir,stack_name,service_name)
            if not isinstance(result,list):
                print(result)
                sys.exit(1)
            format_output(result)
        else:
            result = get_stack_service(tag,stack_dir,stack_name)
            if not isinstance(result,list):
                print(result)
                sys.exit(1)
            format_output(result)

if __name__ == '__main__':
    main_cmd()
