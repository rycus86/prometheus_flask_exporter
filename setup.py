from distutils.core import setup

try:
    long_description = open('README.rst').read()
except IOError:
    long_description = open('README.md').read()

setup(
    name='prometheus_flask_exporter',
    packages=['prometheus_flask_exporter'],
    version='0.0.5',
    description='Prometheus metrics exporter for Flask',
    long_description=long_description,
    license='MIT',
    author='Viktor Adam',
    author_email='rycus86@gmail.com',
    url='https://github.com/rycus86/prometheus-flask-exporter',
    download_url='https://github.com/rycus86/prometheus-flask-exporter/archive/0.0.5.tar.gz',
    keywords=['prometheus', 'flask', 'monitoring', 'exporter'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ],
    install_requires=['prometheus_client', 'flask'],
)
