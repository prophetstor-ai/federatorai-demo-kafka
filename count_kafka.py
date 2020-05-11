import os
import sys
import math
from producer import Producer
from define import topic_name, group_name, traffic_interval, comparision, data_interval, draw_picture
from define import consumer_cpu_limit, consumer_memory_limit, log_interval, traffic_frequency, traffic_ratio
if draw_picture:
    from picture import Picture


def find_tracefile_by_term(dir_term):
    result = {}
    new_dir_list = os.listdir(".")
    dir_name = ""
    for n_dir_name in new_dir_list:
        if n_dir_name.find(dir_term) != -1 and n_dir_name.find("picture") == -1:
            dir_name = n_dir_name
            if dir_name == dir_term:
                break
    if not dir_name:
        dir_name = dir_term
    #   raise Exception("failed to find %s" % dir_term)
    file_list = os.listdir("./%s" % dir_name)
    print "find %s tracefile: %s" % (dir_name, file_list)
    return dir_name, file_list


def read_metrics(dir_name, file_name):
    trace_file = "%s/%s" % (dir_name, file_name)
    metrics_info = {}
    try:
        with open(trace_file, "r") as f:
            output = f.read()
            for line in output.split("\n"):
                if line:
                    timestamp = int(line.split()[0])
                    cpu = int(line.split()[1])
                    cpu_limit = int(float(line.split()[2]))
                    memory = int(line.split()[3])
                    memory_limit = int(float(line.split()[4]))
                    restart = int(line.split()[5])
                    running = int(line.split()[6])
                    crashloopbackoff = int(line.split()[7])
                    oomkilled = int(line.split()[8])
                    overlimit = int(line.split()[9])
                    oom = int(line.split()[10])
                    replica = int(line.split()[11])
                    metrics_info[timestamp] = {}
                    metrics_info[timestamp]["cpu"] = cpu
                    metrics_info[timestamp]["cpulimit"] = cpu_limit
                    metrics_info[timestamp]["memory"] = memory
                    metrics_info[timestamp]["memorylimit"] = memory_limit
                    metrics_info[timestamp]["restart"] = restart
                    metrics_info[timestamp]["running"] = running
                    metrics_info[timestamp]["crashloopbackoff"] = crashloopbackoff
                    metrics_info[timestamp]["oomkilled"] = oomkilled
                    metrics_info[timestamp]["overlimit"] = overlimit
                    metrics_info[timestamp]["oom"] = oom
                    metrics_info[timestamp]["replica"] = replica
    except Exception as e:
        print "failed to read %s: %s" % (trace_file, str(e))
    return metrics_info


def read_latency(dir_name, file_name):
    latency_info = {}
    trace_file = "%s/%s" % (dir_name, file_name)
    try:
        with open(trace_file, "r") as f:
            output = f.read()
            for line in output.split("\n"):
                if line:
                    timestamp = int(line.split()[0])
                    record = int(line.split()[1])
                    max_latency = float(line.split()[2])
                    throughput = float(line.split()[3])
                    avg_latency = float(line.split()[4])
                    t50th_latency = float(line.split()[5])
                    t95th_latency = float(line.split()[6])
                    t99th_latency = float(line.split()[7])
                    t999th_latency = float(line.split()[8])
                    latency_info[timestamp] = {}
                    latency_info[timestamp]["record"] = record
                    latency_info[timestamp]["max_latency"] = max_latency
                    latency_info[timestamp]["throughput"] = throughput
                    latency_info[timestamp]["avg_latency"] = avg_latency
                    latency_info[timestamp]["50th_latency"] = t50th_latency
                    latency_info[timestamp]["95th_latency"] = t95th_latency
                    latency_info[timestamp]["99th_latency"] = t99th_latency
                    latency_info[timestamp]["999th_latency"] = t999th_latency
    except Exception as e:
        print "failed to read %s: %s" % (trace_file, str(e))
    return latency_info


