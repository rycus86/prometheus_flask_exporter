from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics


metrics = GunicornInternalPrometheusMetrics(app=None, group_by="endpoint")


def setup_extensions(app):
    metrics.init_app(app)
    return app
