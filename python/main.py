import boto3
import paramiko
import os
import subprocess
import thread
import time
from botocore.config import Config
from configure import *
from stack import *
from keypair import *
from ami import *



if __name__ == '__main__':

    ACCESS_KEY = os.environ['ACCESS_KEY']
    SECRET_KEY = os.environ['SECRET_KEY']
    REGION = os.environ['REGION']
    print("-------------------------")
    print(ACCESS_KEY)
    print(SECRET_KEY)
    print("-------------------------")

    my_config = Config(
        region_name = 'eu-west-3',
        retries = {
            'max_attempts': 10,
            'mode': 'standard'
        }
    )
    client = boto3.client("ec2",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=my_config
    )
    cloudformation = boto3.client("cloudformation",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=my_config
    )
    autoscaling  = boto3.client('autoscaling',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=my_config
    )
    ec2 = boto3.resource("ec2",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=my_config
    )
    ssh_client=paramiko.SSHClient()
    #r"/data/key/project-key.pem"
    #r"C:\Users\ifezo\.ssh\project-key.pem"


    a = int(sys.argv[1])

    if (a == 0):
        create_cloudformation_stack("VPC-AMI","vpc.yaml",cloudformation)
        securityGroup,securityGroupSsh,subnetId = get_stack_network_info("VPC-AMI",cloudformation)
        create_key_pair(client)
        instanceIp,instanceId = create_ec2_instance(securityGroup,securityGroupSsh,subnetId,client,ec2)
        setup_instance(instanceIp)
        amiId = create_ami(instanceId,ec2,client)
        os.environ['AMI_ID'] = amiId
        subprocess.call("sed -i 's/myami/'$AMI_ID'/' stackTemp.yaml", shell=True)
        delete_ec2_instance(instanceId,client)
        delete_cloudformation_stack("VPC-AMI",cloudformation)
        create_cloudformation_stack("All-in-One","stackTemp.yaml",cloudformation)
        configure(client,autoscaling,ssh_client)
        
    else:
        delete_cloudformation_stack("All-in-One",cloudformation)
        delete_key_pair(client)