def read_prometheus(dir_name, file_name):
    prometheus_info = {}
    trace_file = "%s/%s" % (dir_name, file_name)
    try:
        with open(trace_file, "r") as f:
            output = f.read()
            for line in output.split("\n"):
                if line and line.find(topic_name) != -1:
                    timestamp = int(line.split()[0])
                    prometheus_info[timestamp] = {}
                    prometheus_info[timestamp][topic_name] = {}
            for line in output.split("\n"):
                if line and line.find(topic_name) != -1 and line.find("kafka_consumergroup_lag") != -1:
                    timestamp = int(line.split()[0])
                    topic_value = int(line.split()[-1])
                    prometheus_info[timestamp][topic_name]["kafka_consumergroup_lag"] = topic_value
                if line and line.find(topic_name) != -1 and line.find("kafka_topic_partition_current_offset") != -1:
                    timestamp = int(line.split()[0])
                    topic_value = int(line.split()[-1])
                    prometheus_info[timestamp][topic_name]["kafka_topic_partition_current_offset"] = topic_value
                if line and line.find(topic_name) != -1 and line.find("kafka_consumergroup_current_offset") != -1:
                    timestamp = int(line.split()[0])
                    topic_value = int(line.split()[-1])
                    prometheus_info[timestamp][topic_name]["kafka_consumergroup_current_offset"] = topic_value
    except Exception as e:
        print "failed to read %s: %s" % (trace_file, str(e))
    return prometheus_info


def read_prometheus_query(dir_name, file_name):
    prometheus_query_info = {}
    trace_file = "%s/%s" % (dir_name, file_name)
    try:
        with open(trace_file, "r") as f:
            output = f.read()
            for line in output.split("\n"):
                if line and len(line.split()):
                    timestamp = int(line.split()[0])
                    log_offset = float(line.split()[1])
                    current_offset = float(line.split()[2])
                    lag = float(line.split()[3])
                    log_offset_min = float(line.split()[4])
                    current_offset_min = float(line.split()[5])
                    prometheus_query_info[timestamp] = {}
                    prometheus_query_info[timestamp]["log_offset"] = log_offset
                    prometheus_query_info[timestamp]["current_offset"] = current_offset
                    prometheus_query_info[timestamp]["lag"] = lag
                    prometheus_query_info[timestamp]["log_offset_min"] = log_offset_min
                    prometheus_query_info[timestamp]["current_offset_min"] = current_offset_min
    except Exception as e:
        print "failed to read %s: %s" % (trace_file, str(e))
    return prometheus_query_info


def read_transactions():
    message_list = []
    p = Producer()
    transaction_list = p.read_transaction_list()
    for i in range(traffic_interval):
        for j in range(traffic_frequency):
            transaction = int(transaction_list[i]/traffic_frequency)
            message = transaction * traffic_ratio
            message_list.append(message)
    return message_list


def correct_timestamp(result_info):
    timestamp_list = []
    for iterm in result_info.keys():
        for timestamp in sorted(result_info[iterm].keys()):
            new_timestamp = timestamp / log_interval
            if new_timestamp not in timestamp_list:
                timestamp_list.append(new_timestamp)
    return timestamp_list


def generate_data_by_timestamp(timestamp_list, metrics_info):
    data = {}
    for timestamp in metrics_info.keys():
        new_timestamp = timestamp / log_interval
        time_index = timestamp_list.index(new_timestamp)
        data[time_index] = metrics_info[timestamp]

    item_list = []
    for index in data.keys():
        if data[index]:
            item_list = data[index].keys()
            break

    output_data = {}
    data_length = data_interval * 60 / log_interval
    for i in range(data_length):
        if i not in data.keys():
            if data.get(i-1):
                # print "%dth data is not existed, use %d data to replace it" % (i, i-1)
                data[i] = data[i-1]
                output_data[i] = data[i]
            elif data.get(i+1):
                data[i] = data[i+1]
                output_data[i] = data[i]
            else:
                # print "%dth data cannot replace it" % (i)
                # output_data[i] = {}
                # for item in item_list:
                #    output_data[i][item] = 0
                pass
        else:
            output_data[i] = data[i]
    return output_data


