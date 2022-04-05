#!/usr/bin/env bash

if [ -z "$1" ]; then
    echo 'No version number given'
    exit 1
fi

VERSION="$1"

sed -i '' "s/version=.*,/version='${VERSION}',/" setup.py
sed -i '' "s#download_url=.*,#download_url='https://github.com/rycus86/prometheus_flask_exporter/archive/${VERSION}.tar.gz',#" setup.py
sed -i '' "s/__version__ = '.*'/__version__ = '${VERSION}'/" prometheus_flask_exporter/__init__.py
sed -i '' "s/prometheus-flask-exporter==.*/prometheus-flask-exporter==${VERSION}/" README.md
