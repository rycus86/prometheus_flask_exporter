#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker logs uwsgi-connexion
    docker rm -f uwsgi-connexion > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t uwsgi-connexion ../../. > /dev/null || _fail
docker run -d --name uwsgi-connexion -p 4000:4000 uwsgi-connexion > /dev/null || _fail

echo 'Waiting for the server to start...'

for _ in $(seq 1 10); do
    if curl -fs http://localhost:4000/metrics > /dev/null; then
        break
    else
        sleep 0.2
    fi
done

echo 'Starting the tests...'

for _ in $(seq 1 10); do
    curl -s -i http://localhost:4000/test | grep 'Content-Type: application/json' -q
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

for _ in $(seq 1 7); do
    curl -s -i http://localhost:4000/plain | grep 'Content-Type: text/plain' -q
    if [ "$?" != "0" ]; then
        echo 'Failed to request the plain endpoint'
        _fail
    fi
done

curl -s http://localhost:4000/metrics \
  | grep 'test_by_status_count{code="200"} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

curl -s http://localhost:4000/metrics \
  | grep 'test_plain_total 7.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

docker rm -f uwsgi-connexion > /dev/null
echo 'OK, all done'
