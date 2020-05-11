#!/bin/bash
rm -rf metrics
rm -rf picture
rm -rf traffic
rm -rf alameda*
rm -rf k8shpa*
rm -rf nonhpa*
kubectl apply -f config/kafka-cli.yaml

sleep 15
kubectl -n myproject exec kafka-cli > /dev/null 2>&1 -- bin/kafka-topics.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --delete --topic topic0001
kubectl -n myproject exec kafka-cli > /dev/null 2>&1 -- bin/kafka-consumer-groups.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --delete --group group0001