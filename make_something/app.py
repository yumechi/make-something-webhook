from chalice import Chalice
import requests

app = Chalice(app_name='make_something')

def parse_backlog_model(data):
    return {
        "username": "uchia",
        "content": "うげー。。。",
    }


@app.route('/kibela', methods=['POST'])
def kibela_webhook():
    body = app.current_request.json_body
    print(body)
    return {'mode': 'kibela'}

@app.route('/backlog', methods=['POST'])
def backlog_webhook():
    body = app.current_request.json_body
    request_body = parse_backlog_model(body)
    requests.post(DISCORD_URL, data=request_body)
    return {'mode': 'backlog'}
