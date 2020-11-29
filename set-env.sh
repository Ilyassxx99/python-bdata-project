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
