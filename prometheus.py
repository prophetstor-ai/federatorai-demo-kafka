import sys
import time
import os
import json
from kubectl import Kubectl
from oc import OC
from define import traffic_path, topic_name, group_name, log_interval
from define import query_interval, query_timeout, prometheus_operator_name

class Prometheus:
    
    host = "prometheus-k8s-openshift-monitoring.apps.172.31.5.135.nip.io"
    cmd = "%s/api/v1/query?query=" % host
    oc = OC()
    token = ""

    def __init__(self):
        host = self.get_host() 
        self.cmd = "%s/api/v1/query?query=" % host
        self.token = self.get_token()    

    def get_host(self):
        host = ""
        ret = self.oc.check_platform()
        if ret == 0:
            app_namespace = "openshift-monitoring"
            output = self.oc.get_routes(app_namespace)
            for line in output.split("\n"):
                if line.find(prometheus_operator_name) != -1:
                    host = line.split()[1]
        else:
            app_namespace = "monitoring"
            output = self.oc.get_service(app_namespace)
            for line in output.split("\n"):
                if line.find(prometheus_operator_name) != -1:
                    ip = line.split()[2]
                    port = line.split()[4].split("/")[0].split(":")[0]
                    host = "%s:%s" % (ip, port)  
        print "find host: %s" % host
        return host

    def get_token(self):
        token = ""
        token_name = ""
        namespace = "openshift-monitoring"
        name = "prometheus-k8s-token"
        output = self.oc.get_secret_by_specific_name(namespace, name)
        for line in output.split("\n"):
            if line.find(name) != -1:
                token_name = line.split()[0]
                break
        if token_name:
            output = self.oc.describe_secret(namespace, token_name)
            for line in output.split("\n"):
                if line.find("token:") != -1:
                    token = line.split()[1]
                    break
        #print "find token: ", token
        return token

    def run_cmd(self, metrics):
        cmd = "curl -g --insecure -s 'https://%s%s' -H 'Authorization: Bearer %s'" % (self.cmd, metrics, self.token)
        ret = self.oc.check_platform()
        if ret != 0:
            cmd = "curl -g -s 'http://%s%s'" % (self.cmd, metrics)
        #print cmd
        output = os.popen(cmd).read()
        #print output
        if output:
            output = json.loads(output)
        else:
            output = {}
        return output

    # cpu
    def get_pod_cpu_usage(self):
        metrics = "container_cpu_usage_seconds_total"
        output = self.run_cmd(metrics)
        return output

    def get_pod_cpu_usage_by_sum(self):
        cmd = 'sum(rate(container_cpu_usage_seconds_total{job="kubelet", image!="", container_name!=""}[5m])) by (namespace)'
        output = self.run_cmd(cmd)

        return output

    # memory
    def get_pod_memory_usage(self):
        metrics = "container_memory_usage_bytes"
        output = self.run_cmd(metrics)
        return output

    def get_pod_memory_failure(self):
        metrics = "container_memory_failure_total"
        output = self.run_cmd(metrics)
        return output

    def get_pod_memory_limits(self):
        metrics = "container_spec_memory_limits"
        output = self.run_cmd(metrics)
        return output 

    def get_pod_memory_max_usage(self):
        metrics = "container_spec_memory_max_usage"
        output = self.run_cmd(metrics)
        return output

    # network
    def get_pod_network_receive(self):
        metrics = "container_network_receive_bytes_total"
        output = self.run_cmd(metrics)
        return output

    def get_pod_network_transmit(self):
        metrics = "container_network_transmit_bytes_total"
        output = self.run_cmd(metrics)
        return output

    def get_pod_network_receive_error(self):
        metrics = "container_network_receive_error_total"
        output = self.run_cmd(metrics)
        return output

    def get_pod_network_transmit_error(self):
        metrics = "container_network_transmit_error_total"
        output = self.run_cmd(metrics)
        return output

    # filesystem
    def get_pod_fs_usage_bytes(self):
        metrics = "container_fs_usage_bytes"
        output = self.run_cmd(metrics)
        return output

    # pod limits/requests
    def get_pod_cpu_limits(self):
        metrics = "kube_pod_container_resource_limits_cpu_cores"
        output = self.run_cmd(metrics)
        return output

    def get_pod_memory_limits(self):
        metrics = "kube_pod_container_resource_limits_memory_bytes"
        output = self.run_cmd(metrics)
        return output

    def get_pod_cpu_requests(self):
        metrics = "kube_pod_container_resource_requests_cpu_cores"
        output = self.run_cmd(metrics)
        return output

    def get_pod_memory_requests(self):
        metrics = "kube_pod_container_resource_requests_memory_bytes"
        output = self.run_cmd(metrics)
        return output

    # kafka
    def get_kafka_metrics(self, metrics):
        output = self.run_cmd(metrics)
        return output

    def wait_time(self, value):
        # print "wait %d seconds" % value
        time.sleep(value)


