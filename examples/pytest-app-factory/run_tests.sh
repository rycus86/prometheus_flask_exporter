#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker logs pytest-sample
    docker rm -f pytest-sample > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t pytest-sample ../../. > /dev/null || _fail
docker run --rm --name pytest-sample pytest-sample py.test test

if [ "$?" != "0" ]; then
    echo 'Failed to execute the tests'
    _fail
fi

docker rm -f pytest-sample > /dev/null
echo 'OK, all done'
