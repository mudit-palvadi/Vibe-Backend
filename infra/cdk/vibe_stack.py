from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_cloudfront as cloudfront,
)
from aws_cdk import (
    aws_cloudfront_origins as origins,
)
from aws_cdk import (
    aws_dynamodb as ddb,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct

ROOT = Path(__file__).resolve().parent.parent.parent
LAMBDA_ZIP = ROOT / "build" / "lambda.zip"

SESSION_SECRET_PARAMETER = "/vibe/session-secret"


class VibeStack(Stack):
    """the whole backend of the app, the table, the function, and the files"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        media_base_url: str = "",
        google_client_id: str = "",
        waf_acl_arn: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # the free tier only pays for the provisioned capacity, so the table
        # is not on demand
        self.table = ddb.Table(
            self,
            "VibeTable",
            table_name="vibe",
            partition_key=ddb.Attribute(name="PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="SK", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PROVISIONED,
            read_capacity=15,
            write_capacity=15,
            point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=False,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # the bucket with the song files, it is private, only cloudfront can
        # read the files
        media_bucket = s3.Bucket(
            self,
            "MediaBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="remove-unfinished-uploads",
                    prefix="tmp/",
                    expiration=Duration.days(1),
                )
            ],
        )

        role = iam.Role(
            self,
            "ApiRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:TransactWriteItems",
                ],
                resources=[self.table.table_arn],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:HeadObject",
                ],
                resources=[media_bucket.arn_for_objects("*")],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter{SESSION_SECRET_PARAMETER}"
                ],
            )
        )

        log_group = logs.LogGroup(
            self,
            "ApiLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.function = lambda_.Function(
            self,
            "ApiFunction",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="app.lambda_handler.handler",
            code=lambda_.Code.from_asset(str(LAMBDA_ZIP)),
            memory_size=512,
            timeout=Duration.seconds(30),
            role=role,
            log_group=log_group,
            environment={
                "DB_BACKEND": "dynamodb",
                "DYNAMODB_TABLE_NAME": self.table.table_name,
                "S3_BUCKET": media_bucket.bucket_name,
                "MEDIA_BASE_URL": media_base_url,
                "SESSION_SECRET_PARAMETER": SESSION_SECRET_PARAMETER,
                "GOOGLE_CLIENT_ID": google_client_id,
                "LEGACY_UPLOAD_ENABLED": "false",
            },
        )

        # only cloudfront may call the function, the requests are signed
        function_url = self.function.add_function_url(auth_type=lambda_.FunctionUrlAuthType.AWS_IAM)
        cloudfront_service = iam.ServicePrincipal("cloudfront.amazonaws.com")
        function_url.grant_invoke_url(cloudfront_service)
        self.function.grant_invoke(cloudfront_service)

        # the origin access controls keep the bucket and the function private
        media_oac = cloudfront.S3OriginAccessControl(
            self,
            "MediaOac",
            origin_access_control_name="vibe-media",
            signing=cloudfront.Signing(
                protocol=cloudfront.SigningProtocol.SIGV4,
                behavior=cloudfront.SigningBehavior.ALWAYS,
            ),
        )
        api_oac = cloudfront.FunctionUrlOriginAccessControl(
            self,
            "ApiOac",
            origin_access_control_name="vibe-api",
            signing=cloudfront.Signing(
                protocol=cloudfront.SigningProtocol.SIGV4,
                behavior=cloudfront.SigningBehavior.ALWAYS,
            ),
        )

        self.distribution = cloudfront.Distribution(
            self,
            "Cdn",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.FunctionUrlOrigin.with_origin_access_control(
                    function_url,
                    origin_access_control=api_oac,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
            ),
            additional_behaviors={
                "/songs/*": cloudfront.BehaviorOptions(
                    origin=origins.S3BucketOrigin.with_origin_access_control(
                        media_bucket,
                        origin_access_control=media_oac,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                )
            },
            web_acl_id=waf_acl_arn or None,
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            http_version=cloudfront.HttpVersion.HTTP2_AND_3,
            comment="the vibe app",
        )

        CfnOutput(self, "TableName", value=self.table.table_name)
        CfnOutput(self, "BucketName", value=media_bucket.bucket_name)
        CfnOutput(self, "ApiUrl", value=f"https://{self.distribution.distribution_domain_name}")
        CfnOutput(self, "FunctionUrl", value=function_url.url)
