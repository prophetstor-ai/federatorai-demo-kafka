#!/bin/bash

while :
do
   oc exec -n federatorai `oc get pods -n federatorai|grep alameda-influx|grep Running|cut -d' ' -f1` -- influx -ssl -unsafeSsl -precision rfc3339 -username admin -password adminpass -database alameda_prediction -execute "select * from kafka_consumer_group_current_offset,kafka_topic_partition_current_offset order by time desc limit 1"
   sleep 20
done
