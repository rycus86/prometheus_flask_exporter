from flask import Flask, request
from flask_restx import Resource, Api

from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics.for_app_factory()


def create_app():
    app = Flask(__name__)
    metrics.init_app(app)

    with app.app_context():
        setup_api(app)

        metrics.register_default(
            metrics.counter(
                'by_path_counter', 'Request count by request paths',
                labels={'path': lambda: request.path}
            )
        )

    metrics.register_default(
        metrics.counter(
            'outside_context',
            'Example default registration outside the app context',
            labels={'endpoint': lambda: request.endpoint}
        ),
        app=app
    )

    return app


def setup_api(app):
    api = Api()
    api.init_app(app)

    @api.route('/test')
    class ExampleEndpoint(Resource):
        def get(self):
            return {'hello': 'world'}


if __name__ == '__main__':
    app = create_app()
    app.run('0.0.0.0', 4000)
