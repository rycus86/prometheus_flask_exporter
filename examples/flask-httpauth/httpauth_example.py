from flask import Flask
from flask_httpauth import HTTPBasicAuth
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
auth = HTTPBasicAuth()
metrics = PrometheusMetrics(app, metrics_decorator=auth.login_required)


@auth.verify_password
def verify_credentials(username, password):
    return (username, password) == ('metrics', 'test') or \
           (username, password) == ('user', 'pass')


@app.route('/test')
@auth.login_required
def index():
    return 'Hello world'


if __name__ == '__main__':
    app.run('0.0.0.0', 4000)
