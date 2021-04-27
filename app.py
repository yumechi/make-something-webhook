from chalice import Chalice

app = Chalice(app_name='make_something')

@app.route('/kibela', methods=['POST'])
def kibela_webhook():
    body = app.current_request.json_body
    print(body)
    return {'mode': 'kibela'}

@app.route('/backlog', methods=['POST'])
def backlog_webhook():
    body = app.current_request.json_body
    print(body)
    return {'mode': 'backlog'}
