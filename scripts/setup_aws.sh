#!/usr/bin/env bash
# Creates: private/encrypted/versioned S3 bucket, least-privilege IAM role, security group, EC2 instance
# that builds and runs JobTruth from your public GitHub repo.
# Usage: REPO_URL=https://github.com/YOU/jobtruth.git ./scripts/setup_aws.sh
set -euo pipefail
: "${REPO_URL:?Set REPO_URL to your public GitHub repo URL}"
: "${HMAC_SECRET:?Set HMAC_SECRET before running this script}"
: "${JWT_SECRET_KEY:?Set JWT_SECRET_KEY before running this script}"
REGION=ap-south-1
BUCKET=jobtruth-$(date +%s)
ROLE=jobtruth-ec2-role
SG=jobtruth-sg
MYIP=$(curl -s https://checkip.amazonaws.com)
ITYPE=${INSTANCE_TYPE:-t2.micro}    # t2.micro is free-tier eligible (750 hrs/month for 12 months)

echo "== S3 bucket: $BUCKET"
aws s3api create-bucket --bucket "$BUCKET" --region $REGION \
  --create-bucket-configuration LocationConstraint=$REGION >/dev/null
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-tagging --bucket "$BUCKET" \
  --tagging 'TagSet=[{Key=Project,Value=JobTruth},{Key=Course,Value=CloudComputing}]'
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "{
 \"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"DenyInsecureTransport\",
 \"Effect\":\"Deny\",\"Principal\":\"*\",\"Action\":\"s3:*\",
 \"Resource\":[\"arn:aws:s3:::$BUCKET\",\"arn:aws:s3:::$BUCKET/*\"],
 \"Condition\":{\"Bool\":{\"aws:SecureTransport\":\"false\"}}}]}"
aws s3api put-bucket-lifecycle-configuration --bucket "$BUCKET" --lifecycle-configuration \
 '{"Rules":[{"ID":"expire-offers","Status":"Enabled","Filter":{"Prefix":"offers/"},
 "Expiration":{"Days":30},"NoncurrentVersionExpiration":{"NoncurrentDays":30},
 "AbortIncompleteMultipartUpload":{"DaysAfterInitiation":1}}]}'

echo "== IAM role (least privilege)"
aws iam create-role --role-name $ROLE --assume-role-policy-document \
 '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
aws iam put-role-policy --role-name $ROLE --policy-name s3-offers --policy-document "{
 \"Version\":\"2012-10-17\",\"Statement\":[
 {\"Effect\":\"Allow\",\"Action\":[\"s3:PutObject\",\"s3:GetObject\",\"s3:DeleteObject\"],\"Resource\":\"arn:aws:s3:::$BUCKET/offers/*\"},
 {\"Effect\":\"Allow\",\"Action\":[\"s3:ListBucket\",\"s3:ListBucketVersions\"],\"Resource\":\"arn:aws:s3:::$BUCKET\",
  \"Condition\":{\"StringLike\":{\"s3:prefix\":[\"offers/*\"]}}}]}"
aws iam put-role-policy --role-name $ROLE --policy-name cloudwatch-metrics --policy-document '{
 "Version":"2012-10-17","Statement":[{
  "Effect":"Allow","Action":"cloudwatch:PutMetricData","Resource":"*",
  "Condition":{"StringEquals":{"cloudwatch:namespace":"JobTruth"}}
 }]}'
aws iam create-instance-profile --instance-profile-name $ROLE >/dev/null
aws iam add-role-to-instance-profile --instance-profile-name $ROLE --role-name $ROLE
sleep 25   # IAM propagation (15 s is sometimes too short)

echo "== Security group"
SGID=$(aws ec2 create-security-group --group-name $SG --description "JobTruth" \
  --region $REGION --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id "$SGID" --region $REGION \
  --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null
aws ec2 authorize-security-group-ingress --group-id "$SGID" --region $REGION \
  --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null

echo "== EC2 launch"
AMI=$(aws ssm get-parameter --region $REGION \
  --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query Parameter.Value --output text)

# Quoting 'EOF' prevents the outer shell from expanding variables inside the heredoc.
# The EC2 instance will receive the literal variable names and expand them at boot time.
cat > /tmp/userdata.sh <<'HEREDOC'
#!/bin/bash
set -euo pipefail
dnf install -y git docker
systemctl enable --now docker
git clone REPO_URL_PLACEHOLDER /opt/jobtruth
cd /opt/jobtruth
docker build -t jobtruth .
docker run -d --restart always -p 80:8000 \
  -e S3_BUCKET=BUCKET_PLACEHOLDER \
  -e AWS_REGION=REGION_PLACEHOLDER \
  -e HMAC_SECRET=HMAC_PLACEHOLDER \
  -e JWT_SECRET_KEY=JWT_PLACEHOLDER \
  jobtruth
HEREDOC

# Now substitute the actual values into the userdata file
sed -i "s|REPO_URL_PLACEHOLDER|$REPO_URL|g"     /tmp/userdata.sh
sed -i "s|BUCKET_PLACEHOLDER|$BUCKET|g"          /tmp/userdata.sh
sed -i "s|REGION_PLACEHOLDER|$REGION|g"          /tmp/userdata.sh
sed -i "s|HMAC_PLACEHOLDER|$HMAC_SECRET|g"       /tmp/userdata.sh
sed -i "s|JWT_PLACEHOLDER|$JWT_SECRET_KEY|g"     /tmp/userdata.sh

# HttpPutResponseHopLimit=2 lets the Docker container read the instance-role credentials (IMDSv2)
IID=$(aws ec2 run-instances --region $REGION --image-id "$AMI" --instance-type "$ITYPE" \
  --security-group-ids "$SGID" --iam-instance-profile Name=$ROLE \
  --metadata-options "HttpTokens=required,HttpPutResponseHopLimit=2,HttpEndpoint=enabled" \
  --user-data file:///tmp/userdata.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=jobtruth},{Key=Project,Value=JobTruth}]' \
  --query 'Instances[0].InstanceId' --output text)
aws ec2 wait instance-running --region $REGION --instance-ids "$IID"
IP=$(aws ec2 describe-instances --region $REGION --instance-ids "$IID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

{ echo "BUCKET=$BUCKET"; echo "INSTANCE=$IID"; echo "SG=$SGID"; echo "IP=$IP"; } > scripts/.deployed
echo
echo "Done. Wait about 3-4 minutes for the Docker build, then open http://$IP"
echo "Bucket for the Render env var S3_BUCKET: $BUCKET"
