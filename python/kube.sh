#!/bin/bash
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
