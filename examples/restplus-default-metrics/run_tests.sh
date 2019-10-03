#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    echo "Logs from the application:"
    docker logs restplus-default-metrics
    docker rm -f restplus-default-metrics > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t restplus-default-metrics ../../. > /dev/null || _fail
docker run -d --name restplus-default-metrics -p 4000:4000 restplus-default-metrics > /dev/null || _fail

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
    curl -s http://localhost:4000/test > /dev/null
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

curl -s http://localhost:4000/metrics

curl -s http://localhost:4000/metrics \
  | grep 'by_path_counter_total{path="/test"} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

curl -s http://localhost:4000/metrics \
  | grep 'outside_context_total{endpoint="example_endpoint"} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

docker rm -f restplus-default-metrics > /dev/null
echo 'OK, all done'
