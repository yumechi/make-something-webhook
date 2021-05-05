from chalice import Chalice
import os
from typing import Dict, Any, Optional

app = Chalice(app_name="make_something")


def post_content(url: str, req_body: Dict[str, Any]) -> Optional[str]:
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
        return res.text
    return ""


@app.route("/healthz", methods=["GET"])
def healthz_resource():
    return {"status": "ok"}


@app.route("/kibela", methods=["POST"])
def kibela_webhook():
    from chalicelib.parse_kibela import create_post_body

    body = app.current_request.json_body
    request_body = create_post_body(body)

    # テストボディがなぜかaction_type=send, resource=testで来るので、その際はボディができない
    if not request_body:
        return {
            "status": "skip",
            "reason": "test request",
        }

    webhook_url = os.environ.get("KIBELA_WEBHOOK_URL")
    result = post_content(webhook_url, request_body)
    if not result:
        return {
            "status": "OK",
            "reason": "",
        }
    else:
        return {
            "status": "Discord POST Failed.",
            "reason": result,
        }


@app.route("/backlog", methods=["POST"])
def backlog_webhook():
    from chalicelib.parse_backlog import create_post_body

    body = app.current_request.json_body
    request_body = create_post_body(body)

    webhook_url = os.environ.get("BACKLOG_WEBHOOK_URL")
    result = post_content(webhook_url, request_body)

    if not result:
        return {
            "status": "OK",
            "reason": "",
        }
    else:
        return {
            "status": "Discord POST Failed.",
            "reason": result,
        }
