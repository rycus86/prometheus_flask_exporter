import pytest
import prometheus_client
from flask import Flask
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

from myapp.config import create_app
from myapp import extensions as myapp_extensions


@pytest.fixture()
def app() -> Flask:
    app = create_app('myapp.config.TestConfig')
    prometheus_client.REGISTRY = prometheus_client.CollectorRegistry(auto_describe=True)
    myapp_extensions.metrics = GunicornInternalPrometheusMetrics(app=None, group_by="endpoint")
    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()


def test_http_200(app):
    @app.route('/test')
    def test():
        return 'OK'

    client = app.test_client()
    client.get('/test')

    response = client.get('/metrics')
    assert response.status_code == 200
    assert 'flask_http_request_total' in str(response.data)
    assert 'endpoint="test"' in str(response.data)


def test_http_404(app):
    @app.route('/test')
    def test():
        return 'OK'

    client = app.test_client()
    client.get('/not-found')

    response = client.get('/metrics')
    assert response.status_code == 200
    assert 'flask_http_request_total' in str(response.data)
    assert 'status="404"' in str(response.data)


def test_info(app):
    client = app.test_client()

    response = client.get('/metrics')
    assert response.status_code == 200
    assert 'app_info' in str(response.data)
    assert 'version="0.1.2"' in str(response.data)
