tempcert=$(cat config.yaml | grep "client-certificate-data")
tempkey=$(cat config.yaml | grep "client-key-data")
tempca=$(cat config.yaml | grep "certificate-authority-data")
cert=$(echo $tempcert | cut -d " " -f 2)
key=$(echo $tempkey | cut -d " " -f 2)
ca=$(echo $tempca | cut -d " " -f 2)

echo "This is the kubernetes controller Ip address :"
echo $KUBERNETES_PUBLIC_ADDRESS

kubectl config set-cluster kubernetes-spark \
    --certificate-authority=$ca \
    --embed-certs=true \
    --server=https://${KUBERNETES_PUBLIC_ADDRESS}:6443

kubectl config set-credentials admin \
    --client-certificate=$cert \
    --client-key=$key

kubectl config set-context kubernetes-spark \
    --cluster=kubernetes-spark \
    --user=admin

kubectl config use-context kubernetes-spark
