import sys
import os
import json
from picture import Picture
from define import traffic_ratio, group_name, topic_name

test_dir = "test_result"


def find_trace_dir_by_term():
    nonhpa_list = []
    nativehpa_list = []
    federatorai_list = []
    dir_name = test_dir
    dir_list = os.listdir(dir_name)
    for dir_name in dir_list:
        if dir_name.find("non_hpa") != -1:
            nonhpa_list.append(dir_name)
        if dir_name.find("native") != -1:
            nativehpa_list.append(dir_name)
        if dir_name.find("federator") != -1:
            federatorai_list.append(dir_name)
    print "nonhpa:", nonhpa_list
    print "k8shpa:", nativehpa_list
    print "federatorai:", federatorai_list
    return nonhpa_list, nativehpa_list, federatorai_list


def get_real_workloads(dir_name):
    file_name = ""
    dir_path = "./%s/%s" % (test_dir, dir_name)
    sub_dir_path = ""
    file_name_list = os.listdir(dir_path)
    for file_name in file_name_list:
        if file_name.find("fedai") != -1:
            sub_dir_path = "%s/%s" % (dir_path, file_name)
        if file_name.find("k8s") != -1:
            sub_dir_path = "%s/%s" % (dir_path, file_name)
        if file_name.find("non") != -1:
            sub_dir_path = "%s/%s" % (dir_path, file_name)
    sub_file_list = os.listdir(sub_dir_path)

    for sub_file_name in sub_file_list:
        if sub_file_name.find("prometheus_query") != -1:
            file_name = "%s/%s" % (sub_dir_path, sub_file_name)
    lag_list = []
    producer_rate_list = []
    consumer_rate_list = []
    try:
        with open(file_name, "r") as f:
            output = f.read()
            for line in output.split("\n"):
                if line:
                    producer_rate = float(line.split()[1])
                    consumer_rate = float(line.split()[2])
                    lag = float(line.split()[-1])
                    if len(line.split()) > 4:
                        lag = float(line.split()[-3])
                        producer_rate = float(line.split()[-2])
                        consumer_rate = float(line.split()[-1])
                    lag_list.append(lag)
                    producer_rate_list.append(producer_rate)
                    consumer_rate_list.append(consumer_rate)
    except Exception as e:
        print "failed to read %s: %s" % (file_name, str(e))
    return lag_list, producer_rate_list, consumer_rate_list


def find_recommenderlog_by_trace_dir(dir_name):
    file_name = "./%s/%s/recommender/log" % (test_dir, dir_name)
    print "file=", file_name
    log_data = {}
    try:
        with open(file_name, "r") as f:
            output = f.read().split("\n")
            for line in output:
                if line.find("Desired") != -1:
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
    except Exception as e:
        print "failed to read %s: %s" % (file_name, str(e))
    return log_data


def show_recommender_log(log_data):
    print "\n"
    count = 0
    outlier_count = 0
    total_mape_list = []
    for timestamp in sorted(log_data.keys()):
        print "=== %sth  %s ===" % (count, timestamp)
        current_logoffset = log_data[timestamp]["ma0_data"]["LogOffset"]
        print "current logoffset =", current_logoffset
        print "current currentoffset =", log_data[timestamp]["ma0_data"]["CurrentOffset"]
        print "current lag =", log_data[timestamp]["ma0_data"]["LagOffset"]
        print "current replicas =", log_data[timestamp]["ma0_data"]["CurrentReplicas"]
        for item in sorted(log_data[timestamp].keys()):
            if item != "best_desired_replicas":
                print "--- %s ---" % item
                mape = round((log_data[timestamp][item]["LogOffset"] - current_logoffset)*100, 2)
                if current_logoffset != 0:
                    mape = round((log_data[timestamp][item]["LogOffset"] - current_logoffset)/current_logoffset*100, 2)
                if abs(mape) <= 200:
                    total_mape_list.append(abs(mape))
                else:
                    outlier_count += 1
                print " LogOffset = ", log_data[timestamp][item]["LogOffset"], "MAPE=", mape, "%"
                print " DesiredReplicas = ", log_data[timestamp][item]["DesiredReplicas"]
                if log_data[timestamp][item].get("LogOffset"):
                    print " Lag/LogOffset = ", float(log_data[timestamp][item]["LagOffset"])/float(log_data[timestamp][item]["LogOffset"])
            elif log_data[timestamp].get("best_desired_replicas"):
                best_desired_replicas = log_data[timestamp]["best_desired_replicas"]
                print "best_desired_replicas", best_desired_replicas
        #    print "\n"
        # print total_mape_list
        count += 1
        print "\n"
    print "avg. mape =", round(sum(total_mape_list)/len(total_mape_list), 2), "%"
    print "outlier =", outlier_count
    print "total recommendations: ", len(log_data.keys())


