"""makes the s3 bucket and the rule that removes the uploads that were never finished"""

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

LIFECYCLE_RULE = {
    "ID": "remove-unfinished-uploads",
    "Status": "Enabled",
    "Filter": {"Prefix": "tmp/"},
    "Expiration": {"Days": 1},
}


def main():
    bucket = settings.S3_BUCKET
    if not bucket:
        raise SystemExit("S3_BUCKET is not set")

    client = boto3.client("s3", region_name=settings.S3_REGION)

    try:
        client.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": settings.S3_REGION},
        )
        print(f"created the bucket {bucket}")
    except ClientError as error:
        if error.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise
        print(f"the bucket {bucket} is already there")

    client.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration={"Rules": [LIFECYCLE_RULE]},
    )
    print("the rule that removes the unfinished uploads is set")


if __name__ == "__main__":
    main()
