import boto3
import sys

def create_cloudformation_stack(stack,file,cloudformation):
    cf_template = open(file).read()
    print("Creating stack: "+stack+"...")
    response = cloudformation.create_stack(
        StackName=stack,
        TemplateBody=cf_template,
        Capabilities=[
            "CAPABILITY_NAMED_IAM",
        ],
        OnFailure="DO_NOTHING",
    )
    waiter = cloudformation.get_waiter("stack_create_complete")
    waiter.wait(StackName=stack, WaiterConfig={"Delay": 15, "MaxAttempts": 300})
    print(stack+" created successfully !")

def delete_cloudformation_stack(stack,cloudformation):
    print("Deleting stack: "+stack+" ...")
    response = cloudformation.delete_stack(
        StackName=stack,
    )
    waiter = cloudformation.get_waiter("stack_delete_complete")
    waiter.wait(StackName=stack, WaiterConfig={"Delay": 15, "MaxAttempts": 300})
    print(stack + " deleted successfully !")
