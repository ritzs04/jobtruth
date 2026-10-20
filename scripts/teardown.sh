#!/usr/bin/env bash
# Removes everything setup_aws.sh created. Take your screenshots FIRST.
set -euo pipefail
source scripts/.deployed
REGION=ap-south-1
aws ec2 terminate-instances --region $REGION --instance-ids "$INSTANCE" >/dev/null
aws ec2 wait instance-terminated --region $REGION --instance-ids "$INSTANCE"
aws ec2 delete-security-group --region $REGION --group-id "$SG"
python3 - <<PY
import boto3
b = boto3.resource("s3", region_name="$REGION").Bucket("$BUCKET")
b.object_versions.delete()   # all versions and delete markers
b.delete()
PY
aws iam remove-role-from-instance-profile --instance-profile-name jobtruth-ec2-role --role-name jobtruth-ec2-role
aws iam delete-instance-profile --instance-profile-name jobtruth-ec2-role
aws iam delete-role-policy --role-name jobtruth-ec2-role --policy-name s3-offers
aws iam delete-role --role-name jobtruth-ec2-role
rm -f scripts/.deployed
echo "All JobTruth AWS resources removed."
