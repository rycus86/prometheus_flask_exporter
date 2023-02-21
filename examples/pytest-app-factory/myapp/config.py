from flask import Flask
from .extensions import setup_extensions, metrics

metrics.info('app_info', 'Sample app', version='0.1.2')


class TestConfig:
    DEBUG = False
    TESTING = True


def create_app(config):
    app = Flask('Example app')
    app.config.from_object(config)

    setup_extensions(app)

    return app
