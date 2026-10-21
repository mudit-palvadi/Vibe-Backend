#!/usr/bin/env python3
import os

import aws_cdk as cdk
import boto3
from botocore.exceptions import ClientError

from edge_stack import WEB_ACL_NAME, EdgeStack
from vibe_stack import SESSION_SECRET_PARAMETER, VibeStack

app = cdk.App()

account = os.environ.get("CDK_DEFAULT_ACCOUNT")

# the cdk cli sets the default region to the region of the first stack, so the
# regions are kept here and not taken from the environment
REGION = "ap-south-1"
EDGE_REGION = "us-east-1"
GOOGLE_CLIENT_ID_PARAMETER = "/vibe/google-client-id"


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


def read_parameter(name: str) -> str:
    """reads a value from the parameter store, an empty string when it is not there"""
    client = boto3.client("ssm", region_name=REGION)

    try:
        return client.get_parameter(Name=name)["Parameter"]["Value"]
    except Exception:
        return ""


def find_web_acl_arn() -> str:
    """the web acl of cloudfront is global, so it lives in us east one"""
    client = boto3.client("wafv2", region_name=EDGE_REGION)

    try:
        web_acls = client.list_web_acls(Scope="CLOUDFRONT")["WebACLs"]
    except Exception as e:
        print(f"the web acl could not be read: {e}")
        return ""

    for web_acl in web_acls:
        if web_acl["Name"] == WEB_ACL_NAME:
            return web_acl["ARN"]

    return ""


def find_api_url() -> str:
    """the address of the distribution that is already up, the song links point
    at it"""
    client = boto3.client("cloudformation", region_name=REGION)

    try:
        stacks = client.describe_stacks(StackName="VibeStack")["Stacks"]
    except Exception:
        return ""

    for output in stacks[0].get("Outputs", []):
        if output["OutputKey"] == "ApiUrl":
            return output["OutputValue"].replace("https://", "").rstrip("/")

    return ""


ensure_session_secret()

VibeStack(
    app,
    "VibeStack",
    env=cdk.Environment(account=account, region=REGION),
    media_base_url=app.node.try_get_context("mediaBaseUrl") or find_api_url(),
    google_client_id=app.node.try_get_context("googleClientId")
    or read_parameter(GOOGLE_CLIENT_ID_PARAMETER),
    waf_acl_arn=app.node.try_get_context("wafAclArn") or find_web_acl_arn(),
)

EdgeStack(
    app,
    "EdgeStack",
    env=cdk.Environment(account=account, region=EDGE_REGION),
)

app.synth()
