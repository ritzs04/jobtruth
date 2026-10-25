#!/usr/bin/env bash
# Removes everything setup_aws.sh created. Take your screenshots FIRST.
set -euo pipefail
source scripts/.deployed
REGION=ap-south-1

echo "== Terminating EC2 instance"
aws ec2 terminate-instances --region $REGION --instance-ids "$INSTANCE" >/dev/null
aws ec2 wait instance-terminated --region $REGION --instance-ids "$INSTANCE"
aws ec2 delete-security-group --region $REGION --group-id "$SG"

echo "== Deleting S3 bucket and all versions"
python3 - <<PY
import boto3
b = boto3.resource("s3", region_name="$REGION").Bucket("$BUCKET")
b.object_versions.delete()
b.delete()
PY

echo "== Deleting IAM role and policies"
aws iam remove-role-from-instance-profile --instance-profile-name jobtruth-ec2-role --role-name jobtruth-ec2-role
aws iam delete-instance-profile --instance-profile-name jobtruth-ec2-role
aws iam delete-role-policy --role-name jobtruth-ec2-role --policy-name s3-offers
aws iam delete-role-policy --role-name jobtruth-ec2-role --policy-name cloudwatch-metrics
aws iam delete-role --role-name jobtruth-ec2-role

echo "== Deleting Render IAM user (if it exists)"
aws iam delete-user-policy --user-name jobtruth-render --policy-name render-s3-offers 2>/dev/null || true
aws iam delete-access-key --user-name jobtruth-render \
  --access-key-id "$(aws iam list-access-keys --user-name jobtruth-render \
    --query 'AccessKeyMetadata[0].AccessKeyId' --output text 2>/dev/null)" 2>/dev/null || true
aws iam delete-user --user-name jobtruth-render 2>/dev/null || true

rm -f scripts/.deployed
echo "All JobTruth AWS resources removed."
