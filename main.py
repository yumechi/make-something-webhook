from chalice import Chalice

app = Chalice(app_name='make_something_kibela')

@app.route('/')
def index():
    return {'hello': 'world'}
