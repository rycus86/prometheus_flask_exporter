from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics


metrics = GunicornInternalPrometheusMetrics.for_app_factory(group_by="endpoint")


def setup_extensions(app):
    metrics.init_app(app)
    return app
