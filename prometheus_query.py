import time
import sys
from prometheus import Prometheus
from define import topic_name, group_name, traffic_path
from define import query_interval, query_timeout, log_interval
from oc import OC


class Prometheus_Query:
    p = Prometheus()
    instance_name = "10.244.0.85:9308"
    oc = OC()

    def __init__(self):
        ns, ip, port = self.get_kafka_exporter_ip()
        if ip and port:
            self.instance_name = "%s:%s" % (ip, port)

    def get_kafka_exporter_ip(self):
        ns = ""
        ip = ""
        port = ""
        output = self.oc.get_services_all_namespace()
        try:
            for line in output.split("\n"):
                if line.find("my-cluster-kafka-exporter") != -1:
                    ns = line.split()[0]
                    ip = line.split()[3]
                    port = line.split()[5].split("/")[0].split(":")[0]
        except Exception as e:
            print "it cannot find kafka exporter ip: %s" % str(e)
            return ns, ip, port
        print "find namespace (%s) exporter ip (%s:%s)" % (ns, ip, port)
        return ns, ip, port

    def query_lag(self):
        # cmd = 'sum(kafka_consumergroup_lag{instance="%s",topic=~"%s"}) by (consumergroup, topic)' % (self.instance_name, topic_name)
        cmd = 'sum(kafka_consumergroup_lag{topic=~"%s"})' % (topic_name)
        output = self.p.run_cmd(cmd)
        return output

    def query_avg_lag(self):
        cmd = 'avg_over_time(kafka_consumergroup_lag{topic="%s",consumergroup="%s"}[1m])' % (topic_name, group_name)
        output = self.p.run_cmd(cmd)
        return output

    def query_log_offset(self, duration):
        cmd = 'kafka_topic_partition_current_offset{topic=~"%s"}[%s]' % (topic_name, duration)
        output = self.p.run_cmd(cmd)
        return output

    def query_log_offset_by_min(self):
        cmd = 'sum(delta(kafka_topic_partition_current_offset{topic=~"%s"}[3m])/3)' % (topic_name)
        output = self.p.run_cmd(cmd)
        return output

    def query_log_offset_by_sec(self):
        cmd = 'sum(rate(kafka_topic_partition_current_offset{topic=~"%s"}[1m]))' % (topic_name)
        output = self.p.run_cmd(cmd)
        return output

    def query_current_offset(self, duration):
        cmd = 'kafka_consumergroup_current_offset{topic=~"%s"}[%s]' % (topic_name, duration)
        output = self.p.run_cmd(cmd)
        return output

    def query_current_offset_by_min(self):
        cmd = 'sum(delta(kafka_consumergroup_current_offset{topic=~"%s"}[3m])/3)' % (topic_name)
        output = self.p.run_cmd(cmd)
        return output

    def query_current_offset_by_sec(self):
        cmd = 'sum(rate(kafka_consumergroup_current_offset{topic=~"%s"}[1m]))' % (topic_name)
        output = self.p.run_cmd(cmd)
        return output

    def query_lag_by_sec(self):
        cmd = 'sum(rate(kafka_consumergroup_lag{topic=~"%s"}[1m]))' % (topic_name)
        output = self.p.run_cmd(cmd)
        return output

    def query_lag_by_min(self):
        cmd = 'sum(delta(kafka_consumergroup_lag{topic=~"%s"}[3m])/3)' % (topic_name)
        output = self.p.run_cmd(cmd)
        return output

    def query_pod_start_time(self, pod_name):
        cmd = 'kube_pod_start_time{pod="%s"}' % pod_name
        output = self.p.run_cmd(cmd)
        return output

    def wait_time(self, value):
        # print "wait %d seconds" % value
        time.sleep(value)


def write_prometheus_query_metrics(algo, start_time, log_offset, current_offset, lag, log_offset_min, current_offset_min):
    file_name = "%s/%s_prometheus_query" % (traffic_path, algo)
    try:
        with open(file_name, "a") as f:
            line = "%s %s %s %s %s %s \n" % (start_time, log_offset, current_offset, lag, log_offset_min, current_offset_min)
            print "- Prometheus Query: Log Offset %s; Current Offset %s; Lag %s;" % (log_offset, current_offset, lag)
            print "- Prometheus Query: Log Offset Rate %s; Current Offset Rate %s;" % (log_offset_min, current_offset_min)
            f.write(line)
    except Exception as e:
        print "failed to wrtie %s: %s" % (file_name, str(e))
        return -1
    return 0


