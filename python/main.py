import boto3
import paramiko
import os
import subprocess
from configure import *
from stack import *
from keypair import *
from ami import *



if __name__ == '__main__':

    client = boto3.client("ec2")
    cloudformation = boto3.client("cloudformation")
    autoscaling  = boto3.client('autoscaling')
    ec2 = boto3.resource("ec2")
    ssh_client=paramiko.SSHClient()
    key = paramiko.RSAKey.from_private_key_file(r"/data/key/project-key.pem") # Set Private key
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Auto add instances to known hosts
    #r"/data/key/project-key.pem"
    #r"C:\Users\ifezo\.ssh\project-key.pem"


    a = int(sys.argv[1])
    if (a == 0):
        subprocess.call("touch /data/key/project-key.pem", shell=True)
        subprocess.call("./set-env.sh", shell=True)
        create_cloudformation_stack("VPC-AMI","../vpc.yaml",cloudformation)
        securityGroup,securityGroupSsh,subnetId = get_stack_network_info("VPC-AMI",cloudformation)
        create_key_pair(client)
        instanceIp,instanceId = create_ec2_instance(securityGroup,securityGroupSsh,subnetId,client,ec2)
        setup_instance(instanceIp)
        amiId = create_ami(instanceId,ec2,client)
        os.environ['AMI_ID'] = amiId
        subprocess.call("sed -i 's/myami/'$AMI_ID'/' stackTemp.yaml", shell=True)
        delete_ec2_instance(instanceId,client)
        delete_cloudformation_stack("VPC-AMI",cloudformation)
        create_cloudformation_stack("All-in-One","../stackTemp.yaml",cloudformation)
        configure(client,autoscaling,ssh_client,key)
        subprocess.call("./configure.sh", shell=True)
        subprocess.call("./kube.sh", shell=True)
    else:
        subprocess.call("./set-env.sh")
        delete_cloudformation_stack("All-in-One",cloudformation)
        delete_key_pair(client)
