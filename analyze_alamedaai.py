import sys
import json
from oc import OC
namespace = "fed"


def get_pod_name(pod_name_prefix):
    o = OC()
    pod_name = ""
    pod_output = o.get_pods(namespace).split("\n")
    for line in pod_output:
        if line.find(pod_name_prefix) != -1 and line.find("dispatcher") == -1:
            pod_name = line.split()[0]
            break
    print "find pod:", pod_name
    return pod_name


def get_alamedaai_log(pod_name_prefix):
    log_data = {}
    file_name = "/var/log/alameda/alameda-ai/workload_prediction_1m_topic.log"
    o = OC()
    pod_name = get_pod_name(pod_name_prefix)
    output = o.exec_cat(namespace, pod_name, file_name).split("\n")
    count = 0
    non_seasonal_list = []
    zero_list = []
    non_size_list = []
    outlier_list = []
    for line in output:
        if line and line.find("topic_prediction   : SARIMAX Predicted Summary:") != -1:
            print "=== %d ===" % count
            print line
            if line.find("seasonal") == -1:
                non_seasonal_list.append(count)
            for i in range(len(line.split(":"))):
                if line.split(":")[i].find("sample size") != -1:
                    predict_size = line.split(":")[i+1]
                    if predict_size.find("121/121") == -1:
                        non_size_list.append(count)
                if line.split(":")[i].find("zero count") != -1:
                    zero_data = line.split(":")[i+1]
                    if zero_data.find("/0") == -1:
                        zero_list.append(count)
                if line.split(":")[i].find("{'order'") != -1:
                    predict_order = line.split(":")[i+1]
                    if predict_order.find("0)") == -1:
                        outlier_list.append(count)
            count += 1
    print "\n"
    print "=== Summary ==="
    print "wo-seasonal count: %s/%s" % (len(non_seasonal_list), count)
    print "  wo-seasonal: ", non_seasonal_list
    print "\n"
    print "wo-121-size count: %s/%s" % (len(non_size_list), count)
    print "  wo-121-size: ", non_size_list
    print "\n"
    print "zero count: %s/%s" % (len(zero_list), count)
    print "  zero: ", zero_list
    print "\n"
    print "outlier count: %s/%s" % (len(outlier_list), count)
    print "  outlier: ", outlier_list
    return log_data


def main():
    log_Data = get_alamedaai_log("alameda-ai")


if __name__ == "__main__":
    main()
