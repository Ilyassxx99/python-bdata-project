import boto3

client = boto3.client("ec2")

def create_key_pair(client):
    print("Creating SSH key project-key ...")
    keyPair = client.create_key_pair(
        KeyName='project-key'
        )
#r"C:\Users\ifezo\.ssh\project-key.pem"
#r"/data/key/project-key.pem"
    privateKey = keyPair["KeyMaterial"]
    f = open(r"C:\Users\ifezo\.ssh\project-key.pem", "w")
    f.write(privateKey)
    f.close()
    "SSH key project-key created successfully !"

def delete_key_pair(client):
    "Deleting SSH key project-key ..."
    keyPair = client.delete_key_pair(
        KeyName='project-key'
        )
    print("SSH key project-key deleted successfully !")
