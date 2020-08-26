import connexion
from prometheus_flask_exporter import ConnexionPrometheusMetrics

app = connexion.App(__name__)
metrics = ConnexionPrometheusMetrics(app)

app.add_api('my_api.yaml')


if __name__ == '__main__':
    app.app.run(host='0.0.0.0', port=4000, use_reloader=False)
