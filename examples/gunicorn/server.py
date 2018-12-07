from flask import Flask
from prometheus_client import multiprocess, CollectorRegistry

from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)

metrics = PrometheusMetrics(app, path=None, registry=registry)


@app.route('/test')
def index():
    return 'Hello world'


if __name__ == '__main__':
    metrics.start_http_server(9100)
    app.run(debug=False, port=5000)
