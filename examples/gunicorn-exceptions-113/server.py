from flask import Flask
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

application = Flask(__name__)
metrics = GunicornInternalPrometheusMetrics(application)

# static information as metric
metrics.info('app_info', 'Application info', version='1.0.3')


@application.route('/test')
def main():
    raise Exception("Crashing")
    pass  # requests tracked by default


if __name__ == '__main__':
    application.run(debug=False, port=5000)
