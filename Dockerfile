FROM ubuntu:latest

# update repositories
RUN apt-get update
RUN apt update
RUN apt install software-properties-common
RUN apt-get install curl -y

# download and install python
RUN add-apt-repository ppa:deadsnakes/ppa -y && \
    sudo apt install python3.8 && \
    tar -xf Python-3.8.2.tar.xz && \
    cd Python-3.8.2 && \
    ./configure --enable-optimizations && \
    make -j 4 && \
    make altinstall

# download and install Kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl && mv ./kubectl /usr/local/bin/kubectl

# add scripts and update spark default config
RUN mkdir -p /scripts/k8s
RUN mkdir -p /scripts/python
RUN mkdir -p /data/key
COPY create-script.sh  /scripts
COPY delete-script.sh  /scripts
COPY stackTemp.yaml /scripts
COPY vpc.yaml /scripts
COPY k8s /scripts/k8s
COPY python /scripts/python
RUN cd /scripts && chmod +x create-script.sh
RUN cd /scripts && chmod +x delete-script.sh
WORKDIR /scripts
