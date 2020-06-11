from flask import Flask
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

metrics = GunicornInternalPrometheusMetrics.for_app_factory()


def create_app():
    app = Flask(__name__)
    metrics.init_app(app)
    return app
