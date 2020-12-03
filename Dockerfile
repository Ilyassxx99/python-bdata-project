FROM python:slim-buster

RUN apt-get update && apt-get install -y curl && apt-get install -y gnupg2

# download and install Kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl && mv ./kubectl /usr/local/bin/kubectl

# install boto3 and paramiko
RUN pip3 install boto3
RUN pip3 install paramiko

# Download and install Helm
RUN curl https://baltocdn.com/helm/signing.asc | apt-key add - && \
    apt-get install apt-transport-https --yes && \
    echo "deb https://baltocdn.com/helm/stable/debian/ all main" | tee /etc/apt/sources.list.d/helm-stable-debian.list && \
    apt-get update && \
    apt-get install helm

# add scripts and update spark default config
RUN mkdir -p /scripts/python
RUN mkdir -p /scripts/k8s
RUN mkdir -p /scripts/helm
RUN mkdir -p /data/key
RUN mkdir -p /data/pki
COPY k8s /scripts/k8s
COPY python /scripts/python
RUN chmod +x /scripts/python/create-admin.sh
COPY helm /scripts/helm
WORKDIR /scripts/python
