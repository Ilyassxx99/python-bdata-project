import boto3

def create_key_pair(client):
    print("Creating SSH key project-key ...")
    keypair = client.describe_key_pairs(
                Filters=[
                {
            'Name': 'key-name',
            'Values': [
                'project-key',
                ]
                },
            ],
    )
    if (len(keypair["KeyPairs"])>0):
        print("Deleting previous key pair ...")
        delete_key_pair(client)
    keyPair = client.create_key_pair(
        KeyName='project-key'
        )
#r"C:\Users\ifezo\.ssh\project-key.pem"
#r"/data/key/project-key.pem"
    privateKey = keyPair["KeyMaterial"]
    f = open(r"/root/.kube/project-key.pem", "w")
    f.write(privateKey)
    f.close()
    print("SSH key project-key created successfully !")

def delete_key_pair(client):
    print("Deleting SSH key project-key ...")
    keyPair = client.delete_key_pair(
        KeyName='project-key'
        )
    print("SSH key project-key deleted successfully !")
