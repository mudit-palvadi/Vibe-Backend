from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as ddb
from constructs import Construct


class VibeStack(Stack):
    """the whole backend of the app, the table, the function, and the files"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
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
            read_capacity_units=15,
            write_capacity_units=15,
            point_in_time_recovery=False,
            removal_policy=RemovalPolicy.DESTROY,
        )

        CfnOutput(self, "TableName", value=self.table.table_name)
