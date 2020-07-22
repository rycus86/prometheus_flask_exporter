import connexion
from prometheus_flask_exporter import ConnexionPrometheusMetrics

app = connexion.App(__name__)
metrics = ConnexionPrometheusMetrics(app)


if __name__ == '__main__':
    app.add_api('my_api.yaml')
    app.app.run(host='0.0.0.0', port=4000, use_reloader=False)
