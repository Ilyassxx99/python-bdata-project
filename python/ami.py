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
    k = paramiko.RSAKey.from_private_key_file(r"/root/.kube/project-key.pem")
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
    # stdin, stdout, stderr = ssh_client.exec_command(
    #     'sudo apt install openjdk-8-jdk -y && \
    #      echo "export JAVA_HOME=$(readlink -f /usr/bin/java | sed "s:jre/bin/java::")" >> .bashrc'
    # )
    # lines = stdout.readlines()
    # print(lines)
    # stdin, stdout, stderr = ssh_client.exec_command(
    #     'sudo apt install openssh-server openssh-client -y && \
    #      ssh-keygen -t rsa -P "" -f ~/.ssh/id_rsa && \
    #      cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys && \
    #      chmod 0600 ~/.ssh/authorized_keys'
    # )
    # lines = stdout.readlines()
    # print(lines)
    # stdin, stdout, stderr = ssh_client.exec_command(
    #     'wget https://downloads.apache.org/hadoop/common/hadoop-3.2.1/hadoop-3.2.1.tar.gz && \
    #     sleep 5 && \
    #     tar -xzf hadoop-3.2.1.tar.gz && \
    #     HADOOP_HOME=/home/ubuntu/hadoop-3.2.1 && \
    #     echo "export HADOOP_HOME=/home/ubuntu/hadoop-3.2.1" >> .bashrc')
    # lines = stdout.readlines()
    # print(lines)
    # stdin, stdout, stderr = ssh_client.exec_command(
    #     'echo "export HADOOP_INSTALL=/home/ubuntu/hadoop-3.2.1" >> .bashrc && \
    #     echo "export HADOOP_MAPRED_HOME=/home/ubuntu/hadoop-3.2.1" >> .bashrc && \
    #     echo "export HADOOP_COMMON_HOME=/home/ubuntu/hadoop-3.2.1" >> .bashrc && \
    #     echo "export HADOOP_HDFS_HOME=/home/ubuntu/hadoop-3.2.1" >> .bashrc && \
    #     echo "export YARN_HOME=/home/ubuntu/hadoop-3.2.1" >> .bashrc && \
    #     echo "export HADOOP_COMMON_LIB_NATIVE_DIR=/home/ubuntu/hadoop-3.2.1/lib/native" >> .bashrc && \
    #     echo "export PATH=$PATH:/home/ubuntu/hadoop-3.2.1/sbin:/home/ubuntu/hadoop-3.2.1/bin:$JAVA_HOME/bin" >> .bashrc && \
    #     source ~/.bashrc')
    # lines = stdout.readlines()
    # print(lines)
    stdin,stdout,stderr=ssh_client.exec_command('sudo apt install -y nfs-kernel-server && \
    sudo apt install -y nfs-common && \
    mkdir -p /home/ubuntu/data/spark && \
    sudo chown ubuntu:ubuntu /home/ubuntu/data/spark && \
    sudo chown ubuntu:ubuntu /etc/exports')
    lines = stdout.readlines()
    ssh_client.close()
def create_ami(instanceId,ec2,client):
    print("Creating AMI ...")
    instance = ec2.Instance(instanceId)
    ami = instance.create_image(
        Description="AMI for big data project",
        InstanceId=instanceId,
        Name="kubernetes-optimizied-ami",
    )
    amiId = ami.image_id
    amiName = ami.name
    waiter = client.get_waiter("image_available")
    waiter.wait(
        ImageIds=[
            amiId,
        ],
    )
    print(amiName + " created successfully ")
    return (amiId, amiName)

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

def delete_ami(amiId,amiName,client):
    ownerId = boto3.client('sts').get_caller_identity().get('Account')
    response = client.deregister_image(
    ImageId=amiId,
    )
    snapIds = []
    snapDescribe = client.describe_snapshots(
    Filters=[
            {
                'Name': 'owner-id',
                'Values': [
                    ownerId,
                ]
            },
        ],
    )
    snaps = snapDescribe['Snapshots']
    for snap in snaps:
        snapIds.append(snap['SnapshotId'])
    for snapId in snapIds:
        print(snapId)
        response = client.delete_snapshot(
        SnapshotId=snapId,
        )
    print(amiName + " deleted successfully !")

if __name__ == '__main__':
    client = boto3.client("ec2")
    cloudformation = boto3.client("cloudformation")
    autoscaling  = boto3.client('autoscaling')
    ec2 = boto3.resource("ec2")
    print("Image doesn't exist, creating image ...")
    create_cloudformation_stack("VPC-AMI","vpc.yaml",cloudformation)
    securityGroup,securityGroupSsh,subnetId = get_stack_network_info("VPC-AMI",cloudformation)
    instanceIp,instanceId = create_ec2_instance(securityGroup,securityGroupSsh,subnetId,client,ec2)
    setup_instance(instanceIp)
    # amiId,amiName = create_ami(instanceId,ec2,client)
    # print("-----------AMI-----------")
    # print(amiId)
    # print("-------------------------")
