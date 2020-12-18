import boto3
import paramiko
import os
import subprocess
import time
import sys
from botocore.config import Config
from stack import *


# client = boto3.client("ec2",
#     config=my_config
#     )
# s3 = boto3.client("s3",
#     config=my_config
#     )
# cloudformation = boto3.client("cloudformation",
#     config=my_config
#     )
# autoscaling  = boto3.client('autoscaling',
#     config=my_config
#     )
# sns = boto3.client("sns",
#     config=my_config
#     )
# lamda = boto3.client("lambda",
#     config=my_config
#     )
# logs = boto3.client("logs",
#     config=my_config
#     )
# iam = boto3.client("iam",
#     config=my_config
#     )
# ec2 = boto3.resource("ec2",
#     config=my_config
#     )
# iamRes = boto3.resource('iam')
# s3Res = boto3.resource('s3')


def monitoringCreate(s3,s3Res,lamda,cloudformation,autoscaling):
    roleArn = ""
    snsArn = ""

    s3Bucket = s3.create_bucket(
        ACL='private',
        Bucket='kube-cluster-lambda-bucket',
        CreateBucketConfiguration={
            'LocationConstraint': 'eu-west-3'
        },
    )

    s3Res.Bucket('kube-cluster-lambda-bucket').upload_file('./lambda.zip', 'lambda.zip')
    s3Res.Bucket('kube-cluster-lambda-bucket').upload_file(r'/root/.kube/project-key.pem', 'project-key.pem')

    create_cloudformation_stack("Lambda-Stack","lambdaTemp.yaml",cloudformation)

    stack = cloudformation.describe_stacks(StackName='Lambda-Stack')
    stackOutputs = stack['Stacks'][0]['Outputs']
    for stackOutput in stackOutputs:
        if (stackOutput['OutputKey'] == 'LambdaSNSTopic'):
            snsArn = stackOutput['OutputValue']
        elif (stackOutput['OutputKey'] == 'AutoScalingLifecycleHookRole'):
            roleArn = stackOutput['OutputValue']

    response = lamda.add_permission(
    FunctionName='kubeconfigpy',
    StatementId='sns',
    Action='lambda:InvokeFunction',
    Principal='sns.amazonaws.com',
    SourceArn=snsArn,
    )

    response = autoscaling.put_lifecycle_hook(
        LifecycleHookName='ConfigureKubernetesNode',
        AutoScalingGroupName='WorkersAutoScalingGroup',
        LifecycleTransition='autoscaling:EC2_INSTANCE_LAUNCHING',
        RoleARN=roleArn,
        NotificationTargetARN=snsArn,
        NotificationMetadata='string',
        HeartbeatTimeout=300,
    )


def monitoringDelete(s3,ec2,client,cloudformation,iam,sns,logs,topicArn):
    # Delete All
    subsArn = []
    response = s3.delete_objects(
        Bucket='kube-cluster-lambda-bucket',
        Delete={
            'Objects': [
                {
                    'Key': 'lambda.zip',
                },
                {
                    'Key': 'project-key.pem',
                },
            ],
            'Quiet': False,
        },
    )
    response = s3.delete_bucket(
        Bucket='kube-cluster-lambda-bucket',
    )
    response = iam.delete_role_policy(
    RoleName='lambda-autoscaling-role',
    PolicyName='lambda-autoscaling-policy'
    )
    response = iam.delete_role(
    RoleName='lambda-autoscaling-role'
    )
    subs = sns.list_subscriptions_by_topic(
    TopicArn=topicArn,
    )
    for sub in subs['Subscriptions']:
            subsArn.append(sub['SubscriptionArn'])
    for subArn in subsArn:
        response = sns.unsubscribe(
        SubscriptionArn=subArn
        )
    response = logs.delete_log_group(
    logGroupName=r'/aws/lambda/kubeconfigpy'
    )
    delete_cloudformation_stack(ec2,client,"Lambda-Stack",cloudformation)

#
# elif (a == 2):
#     # Update Lambda function
#     print("Updating lambda Code ...")
#     s3Res.Bucket('kube-cluster-lambda-bucket').upload_file('./lambda.zip', 'lambda.zip')
#     response = lamda.update_function_code(
#     FunctionName='kubeconfigpy',
#     S3Bucket='kube-cluster-lambda-bucket',
#     S3Key='lambda.zip',
#     )
#     print("Lambda code updated successfully !")
# elif (a == 3):
#     # Test lambda function
#     response = lamda.invoke(
#     FunctionName='kubeconfigpy',
#     InvocationType='RequestResponse',
#     LogType='Tail',
# )
