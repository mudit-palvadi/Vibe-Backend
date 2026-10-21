#!/usr/bin/env python3
import os

import aws_cdk as cdk
import boto3
from botocore.exceptions import ClientError

from edge_stack import EdgeStack
from vibe_stack import SESSION_SECRET_PARAMETER, VibeStack

app = cdk.App()

account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION", "ap-south-1")


def ensure_session_secret() -> None:
    """the secret that signs the session tokens, it is kept in the parameter
    store so it never ends up in the lambda settings"""
    client = boto3.client("ssm", region_name=region)

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
    env=cdk.Environment(account=account, region=region),
    media_base_url=app.node.try_get_context("mediaBaseUrl") or "",
    google_client_id=app.node.try_get_context("googleClientId") or "",
    waf_acl_arn=app.node.try_get_context("wafAclArn") or "",
)

EdgeStack(
    app,
    "EdgeStack",
    env=cdk.Environment(account=account, region="us-east-1"),
)

app.synth()
