from app.lambda_handler import handler


def build_event(path: str = "/", method: str = "GET") -> dict:
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {
            "host": "example.com",
            "user-agent": "curl/8.0",
            "x-forwarded-proto": "https",
            "x-forwarded-port": "443",
            "x-forwarded-for": "1.2.3.4",
        },
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "domainName": "example.com",
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "1.2.3.4",
                "userAgent": "curl/8.0",
            },
            "requestId": "request-id",
            "routeKey": "$default",
            "stage": "$default",
            "timeEpoch": 1583348638390,
        },
        "isBase64Encoded": False,
    }


def test_the_handler_answers_the_root_path():
    response = handler(build_event(), {})

    assert response["statusCode"] == 200
    assert "Vibe backend running" in response["body"]


def test_the_handler_answers_an_unknown_path_with_a_not_found():
    response = handler(build_event("/does-not-exist"), {})

    assert response["statusCode"] == 404
