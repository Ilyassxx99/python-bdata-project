#!/bin/bash
#Set AWS credentials
cat <<EOF >./.env
[default]
ACCESS_KEY=$ACCESS_KEY
SECRET_KEY=$SECRET_KEY
REGION=$REGION
EOF
