import sys
import time
from define import traffic_path
from client import Client
from define import data_interval, log_interval, query_interval, query_timeout
from kubectl import Kubectl
from oc import OC
from write_log import WriteLog


class Producer(Client):
    oc = OC()
    k = Kubectl()
    w = WriteLog()

    def __init__(self):
        super(Producer, self).__init__()
        self.namespace = "myproject"
        self.app_name = "producer"
        self.app_type = "deployment"
        self.w.namespace = self.namespace
        self.w.app_name = self.app_name
        self.w.app_type = self.app_type

    def wait_time(self, value):
        # print "wait %d seconds" % value
        time.sleep(value)

    def read_transaction_list(self):
        transaction_list = []
        file_name = "./transaction.txt"
        try:
            with open(file_name, "r") as f:
                output = f.read()
                for line in output.split("\n"):
                    if line:
                        transaction_list.append(float(line))
        except Exception as e:
            print "faild to read %s: %s" % (file_name, str(e))
            return transaction_list
        # print "success to read %s" % (file_name)
        return transaction_list

    def calculate_pod_info(self):
        app_cpu_value = 0
        app_memory_value = 0
        app_cpu_limit = 0
        app_memory_limit = 0
        app_cpu_overlimit = 0
        app_memory_overlimit = 0
        app_restart = 0
        app_status_running = 0
        app_status_crashloopbackoff = 0
        app_status_oomkilled = 0
        for pod in self.w.app_list[self.app_name].keys():
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
        print "- Producers: CPU %s/%s mCore; Memory %s/%s Mi; Restart %s" % (app_cpu_value, app_cpu_limit, app_memory_value, app_memory_limit, app_restart)
        output = "%s %s %s %s %s %s %s %s " % (app_cpu_value, app_cpu_limit, app_memory_value, app_memory_limit, app_restart, app_status_running, app_status_crashloopbackoff, app_status_oomkilled)
        return output

    def calculate_overlimit(self):
        app_cpu_overlimit = 0
        app_memory_overlimit = 0

        # calculate overlimit
        for pod in self.w.app_list[self.app_name].keys():
            cpu_value = self.w.app_list[self.app_name][pod]["cpu_value"]
            memory_value = self.w.app_list[self.app_name][pod]["memory_value"]      
            cpu_limit = self.w.app_list[self.app_name][pod]["pod_cpu_limits"]
            memory_limit = self.w.app_list[self.app_name][pod]["pod_memory_limits"]
            if cpu_limit <= cpu_value:
                app_cpu_overlimit += 1
            if memory_limit <= memory_value:
                app_memory_overlimit += 1
        num_replica = len(self.w.app_list[self.app_name].keys())
        #print "- Producers: OverLimit %s; OOM: %s\n" % (app_cpu_overlimit, app_memory_overlimit)
        output = "%s %s %s" % (app_cpu_overlimit, app_memory_overlimit, num_replica)
        return output

    def calculate_performance(self, producer_info):
        app_record = 0
        app_999th_latency = 0
        app_max_latency = 0
        app_99th_latency = 0
        app_95th_latency = 0
        app_throughput = 0
        app_avg_latency = 0
        app_50th_latency = 0

        # get avg. latency
        for pod in producer_info.keys():
            for item in producer_info[pod].keys():
                if item == "record":
                    app_record += producer_info[pod][item]
                if item == "max_latency":
                    app_max_latency += producer_info[pod][item] * producer_info[pod]["record"] 
                elif item == "throughput":
                    app_throughput += producer_info[pod][item] * producer_info[pod]["record"]
                elif item == "avg_latency":
                    app_avg_latency += producer_info[pod][item] * producer_info[pod]["record"]
                elif item == "50th_latency":
                    app_50th_latency += producer_info[pod][item] * producer_info[pod]["record"]
                elif item == "95th_latency":
                    app_95th_latency += producer_info[pod][item] * producer_info[pod]["record"]
                elif item == "99th_latency":
                    app_99th_latency += producer_info[pod][item] * producer_info[pod]["record"]
                elif item == "99.9th_latency":
                    app_999th_latency += producer_info[pod][item] * producer_info[pod]["record"]
        if app_record == 0:
            app_record = -1
        app_max_latency = app_max_latency / app_record
        app_throughput = app_throughput / app_record 
        app_avg_latency = app_avg_latency / app_record
        app_50th_latency = app_50th_latency / app_record
        app_95th_latency = app_95th_latency / app_record
        app_99th_latency = app_99th_latency / app_record
        app_999th_latency = app_999th_latency / app_record
        output = "%s %s %s %s %s %s %s %s " % (app_record, app_max_latency, app_throughput, app_avg_latency, app_50th_latency, app_95th_latency, app_99th_latency, app_999th_latency)
        return output

    def write_logs(self, algo_name):
        self.w.get_deploymentconfig()
        self.w.get_pod_info()
        self.w.get_limits()
        self.w.get_metrics()
        self.w.get_status()
      
        timestamp = int(time.time())
        line = "%s " % timestamp
        line += self.calculate_pod_info()
        line += self.calculate_overlimit()
        line += "\n"

        file_name = "%s/%s_producer_metrics" % (traffic_path, algo_name)
        try:
            with open(file_name, "a") as f:
                f.write(line)
        except Exception as e:
            print "failed to write producer logs(%s): %s" % (file_name, str(e))
            return -1

        # print "success to write producer logs(%s)" % file_name
        return 0

    def write_latency(self, algo_name, producer_info):
        timestamp = int(time.time())
        line = "%s " % timestamp
        line += self.calculate_performance(producer_info)
        line += "\n"

        file_name = "%s/%s_producer_latency" % (traffic_path, algo_name)
        try:
            with open(file_name, "a") as f:
                f.write(line)
        except Exception as e:
            print "failed to write producer latency(%s): %s" % (file_name, str(e))
            return -1

        # print "success to write producer logs(%s)" % file_name
        return 0
  

def main():
    algo_name = sys.argv[1]
    p = Producer()
    count = 0
    time_value = query_interval
    time_interval = log_interval
    start_time = time.time()
    try:
        p.write_logs(algo_name)
        inter_start_time = time.time()
        for i in range(query_timeout):
            p.wait_time(time_value)
            inter_end_time = time.time()
            if inter_end_time - inter_start_time >= time_interval:
                 break
    except Exception as e:
        print "failed to run producer.py: %s" % str(e)


if __name__ == "__main__":
    main()

