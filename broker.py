import sys
import time
from client import Client
from define import data_interval, topic_name
from define import traffic_path, log_interval, query_interval, query_timeout
from kubectl import Kubectl
from oc import OC
from write_log import WriteLog


class Broker(Client):
    oc = OC()
    k = Kubectl()
    w = WriteLog()

    def __init__(self):
        super(Broker, self).__init__()
        self.namespace = "myproject"
        self.app_name = "my-cluster-kafka"
        self.app_type = "statefulset"
        self.w.namespace = self.namespace
        self.w.app_name = self.app_name
        self.w.app_type = self.app_type

    def wait_time(self, value):
        # print "wait %d seconds" % value
        time.sleep(value)

    def calculate_pod_info(self): 
        app_cpu_value = 0
        app_memory_value = 0
        app_cpu_limit = 0
        app_memory_limit = 0
        app_restart = 0
        app_status_running = 0
        app_status_crashloopbackoff = 0
        app_status_oomkilled = 0

        for pod in self.w.app_list[self.app_name].keys():
            if pod.find("zookeeper") != -1 or pod.find("exporter") != -1:
                continue
            for item in self.w.app_list[self.app_name][pod].keys():
                if item in ["cpu_value"]:
                    app_cpu_value += self.w.app_list[self.app_name][pod]["cpu_value"]
                elif item in ["memory_value"]:
                    app_memory_value += self.w.app_list[self.app_name][pod]["memory_value"]
                elif item in ["pod_cpu_limits"]:
                    app_cpu_limit += self.w.app_list[self.app_name][pod]["pod_cpu_limits"]
                elif item in ["pod_memory_limits"]:
                    app_memory_limit += self.w.app_list[self.app_name][pod]["pod_memory_limits"]
                elif item in ["restart"]:
                    app_restart += self.w.app_list[self.app_name][pod]["restart"]
                elif item == "status":
                    status = self.w.app_list[self.app_name][pod]["status"] 
                    if status in ["Running"]:
                        app_status_running += 1
                    if status in ["CrashLoopBackOff"]:
                        app_status_crashloopbackoff += 1
                    if status in ["OOMKilled"]:
                        app_status_oomkilled += 1
        print "- Brokers: CPU %s/%s mCore; Memory %s/%s Mi; Restart %s" % (app_cpu_value, app_cpu_limit, app_memory_value, app_memory_limit, app_restart)
        output = "%s %s %s %s %s %s %s %s " % (app_cpu_value, app_cpu_limit, app_memory_value, app_memory_limit, app_restart, app_status_running, app_status_crashloopbackoff, app_status_oomkilled)
        return output

    def calculate_overlimit(self):
        app_cpu_overlimit = 0
        app_memory_overlimit = 0
        
        count = 0    
        # calculate overlimit
        for pod in self.w.app_list[self.app_name].keys():
            if pod.find("zookeeper") != -1 or pod.find("exporter") != -1:
                continue
            cpu_value = self.w.app_list[self.app_name][pod]["cpu_value"]
            memory_value = self.w.app_list[self.app_name][pod]["memory_value"]
            cpu_limit = self.w.app_list[self.app_name][pod]["pod_cpu_limits"]
            memory_limit = self.w.app_list[self.app_name][pod]["pod_memory_limits"]
            if cpu_limit <= cpu_value:
                app_cpu_overlimit += 1
            if memory_limit <= memory_value:
                app_memory_overlimit += 1
            count += 1
        num_replica = count
        print "- Brokers: OverLimit %s; OOM: %s" % (app_cpu_overlimit, app_memory_overlimit)
        output = "%s %s %s " % (app_cpu_overlimit, app_memory_overlimit, num_replica)
        return output

    def calculate_performance(self):
        num_partition = 0
        output = self.describe_topic(topic_name)
        for line in output.split("\n"):
            if line and line.find("ReplicationFactor") == -1:
                if line.find("Isr") != -1:
                    num_partition += 1
        print "- Brokers: Partitions %s" % num_partition
        result = "%s " % num_partition
        return result


    def write_logs(self, algo_name):
        self.w.get_deploymentconfig()
        self.w.get_pod_info()
        self.w.get_limits()
        self.w.get_metrics()
        self.w.get_status()

        file_name = "%s/%s_broker_metrics" % (traffic_path, algo_name)
        timestamp = int(time.time())
        line = "%s " % (timestamp)
        line += self.calculate_pod_info()
        line += self.calculate_overlimit()
        line += self.calculate_performance()
        line += "\n"

        try:
            with open(file_name, "a") as f:
                f.write(line)
        except Exception as e:
            print "failed to write broker logs(%s): %s" % (file_name, str(e))
            return -1

        # print "success to write broker logs(%s)" % file_name
        return 0
  

def main():
    algo_name = sys.argv[1]
    print "in broker.py algo_name = %s" % algo_name
    b = Broker()
    time_value = query_interval
    time_interval = log_interval
    try:
        b.write_logs(algo_name)
        inter_start_time = time.time()
        for i in range(query_timeout):
            b.wait_time(time_value)
            inter_end_time = time.time()
            if inter_end_time - inter_start_time >= time_interval:
                continue
    except Exception as e:
        print "failed to run broker.py: %s" % str(e)


if __name__ == "__main__":
    main()

