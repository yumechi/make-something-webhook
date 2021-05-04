from chalice import Chalice
import os
from typing import Dict, Any
import requests
from parse_model import parse_backlog_model, parse_kibela_model

app = Chalice(app_name='make_something')

def post_content(url: str, body: Dict[str, Any]):
    headers = {
        'Content-Type' : 'application/json',
        'User-Agent': 'Yumechi WebHook/1.0',
    }
    requests.post(url, data=body)


@app.route('/kibela', methods=['POST'])
def kibela_webhook():
    body = app.current_request.json_body
    request_body = parse_kibela_model(body)

    webhook_url = os.environ.get('WEBHOOK_URL')
    post_content(webhook_url, request_body)
    return {'mode': 'kibela'}

@app.route('/backlog', methods=['POST'])
def backlog_webhook():
    body = app.current_request.json_body
    request_body = parse_backlog_model(body)

    webhook_url = os.environ.get('WEBHOOK_URL')
    post_content(webhook_url, request_body)
    return {'mode': 'backlog'}
