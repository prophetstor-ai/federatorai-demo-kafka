import sys
import time
from client import Client
from define import data_interval, log_interval, query_interval, query_timeout
from define import traffic_path, group_name, topic_name
from kubectl import Kubectl
from oc import OC
from write_log import WriteLog


class Consumer(Client):
    oc = OC()
    k = Kubectl()
    w = WriteLog()

    def __init__(self):
        super(Consumer, self).__init__()
        self.namespace = "myproject"
        self.app_name = "consumer"
        self.app_type = "deployment"
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
                elif item == "reason":
                    reason_list = self.w.app_list[self.app_name][pod]["reason"]
                    for reason in reason_list:
                        if reason == "OOMKilled":
                            app_status_oomkilled += 1
        print "- Consumers: CPU %s/%s mCore; Memory %s/%s Mi; Restart %s OOMKilled %s" % (app_cpu_value, app_cpu_limit, app_memory_value, app_memory_limit, app_restart, app_status_oomkilled)
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
        print "- Consumers: Replica: %s\n" % (num_replica)
        output = "%s %s %s " % (app_cpu_overlimit, app_memory_overlimit, num_replica)
        return output

    def calculate_performance(self, group_name, topic_name):
        total_lag = 0
        total_log_offset = 0
        total_current_offset = 0
        active_client = 0
        inactive_client = 0
        partition_list = []
        active_client_list = []
        start_time = time.time()
        num_sample = 3
        # print "--------", group_name, topic_name
        for i in range(num_sample):
            output = self.describe_consumer_group(group_name)
            print "==="
            print "%s" % output
            print "==="
            for line in output.split("\n"):
                if line and line.find(topic_name) != -1 and line.find("Error") == -1:
                    partition = int(line.split()[2])
                    if partition not in partition_list:
                        partition_list.append(partition)
                    current_offset = int(line.split()[3])
                    log_offset = int(line.split()[4])
                    lag = int(line.split()[5])
                    consumer_id = line.split()[6]
                    total_log_offset += log_offset
                    total_current_offset += current_offset
                    total_lag += lag
                    if consumer_id.find("consumer-1") == -1:
                        inactive_client += 1
                    if consumer_id not in active_client_list:
                        active_client_list.append(consumer_id)
            # print i, "total describe lag=", lag, time.time()
        total_lag = total_lag/(num_sample*1.0)
        total_log_offset = total_log_offset/(num_sample*1.0)
        total_current_offset = total_current_offset/(num_sample*1.0)
        inactive_client = inactive_client /(num_sample*1.0)
        active_client = len(active_client_list)
        print "- Consumers: Log Offset %s;" % total_log_offset, "Current Offset %s;" % total_current_offset, "Lag %s;" % total_lag
        print "- Consumers: Active %s;" % active_client, "Inactive %s" % inactive_client
        print "\n"
        output = "%s %s %s %s %s %s %s %s " % (group_name, topic_name, total_lag, active_client, inactive_client, total_log_offset, total_current_offset, len(partition_list))
        end_time = time.time()
        #print ">> describe time = ", end_time - start_time
        return output

    def write_logs(self, algo_name, group_name, topic_name):
        self.w.get_deploymentconfig()
        self.w.get_pod_info()
        self.w.get_limits()
        self.w.get_metrics()
        self.w.get_status()

        file_name = "%s/%s_consumer_metrics" % (traffic_path, algo_name)
        timestamp = int(time.time())
        line = "%s " % (timestamp)
        line += self.calculate_pod_info()
        line += self.calculate_overlimit()
        # hungo test - block calculate (per maygy)
        #line += self.calculate_performance(group_name, topic_name)
        line += "\n"

        try:
            with open(file_name, "a") as f:
                f.write(line)
        except Exception as e:
            print "failed to write consumer logs(%s): %s" % (file_name, str(e))
            return -1

        # print "success to write consumer logs(%s)" % file_name
        return 0

    def delete_all_consumer_groups(self):
        # delete all consumer groups
        group_list = self.list_consumer_group()
        for group in group_list:
            output = self.delete_consumer_group(group)

  

def main():
    algo_name = sys.argv[1]
    c = Consumer()
    time_value = query_interval
    time_interval = log_interval

    try:
        c.write_logs(algo_name, group_name, topic_name)         
        inter_start_time = time.time()
        for i in range(query_timeout):
            c.wait_time(time_value)
            inter_end_time = time.time()
            if inter_end_time - inter_start_time >= time_interval:
                break
    except Exception as e:
        print "failed to run consumer: %s" % str(e)


if __name__ == "__main__":
    main()

