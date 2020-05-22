import os
import sys
import yaml
import time
from define import topic_name, group_name, traffic_interval, initial_consumer, consumer_cpu_limit, consumer_memory_limit, consumer_pod_specified_node_key, consumer_pod_specified_node_value, producer_pod_specified_node_key, producer_pod_specified_node_value
from define import traffic_frequency, traffic_ratio, workload_type, config_path
from define import transaction_value, number_k8shpa, k8shpa_type
from producer import Producer
from client import Client
from oc import OC


def update_consumer_yaml():
    file_name = "%s/consumer-deployment.yaml" % config_path
    if number_k8shpa == 1 and k8shpa_type == "cpu":
        file_name = "%s/consumer-cpu-deployment.yaml" % config_path
    file_name_tmp = "%s.tmp" % file_name
    output = {}
    try:
        with open(file_name, "r") as f_r:
            output = yaml.load(f_r)
            new_cmd = "/opt/kafka/bin/kafka-verifiable-consumer.sh --broker-list my-cluster-kafka-brokers:9092 --group-instance-id $RANDOM --group-id %s --topic %s" % (group_name, topic_name)
            output["spec"]["replicas"] = initial_consumer
            output["spec"]["template"]["spec"]["containers"][0]["command"][-1] = new_cmd
            output["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["cpu"] = str(consumer_cpu_limit) + "m"
            output["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["memory"] = str(consumer_memory_limit) + "Mi"
            output["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["cpu"] = str(consumer_cpu_limit) + "m"
            output["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["memory"] = str(consumer_memory_limit) + "Mi"
            if consumer_pod_specified_node_key != "" and consumer_pod_specified_node_value != "":
                output["spec"]["template"]["spec"]["nodeSelector"] = {}
                output["spec"]["template"]["spec"]["nodeSelector"][consumer_pod_specified_node_key] = consumer_pod_specified_node_value
        with open(file_name_tmp, "w") as f_w:
            yaml.dump(output, f_w)
    except Exception as e:
        print "failed to update %s: %s" % (file_name, str(e))
        return -1
    print "success to update %s" % file_name
    os.rename(file_name_tmp, file_name)
    return 0


def update_producer_yaml():
    file_name = "%s/producer-deployment.yaml" % config_path
    file_name_tmp = "%s.tmp" % file_name
    output = {}
    try:
        with open(file_name, "r") as f_r:
            output = yaml.load(f_r)
            if producer_pod_specified_node_key != "" and producer_pod_specified_node_value != "":
                output["spec"]["template"]["spec"]["nodeSelector"] = {}
                output["spec"]["template"]["spec"]["nodeSelector"][producer_pod_specified_node_key] = producer_pod_specified_node_value
        with open(file_name_tmp, "w") as f_w:
            yaml.dump(output, f_w)
    except Exception as e:
        print "failed to update %s: %s" % (file_name, str(e))
        return -1
    print "success to update %s" % file_name
    os.rename(file_name_tmp, file_name)
    return 0


def apply_consumer_yaml():
    file_name = "%s/consumer-deployment.yaml" % config_path
    if number_k8shpa == 1 and k8shpa_type == "cpu":
        file_name = "%s/consumer-cpu-deployment.yaml" % config_path
    o = OC()
    output = o.apply_file(file_name)
    return output


def apply_producer_yaml():
    file_name = "%s/producer-deployment.yaml" % config_path
    o = OC()
    output = o.apply_file(file_name)
    return output


def delete_consumer_yaml():
    file_name = "%s/consumer-deployment.yaml" % config_path
    if number_k8shpa == 1 and k8shpa_type == "cpu":
        file_name = "%s/consumer-cpu-deployment.yaml" % config_path
    o = OC()
    output = o.delete_file(file_name)
    return output


def main(algo, count):
    p = Producer()
    c = Client()
    interval = traffic_frequency

    c.describe_topic(topic_name)
    c.describe_consumer_group(group_name)
    for i in range(interval):
        transaction_list = p.read_transaction_list()
        count1 = count % len(transaction_list)
        transaction = int(transaction_list[count1])
        if workload_type == "fix":
            transaction = transaction_value
        message_count = traffic_ratio * int(transaction/interval)

        start_time = time.time()
        producer_info = p.producer_per_test(topic_name, message_count)
        end_time = time.time()
        time_diff = end_time - start_time
        print "producers take %s time " % time_diff
        p.write_latency(algo, producer_info)
        # output = c.describe_consumer_group(group_name)
        # print output

        duration = int(60/interval)
        for i in range(int(duration)):
            p.wait_time(1)
            inter_end_time = time.time()
            if inter_end_time - start_time >= duration:
                break

    # if count == (traffic_interval-1):
    #    delete_consumer_yaml()
    #    c.delete_topic(topic_name)


if __name__ == "__main__":
    algo = sys.argv[1]
    count = int(sys.argv[2])
    main(algo, count)
