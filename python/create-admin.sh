tempcert=$(cat config.yaml | grep "client-certificate-data")
tempkey=$(cat config.yaml | grep "client-key-data")
tempca=$(cat config.yaml | grep "certificate-authority-data")
cert=$(echo $tempcert | cut -d " " -f 2)
key=$(echo $tempkey | cut -d " " -f 2)
ca=$(echo $tempca | cut -d " " -f 2)

echo $ca > /data/pki/ca.pem
echo $cert > /data/pki/admin.pem
echo $key > /data/pki/admin-key.pem
