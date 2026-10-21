#!/usr/bin/env python3
import os

import aws_cdk as cdk

from vibe_stack import VibeStack

app = cdk.App()

VibeStack(
    app,
    "VibeStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "ap-south-1"),
    ),
)

app.synth()
