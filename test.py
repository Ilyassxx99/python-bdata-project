import paramiko
from configure import *

controllerIp="35.180.203.220"
controllersPrivateIp="192.168.10.59"

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#r"/data/key/project-key.pem"
k = paramiko.RSAKey.from_private_key_file(r"C:\Users\ifezo\.ssh\AWS-keypair.pem")
ssh_client.connect(hostname=controllerIp, username="ubuntu", pkey=k)


ftp = ssh_client.open_sftp()
core_site = '<configuration> \n\
<property> \n\
  <name>hadoop.tmp.dir</name> \n\
  <value>/home/ubuntu/data/spark</value> \n\
</property> \n\
<property> \n\
  <name>fs.default.name</name> \n\
  <value>hdfs://'+controllersPrivateIp+':9000</value> \n\
</property> \n\
</configuration>'
file=ftp.file('/home/ubuntu/hadoop-3.2.1/etc/hadoop/core-site.xml', "w", -1)
file.write(core_site)
file.flush()
hdfs_site = '<configuration> \n\
<property> \n\
  <name>dfs.data.dir</name> \n\
  <value>/home/ubuntu/data/spark/namenode</value> \n\
</property> \n\
<property> \n\
  <name>dfs.data.dir</name> \n\
  <value>/home/ubuntu/data/spark/datanode</value> \n\
</property> \n\
<property> \n\
  <name>dfs.replication</name> \n\
  <value>1</value> \n\
</property> \n\
</configuration>'
file=ftp.file('/home/ubuntu/hadoop-3.2.1/etc/hadoop/hdfs-site.xml', "w", -1)
file.write(hdfs_site)
file.flush()
mapred_site = '<configuration> \n\
<property> \n\
  <name>mapreduce.framework.name</name> \n\
  <value>yarn</value> \n\
</property> \n\
</configuration>'
file=ftp.file('/home/ubuntu/hadoop-3.2.1/etc/hadoop/mapred-site.xml', "w", -1)
file.write(mapred_site)
file.flush()
ftp.close()
