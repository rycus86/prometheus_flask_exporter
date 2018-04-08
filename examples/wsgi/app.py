from flask import Flask

from prometheus_client import multiprocess
from prometheus_client.core import CollectorRegistry
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry, path='/tmp')

metrics = PrometheusMetrics(app, registry=registry)


@app.route('/test')
def test():
    return 'OK'


if __name__ == '__main__':
    app.run()
