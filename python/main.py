import boto3
import paramiko
import os
import subprocess
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
    amiId = ""
    amiName = ""
    #r"/data/key/project-key.pem"
    #r"C:\Users\ifezo\.ssh\project-key.pem"
    response = client.describe_images(
        Filters=[
            {
                'Name': 'name',
                'Values': [
                    'kubernetes-optimizied-ami',
                ]
            },
            ]
    )
    amis = response["Images"]

    a = int(sys.argv[1])

    if (a == 0):
        if (len(amis) == 0):
            print("Image doesn't exist, creating image ...")
            create_cloudformation_stack("VPC-AMI","vpc.yaml",cloudformation)
            securityGroup,securityGroupSsh,subnetId = get_stack_network_info("VPC-AMI",cloudformation)
            create_key_pair(client)
            instanceIp,instanceId = create_ec2_instance(securityGroup,securityGroupSsh,subnetId,client,ec2)
            setup_instance(instanceIp)
            amiId,amiName = create_ami(instanceId,ec2,client)
            print("-----------AMI-----------")
            print(amiId)
            print("-------------------------")
            os.environ['AMI_ID'] = amiId
            subprocess.call("sed -i 's/myami/'$AMI_ID'/' stackTemp.yaml", shell=True)
            delete_ec2_instance(instanceId,client)
            delete_cloudformation_stack("VPC-AMI",cloudformation)
        else :
            print("Image exists, creating cluster ...")
            amiId = amis[0]["ImageId"]
            os.environ['AMI_ID'] = amiId
            subprocess.call("sed -i 's/myami/'$AMI_ID'/' stackTemp.yaml", shell=True)
            create_cloudformation_stack("All-in-One","stackTemp.yaml",cloudformation)
            configure(client,autoscaling,ssh_client)

    elif (a == 1):
        print("Deleting stack only ...")
        delete_cloudformation_stack("All-in-One",cloudformation)
    else:
        print("Deleting All ...")
        delete_cloudformation_stack("All-in-One",cloudformation)
        delete_key_pair(client)
        delete_ami(amiId,amiName,client)
