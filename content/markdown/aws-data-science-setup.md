Title: Deep Learning experiments in AWS
Date: 2019-02-15
Category: posts
Tags: aws, experiments, setup, workflow
Slug: aws-exp-setup
Author: Alex Kim

## What is this tutorial about?
This tutorial provides step-by-step instructions on how to set up a Data Science workflow in AWS that allows for easy experimentation, quick iteration through your ideas (e.g. various ML algorithms) while keeping the AWS bill under control.
It assumes you are familiar (at least at a high-level) with AWS services such as EC2, EBS, EFS and VPC.
If not, I'd recommend you read up on what each of these services does and come back to this tutorial later.
The steps below are essentially a sequence of bash commands that you would copy-paste into your terminal.
While the instructions will work for any type of EC2 instance, experimenting with Deep Learning is where it really shines compared to, for example, a local desktop, mainly, because it allows you to scale your GPU capacity up or down depending on the project as well as provides access to an unlimited data storage.

![image]({attach}/images/ec2_efs.png "EFS and multiple EC2 instances")
<font size="2"><span style="color:grey">Source: https://www.researchgate.net/figure/Amazon-Elastic-File-System-from-Amazon-2016_fig5_305508410</span></font>

## What is the end result?

After following these instructions, you will have:

- One (or more if needed) EC2 instance that is configured to your project's requirements (e.g. with or without a GPU)
- An EFS filesystem mounted to your EC2 instances for storing your data
- A VPC and a subnet that allows the above things to talk to each other while keeping everything secure

## What I like about it?
This setup keeps the data (on EFS) separate from the computing resources (on EC2), thus allowing me to:

- Test different ideas (Deep Learning architectures, sets of hyperparameters, etc.) in parallel using separate EC2 instances
- Keep my AWS bill from growing out of proportion to my usage

I consider this approach to be a lot more flexible and cost-efficient compared to spinning up an EC2 instance with a large EBS volume for storing your data for the following reasons:

- While EBS price ($0.10/GB/month) is lower than that of EFS ($0.30/GB/month), they have different a pricing structure. You will be paying for the former by the amount of storage you provision which means you need to know in advance how much storage you will need for you project. It is possible to increase the size of your EBS mount later, but it is not very convenient. EFS, however, allows you to store as much data as you need on the pay-as-you-go basis
- EFS has built-in redundancy: there is a much lower risk of losing your data when it is stored on EFS compared to EBS
- More importantly, unlike EBS mounts, EFS, being essentially AWS' implementation of the NFS protocol, has virtually no upper limit on how many EC2 instances it can be mounted to. This makes it a decent choice for either 1) quickly iterating through your ideas by running them in parallel on multiple EC2 instances or 2) collaborating with multiple people on a project that requires them having access to the same large dataset without the need to duplicate it

However, it is worth noting that EFS does have higher latency compared to EBS, but the gains in flexibility, in my opinion, far outweigh the latency concerns.

## Contents

