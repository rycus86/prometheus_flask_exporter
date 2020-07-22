from flask import Flask, request
from flask_restful import Resource, Api
from prometheus_flask_exporter import RESTfulPrometheusMetrics

app = Flask(__name__)
restful_api = Api(app)

metrics = RESTfulPrometheusMetrics.for_app_factory()


class Test(Resource):
    status = 200

    @staticmethod
    @metrics.summary('test_by_status', 'Test Request latencies by status', labels={
        'code': lambda r: r.status_code
    })
    def get():
        if 'fail' in request.args:
            return None, 400
        else:
            return None, 200


restful_api.add_resource(Test, '/api/v1/test', endpoint='test')


if __name__ == '__main__':
    metrics.init_app(app, restful_api)
    app.run('0.0.0.0', 4000)
