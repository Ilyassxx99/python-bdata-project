FROM ubuntu:latest

# update repositories
RUN apt-get update
RUN apt-get install curl -y

# download and install python
RUN apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libsqlite3-dev libreadline-dev libffi-dev curl libbz2-dev && \
    curl -O https://www.python.org/ftp/python/3.8.2/Python-3.8.2.tar.xz && \
    tar -xf Python-3.8.2.tar.xz && \
    cd Python-3.8.2 && \
    ./configure --enable-optimizations && \
    make -j 4 && \
    make altinstall

# download and install Kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl && mv ./kubectl /usr/local/bin/kubectl

# install boto3 and paramiko
RUN pip3.8 install boto3
RUN pip3.8 install paramiko

# add scripts and update spark default config
RUN mkdir -p /scripts/k8s
RUN mkdir -p /scripts/python
RUN mkdir -p /data/key
WORKDIR /scripts
COPY create-admin.sh  /scripts
COPY kube.sh  /scripts
COPY set-env.sh  /scripts
COPY stackTemp.yaml /scripts
COPY vpc.yaml /scripts
COPY k8s /scripts/k8s
COPY python /scripts/python
RUN chmod +x create-admin.sh.sh
RUN chmod +x kube.sh
RUN chmod +x set-env.sh
