from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)


@app.route('/test')
def index():
    return 'Hello world'


@app.route('/ping')
@metrics.do_not_track()
def ping():
    return 'pong'


if __name__ == '__main__':
    app.run('0.0.0.0', 4000, debug=True)