def generate_resource_picture(dir_term, role, timestamp_list, metrics_info):
    data = generate_data_by_timestamp(timestamp_list, metrics_info)

    cpu_list = []
    cpu_limit_list = []
    overlimit_list = []
    memory_list = []
    memory_limit_list = []
    oom_list = []

    restart_list = []
    crashloopbackoff_list = []
    oomkilled_list = []
    replica_list = []
    time_list = []
    count = 0
    data = metrics_info
    for index in sorted(data.keys()):
        cpu = data[index].get("cpu", 0)
        cpu_limit = data[index].get("cpulimit", 0)
        overlimit = data[index].get("overlimit", 0)
        cpu_list.append(cpu)
        cpu_limit_list.append(cpu_limit)
        overlimit_list.append(overlimit)

        memory = data[index].get("memory", 0)
        memory_limit = data[index].get("memorylimit", 0)
        oom = data[index]["oom"]
        replica = data[index]["replica"]

        memory_list.append(memory)
        memory_limit_list.append(memory_limit)
        oom_list.append(oom)
        replica_list.append(replica)
        count += 1
        time_list.append(count)
    print "--- %s ---" % role
    print "avg. cpu", sum(cpu_list)/len(cpu_list), "mCore"
    print "avg. memory", sum(memory_list)/len(memory_list), "MB"
    print "cpu overlimit", sum(overlimit_list)
    print "memory oom", sum(oom_list)
    print "avg. replicas", sum(replica_list)/len(replica_list)
    print "min. replicas", min(replica_list)
    print "max. replicas", max(replica_list)
    if draw_picture:
        p = Picture(item=dir_term)
        p.get_cpu_mem_picture(role, time_list, cpu_list, cpu_limit_list, memory_list, memory_limit_list)
        p.get_replica_picture(group_name, time_list, replica_list)


def generate_latency_picture(dir_term, timestamp_list, producer_info):
    producer_data = generate_data_by_timestamp(timestamp_list, producer_info)
    avg_latency_list = []
    record_list = []
    throughput_list = []
    max_latency_list = []
    t50latency_list = []
    t95latency_list = []
    t99latency_list = []
    t999latency_list = []
    drop_count = 0
    for index in sorted(producer_data.keys()):
        avg_latency = producer_data[index]["avg_latency"]
        record = producer_data[index]["record"]
        if record == -1:
            drop_count += 1

        max_latency = producer_data[index]["max_latency"]
        throughput = producer_data[index]["throughput"]
        t50latency = producer_data[index]["50th_latency"]
        t95latency = producer_data[index]["95th_latency"]
        t99latency = producer_data[index]["99th_latency"]
        t999latency = producer_data[index]["999th_latency"]
        avg_latency_list.append(avg_latency)
        record_list.append(record)
        max_latency_list.append(max_latency)
        throughput_list.append(throughput)
        t50latency_list.append(t50latency)
        t95latency_list.append(t95latency)
        t99latency_list.append(t99latency)
        t999latency_list.append(t999latency)
    print "--- producer latency ---"
    print "drop count", drop_count
    print "avg. num records", round(sum(record_list)/len(record_list), 2), "sent"
    print "avg. latency", round(sum(avg_latency_list)/len(avg_latency_list), 2), "ms"
    print "avg. throughput", round(sum(throughput_list)/len(throughput_list), 2), "records/sec"

    request_list = []
    response_list = []
    index_list = []
    count = 0
    message_list = read_transactions()
    for timestamp in sorted(producer_info.keys()):
        response = producer_info[timestamp]["record"]
        response_list.append(response)
        count += 1
        index_list.append(count)
        request = 0
        if count < len(message_list):
            request = message_list[count]
        request_list.append(request)

    if draw_picture:
        p = Picture(item=dir_term)
        p.get_latency_picture(sorted(producer_data.keys()), record_list, avg_latency_list)
        p.get_message_picture(index_list, response_list, request_list)


