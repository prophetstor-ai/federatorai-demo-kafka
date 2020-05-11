import os
import sys
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from define import picture_x_axis, picture_y_ratio, log_interval, comparision


class Picture:
    item = "nonhpa"
    alpha = 1.5
    path = "./picture"

    def __init__(self, item=""):
        if item:
            self.item = item
        if item and item.find("test_result") != -1:
            new_item = item.split("/")
            self.path = "%s/%s/picture" % (new_item[0], new_item[1])
            self.item = item.split("/")[-1]

    def get_cpu_mem_picture(self, role, x, hpa_cpu_y, hpa_cpu_y_limit, hpa_mem_y, hpa_mem_y_limit):
        # cpu
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, hpa_cpu_y, label="observed(%s)" % (self.item), color="k", linewidth=1.5)
        plt.plot(x, hpa_cpu_y_limit, label="hpa-limit (%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("CPU m")
        ylim = max([max(hpa_cpu_y), max(hpa_cpu_y_limit)])*self.alpha
        plt.ylim(0, ylim)
        plt.title("CPU and Memory Utilization for %s" % role)
        plt.legend(loc=1, ncol=3)

        # memory
        plt.subplot(2, 1, 2)
        plt.plot(x, hpa_mem_y, label="oberserved(%s)" % (self.item), color="k", linewidth=1.5)
        plt.plot(x, hpa_mem_y_limit, label="hpa-limit (%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Memory Size (MB)")
        ylim = max([max(hpa_mem_y), max(hpa_mem_y_limit)])*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        # print "save file to ./picture/cpu-mem-%s-%s.png" % (self.item, role)
        plt.savefig("%s/cpu-mem-%s-%s.png" % (self.path, self.item, role))
        plt.close()

    def get_cpu_picture(self, role, x, hpa_y, hpa_y_limit, hpa_y_overlimit):
        # cpu
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, hpa_y, label="observed(%s)" % (self.item), color="k", linewidth=1.5)
        plt.plot(x, hpa_y_limit, label="hpa-limit (%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("CPU m")
        ylim = max([max(hpa_y), max(hpa_y_limit)])*self.alpha
        plt.ylim(0, ylim)
        plt.title("CPU Utilization and CPU OverLimit for %s" % role)
        plt.legend(loc=1, ncol=3)
        # overlimit
        plt.subplot(2, 1, 2)
        plt.bar(x, hpa_y_overlimit, label="hpa-overlimit (%s)" % (self.item))
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Number of CPU OverLimit")
        plt.legend(loc=0)
        ylim = max(hpa_y_overlimit)*self.alpha
        plt.ylim(0, ylim)
        # print "save file to ./picture/cpu-%s-%s.png" % (self.item, role)
        plt.savefig("%s/cpu-%s-%s.png" % (self.path, self.item, role))
        plt.close()

    def get_memory_picture(self, role, x, hpa_y, hpa_y_limit, hpa_y_overlimit):
        # memory
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, hpa_y, label="oberserved(%s)" % (self.item), color="k", linewidth=1.5)
        plt.plot(x, hpa_y_limit, label="hpa-limit (%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Memory Size (MB)")
        ylim = max([max(hpa_y), max(hpa_y_limit)])*self.alpha
        plt.ylim(0, ylim)
        plt.title("Memory Utilization and Memory OverLimit for %s" % role)
        plt.legend(loc=1, ncol=3)
        # oom
        plt.subplot(2, 1, 2)
        plt.bar(x, hpa_y_overlimit, label="hpa-oom (%s-%s)" % (self.item, role))
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        ylim = max(hpa_y_overlimit)*self.alpha
        plt.ylim(0, ylim)
        plt.ylabel("Number of OOM")
        plt.legend(loc=0)
        # print "save file to ./picture/mem-%s-%s.png" % (self.item, role)
        plt.savefig("%s/mem-%s-%s.png" % (self.path, self.item, role))
        plt.close()

    def get_status_picture(self, role, x, restart_y, oomkilled_y):
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, restart_y, label="restart(%s)" % (self.item), color="k", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Restart Pods")
        ylim = max(restart_y)*self.alpha
        plt.ylim(0, ylim)
        plt.title("Restart and OOMKilled Pods for %s" % role)
        plt.legend(loc=1, ncol=3)

        plt.subplot(2, 1, 2)
        plt.plot(x, oomkilled_y, label="oomkilled(%s)" % (self.item), color="g", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Error Pods")
        ylim = max(oomkilled_y)*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        # print "save file to ./picture/status-%s-%s.png" % (self.item, role)
        plt.savefig("%s/status-%s-%s.png" % (self.path, self.item, role))
        plt.close()

    def get_lag_picture(self, consumergroup, topic, x, topic_lag_y, role):
        plt.figure(figsize=(8, 4))
        plt.plot(x, topic_lag_y, label="topic lag(%s)" % (role), color="k", linewidth=1.5)
        if role.find("prom") == -1:
            plt.xlabel("Time Intervals(per 1 min)")
        else:
            plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Topic Lags")
        ylim = max(topic_lag_y)*self.alpha
        plt.ylim(0, ylim)
        plt.title("Lags for %s" % (role))
        plt.legend(loc=1, ncol=3)
        # print "save file to ./picture/lag-%s.png" % (topic)
        plt.savefig("%s/lag-%s.png" % (self.path, role))
        plt.close()

    def get_replica_picture(self, consumergroup, x, replica_y):
        plt.figure(figsize=(8, 4))
        plt.plot(x, replica_y, label="replica(%s)" % (self.item), color="k", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Replicas")
        ylim = max(replica_y)*self.alpha
        plt.ylim(0, ylim)
        plt.title("Replicas for ConsumerGroup(%s)" % (consumergroup))
        plt.legend(loc=1, ncol=3)
        # print "save file to ./picture/replica-%s-%s.png" % (self.item, consumergroup)
        plt.savefig("%s/replica-%s-%s.png" % (self.path, self.item, consumergroup))
        plt.close()

    def get_prom_lag_picture(self, consumergroup, topic, x, prom_topic_lag_y, replica_y, prom_overprovision_lag_y):

        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        if prom_overprovision_lag_y:
            plt.plot(x, prom_overprovision_lag_y, label="prom. topic lag(%s)" % comparision, color="g", linewidth=1.5)
        plt.plot(x, prom_topic_lag_y, label="prom. topic lag(%s)" % (self.item), color="k", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Prom. Topic Lags")
        ylim = max(max(prom_topic_lag_y), max(prom_overprovision_lag_y))*self.alpha

        plt.ylim(0, ylim)
        plt.title("Prom. Topic(%s) Lags for ConsumerGroup(%s)" % (topic, consumergroup))
        plt.legend(loc=1, ncol=3)

        plt.subplot(2, 1, 2)
        plt.plot(x, replica_y, label="replicas(%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Running Replicas")
        ylim = max(replica_y)*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        # print "save file to ./picture/lag-%s-%s.png" % (self.item, topic)
        plt.savefig("%s/prom-lag-%s-%s.png" % (self.path, self.item, topic))
        plt.close()

    def get_current_offset_diff_picture(self, consumergroup, topic, x, current_offset_diff_y, role):
        plt.figure(figsize=(8, 4))
        plt.plot(x, current_offset_diff_y, label="consumer rate(%s)" % (role), color="g", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Current Offset Diff")
        ylim = max(current_offset_diff_y)*self.alpha
        plt.ylim(0, ylim)
        plt.title("Consumer Rate/Min for %s" % (role))
        plt.savefig("%s/current-offset-diff-%s.png" % (self.path, topic))
        plt.close()

    def get_log_offset_diff_picture(self, consumergroup, topic, x, log_offset_diff_y, role):
        plt.figure(figsize=(8, 4))
        plt.plot(x, log_offset_diff_y, label="producer rate(%s)" % (role), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Log OFfset Diff")
        ylim = max(log_offset_diff_y)*self.alpha
        plt.ylim(0, ylim)
        plt.title("Producer Rate/min for %s" % (role))
        plt.savefig("%s/log-offset-diff-%s.png" % (self.path, topic))
        plt.close()

    def get_log_current_offset_picture(self, consumergroup, topic, x, log_offset_y, current_offset_y):
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, log_offset_y, label="log offset(%s)" % (self.item), color="k", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Log Offset")
        ylim = max(log_offset_y)*self.alpha
        plt.ylim(0, ylim)
        plt.title("Topic(%s) Log Offset for ConsumerGroup(%s)" % (topic, consumergroup))
        plt.legend(loc=1, ncol=3)

        plt.subplot(2, 1, 2)
        plt.plot(x, current_offset_y, label="current offset(%s)" % (self.item), color="g", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Current Offset")
        ylim = max(current_offset_y)*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        # print "save file to ./picture/log-current-offset-%s-%s.png" % (self.item, topic)
        plt.savefig("%s/log-current-offset-%s-%s.png" % (self.path, self.item, topic))
        plt.close()

    def get_prom_log_current_offset_picture(self, consumergroup, topic, x, log_offset_y, current_offset_y, prom_log_offset_y, prom_current_offset_y):
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, log_offset_y, label="log offset(%s)" % (self.item), color="k", linewidth=1.5)
        plt.plot(x, prom_log_offset_y, label="prom. log offset(%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Prom. Log Offset")
        ylim = max(log_offset_y)*self.alpha
        plt.ylim(0, ylim)
        plt.title("Topic(%s) Log Offset for ConsumerGroup(%s)" % (topic, consumergroup))
        plt.legend(loc=1, ncol=3)

        plt.subplot(2, 1, 2)
        plt.plot(x, current_offset_y, label="current offset(%s)" % (self.item), color="g", linewidth=1.5)
        plt.plot(x, prom_current_offset_y, label="prom. current offset(%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Prom. Current Offset")
        ylim = max(current_offset_y)*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        # print "save file to ./picture/log-current-offset-%s-%s.png" % (self.item, topic)
        plt.savefig("%s/prom-log-current-offset-%s-%s.png" % (self.path, self.item, topic))
        plt.close()

    def get_lag_log_diff_picture(self, consumergroup, topic, x, lag_diff_y, current_log_diff_y):
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, lag_diff_y, label="lag_diff/replica(%s)" % (self.item), color="k", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Lag Diff/currentReplica")
        ylim = max(lag_diff_y)*self.alpha
        ylim1 = min(lag_diff_y)*self.alpha
        plt.ylim(ylim1, ylim)
        plt.title("Topic(%s) Lag Diff/Replica && Log Offset Diff/Current Offset Diff" % (topic))
        plt.legend(loc=1, ncol=3)

        plt.subplot(2, 1, 2)
        plt.plot(x, current_log_diff_y, label="log_diff/current_diff(%s)" % (self.item), color="g", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Log Diff/Current Diff")
        ylim = max(current_log_diff_y)*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        plt.savefig("%s/lag-log-diff-%s-%s.png" % (self.path, self.item, topic))
        plt.close()

    def get_latency_picture(self, x, record_y, avg_latency_y):
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, record_y, label="response(%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Records")
        ylim = max(record_y)*self.alpha
        plt.ylim(0, ylim)
        plt.title("Messages and Latency for Producer")
        plt.legend(loc=1, ncol=3)

        plt.subplot(2, 1, 2)
        plt.plot(x, avg_latency_y, label="avg. latency(%s)" % (self.item), color="k", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Latency (ms)")
        ylim = max(avg_latency_y)*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        # print "save file to ./picture/latency-%s-producer.png" % (self.item)
        plt.savefig("%s/latency-%s-producer.png" % (self.path, self.item))
        plt.close()

    def get_consumer_picture(self, consumergroup, topic, x, active_consumer_y, inactive_consumer_y):
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, active_consumer_y, label="active consumer(%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Active Consumers")
        ylim = max(active_consumer_y)*self.alpha
        plt.ylim(0, ylim)
        plt.title("Topic(%s) Status Accessed By Consumergroup(%s)" % (topic, consumergroup))
        plt.legend(loc=1, ncol=3)

        plt.subplot(2, 1, 2)
        plt.plot(x, inactive_consumer_y, label="inactive consumer(%s)" % (self.item), color="g", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Inactive Consumers")
        ylim = max(inactive_consumer_y)*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        plt.savefig("%s/consumer-%s-%s.png" % (self.path, self.item, topic))
        plt.close()

    def get_message_picture(self, x, record_y, message_y):
        plt.figure(figsize=(8, 4))
        # plt.plot(x, record_y, label="response(%s)" % (self.item), color="k", linewidth=1.5)
        plt.plot(x, message_y, label="request(%s)" % (self.item), color="g", linewidth=1.5)
        plt.xlabel("Time Intervals(per 10 sec)")
        plt.ylabel("Records")
        ylim = max(max(record_y), max(message_y))*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        plt.title("Requests for Producer")
        plt.savefig("%s/message-%s-producer.png" % (self.path, self.item))
        plt.close()

    def get_prediction_picture(self, x, real_y, predict_y, main_y, item, role):
        plt.figure(figsize=(8, 4))
        plt.plot(x, real_y, label="real(%s)" % (item), color="k", linewidth=1.5)
        if not main_y:
            plt.plot(x, predict_y, label="prediction by LR(%s)" % (item), color="g", marker="o", linewidth=1.5)
        if main_y:
            plt.plot(x, main_y, label="prediction by ACP(%s)" % (item), color="b", marker="^", linewidth=1.5)
        plt.xlabel("Time Intervals(per 30 sec)")
        item_value = "Values"
        if item == "cpu":
            item_value = "CPU Cores"
        elif item == "memory":
            item_value = "Memory Size(GB)"
        elif item == "network":
            item_value = "Network(MBps)"
        plt.ylabel(item_value)
        ylim = max(max(real_y), max(predict_y))*self.alpha
        if main_y:
            ylim = max(max(real_y), max(predict_y), max(main_y))*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        plt.title("Predictions for %s" % role)
        # print "save file to ./picture/prediction-%s-%s.png" % (item, role)
        plt.savefig("%s/prediction-%s-%s.png" % (self.path, item, role))
        plt.close()

    def get_cosin_picture(self, x, real_y, predict_y, item, role):
        plt.figure(figsize=(8, 4))
        plt.plot(x, real_y, label="real(%s)" % (item), color="k", linewidth=1.5)
        plt.plot(x, predict_y, label="prediction(%s)" % (item), color="g", marker="o", linewidth=1.5)
        plt.xlabel("Time Intervals(per 30 sec)")
        item_value = "Values"
        if item == "cpu":
            item_value = "CPU Cores"
        elif item == "memory":
            item_value = "Memory Size(GB)"
        elif item == "network":
            item_value = "Network(MBps)"
        plt.ylabel(item_value)
        ylim = max(max(real_y), max(predict_y))*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        plt.title("Predictions for %s" % role)
        # print "save file to ./picture/cosine-%s-%s.png" % (item, role)
        plt.savefig("%s/cosine-%s-%s.png" % (self.path, item, role))
        plt.close()

    def get_regression_picture(self, x, real_y, predict_y, item, role, entry):
        plt.figure(figsize=(8, 4))
        plt.plot(x, real_y, label="real(%s)" % (item), color="k", linewidth=1.5)
        plt.plot(x, predict_y, label="prediction(%s)" % (item), color="g", marker="o", linewidth=1.5)
        plt.xlabel("Time Intervals(per 30 sec)")
        item_value = "Values"
        if item == "cpu":
            item_value = "CPU Cores"
        elif item == "memory":
            item_value = "Memory Size(GB)"
        elif item == "network":
            item_value = "Network(MBps)"
        plt.ylabel(item_value)
        # ylim = max(max(real_y), max(predict_y))*self.alpha
        # plt.ylim(0, ylim)
        plt.legend(loc=0)
        plt.title("%s for %s" % (entry, role))
        if entry.find("Regression") != -1:
            # print "save file to ./picture/regression-%s-%s.png" % (item, role)
            plt.savefig("%s/regression-%s-%s.png" % (self.path, item, role))
        elif entry.find("Prediction*C") != -1:
            # print "save file to ./picture/predictionc-%s-%s.png" % (item, role)
            plt.savefig("%s/predictionc-%s-%s.png" % (self.path, item, role))
        else:
            # print "save file to ./picture/prediction-%s-%s.png" % (item, role)
            plt.savefig("%s/prediction-%s-%s.png" % (self.path, item, role))
        plt.close()

    def get_workload_picture(self, x, message_y):
        plt.figure(figsize=(8, 4))
        plt.plot(x, message_y, label="ma workload", color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per 30 sec)")
        plt.ylabel("Messages(M)")
        plt.legend(loc=0)
        plt.title("MA's Workloads(messages)")
        plt.savefig("%s/ma-workload.png" % self.path)
        plt.close()

    def get_correlation_picture(self, x, correlation_y, role1, role2):
        plt.figure(figsize=(8, 4))
        plt.plot(x, correlation_y, label="%s-%s" % (role1, role2), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per 30 sec)")
        plt.ylabel("Correlations")
        plt.ylim(-1.2, 1.2)
        plt.legend(loc=0)
        plt.title("%s-->%s Correlations" % (role1, role2))
        plt.savefig("%s/%s-%s-correlation.png" % (self.path, role1, role2))
        plt.close()

    def get_ratio_picture(self, x, ratio_y, role1, role2):
        plt.figure(figsize=(8, 4))
        plt.plot(x, ratio_y, label="ratio-%s-%s" % (role1, role2), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per 30 sec)")
        plt.ylabel("Ratios")
        # plt.ylim(0, 1.2)
        plt.legend(loc=0)
        plt.title("%s's %s Ratio" % (role1, role2))
        plt.savefig("%s/%s-%s-ratio" % (self.path, role1, role2))
        plt.close()

    def get_utilization_picture(self, x, utilization_y, role, item):
        plt.figure(figsize=(8, 4))
        plt.plot(x, utilization_y, label="utilization(%s)" % (role), color="k", linewidth=1.5)
        plt.xlabel("Time Intervals(per 30 sec)")
        item_value = "Values"
        if item == "cpu":
            item_value = "CPU Cores"
        elif item == "memory":
            item_value = "Memory Size(GB)"
        elif item == "network":
            item_value = "Network(MBps)"
        plt.ylabel(item_value)
        plt.legend(loc=0)
        plt.title("%s %s Utilization" % (role, item))
        # print "save file to ./picture/%s-%s-utilization.png" % (role, item)
        plt.savefig("%s/%s-%s-utilization.png" % (sefl.path, role, item))
        plt.close()

    def get_producer_consumer_rate_picture(self, x, current_producer_list, current_consumer_list, sarima_producer_list, role):
        plt.figure(figsize=(8, 4))
        plt.plot(x, current_producer_list, label="Current-Producer-Rate(%s)" % role, color="b", linewidth=1.5)
        plt.plot(x, current_consumer_list, label="Current-Consumer-Rate(%s)" % role, color="g", linewidth=1.5)
        plt.plot(x, sarima_producer_list, label="SARIMA-Producer-Rate(%s)" % (role), color="k", linewidth=1.5, linestyle=":")
        plt.xlabel("Time Intervals(per 1 min)")
        plt.ylabel("Message/Min")
        plt.legend(loc=0)
        max_y = max([max(current_producer_list), max(current_consumer_list), max(sarima_producer_list)])*self.alpha
        plt.ylim(0, max_y)
        plt.title("Producer/Consumer Processing Rate/Min")
        plt.savefig("%s/producer-consumer-rate" % (self.path))
        plt.close()

    def get_desired_replica_picture(self, x, ma_replica_list, sarima_replica_list, best_replica_list, role):
        plt.figure(figsize=(8, 4))
        plt.plot(x, ma_replica_list, label="MA-Replica(%s)" % role, color="b", linewidth=1.5, linestyle=":")
        plt.plot(x, sarima_replica_list, label="SARIMA-Replica(%s)" % (role), color="k", linewidth=1.5, linestyle=":")
        plt.plot(x, best_replica_list, label="Best-Replica(%s)" % role, color="r", marker="o", linewidth=1.5)
        plt.xlabel("Time Intervals(per 1 min)")
        plt.ylabel("Number of Replicas")
        plt.legend(loc=0)
        max_y = max([max(ma_replica_list), max(best_replica_list), max(sarima_replica_list)])*self.alpha
        plt.ylim(0, max_y)
        plt.title("Recommendation - Desired Replicas")
        plt.savefig("%s/desired-replicas" % (self.path))
        plt.close()

    def get_producer_consumer_lag_picture(self, x, producer_list, consumer_list, lag_list, role):
        plt.figure(figsize=(8, 4))
        plt.plot(x, producer_list, label="Producer Rate(%s)" % role, color="b", linewidth=1.5)
        plt.plot(x, consumer_list, label="Consumer Rate(%s)" % role, color="g", linewidth=1.5)
        plt.plot(x, lag_list, label="Lag(%s)" % role, color="k", linewidth=1.5)
        plt.xlabel("Time Intervals(per 15 sec)")
        plt.ylabel("Message/Min")
        plt.legend(loc=0)
        max_y = max([max(producer_list), max(consumer_list), max(lag_list)])*self.alpha
        plt.ylim(0, max_y)
        plt.title("Producer Rate/Consumer Rate/Lag")
        plt.savefig("%s/producer-consumer-lag" % (self.path))
        plt.close()

    def get_replica_lag_picture(self, x, cpu_list, cpu_limit_list, lag_list):
        # cpu
        plt.figure(figsize=(8, 4))
        plt.subplot(2, 1, 1)
        plt.plot(x, cpu_list, label="CPU (%s)" % (self.item), color="k", linewidth=1.5)
        plt.plot(x, cpu_limit_list, label="CPU Limit (%s)" % (self.item), color="b", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("CPU mCores")
        ylim = max(cpu_limit_list)*self.alpha
        plt.ylim(0, ylim)
        plt.title("CPU Utilization for %s" % self.item)
        plt.legend(loc=1, ncol=3)

        # lag
        plt.subplot(2, 1, 2)
        plt.plot(x, lag_list, label="Lag(%s)" % (self.item), color="k", linewidth=1.5)
        plt.xlabel("Time Intervals(per %s sec)" % log_interval)
        plt.ylabel("Lag")
        ylim = max(lag_list)*self.alpha
        plt.ylim(0, ylim)
        plt.legend(loc=0)
        plt.savefig("%s/cpu-lag-%s.png" % (self.path, self.item))
        plt.close()


