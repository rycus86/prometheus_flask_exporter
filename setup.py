from distutils.core import setup

setup(
    name='prometheus_flask_exporter',
    packages=['prometheus_flask_exporter'],
    version='0.0.2',
    description='Prometheus metrics exporter for Flask',
    author='Viktor Adam',
    author_email='rycus86@gmail.com',
    url='https://github.com/rycus86/prometheus-flask-exporter',
    download_url='https://github.com/rycus86/prometheus-flask-exporter/archive/0.0.2.tar.gz',
    keywords=['prometheus', 'flask', 'monitoring', 'exporter'],
    classifiers=[],
    install_requires=['prometheus_client'],
)
