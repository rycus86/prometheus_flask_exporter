from flask import Flask
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

metrics = GunicornInternalPrometheusMetrics(app=None)


def create_app():
    app = Flask(__name__)
    metrics.init_app(app)
    return app
