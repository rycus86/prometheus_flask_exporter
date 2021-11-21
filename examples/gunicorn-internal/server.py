from flask import Flask

from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

app = Flask(__name__)
metrics = GunicornInternalPrometheusMetrics(app)


@app.route('/test')
def index():
    return 'Hello world'


@app.route('/error')
def error():
    raise Exception('Fail')


if __name__ == '__main__':
    app.run(debug=False, port=5000)
