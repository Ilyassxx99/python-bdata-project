#!/bin/bash
#Set AWS credentials
mkdir -p ~/.aws/
cat <<EOF >~/.aws/config
[default]
region = $REGION
EOF
cat <<EOF >~/.aws/credentials
[default]
aws_access_key_id = $ACCESS_KEY
aws_secret_access_key = $SECRET_KEY
EOF
#CloudFormation Stack creation
echo "Executing python script ..."
python main.py 0
echo "python script executed successfully !"
#Configure admin access to cluster
echo "Executing the create-admin.sh script ..."
./create-admin.sh
echo "create-admin.sh executed successfully !"
#Listing Cluster nodes
kubectl get nodes
#Creating service account to be used by spark job
kubectl create serviceaccount spark
kubectl create clusterrolebinding spark-role --clusterrole=edit  --serviceaccount=default:spark --namespace=default
kubectl apply -f k8s
echo "Deploying kube-opex-analytics ..."
sleep 40
podname=$(kubectl get pods -o jsonpath='{.items[0].metadata.name}')
kubectl port-forward $podname 5483:5483
