import sys
import time
import os
import json
from oc import OC
from kubectl import Kubectl
from define import group_name, topic_name, message_size, partition_number


class Client(object):
    oc = OC()
    kubectl = Kubectl()
    zookeeper = ""

    def __init__(self):
        pass

    def find_broker_ip(self):
        ns = ""
        ip = ""
        port = ""
        output = self.oc.get_services_all_namespace()
        try:
            for line in output.split("\n"):
                if line.find("my-cluster") != -1 and line.find("bootstrap") == -1 and line.find("zookeeper") == -1 and line.find("exporter") == -1:
                    ns = line.split()[0]
                    ip = line.split()[1]
                    #port = line.split()[5].split("/")[0].split(":")[0]
        except Exception as e:
            print "it cannot find broker ip: %s" % str(e)
            return ns, ip, port
        print "find broker ip (%s:%s)" % (ip, port)
        # Hard core port to 9092
        return ns, ip, 9092

    def find_zookeeper_ip(self):
        ns = ""
        ip = ""
        port = ""
        output = self.oc.get_services_all_namespace()
        try:
            for line in output.split("\n"):
                if line.find("zookeeper-client") != -1 and line.find("zookeeper-headless") == -1:
                    ns = line.split()[0]
                    ip = line.split()[1]
                    #port = line.split()[5].split("/")[0].split(":")[0]
        except Exception as e:
            print "it cannot find zookeeper ip: %s" % str(e)
            return ns, ip, port
        # print "find zookeeper ip (%s:%s)" % (ip, port)
        # hard code port to 2181
        return ns, ip, 2181

    def find_producer_pod(self):
        ns = ""
        pod_list = []
        output = self.oc.get_pods_all_namespace()
        try:
            for line in output.split("\n"):
                if line.find("producer") != -1 and line.find("Running") != -1:
                    ns = line.split()[0]
                    pod = line.split()[1]
                    pod_list.append(pod)
        except Exception as e:
            print "it cannot find producer pod: %s" % str(e)
            return ns, pod_list
        # print "find %s producers in ns (%s)" % (len(pod_list), ns)
        return ns, pod_list

    def find_consumer_pod(self):
        ns = ""
        pod_list = []
        output = self.oc.get_pods_all_namespace()
        try:
            for line in output.split("\n"):
                if line.find("consumer") != -1 and line.find("Running") != -1:
                    ns = line.split()[0]
                    pod = line.split()[1]
                    pod_list.append(pod)
        except Exception as e:
            print "it cannot find consumer pod: %s" % str(e)
            return ns, pod_list
        # print "find %s consumers in ns (%s)" % (len(pod_list), ns)
        return ns, pod_list

    def find_zookeeper_pod(self):
        ns = ""
        pod_list = []
        output = self.oc.get_pods_all_namespace()
        try:
            for line in output.split("\n"):
                if line.find("zookeeper-client") != -1:
                    ns = line.split()[0]
                    pod = line.split()[1]
                    pod_list.append(pod)
        except Exception as e:
            print "it cannot find consumer pod: %s" % str(e)
            return ns, pod_list
        print "find %s zookeepers in ns (%s)" % (len(pod_list), ns)
        return ns, pod_list

    def find_broker_pod(self):
        ns = ""
        pod_list = []
        output = self.oc.get_pods_all_namespace()
        try:
            for line in output.split("\n"):
                if line.find("my-cluster") != -1 and line.find("export") == -1 and line.find("operator") == -1 and line.find("zookeeper") == -1:
                    ns = line.split()[0]
                    pod = line.split()[1]
                    pod_list.append(pod)
        except Exception as e:
            print "it cannot find consumer pod: %s" % str(e)
            return ns, pod_list
        print "find %s brokers in ns (%s)" % (len(pod_list), ns)
        return ns, pod_list

    def list_topic(self):
        topic_list = []
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_producer_pod()
        pod = pod_list[0]
        cmd = "/opt/kafka/bin/kafka-topics.sh --bootstrap-server %s:%s --list" % (ip, port)
        output = self.oc.exec_cmd(ns, pod, cmd)
        if not output:
            print "there is no topics in %s" % pod
        else:
            for line in output.split("\n"):
                if line:
                    item = line.split()[0]
                    if item and item not in topic_list:
                        topic_list.append(item)
        print "current topics: %s" % ",".join(topic_list)
        return topic_list

    def describe_topic(self, topic_name):
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_producer_pod()
        pod = pod_list[0]
        cmd = "/opt/kafka/bin/kafka-topics.sh --bootstrap-server %s:%s --describe --topic %s" % (ip, port, topic_name)
        output = self.oc.exec_cmd(ns, pod, cmd)
        return output

    def create_topic(self, topic_name):
        # references: https://blog.csdn.net/u010886217/article/details/83119774
        # --replication-factor<=number of brokers
        # --partitions: 1x or 2x number of brokers
        ns, broker_list = self.find_broker_pod()
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_producer_pod()
        pod = pod_list[0]
        partition = len(broker_list)
        replication = len(broker_list)
        cmd = "/opt/kafka/bin/kafka-topics.sh --bootstrap-server %s:%s --topic %s --create --partitions %d --replication-factor %d" % (ip, port, topic_name, partition, replication)
        print cmd
        output = self.oc.exec_cmd(ns, pod, cmd)
        print output
        return output

    def delete_topic(self, topic_name):
        print "delete topic:", topic_name
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_producer_pod()
        pod = pod_list[0]
        cmd = "/opt/kafka/bin/kafka-topics.sh --delete --bootstrap-server %s:%s --topic %s delete.topic.enable=true" % (ip, port, topic_name)
        output = self.oc.exec_cmd(ns, pod, cmd)
        return output

    def modify_topic(self, topic_name, num_partition):
        print "modify topic:", topic_name
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_producer_pod()
        pod = pod_list[0]
        cmd = "/opt/kafka/bin/kafka-topics.sh --alter --bootstrap-server %s:%s --topic %s --partitions %s" % (ip, port, topic_name, num_partition)
        print cmd
        output = self.oc.exec_cmd(ns, pod, cmd)
        print output
        return output

    def list_consumer_group(self):
        # print "--- list consumer group ---"
        group_list = []
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_producer_pod()
        if not pod_list:
            raise Exception("consumer is not existed")
        pod = pod_list[0]
        cmd = "/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server %s:%s --list" % (ip, port)
        output = self.oc.exec_cmd(ns, pod, cmd)
        for group in output.split("\n"):
            if group and group.find("Note") == -1:
                group_list.append(group)
        return group_list

    def describe_consumer_group(self, consumer_group_name):
        # print "describe consumer group: ", consumer_group_name
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_producer_pod()
        pod = pod_list[0]
        cmd = "/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server %s:%s --describe --group %s" % (ip, port, consumer_group_name)
        output = self.oc.exec_cmd(ns, pod, cmd)
        return output

    def delete_consumer_group(self, consumer_group_name):
        print "delete consumer group: ", consumer_group_name
        # only delete consumer group by zookeeper
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_producer_pod()
        pod = pod_list[0]
        cmd = "/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server %s:%s --delete --group %s" % (ip, port, consumer_group_name)
        print cmd
        output = self.oc.exec_cmd(ns, pod, cmd)
        return output

    def producer_per_test(self, topic_name, message_count):
        # reference1: https://gist.github.com/ueokande/b96eadd798fff852551b80962862bfb3
        # reference2: https://blog.csdn.net/tom_fans/article/details/75517367
        # print "--- producer_per_test ---"
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_producer_pod()
        if not pod_list:
            raise Exception("producer is not existed")
        pod_info = {}
        record_size = message_size
        for pod in pod_list:
            pod_info[pod] = {}
            cmd = "/opt/kafka/bin/kafka-producer-perf-test.sh --topic %s --num-records %s --record-size %s --throughput 1000000 --producer-props bootstrap.servers=%s:%s" % (topic_name, message_count, record_size, ip, port)  
            print cmd
            output = self.oc.exec_cmd(ns, pod, cmd)
            #print "%s: " % pod, output
            if not output:
                raise Exception("failed to produces messages")
            print "%s produces %s messages for topic %s" % (pod, message_count, topic_name)
            try:
                for line in output.split("\n"):
                    if line and len(line.split()) > 20 and line.find("OpenJDK") == -1:
                        pod_info[pod]["record"] = int(line.split()[0])
                        pod_info[pod]["throughput"] = float(line.split()[3])
                        pod_info[pod]["avg_latency"] = float(line.split()[7])
                        pod_info[pod]["max_latency"] = float(line.split()[11])
                        pod_info[pod]["50th_latency"] = float(line.split()[15])
                        pod_info[pod]["95th_latency"] = float(line.split()[18])
                        pod_info[pod]["99th_latency"] = float(line.split()[21])
                        pod_info[pod]["99.9th_latency"] = float(line.split()[24])
            except Exception as e:
                print "failed to get producer metrics: %s" % str(e)
                pod_info[pod]["record"] = 0
                pod_info[pod]["throughput"] = 0
                pod_info[pod]["avg_latency"] = 0
                pod_info[pod]["max_latency"] = 0
                pod_info[pod]["50th_latency"] = 0
                pod_info[pod]["95th_latency"] = 0
                pod_info[pod]["99th_latency"] = 0
                pod_info[pod]["99.9th_latency"] = 0
        return pod_info
        
    def consumer_per_test(self, topic_name, message_count):
        # reference: https://gist.github.com/ueokande/b96eadd798fff852551b80962862bfb3
        print "--- consumer_per_test ---"
        ns, ip, port = self.find_zookeeper_ip()
        ns, pod_list = self.find_consumer_pod()
        if not pod_list:
            raise Exception("consumer is not existed")
        pod_info = {}
        for pod in pod_list:
            pod_info[pod] = {}
            cmd = "/opt/kafka/bin/kafka-consumer-perf-test.sh --topic %s --messages %s --zookeeper=%s:%s --threads 1" % (topic_name, message_count, ip, port)
            # cmd = "/opt/kafka/bin/kafka-run-class.sh kafka.tools.ConsumerPerformance --topic %s --messages %s --zookeeper=%s:%s --threads 1" % (topic_name, message_count, ip, port)
            print cmd
            output = self.oc.exec_cmd(ns, pod, cmd)
            print "%s receives %s messages for topic %s" % (pod, message_count, topic_name)
            # print output
            for line in output.split("\n"):
                if line and line.find("start.time") == -1:
                    pod_info[pod]["MB.sec"] = float(line.split()[-3].split(",")[0])
                    pod_info[pod]["nMsg.sec"] = float(line.split()[-1])
        return pod_info

    def get_topic_info(self, topic_name):
        num_partition = 0
        output = self.describe_topic(topic_name)
        try:
            num_partition = int(output.split()[1].split(":")[1])
        except Exception as e:
            num_partition = 0
        print "%s has %s partitions" % (topic_name, num_partition)
        return num_partition

    def get_consumer_group_info(self, topic_name, group_name):
        topic_info = {}
        output = self.describe_consumer_group(group_name)
        for line in output.split("\n"):
            if line.find(topic_name) != -1:
                partition = int(line.split()[1])
                current_offset = int(line.split()[2])
                topic_info[partition] = current_offset
        return topic_info

    def simple_consumer_shell(self, topic_name, max_messages):
        # reference: https://segmentfault.com/a/1190000016106045
        # print "--- simple-consumer-shell ---"
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_consumer_pod()
        num_partition = self.get_topic_info(topic_name)
        topic_info = self.get_consumer_group_info(topic_name, group_name)
        if num_partition == 0:
            raise Exception("%s is not existed" % (topic_name))
        for pod in pod_list:
            pod_id = pod_list.index(pod)
            partition = pod_id % num_partition
            current_offset = topic_info[partition]
            offset = current_offset
            cmd = "/opt/kafka/bin/kafka-simple-consumer-shell.sh --broker-list %s:%s --partition %s --offset %s --max-messages %s --topic %s --property group_id=%s" % (ip, port, partition, offset, max_messages, topic_name, group_name)
            print cmd
            output = self.oc.exec_cmd(ns, pod, cmd)
            print "consumer(%s) of group(%s) receives %s messages at offset(%s) in partition(%s) of topic(%s) " % (pod, group_name, max_messages, offset, partition, topic_name)
        return 0

    def console_consumer(self, topic_name):
        print "--- console-consumer ---"
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_consumer_pod()
        for pod in pod_list:
            cmd = "/opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server %s:%s --topic %s --consumer-property group.id=test1" % (ip, port, topic_name)
            print cmd
            output = self.oc.exec_cmd(ns, pod, cmd)
        return 0

    def verify_consumer(self, group_name, topic_name):
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_consumer_pod()
        for pod in pod_list:
            cmd = "/opt/kafka/bin/kafka-verifiable-consumer.sh --broker-list %s:%s --group-id %s --topic %s" % (ip, port, group_name, topic_name)
            print cmd
            output = self.oc.exec_cmd(ns, pod, cmd)
            print "consumer(%s) of group(%s) receives messages for topic(%s) " % (pod, group_name, topic_name)
        return 0

    def verify_producer(self, topic_name):
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_consumer_pod()
        for pod in pod_list:
            cmd = "kafka-verifiable-producer.sh --broker-list %s:%s --max-messages %s --topic %s" % (ip, port, messages, topic_name)
            output = self.oc.exec_cmd(ns, pod, cmd)
            print "producer(%s) send %s messages to topic(%s) " % (pod, messages, topic_name)
        return 0

    def end_to_end_latency(self, topic_name, num_messages):
        print "--- latency from producer to broker and broker to consumer ---"
        ns, ip, port = self.find_broker_ip()
        ns, pod_list = self.find_consumer_pod()
        if not pod_list:
            raise Exception("consumer is not existed")
        pod_info = {}
        for pod in pod_list:
            pod_info[pod] = {}
        cmd = "/opt/kafka/bin/kafka-run-class.sh kafka.tools.EndToEndLatency %s:%s %s %s all 100" % (ip, port, topic_name, num_messages)
        output = self.oc.exec_cmd(ns, pod, cmd)
        return output


    def compute_avg_metrics(self, pod_info_list):
        total_metric = {}
        avg_metric = {}
        pod_info = pod_info_list[0]
        pod_num = len(pod_info.keys())
        pod_name = pod_info.keys()[0]
        for metric in pod_info[pod_name].keys():
            total_metric[metric] = 0
            avg_metric[metric] = 0
    
        for pod_info in pod_info_list:
            for pod in pod_info.keys():
                for metric in pod_info[pod].keys():
                    if pod_info[pod].get(metric):
                        if metric == "record":
                            total_metric[metric] += pod_info[pod][metric]
                        else:
                            total_metric[metric] += pod_info[pod][metric] * pod_info[pod]["record"]

        num_time = len(pod_info_list)
        for metric in avg_metric.keys():
            if metric == "record":
                avg_metric[metric] = total_metric[metric] / (pod_num*1.0) / num_time
            else:
                avg_metric[metric] = total_metric[metric] / (pod_num*1.0) / total_metric["record"]
        return avg_metric

    def calculate_consumer_rate(self):
        consumer_rate = 0
        ns, pod_list = self.find_consumer_pod()
        start_time = 0
        end_time = 0
        total_count = 0
        comsumer_rate = 0
        for pod in pod_list:
            output = self.oc.log_pod(ns, pod)
            for line in output.split("\n"):
                # print line
                if line and line.find("WARN") == -1:
                    line = json.loads(line)
                    timestamp = line.get("timestamp")
                    count = line.get("count")
                    if count:
                        start_time = timestamp
                        break
        for pod in pod_list:
            output = self.oc.log_pod(ns, pod)
            for line in output.split("\n"):
                if line and line.find("WARN") == -1:
                    line = json.loads(line)
                    timestamp = line.get("timestamp")
                    count = line.get("count")
                    if count:
                        total_count += count
                        end_time = timestamp
        time_diff = (end_time - start_time) * 1.0
        if time_diff:
            comsumer_rate = total_count / time_diff * 1000
        print "consumer process rate: ", comsumer_rate, total_count, time_diff
        return consumer_rate


    def delete_topic_data(self, topic_name):
        nfs_dir = "/data"
        data_list = os.listdir(nfs_dir)
        for broker in data_list:
            broker_dir = "%s/%s" % (nfs_dir, broker)
            broker_data_list = os.listdir(broker_dir)
            for log_dir in broker_data_list:
                broker_data = "%s/%s" % (broker_dir, log_dir)
                data_list = os.listdir(broker_data)
                for data in data_list:
                    if data.find(topic_name) != -1:
                        print data
                        break


def main():
    action = sys.argv[1]
    target = sys.argv[2]
    c = Client()
    if action == "create" and target == "topic":
        c.create_topic(topic_name)
    elif action == "delete" and target == "group":
        c.delete_consumer_group(group_name)
    elif action  == "describe" and target == "group":
        print c.describe_consumer_group(group_name)
    elif action == "delete" and target == "topic":
        c.delete_topic(topic_name)
        c.delete_topic_data(topic_name)
    elif action == "modify" and target == "topic":
        c.modify_topic(topic_name, partition_number)
    elif action  == "describe" and target == "topic":
        print c.describe_topic(topic_name)
    elif action  == "show" and target == "group":
        c.calculate_consumer_rate()
    elif action  == "list" and target == "topic":
        print c.list_topic()
    elif action  == "list" and target == "group":
        print c.list_consumer_group()
    else:
        print "input: <action> <target> "
    

if __name__ == "__main__":
    main()
