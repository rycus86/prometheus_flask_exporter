from flask import Flask
from prometheus_flask_exporter.multiprocess import MultiprocessInternalPrometheusMetrics

app = Flask(__name__)
metrics = MultiprocessInternalPrometheusMetrics(app)


@app.route('/test')
def index():
    return 'Hello world'


if __name__ == '__main__':
    app.run('0.0.0.0', 4000, processes=5, threaded=False)
