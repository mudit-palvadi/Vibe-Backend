#!/usr/bin/env python3
import os

import aws_cdk as cdk
import boto3
from botocore.exceptions import ClientError

from edge_stack import EdgeStack
from vibe_stack import SESSION_SECRET_PARAMETER, VibeStack

app = cdk.App()

account = os.environ.get("CDK_DEFAULT_ACCOUNT")

# the cdk cli sets the default region to the region of the first stack, so the
# regions are kept here and not taken from the environment
REGION = "ap-south-1"
EDGE_REGION = "us-east-1"


def ensure_session_secret() -> None:
    """the secret that signs the session tokens, it is kept in the parameter
    store so it never ends up in the lambda settings"""
    client = boto3.client("ssm", region_name=REGION)

    try:
        client.get_parameter(Name=SESSION_SECRET_PARAMETER)
        return
    except ClientError:
        pass
    except Exception as e:
        print(f"the parameter store is not reachable, the secret is not checked: {e}")
        return

    import secrets

    client.put_parameter(
        Name=SESSION_SECRET_PARAMETER,
        Value=secrets.token_urlsafe(48),
        Type="String",
        Overwrite=False,
    )


ensure_session_secret()

VibeStack(
    app,
    "VibeStack",
    env=cdk.Environment(account=account, region=REGION),
    media_base_url=app.node.try_get_context("mediaBaseUrl") or "",
    google_client_id=app.node.try_get_context("googleClientId") or "",
    waf_acl_arn=app.node.try_get_context("wafAclArn") or "",
)

EdgeStack(
    app,
    "EdgeStack",
    env=cdk.Environment(account=account, region=EDGE_REGION),
)

app.synth()
