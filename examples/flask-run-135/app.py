from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics


app = Flask(__name__)
metrics = PrometheusMetrics(app)


@app.get('/info')
def info():
    import os
    return {'response': 'ok', 'env': dict(os.environ)}


if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=True, use_reloader=True)