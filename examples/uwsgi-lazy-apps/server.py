from flask import Flask

from prometheus_flask_exporter.multiprocess import UWsgiPrometheusMetrics

app = Flask(__name__)
metrics = UWsgiPrometheusMetrics(app)
metrics.register_endpoint('/metrics')


@app.route('/test')
def index():
    return 'Hello world'


if __name__ == '__main__':
    metrics.start_http_server(9100)
    app.run(debug=False, port=5000)
