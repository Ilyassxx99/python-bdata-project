import os
import paramiko
import time
import signal
import subprocess


def configure(client,ec2,autoscaling,ssh_client,cloudformation):

    workersIp = [] # List of workers Ip addresses
    controllersIp = [] # List of controllers Ip addresses
    controllersPrivateIp = []
    workersId = [] # List of workers Ids
    controllersId = [] # List of controller Ids
    controllersCount = 0 # Number of running controllers
    workersCount = 0 # Number of running workers
    newWorkersCount = 0 # Number of restarted Workers
    newControllersCount = 0 # Number of restarted Controllers
    loopCounter = 0
    joincmd = "" # Cluster join command

    k = paramiko.RSAKey.from_private_key_file(r"/root/.kube/project-key.pem") # Set Private key
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Auto add instances to known hosts

    # Get controllers and workers informations
    controllers = client.describe_instances(Filters=[{'Name': 'tag:Type', 'Values': ['Controller']},{'Name': 'instance-state-name', 'Values': ['running']}])
    workers = client.describe_instances(Filters=[{'Name': 'tag:Type', 'Values': ['Worker']},{'Name': 'instance-state-name', 'Values': ['running']}])


    for reservation in controllers["Reservations"]:
        for instance in reservation["Instances"]:
            controllersIp.append(instance["PublicIpAddress"]) # Get controller Ip address
            controllersPrivateIp.append(instance["PrivateIpAddress"])
            controllersId.append(instance["InstanceId"]) # Get controller Id
            print("--------------------------------")
            print("Controller-{} ip: ".format(controllersCount) + instance["PublicIpAddress"])
            print("--------------------------------")
            waiter = client.get_waiter('instance_status_ok') # Wait for controller to change status ok
            waiter.wait(
                InstanceIds=[
                    controllersId[controllersCount],
                    ],
                WaiterConfig={
                    'Delay': 30,
                    'MaxAttempts': 123
                    }
                    )
            ec2.Instance(instance["InstanceId"]).modify_attribute(
            DisableApiTermination={
            'Value': True
            })
            ssh_client.connect(hostname=instance["PublicIpAddress"], username="ubuntu", pkey=k) # Connect to controller
            print("Initiating Kubernetes cluster ...")
            # Execute command to initiate Kubernetes cluster
            cmd = 'sudo hostnamectl set-hostname master-node && \
             sudo service docker start && \
             sudo kubeadm init --control-plane-endpoint "'+instance["PublicIpAddress"]+':6443" --pod-network-cidr=10.244.0.0/16 && \
             mkdir -p /home/ubuntu/.kube && \
             sudo cp -i /etc/kubernetes/admin.conf /home/ubuntu/.kube/config && \
             sudo chown $(id -u):$(id -g) /home/ubuntu/.kube/config && \
             sudo mkdir /data/ && \
             sudo kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml'
            stdin,stdout,stderr=ssh_client.exec_command(cmd)
            lines = stdout.readlines() # read output of command
            subprocess.call("./create-admin.sh",shell=True)
            print("Kubernetes cluster initiated successfully !")
            print("-------------------------------------------")
            # Copying files to remote controller
            sftp = ssh_client.open_sftp()
            sftp.get("/home/ubuntu/.kube/config","/root/.kube/config")
            sftp.close()
            stdin,stdout,stderr=ssh_client.exec_command("sudo kubeadm token create --print-join-command") # Get token used by workers to join cluster
            lines = stdout.readlines()
            ssh_client.close()
            print(lines)
            controllersCount = controllersCount + 1
            joincmd = lines[0][:-2]
            joincmd = "sudo "+ joincmd # The join command to enter in controllers to join cluster
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    for reservation in workers["Reservations"]:
        for instance in reservation["Instances"]:
            stdo = ""
            workersIp.append(instance["PublicIpAddress"]) # Get worker Ip address
            workersId.append(instance["InstanceId"]) # Get worker Id
            print("--------------------------------")
            print("Worker-{} ip: ".format(workersCount) + instance["PublicIpAddress"])
            print("--------------------------------")
            waiter = client.get_waiter('instance_status_ok') # Wait for worker status Ok
            waiter.wait(
                InstanceIds=[
                    workersId[workersCount],
                    ],
                WaiterConfig={
                    'Delay': 30,
                    'MaxAttempts': 123
                    }
                    )
            ssh_client.connect(hostname=instance["PublicIpAddress"], username="ubuntu", pkey=k) # Setup SSH connection
            stdin,stdout,stderr=ssh_client.exec_command("sudo hostnamectl set-hostname worker-node-{}".format(workersCount)) # Change worker hostname
            lines = stdout.readlines()
            stdin,stdout,stderr=ssh_client.exec_command('chmod +x result.sh')
            lines = stdout.readlines()
            stdin,stdout,stderr=ssh_client.exec_command("sudo service docker start")
            lines = stdout.readlines()
            stdin,stdout,stderr=ssh_client.exec_command(joincmd) # Command to join cluster
            lines = stderr.readlines()
            ssh_client.close()
            # for line in lines:
            #     stdo = stdo + line # Output of join command
            # print(stdo)
            workersCount = workersCount + 1
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("--------------------------------")
    print("Deploying the kubernetes objects ...")
    subprocess.call("kubectl apply -f /scripts/k8s",shell=True)
    subprocess.call("kubectl label nodes worker-node-0 spark=yes",shell=True)
    print("--------------------------------")
    print("Deploying the kube-opex-analytics ...")
    subprocess.call('helm upgrade \
                    --namespace kube-system \
                    --install kube-opex-analytics \
                    /scripts/helm/kube-opex-analytics/', shell=True)
    print("--------------------------------")
    print("Access Kube-Opex-Analytics on: "+workersIp[0]+":31082")
    print("--------------------------------")