def get_prometheus_metrics(app_namespace, resource):
    p = Prometheus()
    metrics_info = {}

    term_list = ["kafka_topic_partition_current_offset", "kafka_consumergroup_current_offset", "kafka_consumergroup_lag"]
    for term in term_list:
        metrics_info[term] = {}
        metrics_info[term][group_name] = {}
        metrics_info[term][group_name][topic_name] = 0

    lag_count = 0
    lo_count = 0
    co_count = 0
    for term in term_list:
        output = p.get_kafka_metrics(term)
        for result in output.get("data", {}).get("result", []):
            topic = result.get("metric", {}).get("topic", "")
            group = result.get("metric", {}).get("consumergroup", "")
            if topic == topic_name and term == "kafka_consumergroup_lag":
                lag_value = int(result.get("value", [])[1])
                metrics_info["kafka_consumergroup_lag"][group_name][topic_name] += lag_value
                lag_count += 1
            if topic == topic_name and term == "kafka_topic_partition_current_offset":
                lo_value = int(result.get("value", [])[1])
                metrics_info["kafka_topic_partition_current_offset"][group_name][topic_name] += lo_value
                lo_count += 1
            if topic == topic_name and term == "kafka_consumergroup_current_offset" and group == group_name:
                co_value = int(result.get("value", [])[1])
                metrics_info["kafka_consumergroup_current_offset"][group_name][topic_name] += co_value
                co_count += 1
    #print "find metrics_info: ", metrics_info
    return metrics_info


def write_prometheus_metrics(algo, start_time, item, metrics):
    try:
        file_name = "%s/%s_prometheus" % (traffic_path, algo)
        with open(file_name, "a") as f:
            for entry in metrics.keys():
                for topic in metrics[entry].keys():
                    value = metrics[entry][topic]
                    if topic == topic_name:
                        print "- Prometheus: ", item, value
                        line = "%d %s %s %s %s\n" % (start_time, item, entry, topic, value)
                        f.write(line)
    except Exception as e:
        print "failed to wrtie %s: %s" % (file_name, str(e))
        return -1
    # print "success to wrtie %s" % (file_name)
    return 0


if __name__ == "__main__":
    algo_name = sys.argv[1]
    time_value = query_interval
    time_interval = log_interval
    p = Prometheus()
    try:
        timestamp = int(time.time())
        metrics_info = get_prometheus_metrics("kafka", "my-kafka")
        for item in metrics_info.keys():
            if metrics_info[item]:
                write_prometheus_metrics(algo_name, timestamp, item, metrics_info[item])
        inter_start_time = time.time()
        for i in range(query_timeout):
            p.wait_time(time_value)
            inter_end_time = time.time()
            if inter_end_time - inter_start_time >= time_interval:
                break
    except Exception as e:
        print "failed to run prometheus.py: %s" % str(e)

