import os
import uuid

import boto3
import pytest
from contracts import Repositories, RepositoryContract

from app.repositories.dynamodb_repositories import (
    DynamoDbFavouriteRepository,
    DynamoDbPlaylistRepository,
    DynamoDbSongRepository,
    DynamoDbUserRepository,
)

REGION = os.environ.get("AWS_REGION", "ap-south-1")


def _clear_table(table) -> None:
    """the table is shared by the tests, so it is emptied before every one"""
    while True:
        response = table.scan(ProjectionExpression="PK,SK")
        items = response.get("Items", [])
        if not items:
            return
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})


@pytest.fixture(scope="module")
def dynamodb_table():
    if not os.environ.get("RUN_DYNAMODB_TESTS"):
        pytest.skip("set RUN_DYNAMODB_TESTS=1 to run the dynamodb contract tests")

    client = boto3.client("dynamodb", region_name=REGION)
    table_name = f"vibe-test-{uuid.uuid4().hex[:8]}"

    client.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    client.get_waiter("table_exists").wait(TableName=table_name)

    table = boto3.resource("dynamodb", region_name=REGION).Table(table_name)

    yield table

    client.delete_table(TableName=table_name)
    client.get_waiter("table_not_exists").wait(TableName=table_name)


@pytest.fixture()
def table(dynamodb_table):
    _clear_table(dynamodb_table)
    return dynamodb_table


class TestDynamoDbRepositories(RepositoryContract):
    """the contract the dynamodb repositories have to keep"""

    def make_repositories(self, table) -> Repositories:
        return Repositories(
            users=DynamoDbUserRepository(table),
            songs=DynamoDbSongRepository(table),
            playlists=DynamoDbPlaylistRepository(table),
            favourites=DynamoDbFavouriteRepository(table),
        )

    @pytest.fixture()
    def repos(self, table):
        return self.make_repositories(table)
