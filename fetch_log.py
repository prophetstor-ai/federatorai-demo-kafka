from kubectl import Kubectl
from oc import OC
import json


class FetchLog:
    k = Kubectl()
    o = OC()
    namespace = "myproject"
    app_name = "consumer"

    def __init__(self):
        pass

    def get_pod_list(self):
        pod_list = []
        output = self.o.get_pods(self.namespace)
        for line in output.split("\n"):
            if line.find(self.app_name) != -1 and line:
                pod_name = line.split()[0]
                pod_list.append(pod_name)
        return pod_list

    def fetch_log(self, pod_name):
        # print "pod_name=", pod_name
        data = {}
        data["start_complete_time"] = 0
        data["partitions_revoked_time"] = {}
        data["partitions_assigned_time"] = {}
        data["rebalance_time"] = {}
        revoked_index = 0
        assigned_index = 0
        output = self.o.log_pod(self.namespace, pod_name)
        for line in output.split("\n"):
            if line.find("startup_complete") != -1:
                # print line
                startup_complete_time = json.loads(line).get("timestamp")
                data["start_complete_time"] = int(startup_complete_time)
            if line.find("partitions_revoked") != -1:
                # print line
                partitions_revoked_time = json.loads(line).get("timestamp")
                data["partitions_revoked_time"][revoked_index] = int(partitions_revoked_time)
                revoked_index += 1
            if line.find("partitions_assigned") != -1:
                # print line
                partitions_assigned_time = json.loads(line).get("timestamp")
                data["partitions_assigned_time"][assigned_index] = int(partitions_assigned_time)
                assigned_index += 1
        rebalance_count = len(data["partitions_assigned_time"].keys())
        for i in range(rebalance_count):
            if i == 0:
                data["rebalance_time"][i] = data["partitions_assigned_time"][i] - data["start_complete_time"]
            elif data["partitions_revoked_time"]:
                data["rebalance_time"][i] = data["partitions_assigned_time"][i] - data["partitions_revoked_time"][i-1]
        # print data
        return data


def fetch_data():
    f = FetchLog()
    pod_data_info = {}
    try:
        pod_list = f.get_pod_list()
        for pod in pod_list:
            pod_data = f.fetch_log(pod)
            pod_data_info[pod] = pod_data
    except Exception as e:
        print "failed to fetch consumer logs: %s" % str(e)
        pass
    return pod_data_info


if __name__ == "__main__":
    fetch_data()
