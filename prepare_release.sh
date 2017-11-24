#!/usr/bin/env bash

if [ -z "$1" ]; then
    echo 'No version number given'
    exit 1
fi

VERSION="$1"

sed -i "s/version=.*,/version='${VERSION}',/" setup.py
sed -i "s#download_url=.*,#download_url='https://github.com/rycus86/prometheus-flask-exporter/archive/${VERSION}.tar.gz',#" setup.py