def draw_picture(log_data, dir_name):
    file_path = "%s/%s" % (test_dir, dir_name)
    count = 0
    data_interval = 5
    current_producer_data_list = []
    current_consumer_data_list = []
    current_lag_list = []
    ma_replica_list = []
    sarima_replica_list = []
    best_replica_list = []
    sarima_producer_data_list = []
    time_list = []
    time_count = 0
    for timestamp in sorted(log_data.keys()):
        current_producer_data = log_data[timestamp]["ma0_data"]["LogOffset"]
        current_consumer_data = log_data[timestamp]["ma0_data"]["CurrentOffset"]
        current_lag = log_data[timestamp]["ma0_data"]["LagOffset"]
        best_replica = log_data[timestamp].get("best_desired_replicas")
        ma_replica = log_data[timestamp]["ma0_data"]["DesiredReplicas"]
        for i in range(data_interval):
            current_producer_data_list.append(current_producer_data)
            current_consumer_data_list.append(current_consumer_data)
            current_lag_list.append(current_lag)
            ma_replica_list.append(ma_replica)
            best_replica_list.append(best_replica)
        for i in range(data_interval):
            sarima_producer_data = 0
            sarima_replica = 0
            if log_data[timestamp].get("predict%s_data" % (i+1)):
                sarima_producer_data = log_data[timestamp]["predict%s_data" % (i+1)]["LogOffset"]
                sarima_replica = log_data[timestamp]["predict%s_data" % (i+1)]["DesiredReplicas"]
            sarima_producer_data_list.append(sarima_producer_data)
            sarima_replica_list.append(sarima_replica)
            time_count += 1
            time_list.append(time_count)
    lag_list, producer_rate_list, consumer_rate_list = get_real_workloads(dir_name)
    time2_list = []
    for i in range(len(producer_rate_list)):
        time2_list.append(i)

    p = Picture(file_path)
    p.get_producer_consumer_rate_picture(time_list, current_producer_data_list, current_consumer_data_list, sarima_producer_data_list, dir_name)
    dir_name1 = "%s-prom" % dir_name.split("_")[-1]
    p.get_lag_picture(group_name, topic_name, time2_list, lag_list, dir_name1)
    p.get_current_offset_diff_picture(group_name, topic_name, time2_list, consumer_rate_list, dir_name)
    p.get_log_offset_diff_picture(group_name, topic_name, time2_list, producer_rate_list, dir_name)
    p.get_producer_consumer_lag_picture(time2_list, producer_rate_list, consumer_rate_list, lag_list, dir_name)

    p.get_desired_replica_picture(time_list, ma_replica_list, sarima_replica_list, best_replica_list, dir_name)
    p.get_lag_picture(group_name, topic_name, time_list, current_lag_list, dir_name)


def main(algo_name, timestamp):
    nonhpa_list, nativehpa_list, federatorai_list = find_trace_dir_by_term()
    dir_list = []
    if algo_name.find("nonhpa") != -1:
        dir_list = nonhpa_list
    elif algo_name.find("nativehpa") != -1:
        dir_list = nativehpa_list
    elif algo_name.find("federatorai") != -1:
        dir_list = federatorai_list
    dir_name = dir_list[-1]
    for dir_prefix in dir_list:
        if dir_prefix.find(timestamp) != -1:
            dir_name = dir_prefix
    print "find dir: =", dir_name
    recommender_log = find_recommenderlog_by_trace_dir(dir_name)
    show_recommender_log(recommender_log)
    draw_picture(recommender_log, dir_name)


if __name__ == "__main__":
    algo_name = sys.argv[1]
    timestamp = sys.argv[2]
    main(algo_name, timestamp)
