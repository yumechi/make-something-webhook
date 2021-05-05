from chalice import Chalice
import os
from typing import Dict, Any

app = Chalice(app_name="make_something")


def post_content(url: str, req_body: Dict[str, Any]):
    import requests
    import json

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Yumechi WebHook/1.0",
    }
    # NOTE: headerの指定とjson.dumpをかますとembedsのPOSTがうまくいくようになる
    # refer: https://jibundex.com/python/webhook-python
    res = requests.post(url, data=json.dumps(req_body), headers=headers)
    if res.status_code >= 400:
        body = app.current_request.json_body
        print(f"discord post error: {res.text}")
        print(f"req_body={req_body}")
        # TODO: S3に書き出してデバッグ可能にしておく
        print(f"body={body}")


@app.route("/healthz", methods=["GET"])
def healthz_resource():
    return {"status": "ok"}


@app.route("/kibela", methods=["POST"])
def kibela_webhook():
    from chalicelib.parse_kibela import create_post_body

    body = app.current_request.json_body
    request_body = create_post_body(body)

    webhook_url = os.environ.get("KIBELA_WEBHOOK_URL")
    post_content(webhook_url, request_body)
    # TODO: レスポンスもログ出しも雑
    return {"mode": "kibela"}


@app.route("/backlog", methods=["POST"])
def backlog_webhook():
    from chalicelib.parse_backlog import create_post_body

    body = app.current_request.json_body
    request_body = create_post_body(body)

    webhook_url = os.environ.get("BACKLOG_WEBHOOK_URL")
    post_content(webhook_url, request_body)
    # TODO: レスポンスもログ出しも雑
    return {"mode": "backlog"}
