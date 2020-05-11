import sys
import json
import os
from oc import OC
from fetch_log import fetch_data
from write_log import WriteLog
namespace = "fed"


def get_pod_name(pod_name_prefix):
    o = OC()
    pod_name = ""
    pod_output = o.get_pods(namespace).split("\n")
    for line in pod_output:
        if line.find(pod_name_prefix) != -1:
            pod_name = line.split()[0]
            break
    return pod_name


def get_recommender_log(pod_name_prefix):
    log_data = {}
    o = OC()
    pod_name = get_pod_name(pod_name_prefix)
    log_output = o.log_pod(namespace, pod_name).split("\n")
    for line in log_output:
        if line and line.find("Desired") != -1:
            if line.find("Evaluate Cost parameters") != -1:
                timestamp = line.split()[0].split(".")[0]
                cost_data_list = line.split("\t")[-1].split()
            if line.find("desired replicas result") != -1 and line.find("best") == -1:
                timestamp = line.split()[0].split(".")[0]
                log_data[timestamp] = {}
                recommender_data_list = json.loads(line.split("\t")[-1].split()[-1])
                count = 0
                for data in recommender_data_list:
                    if count == 0:
                        log_data[timestamp]["ma%d_data" % count] = data
                    else:
                        log_data[timestamp]["predict%d_data" % count] = data
                    count += 1
            if line.find("best desired replicas result") != -1:
                timestamp = line.split()[0].split(".")[0]
                if log_data.get(timestamp):
                    best_desired_replicas = json.loads(line.split("\t")[-1].split()[-1]).get("DesiredReplicas")
                    log_data[timestamp]["best_desired_replicas"] = best_desired_replicas
                    best_execution_time = json.loads(line.split("\t")[-1].split()[-1]).get("BestExecutationTime")
                    log_data[timestamp]["best_execution_time"] = best_execution_time
    return log_data


def get_prometheus_log():
    file_list = os.listdir("./traffic")
    file_name = "./traffic/"
    for file_prefix in file_list:
        if file_prefix.find("prometheus_query") != -1:
            file_name = "./traffic/%s" % file_prefix
            break
    print "file_name =", file_name
    data = {}
    data["lag"] = []
    data["producer_rate"] = []
    data["consumer_rate"] = []
    try:
        with open(file_name, "r") as f:
            output = f.read().split("\n")
            for line in output:
                if line:
                    line = line.split()
                    lag = int(float(line[-3]))
                    producer_rate = int(float(line[-2]))
                    consumer_rate = int(float(line[-1]))
                    data["lag"].append(lag)
                    data["producer_rate"].append(producer_rate)
                    data["consumer_rate"].append(consumer_rate)
    except Exception as e:
        print "failed to read %s: %s" % (file_name, str(e))
    return data


def main():
    recommender_data = get_recommender_log("recommender")
    show_recommender_data(recommender_data)
    # lod_data = get_prometheus_log()


def show_recommender_data(recommender_data):
    count = 0
    best_execution_time_list = []
    error_rate_list = []
    for timestamp in sorted(recommender_data.keys()):
        print "=== %s - %s ===" % (count, timestamp)
        print sorted(recommender_data[timestamp].keys())
        if "ma0_data" in recommender_data[timestamp].keys():
            current_logoffset = recommender_data[timestamp]["ma0_data"]["LogOffset"]
            current_currentoffset = recommender_data[timestamp]["ma0_data"]["CurrentOffset"]
            current_lag = recommender_data[timestamp]["ma0_data"]["LagOffset"]
            current_replicas = recommender_data[timestamp]["ma0_data"]["CurrentReplicas"]
            print "current producer rate = %s; consumer rate = %s; lag=%s; replicas= %s" % (current_logoffset, current_currentoffset, current_lag, current_replicas)
        for item in sorted(recommender_data[timestamp].keys()):
            if item not in ["best_desired_replicas", "best_execution_time"]:
                print "- %s " % item
                LogOffset = recommender_data[timestamp][item]["LogOffset"]
                LagOffset = recommender_data[timestamp][item]["LagOffset"]
                CurrentOffset = recommender_data[timestamp][item]["CurrentOffset"]
                DesiredReplicas = recommender_data[timestamp][item]["DesiredReplicas"]
                CurrentReplicas = recommender_data[timestamp][item]["CurrentReplicas"]
                Cost = recommender_data[timestamp][item]["Cost"]
                if current_logoffset != 0:
                    error_rate = round((LogOffset - current_logoffset)/current_logoffset*100, 2)
                    error_rate_list.append(abs(error_rate))
                print "   LogOffset = %s, ErrorRate=%s" % (LogOffset, error_rate), "%"
                print "   DesiredReplicas = %s" % (DesiredReplicas)
                print "   Cost = %s" % Cost
                if CurrentOffset != 0:
                    replicas = (LogOffset + LagOffset/5)/CurrentOffset*CurrentReplicas
                    # print "   ComputedReplicas = %s" % (replicas)
                if LogOffset != 0:
                    lag_ratio = LagOffset/LogOffset
                    print "   lag_ratio=", lag_ratio
            else:
                print "- summary "
                print "   %s = %s" % (item, recommender_data[timestamp][item])
                if recommender_data[timestamp].get("best_execution_time"):
                    best_execution_time = recommender_data[timestamp].get("best_execution_time")*60
                    best_execution_time_list.append(best_execution_time)
        print "\n"
        count += 1
    if count > 1:
        print "=== Summary ==="
        print "avg. prediction error rate =", round(sum(error_rate_list)/len(error_rate_list), 2), "%"
        calculate_scale_up_time(best_execution_time_list)


def calculate_scale_up_time(best_execution_time_list):
    pod_data_info = fetch_data()
    pod_start_time_list = []
    rebalance_time_list = {}
    for pod_name in pod_data_info.keys():
        pod_start_time = 0
        revoke_time_list = pod_data_info[pod_name].get("partitions_revoked_time")
        if revoke_time_list:
            pod_start_index = sorted(revoke_time_list.keys())[-1]
            pod_start_time = revoke_time_list[pod_start_index]
        for best_execution_time in best_execution_time_list:
            if pod_start_time != 0 and pod_start_time > best_execution_time:
                diff_time = pod_start_time - best_execution_time * 1000
                if diff_time < 300000 and diff_time > 0:
                    pod_start_time_list.append(diff_time)
        rebalance_time_list = pod_data_info[pod_name].get("rebalance_time")
    if rebalance_time_list:
        print "avg. rebalance time(ms) =", sum(rebalance_time_list.values())/len(rebalance_time_list.values())
    if pod_start_time_list:
        print "avg. join/leave time(ms) =", sum(pod_start_time_list)/len(pod_start_time_list)
    # print pod_start_time_list


if __name__ == "__main__":
    main()
