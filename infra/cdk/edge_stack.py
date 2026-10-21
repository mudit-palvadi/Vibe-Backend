from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_wafv2 as wafv2
from constructs import Construct

WEB_ACL_NAME = "vibe-web-acl"


class EdgeStack(Stack):
    """the web acl of the app, it has to live in us east 1 because the
    cloudfront web acl is a global resource

    this stack is not deployed while the account is on the free plan, a
    cloudfront web acl costs money every month. it comes back when the
    account is on the paid plan and the flat rate plan is used"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.web_acl = wafv2.CfnWebACL(
            self,
            "WebAcl",
            name=WEB_ACL_NAME,
            scope="CLOUDFRONT",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(
                allow=wafv2.CfnWebACL.AllowActionProperty()
            ),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="vibe",
                sampled_requests_enabled=True,
            ),
            rules=[
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimit",
                    priority=0,
                    action=wafv2.CfnWebACL.RuleActionProperty(
                        block=wafv2.CfnWebACL.BlockActionProperty()
                    ),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=2000,
                            aggregate_key_type="IP",
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimit",
                        sampled_requests_enabled=True,
                    ),
                )
            ],
        )

        CfnOutput(self, "WebAclArn", value=self.web_acl.attr_arn)
