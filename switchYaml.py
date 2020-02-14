#coding:utf-8
from ruamel import yaml
import sys

def up_yml(service_name, file_name):
    with open('/root/k8s/yaml/'+file_name) as f:
        content = yaml.load(f, Loader=yaml.RoundTripLoader)
        content['metadata']['name'] =service_name+'-deployment'
        content['metadata']['labels']['app'] = service_name+'-deployment'
        content['metadata']['labels']['wayne-app'] = service_name
        content['spec']['selector']['matchLabels']['app'] = service_name+'-deployment'
        content['spec']['template']['metadata']['labels']['app'] = service_name+'-deployment'
        content['spec']['template']['metadata']['labels']['wayne-app'] = service_name
        content['spec']['template']['spec']['affinity']['podAntiAffinity']['requiredDuringSchedulingIgnoredDuringExecution'][0]['labelSelector']['matchExpressions'][0]['values'][0] = service_name+'-deployment' 
    with open('/root/k8s/yaml/'+file_name, 'w') as nf:
        yaml.dump(content, nf, Dumper=yaml.RoundTripDumper)

if __name__ == '__main__':
    service_name=sys.argv[1]
    file_name=sys.argv[2]
    if len(service_name) > 32:
        print "The name of service is too long!"
    else:
        up_yml(service_name, file_name)