def generate_prometheus_picture(dir_term, timestamp_list, prometheus_query_info, consumer_info):
    prometheus_query_data = generate_data_by_timestamp(timestamp_list, prometheus_query_info)
    consumer_data = generate_data_by_timestamp(timestamp_list, consumer_info)
    prom_query_lag_list = []
    prom_query_log_offset_list = []
    prom_query_current_offset_list = []
    prom_query_log_offset_min_list = []
    prom_query_current_offset_min_list = []
    prom_query_lag_diff_list = []
    for index in sorted(prometheus_query_data.keys()):
        prom_query_lag = prometheus_query_data[index]["lag"]
        prom_query_log_offset = prometheus_query_data[index]["log_offset"]
        prom_query_current_offset = prometheus_query_data[index]["current_offset"]
        prom_query_log_offset_min = prometheus_query_data[index]["log_offset_min"]
        prom_query_current_offset_min = prometheus_query_data[index]["current_offset_min"]
        prom_query_lag_list.append(prom_query_lag)
        prom_query_log_offset_list.append(prom_query_log_offset)
        prom_query_current_offset_list.append(prom_query_current_offset)
        prom_query_log_offset_min_list.append(prom_query_log_offset_min)
        prom_query_current_offset_min_list.append(prom_query_current_offset_min)
        lag_diff = prom_query_log_offset_min - prom_query_current_offset_min
        prom_query_lag_diff_list.append(lag_diff)

    print "--- prometheus query ---"
    avg_prom_query_lag = sum(prom_query_lag_list)/len(prom_query_lag_list)
    print "avg. prom. query lag = ", avg_prom_query_lag
    print "max. prom. query lag = ", max(prom_query_lag_list)
    avg_prom_query_log_offset_min = sum(prom_query_log_offset_min_list)/len(prom_query_log_offset_min_list)
    avg_prom_query_current_offset_min = sum(prom_query_current_offset_min_list)/len(prom_query_current_offset_min_list)
    print "avg. prom. producer processing rate = ", avg_prom_query_log_offset_min
    print "avg. prom. consumer processing rate = ", avg_prom_query_current_offset_min
    # print "avg. Prom. query log offset - current offset =", sum(prom_query_lag_diff_list)/len(prom_query_lag_diff_list)

    cpu_list = []
    cpu_limit_list = []
    for index in sorted(consumer_data.keys()):
        cpu = consumer_data[index].get("cpu", 0)
        cpu_limit = consumer_data[index].get("cpulimit", 0)
        cpu_list.append(cpu)
        cpu_limit_list.append(cpu_limit)
    if len(consumer_data.keys()) < len(prom_query_lag_list):
        diff = len(prom_query_lag_list) - len(consumer_data.keys())
        for i in range(diff):
            prom_query_lag_list.pop(len(prom_query_lag_list)-1)

    if draw_picture:
        p = Picture(item=dir_term)
        p.get_replica_lag_picture(sorted(consumer_data.keys()), cpu_list, cpu_limit_list, prom_query_lag_list)


def generate_result_info(dir_term):
    result_info = {}
    dir_name, file_list = find_tracefile_by_term(dir_term)
    for file_name in file_list:
        if file_name.find(".swp") != -1:
            continue
        if file_name.find("test") != -1:
            continue
        if file_name.find("broker_metrics") != -1:
            result_info["broker"] = read_metrics(dir_name, file_name)
        elif file_name.find("zookeeper_metrics") != -1:
            result_info["zookeeper"] = read_metrics(dir_name, file_name)
        elif file_name.find("producer_metrics") != -1:
            producer_info = read_metrics(dir_name, file_name)
            result_info["producer_metrics"] = producer_info
        elif file_name.find("consumer") != -1:
            result_info["consumer"] = read_metrics(dir_name, file_name)
        elif file_name.find("producer_latency") != -1:
            latency_info = read_latency(dir_name, file_name)
            result_info["producer_latency"] = latency_info
        elif file_name.find("prometheus") != -1 and file_name.find("prometheus_query") == -1:
            result_info["prometheus"] = read_prometheus(dir_name, file_name)
        elif file_name.find("prometheus") != -1 and file_name.find("prometheus_query") != -1:
            result_info["prometheus_query"] = read_prometheus_query(dir_name, file_name)
    return result_info


def main(dir_term):
    result_info = generate_result_info(dir_term)
    timestamp_list = correct_timestamp(result_info)
    overprovision_info = {}
    overprovision_timestamp_list = {}
    if os.path.exists(comparision):
        overprovision_info = generate_result_info(comparision)
        overprovision_timestamp_list = correct_timestamp(overprovision_info)
    if result_info.get("producer_metrics"):
        generate_resource_picture(dir_term, "producer", timestamp_list, result_info["producer_metrics"])
    if result_info.get("consumer"):
        generate_resource_picture(dir_term, "consumer", timestamp_list, result_info["consumer"])
    if result_info.get("producer_latency"):
        generate_latency_picture(dir_term, timestamp_list, result_info["producer_latency"])
    if result_info.get("prometheus_query"):
        generate_prometheus_picture(dir_term, timestamp_list, result_info["prometheus_query"], result_info["consumer"])


if __name__ == "__main__":
    dir_term = sys.argv[1]
    main(dir_term)
