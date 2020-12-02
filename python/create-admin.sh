tempcert=$(cat /root/.kube/config | grep "client-certificate-data")
tempkey=$(cat /root/.kube/config | grep "client-key-data")
tempca=$(cat /root/.kube/config | grep "certificate-authority-data")
cert=$(echo $tempcert | cut -d " " -f 2)
key=$(echo $tempkey | cut -d " " -f 2)
ca=$(echo $tempca | cut -d " " -f 2)

echo $ca > /data/pki/ca-base64.pem
echo $cert > /data/pki/admin-base64.pem
echo $key > /data/pki/admin-key-base64.pem

base64 -d /data/pki/ca-base64.pem > /data/pki/ca.pem
base64 -d /data/pki/admin-base64.pem > /data/pki/admin.pem
base64 -d /data/pki/admin-key-base64.pem > /data/pki/admin-key.pem
