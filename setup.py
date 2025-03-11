from pathlib import Path
from setuptools import setup

long_description = Path('README.md').read_text()

setup(
    name='prometheus_flask_exporter',
    packages=['prometheus_flask_exporter'],
    version='0.23.2',
    description='Prometheus metrics exporter for Flask',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    author='Viktor Adam',
    author_email='rycus86@gmail.com',
    url='https://github.com/rycus86/prometheus_flask_exporter',
    download_url='https://github.com/rycus86/prometheus_flask_exporter/archive/0.23.2.tar.gz',
    keywords=['prometheus', 'flask', 'monitoring', 'exporter'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    install_requires=['prometheus_client', 'flask'],
)
