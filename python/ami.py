import boto3
import paramiko
import os
from stack import create_cloudformation_stack,delete_cloudformation_stack
from keypair import create_key_pair,delete_key_pair

def get_stack_network_info(stack,cloudformation):
    response = cloudformation.describe_stacks(
        StackName=stack,
    )
    for output in response["Stacks"][0]["Outputs"]:
        if output["OutputKey"] == "SecurityGroup":
            securityGroup = output["OutputValue"]
        if output["OutputKey"] == "SecurityGroupSsh":
            securityGroupSsh = output["OutputValue"]
        if output["OutputKey"] == "PublicSubnet01Id":
            subnetId = output["OutputValue"]
    print("Subnet Id is: " + str(subnetId))
    print("SecurityGroupSsh Id is: " + str(securityGroupSsh))
    print("SecurityGroup Id is: " + str(securityGroup))
    return (securityGroup,securityGroupSsh,subnetId)

def create_ec2_instance(securityGroup,securityGroupSsh,subnetId,client,ec2):
    print("Creating EC2 instance ...")
    instance = client.run_instances(
        ImageId="ami-089d839e690b09b28",
        MinCount=1,
        MaxCount=1,
        SubnetId=subnetId,
        InstanceType="t2.micro",
        KeyName="project-key",
        SecurityGroupIds=[
            securityGroup,
            securityGroupSsh,
        ],
    )
    instanceId = instance["Instances"][0]["InstanceId"]
    instance = ec2.Instance(instanceId)
    print("Waiting for instance to start ...")
    waiter = client.get_waiter("instance_status_ok")
    waiter.wait(
        InstanceIds=[
            instanceId,
        ],
        WaiterConfig={"Delay": 30, "MaxAttempts": 123},
    )
    instanceIp = instance.public_ip_address
    print("Instance Ip: " + str(instanceIp))
    print("Instance started !")
    return (instanceIp,instanceId)

def setup_instance(instanceIp):
    print("Installing required software ...")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #r"/data/key/project-key.pem"
    k = paramiko.RSAKey.from_private_key_file(r"/data/key/project-key.pem")
    ssh_client.connect(hostname=instanceIp, username="ubuntu", pkey=k)

    stdin, stdout, stderr = ssh_client.exec_command(
        'sudo apt-get update && \
     sudo apt-get install -y docker.io && \
     sudo systemctl enable docker && \
     sudo systemctl start docker && \
     sudo apt-get install -y curl && \
     curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add && \
     sudo apt-add-repository "deb http://apt.kubernetes.io/ kubernetes-xenial main" && \
     sudo apt-get install -y kubeadm kubelet kubectl && \
     sudo apt-mark hold kubeadm kubelet kubectl && \
     sudo docker ––version && \
     kubeadm version && \
     sudo swapoff –a'
    )
    lines = stdout.readlines()
    print(lines)

def create_ami(instanceId,ec2,client):
    print("Creating AMI ...")
    instance = ec2.Instance(instanceId)
    ami = instance.create_image(
        Description="AMI for big data project",
        InstanceId=instanceId,
        Name="kubernetes-optimizied-ami",
    )
    amiId = ami.image_id
    waiter = client.get_waiter("image_available")
    waiter.wait(
        ImageIds=[
            amiId,
        ],
    )
    print("AMI created successfully ")
    return amiId

def delete_ec2_instance(instanceId,client):
    print("Terminating the EC2 instance: "+ instanceId +" ...")
    terminate = client.terminate_instances(
        InstanceIds=[
            instanceId,
        ],
    )
    waiter = client.get_waiter('instance_terminated')
    waiter.wait(
        InstanceIds=[
            instanceId,
            ]
    )
    print(instanceId + " terminated !")

def delete_ami(amiId,client,cloudformation):
    print("Deleting ami: "+amiId+" ...")
    response = client.deregister_image(
    ImageId=amiId,
    )
    waiter = cloudformation.get_waiter("stack_delete_complete")
    waiter.wait(StackName="VPC-AMI", WaiterConfig={"Delay": 10, "MaxAttempts": 300})
    print(amiId + " deleted successfully !")
