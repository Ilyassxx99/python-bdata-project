aws lambda create-function --function-name pytest \
--zip-file fileb://my-deployment-package.zip --handler index.handler --runtime python3.6 \
--role arn:aws:iam::225616068815:role/lambda-ex

pip3 install -t . --system paramiko
pip3 install -t . --system cryptography
pip3 install -t . --system netmiko

zip -r lambda.zip ./*

zip -g lambda.zip index.py

aws lambda update-function-code --function-name pytest --zip-file fileb://lambda.zip

aws lambda invoke --function-name pytest out --log-type Tail --query 'LogResult' --output text |  base64 -d