1. [Prerequisites](#prerequisites)
2. [General AWS setup](#aws-setup)
3. [Configure first EC2 instance](#ec2commands)
4. [Create more instances](#more-instances)
5. [Tips](#tips)

<a name="prerequisites"></a>
### 1. Prerequisites
- EC2 key-pair stored somewhere on your machine (typically in `~/.ssh/`):

    - If not, see: [https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html)

- AWS Command Line Interface installed and configured on your local machine:

    - If not, see: [https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
    - Output format of `aws cli` needs to be set to `text` (the choice of the region name is up to you):
```bash
aws configure
> AWS Access Key ID [****************BLAH]:
> AWS Secret Access Key [****************abcd]:
> Default region name [us-east-1]:
> Default output format [json]: text
```

<a name="aws-setup"></a>
### 2. General AWS setup

- Set environment variables, including IPv4 network range for the VPC (`cidr_block`) and the base image (`base_ami_id`). Feel free to change to your desired values. Here I am using a [`p2.xlarge`](https://aws.amazon.com/ec2/instance-types/p2/) instance with a [`ami-0f9cf087c1f27d9b1`](https://aws.amazon.com/marketplace/pp/B077GCZ4GR) (Ubuntu-based Deep Learning Base AMI)
```bash
export my_aws_keyname="my_aws_keyname"
export my_aws_key="~/.ssh/my_aws_keyname.pem"
export cidr_block="10.0.0.0/28"
export instance_type="p2.xlarge" # e.g. use "p3.2xlarge" for a more powerful GPU or "t3.medium" for an instance without a GPU
export base_ami_id="ami-0f9cf087c1f27d9b1" # e.g. use "ami-03a935aafa6b52b97" for an AMI without CUDA drivers
export instance_key="MyInstanceKey"
export instance_value="MyInstanceValue"
export sg_name="MySecurityGroup"
export subnet_name="MySubnet"
export my_vpc_key="MyVpcKey"
export my_vpc_name="MyVPC"
export my_ami_name="MyAmiName"
```

- Create and name your VPC:
```bash
export vpc_id=$(aws ec2 create-vpc --cidr-block $cidr_block --query "Vpc.VpcId") && echo "VPN id: $vpc_id"
aws ec2 modify-vpc-attribute --vpc-id $vpc_id --enable-dns-hostnames
aws ec2 create-tags --resources $vpc_id  --tags Key=$my_vpc_key,Value=$my_vpc_name
```

- Create an Internet Gateway, a Route Table and a Subnet:
```bash
# Internet Gateway
export igw_id=$(aws ec2 create-internet-gateway --query "InternetGateway.InternetGatewayId") && echo "IGW id: $igw_id"
aws ec2 attach-internet-gateway --internet-gateway-id $igw_id --vpc-id $vpc_id
# Route Table
export rt_id=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$vpc_id" \
--query "RouteTables[].RouteTableId") && echo "Route Table id: $rt_id"
aws ec2 create-route --route-table-id $rt_id --gateway-id $igw_id --destination-cidr-block 0.0.0.0/0
# Subnet
export subnet_id=$(aws ec2 create-subnet --vpc-id $vpc_id --cidr-block $cidr_block \
--availability-zone us-east-1a  --query "Subnet.SubnetId") && echo "Subnet id: $subnet_id"
aws ec2 create-tags --resources $subnet_id  --tags "Key=Name,Value=$subnet_name"
aws ec2 associate-route-table --route-table-id $rt_id --subnet-id $subnet_id
```

- Create and configure a Security Group:
```bash
export sg_id=$(aws ec2 create-security-group --vpc-id $vpc_id \
--group-name $sg_name --description "My Security Group") && echo "Security Group id: $sg_id"
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol tcp \
--port 22 --cidr $(curl https://checkip.amazonaws.com)/32
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol tcp \
--port 8889 --cidr $(curl https://checkip.amazonaws.com)/32
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol tcp \
--port 2049 --cidr $cidr_block
```

- Create an EFS storage
```bash
export efs_id=$(aws efs create-file-system --creation-token "efs_token" --query "FileSystemId") && echo "EFS id: $efs_id"
```
You need to wait for a bit (5-10 s) after running this command for the EFS to fully initialize.

- Associate your EFS with your subnet and security group:
```bash
aws efs create-mount-target --file-system-id $efs_id --subnet-id $subnet_id --security-groups $sg_id
```

- Create your first EC2 instance (feel free to change `VolumeSize` to your desired value in GB):
```bash
aws ec2 run-instances --image-id $base_ami_id --count 1 --instance-type "$instance_type" \
--block-device-mapping "DeviceName=/dev/sda1,Ebs={VolumeSize=55}" --associate-public-ip-address \
--key-name $my_aws_keyname --subnet-id $subnet_id --security-group-ids $sg_id \
--tag-specifications "ResourceType=instance,Tags=[{Key=$instance_key,Value=$instance_value}]"
```
Wait another 15-20 s for the instance to initialize.

- Get the instance's id and ip values:
```bash
export ec2_id=$(aws ec2 describe-instances --filters "Name=tag:$instance_key,Values=$instance_value" \
--query "Reservations[].Instances[].InstanceId" --output text) && echo "EC2 id: $ec2_id"
export ec2_ip=$(aws ec2 describe-instances --filters "Name=tag:$instance_key,Values=$instance_value" \
--query "Reservations[].Instances[].PublicIpAddress" --output text) && echo "EC2 ip: $ec2_ip"
```

- Optionally, tag your instance (change `datascience_instance` to whatever you want):
```bash
aws ec2 create-tags --resources $ec2_id --tag "Key=Name,Value=datascience_instance"
```

- Export EFS id to the instance:
```bash
ssh -i $my_aws_key ubuntu@$ec2_ip "echo export efs_id=$efs_id >> ~/.bashrc"
```

<a name="ec2commands"></a>
### 3. Configure first EC2 instance
- SSH into the instance:
```bash
ssh -i $my_aws_key ubuntu@$ec2_ip
```

- Update list of packages and upgrade Ubuntu packages:
```bash
sudo apt-get update -y
sudo apt-get upgrade -y
```

- Mount EFS to the instance:
```bash
mkdir ~/downloads && cd ~/downloads
sudo apt-get -y install binutils
git clone https://github.com/aws/efs-utils && cd efs-utils/
./build-deb.sh
sudo apt-get -y install ./build/amazon-efs-utils*deb
sudo mkdir /efs
sudo mount -t efs $efs_id /efs
sudo chown -R ubuntu /efs
# confirm that EFS was mounted to /efs
df -h
# optionally create test file
echo "test" > /efs/testfile
```
- Edit fstab so that EFS get mounted after a restart
```bash
echo "$efs_id:/ /efs efs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
```

- Optionally, install whatever software you want all your future instances to have by default. If you chose a GPU instance earlier and plan to experiment with Deep Learning libraries, you might want to install the following:
```bash
# link cuda drivers
sudo ln -sfn /usr/local/cuda-9.2 /usr/local/cuda
# Install Anaconda Python
cd ~/downloads
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
unset PYTHONPATH
bash Miniconda3-latest-Linux-x86_64.sh -b
export PATH="/home/ubuntu/miniconda3/bin:$PATH"
echo 'PATH="/home/ubuntu/miniconda3/bin:$PATH"' >> ~/.bashrc
# Install Deep Learning libraries
conda install -y -c anaconda keras-gpu
conda install -y -c pytorch pytorch
...
```
- Exit the instance
- Create AMI:
```bash
export my_ami_id=$(aws ec2 create-image --instance-id $ec2_id --name $my_ami_name --query "ImageId") && echo "My AMI id: $my_ami_id"
```
This will take several minutes to complete.
<a name="more-instances"></a>
### 4. Create more instances (repeat as many times as needed throughout the lifetime of your project)
If, in the future, you need more instances (of the same or different type) that have access to the same EFS, you can achieve this by running the following commands.
- Set environment variables:
```bash
export new_instance_type="t3.small"
export new_instance_key="MyInstanceKey2"
export new_instance_value="MyInstanceValue2"
```
- Create new instance:
```bash
aws ec2 run-instances --image-id $my_ami_id --count 1 --instance-type "$new_instance_type" \
--block-device-mapping "DeviceName=/dev/sda1,Ebs={VolumeSize=55}" --associate-public-ip-address \
--key-name $my_aws_keyname --subnet-id $subnet_id --security-group-ids $sg_id \
--tag-specifications "ResourceType=instance,Tags=[{Key=$new_instance_key,Value=$new_instance_value}]" 
```
- Get new instance's id and ip:
```bash
export ec2_id_2=$(aws ec2 describe-instances --filters "Name=tag:$new_instance_key,Values=$new_instance_value" \
--query "Reservations[].Instances[].InstanceId" --output text) && echo "New instance id: $ec2_id_2"
export ec2_ip_2=$(aws ec2 describe-instances --filters "Name=tag:$new_instance_key,Values=$new_instance_value" \
--query "Reservations[].Instances[].PublicIpAddress" --output text) && echo "New instance ip: $ec2_ip_2"
```
- Name the instance:
```bash
aws ec2 create-tags --resources $ec2_id_2 --tag "Key=Name,Value=datascience_instance_2"
```

<a name="tips"></a>
### 5. Tips
- If you don't feel comfortable with `aws cli` yet, try and identify the changes (creation/configuration of new AWS resources) on the AWS dashboard.
- When [configuring your first EC2 instance](#ec2commands), try to install/configure everything you think you might need in other instances in the future. This will save you time when creating new instances from the saved AMI
- If you have `jupyter`, `jupyterlab` and `aws cli` installed, I recommend adding these aliases to your bash profile:
```bash
alias stop_instance="aws ec2 stop-instances --instance-ids $(wget -q -O - http://169.254.169.254/latest/meta-data/instance-id)"
alias start_jupyter="jupyter notebook --no-browser --ip=* --port=8889"
alias start_jupyterlab="jupyter lab --no-browser --ip=* --port=8889"
alias jupyterurl="jupyter notebook list | grep localhost | sed "s/localhost/$(dig +short myip.opendns.com @resolver1.opendns.com)/g""
```
The first command `stop_instance` will stop the instance from the inside (which will, obviously, log you out) and is useful if you need to start a long/overnight command and want to stop your instance as soon as the command is done running (or results in an error). E.g.:
```bash
python super_long_running_script.py; stop_instance
```
The second `start_jupyter` and the third one `start_jupyterlab` will start `jupyter` or `jupyterlab`, respectively, in the background mode (no browser) on port 8889. I recommend doing this in a `tmux` session.
Then the last command `jupyterurl` will print out a URL (that includes a secure token) for you to copy-paste into your browser and start coding.

Hope this helps!
If you encounter an issue, feel free to report it [here](https://github.com/alexkimxyz/alexkimxyz.github.io/issues)

-Alex


