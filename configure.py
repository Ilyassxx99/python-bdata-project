import os
import paramiko
import time
import signal
import subprocess

# def hdfs_config(ssh_client,controllersPrivateIp):
#     ftp = ssh_client.open_sftp()
#     core_site = '<configuration> \n\
#     <property> \n\
#       <name>hadoop.tmp.dir</name> \n\
#       <value>/data/default/user/spark</value> \n\
#     </property> \n\
#     <property> \n\
#       <name>fs.default.name</name> \n\
#       <value>hdfs://'+controllersPrivateIp[0]+':9000</value> \n\
#     </property> \n\
#     </configuration>'
#     file=ftp.file('$HADOOP_HOME/etc/hadoop/core-site.xml', "w", -1)
#     file.write(core_site)
#     file.flush()
#     hdfs_site = '<configuration> \n\
#     <property> \n\
#       <name>dfs.data.dir</name> \n\
#       <value>/data/default/user/spark/namenode</value> \n\
#     </property> \n\
#     <property> \n\
#       <name>dfs.data.dir</name> \n\
#       <value>/data/default/user/spark/datanode</value> \n\
#     </property> \n\
#     <property> \n\
#       <name>dfs.replication</name> \n\
#       <value>1</value> \n\
#     </property> \n\
#     </configuration>'
#     file=ftp.file('$HADOOP_HOME/etc/hadoop/hdfs-site.xml', "w", -1)
#     file.write(hdfs_site)
#     file.flush()
#     mapred_site = '<configuration> \n\
#     <property> \n\
#       <name>mapreduce.framework.name</name> \n\
#       <value>yarn</value> \n\
#     </property> \n\
#     </configuration>'
#     file=ftp.file('$HADOOP_HOME/etc/hadoop/mapred-site.xml', "w", -1)
#     file.write(mapred_site)
#     file.flush()
#     ftp.close()

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
            print("Controller-{} ip: ".format(controllersCount) + instance["PublicIpAddress"])
            os.environ["CONTROLLER_IP"]=controllersIp[0]
            subprocess.call('echo "--------------------------------" && echo "Controller IP: $CONTROLLER_IP" && echo "--------------------------------"', shell = True)
            #subprocess.call("echo $CONTROLLER_IP > /root/.kube/MasterIp", shell=True)
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
            print("Configuring Hadoop cluster on Master ...")
            hdfs_config(ssh_client,controllersPrivateIp)
            stdin,stdout,stderr=ssh_client.exec_command("hdfs namenode -format && ./start-dfs.sh") # Get token used by workers to join cluster
            lines = stdout.readlines()
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
            #stdin,stdout,stderr=ssh_client.exec_command('sudo apt install nfs-kernel-server && \
            #sudo mkdir -p /data/default/user/spark && sudo chown nobody:nogroup && \
            #echo "/data/default/user/spark    192.168.0.0/16(rw,sync,no_subtree_check)" >> /etc/exports && \
            #sudo systemctl restart nfs-kernel-server && \
            #sudo ufw allow from 192.168.0.0/16 to any port nfs')
            #lines = stdout.readlines()
            subprocess.call("./create-admin.sh",shell=True)
            print("Controller-{} id: ".format(controllersCount) + lines[0])
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

    for reservation in workers["Reservations"]:
        for instance in reservation["Instances"]:
            stdo = ""
            workersIp.append(instance["PublicIpAddress"]) # Get worker Ip address
            workersId.append(instance["InstanceId"]) # Get worker Id
            os.environ["WORKER_IP"]=workersIp[workersCount]
            subprocess.call('echo "--------------------------------" && echo "Worker IP: $WORKER_IP" && echo "--------------------------------"', shell = True)
            print("Worker-{} ip: ".format(workersCount) + instance["PublicIpAddress"])
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
            hdfs_config(ssh_client,controllersPrivateIp)
            stdin,stdout,stderr=ssh_client.exec_command("sudo hostnamectl set-hostname worker-node-{}".format(workersCount)) # Change worker hostname
            lines = stdout.readlines()
            stdin,stdout,stderr=ssh_client.exec_command('chmod +x result.sh')
            lines = stdout.readlines()
            cmd = 'sudo apt install nfs-common && \
            sudo mkdir -p /data/default/user/spark && \
            sudo mount'+controllersPrivateIp[0]+':/data/default/user/spark /data/default/user/spark'
            #stdin,stdout,stderr=ssh_client.exec_command(cmd)
            #lines = stdout.readlines()
            stdin,stdout,stderr=ssh_client.exec_command("sudo service docker start")
            lines = stdout.readlines()
            stdin,stdout,stderr=ssh_client.exec_command(joincmd) # Command to join cluster
            lines = stderr.readlines()
            ssh_client.close()
            for line in lines:
                stdo = stdo + line # Output of join command
            print(stdo)
            print("-------------------------------------------")
            workersCount = workersCount + 1
    ssh_client.connect(hostname=controllersIp[0], username="ubuntu", pkey=k) # Connect to controller
    for workerIp in workerIps:
        cmd = 'echo "'+workerIp+'" >> $HADOOP_HOME/etc/hadoop/workers'
        stdin,stdout,stderr=ssh_client.exec_command(cmd)
        lines = stdout.readlines()
    ssh_client.close()
    print("--------------------------------")
    print("Deploying the kubernetes objects ...")
    subprocess.call("kubectl apply -f /scripts/k8s",shell=True)
    subprocess.call("kubectl label nodes worker-node-0 spark=yes",shell=True)
    print("--------------------------------")
    print("Deploying the kube-opex-analytics ...")
    subprocess.call('helm upgrade \
                    --namespace default \
                    --install kube-opex-analytics \
                    /scripts/helm/kube-opex-analytics/', shell=True)
    print("--------------------------------")
    print("-----------------------------------------------------------Access Kube-Opex-Analytics on: $WORKER_IP:31082-----------------------------------------------------------")

    # while True:
    #     # Loop to check for new instances
    #     print("Loop number: "+ str(loopCounter))
    #     print("-------------------------------------------")
    #     print("Current controllers number: ".format(controllersCount) + str(len(controllersId)))
    #     print("Current workers number: ".format(workersCount) + str(len(workersId)))
    #     print("-------------------------------------------")
    #     loopCounter = loopCounter + 1
    #     workersCount = 0 # Number of current workers
    #     controllersCount = 0 # Number of current controllers
    #     newControllersCount = 0 # Number of new controllers
    #     newWorkersCount = 0 # Number of new workers
    #     workersIpNew = [] # List of newly launched workers Ip addresses
    #     controllersIpNew = [] # List of newly launched controllers Ip addresses
    #     workersIdNew = [] # List of newly launched workers Ids
    #     controllersIdNew = [] # List of newly launched controllers Ids
    #     workersIpTemp = [] # Temporary list of workers Ip addresses
    #     controllersIpTemp = [] # Temporary list of controllers Ip addresses
    #     workersIdTemp = [] # Temporary list of workers Ids
    #     controllersIdTemp = [] # Temporary list of controllers Ids
    #     controllers = client.describe_instances(Filters=[{'Name': 'tag:Type', 'Values': ['Controller']},{'Name': 'instance-state-name', 'Values': ['running']}])
    #     for reservation in controllers["Reservations"]:
    #         for instance in reservation["Instances"]:
    #             controllersCount = controllersCount + 1 # Get number of current controllers
    #             controllersIpTemp.append(instance["PublicIpAddress"])
    #             controllersIdTemp.append(instance["InstanceId"])
    #             if (instance["InstanceId"] not in controllersId): # Check for newly launched controllers
    #                 print("\n I'm adding new controllers to the list")
    #                 newControllersCount = newControllersCount + 1 # Number of newly launched controllers
    #                 controllersIpNew.append(instance["PublicIpAddress"]) # Add newly launched controllers Ip address
    #                 controllersIdNew.append(instance["InstanceId"]) # Add newly launched controllers Id
    #
    #     controllersId = controllersIdTemp[:] # Set current controllers Id list to the temporary controllers Id list
    #     controllersIp = controllersIpTemp[:] # Set current controllers Ip addresses list to the temporary controllers Ip addresses list
    #     print("\n Number of new controllers: "+str(newControllersCount))
    #     print("-------------------------------------")
    #     if (newControllersCount > 0): # If there are newly launched controllers execute commands
    #         for i in range(0,newControllersCount):
    #             print("New Controller-{} ip: ".format(i) + controllersIpNew[i])
    #             waiter = client.get_waiter('instance_status_ok') # Wait for new controllers status Ok
    #             waiter.wait(
    #                 InstanceIds=[
    #                     controllersIdNew[i],
    #                     ],
    #                 WaiterConfig={
    #                     'Delay': 30,
    #                     'MaxAttempts': 123
    #                     }
    #                     )
    #             stdin,stdout,stderr=ssh_client.exec_command("curl http://169.254.169.254/latest/meta-data/instance-id") # Execute command to create kubernetes cluster
    #             lines = stdout.readlines() # read output of create cluster command
    #             print("New Controller-{} id: ".format(i) + lines[0])
    #             print("-------------------------------------------")
    #
    #     workers = client.describe_instances(Filters=[{'Name': 'tag:Type', 'Values': ['Worker']},{'Name': 'instance-state-name', 'Values': ['running']}])
    #     for reservation in workers["Reservations"]:
    #         for instance in reservation["Instances"]:
    #             workersCount = workersCount + 1 # Get number of current workers
    #             workersIpTemp.append(instance["PublicIpAddress"])
    #             workersIdTemp.append(instance["InstanceId"])
    #             if instance["InstanceId"] not in workersId: # Check for newly launched workers
    #                 print("\n I'm adding new workers to the list")
    #                 newWorkersCount = newWorkersCount + 1 # Number of newly launched controllers
    #                 workersIpNew.append(instance["PublicIpAddress"]) # Add newly launched workers Ip address
    #                 workersIdNew.append(instance["InstanceId"]) # Add newly launched workers Id
    #     workersId = workersIdTemp[:] # Set current workers Id list to the temporary workers Id list
    #     workersIp = workersIpTemp[:] # Set current workers Ip addresses list to the temporary workers Ip addresses list
    #     print("\n Number of new workers: "+str(newWorkersCount))
    #     print("-------------------------------------")
    #
    #     if (newWorkersCount > 0): # If there are newly launched workers execute commands
    #         for i in range(0,newWorkersCount):
    #             print("New Worker-{} ip: ".format(i) + workersIpNew[i])
    #             waiter = client.get_waiter('instance_status_ok') # Wait for new workers status Ok
    #             waiter.wait(
    #                 InstanceIds=[
    #                     workersIdNew[i],
    #                     ],
    #                 WaiterConfig={
    #                     'Delay': 30,
    #                     'MaxAttempts': 123
    #                     }
    #                     )
    #             ssh_client.connect(hostname=workersIpNew[i], username="ubuntu", pkey=k)
    #             stdin,stdout,stderr=ssh_client.exec_command("sudo hostnamectl set-hostname worker-node-{}-{}".format(loopCounter,i)) # Change hostname of worker node
    #             lines = stdout.readlines()
    #             print(lines)
    #             stdin,stdout,stderr=ssh_client.exec_command("sudo service docker start")
    #             lines = stdout.readlines()
    #             stdin,stdout,stderr=ssh_client.exec_command(joincmd) # Execute command to join cluster
    #             lines = stdout.readlines()
    #             for line in lines:
    #                 stdo = stdo + line # Get output of join command
    #             print("Stdout: " + stdo)
    #             print("New Worker-{}-{} id: ".format(loopCounter,i) + lines[0])
    #             print("-------------------------------------------")
    #
    #     if (newControllersCount == 0): # If no controllers have been launched
    #         print("No controller has been added")
    #     if (newWorkersCount == 0):  # If no workers have been launched
    #         print("No worker has been added")
    #
    #     time.sleep(60)
    # # Get controllers Ids
