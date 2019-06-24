from flask import Flask, Blueprint, request
from flask_restful import Resource, Api
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
blueprint = Blueprint('api_v1', __name__, url_prefix='/api/v1')
restful_api = Api(blueprint)

metrics = PrometheusMetrics(app)


class Test(Resource):
    status = 200

    @staticmethod
    @metrics.summary('test_by_status', 'Test Request latencies by status', labels={
        'code': lambda r: r.status_code
    })
    def get():
        if 'fail' in request.args:
            return 'Not OK', 400
        else:
            return 'OK'


restful_api.add_resource(Test, '/test', endpoint='test')
app.register_blueprint(blueprint)


if __name__ == '__main__':
    app.run('0.0.0.0', 4000)
