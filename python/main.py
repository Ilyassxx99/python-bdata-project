import boto3
import paramiko
import os
from configure import *
from stack import *
from keypair import *
from ami import *



if __name__ == '__main__':

    client = boto3.client("ec2")
    cloudformation = boto3.client("cloudformation")
    autoscaling  = boto3.client('autoscaling')
    ec2 = boto3.resource("ec2")


    a = int(sys.argv[1])
    if (a == 0):
        create_cloudformation_stack("VPC-AMI","../vpc.yaml",cloudformation)
        securityGroup,securityGroupSsh,subnetId = get_stack_network_info("VPC-AMI")
        create_key_pair(client)
        instanceIp,instanceId = create_ec2_instance(securityGroup,securityGroupSsh,subnetId)
        setup_instance(instanceIp)
        amiId = create_ami(instanceId)
        delete_ec2_instance(instanceId)
        delete_cloudformation_stack("VPC-AMI",cloudformation)
        create_cloudformation_stack("All-in-One","../stackTemp.yaml",cloudformation)
        configure(ec2,autoscaling)
    else:
        delete_cloudformation_stack("All-in-One",cloudformation)
        delete_key_pair(client)