def sum_offset_data(offset_output):
    offset_list = {}
    if offset_output.get("data", {}).get("result", []):
        for result in offset_output.get("data", {}).get("result", []):
            for value in result.get("values"):
                timestamp = int(value[0])
                offset_list[timestamp] = 0
        for result in offset_output.get("data", {}).get("result", []):
            for value in result.get("values"):
                timestamp = int(value[0])
                offset = int(value[1])
                offset_list[timestamp] += offset
    return offset_list


def calculate_lag(log_offset_list, current_offset_list):
    lag = 0
    log_offset = 0
    last_logoffset_timestamp = 0
    lag_flag = False
    if log_offset_list:
        last_logoffset_timestamp = sorted(log_offset_list.keys())[-1]
        log_offset = log_offset_list[last_logoffset_timestamp]

    current_offset = 0
    last_current_timestamp = 0
    if current_offset_list:
        last_current_timestamp = sorted(current_offset_list.keys())[-1]
        current_offset = current_offset_list[last_current_timestamp]

    # print "log offset=", last_logoffset_timestamp, log_offset, "current offset=", last_current_timestamp, current_offset
    if last_logoffset_timestamp >= last_current_timestamp and log_offset >= current_offset:
        lag = log_offset - current_offset
    else:
        lag_flag = True
        # print "current offset > log offset, use extrapolation to get lag"
        if len(log_offset_list.keys()) > 1:
            last_two_logoffset_timestamp = sorted(log_offset_list.keys())[-2]
            old_log_offset = log_offset_list[last_two_logoffset_timestamp]
            timestamp_diff = last_logoffset_timestamp - last_two_logoffset_timestamp
            logoffset_diff = log_offset_list[last_logoffset_timestamp] - log_offset_list[last_two_logoffset_timestamp]
            vary = logoffset_diff/(timestamp_diff*1.0)
            x = (last_current_timestamp - last_two_logoffset_timestamp)/(timestamp_diff*1.0)
            if last_current_timestamp != last_logoffset_timestamp:
                log_offset = x * vary + old_log_offset
            else:
                log_offset = current_offset
            # print "old log offset =", old_log_offset, last_two_logoffset_timestamp
            # print "timestamp_diff=", timestamp_diff, "logoffset_diff=", logoffset_diff, "vary=", vary, "x=", x
            # print "new log offset =", log_offset
            lag = log_offset - current_offset
    # if lag < 0:
    #    raise Exception("Lag(%s) should not be less than 0" % lag)
    return log_offset, current_offset, lag, lag_flag


if __name__ == "__main__":
    algo_name = sys.argv[1]
    time_value = query_interval
    time_interval = log_interval

    try:
        pq = Prometheus_Query()
        log_offset_output = pq.query_log_offset("1m")
        log_offset_list = sum_offset_data(log_offset_output)
        current_offset_output = pq.query_current_offset("1m")
        current_offset_list = sum_offset_data(current_offset_output)
        log_offset, current_offset, lag, lag_flag = calculate_lag(log_offset_list, current_offset_list)
        lag = 0
        if pq.query_lag().get("data", {}).get("result", []):
            lag = pq.query_lag().get("data", {}).get("result", [])[0].get("value")[1]
        avg_lag = float(lag)
        if avg_lag < 0:
            avg_lag = 0
        log_offset_min = pq.query_log_offset_by_min().get("data", {}).get("result", [])[0].get("value")[1]
        current_offset_min = pq.query_current_offset_by_min().get("data", {}).get("result", [])[0].get("value")[1]
        start_time = int(time.time())
        write_prometheus_query_metrics(algo_name, start_time, log_offset, current_offset, avg_lag, log_offset_min, current_offset_min)
        inter_start_time = time.time()
        for i in range(query_timeout):
            pq.wait_time(time_value)
            inter_end_time = time.time()
            if inter_end_time - inter_start_time >= time_interval:
                break
    except Exception as e:
        print "failed to run prometheus_query.py: %s" % str(e)
        pass
