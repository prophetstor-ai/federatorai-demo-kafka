import sys
import time
import os
import yaml
import shutil
from oc import OC
from datetime import datetime
from define import warm_up, metrics_path,  picture_path, partition_number
from define import initial_consumer, traffic_path, consumer_cpu_limit, consumer_memory_limit
from define import k8shpa_type, k8shpa_percent, query_mode, partition_number, config_path


def wait_pod_running(namespace):
    print "wait pods in %s running" % namespace
    start_time = time.time()
    while True:
        output = OC().get_pods(namespace)
        print "wait 30 sec"
        time.sleep(30)
        end_time = time.time()
        if end_time - start_time >= 600:
            raise Exception("timeout for waiting pods running")
            break
        count = 0
        for line in output.split("\n"):
            if line and line.find("NAME") == -1:
                status = line.split()[2]
                ready = line.split()[1]
                if ready != "1/1" and status != "Running":
                    print line
                elif (ready == "1/1" or ready == "2/2" or ready == "3/3") and status == "Running":
                    count += 1
        print "%s pods in %s are running" % (count, namespace) 
        if count >= 8 + initial_consumer:
            print "all pods in %s are running and ready" % namespace
            break

def clean_data(algo, namespace, resource_type, resource):
    #output = OC().scale_replica(namespace, resource_type, resource, 0)
    #if algo in ["k8shpa", "alameda"]:
    #output = OC().scale_replica(namespace, resource_type, resource, initial_consumer)
    #else:
    #    output = OC().scale_replica(namespace, resource_type, resource, overprovision_replica)
    wait_pod_running(namespace)
    #return output


def create_directory():
    if not os.path.exists(traffic_path):
        os.mkdir(traffic_path)
        print "%s is created" % traffic_path
    elif os.path.exists(traffic_path):
        print "%s is existed" % traffic_path

    if not os.path.exists(metrics_path):
        os.mkdir(metrics_path)
        print "%s is created" % metrics_path
    elif os.path.exists(metrics_path):
        print "%s is existed" % metrics_path

    if not os.path.exists(picture_path):
        os.mkdir(picture_path)
        print "%s is created" % picture_path
    elif os.path.exists(picture_path):
        print "%s is existed" % picture_path


def remove_directory():
    shutil.rmtree(traffic_path)
    shutil.rmtree(metrics_path)
    shutil.rmtree(picture_path)


def change_directory_name(dir_name):
    if os.path.exists(traffic_path):
        os.rename(traffic_path, dir_name)
        print "change %s to %s" % (traffic_path, dir_name)
    else:
        print "dir: %s is not existed" % traffic_path


def find_pod_name(app_name, app_namespace):
    pod_name_list = []
    status = ""
    output = OC().get_pods(app_namespace)
    for line in output.split("\n"):
        if line.find(app_name) != -1:
            pod_name = line.split()[0]
            if pod_name.find("build") != -1:
                continue
            status = line.split()[2]
            if status not in ["Running"]:
                raise Exception("%s is %s" % (pod_name, status))
            pod_name_list.append(pod_name)
    if not pod_name_list:
        raise Exception("%s is not existed in %s" % (app_name, app_namespace))
    return pod_name_list


def find_alameda_namespace(app_name):
    namespace = ""
    output = OC().get_pods_all_namespace()
    for line in output.split("\n"):
        if line.find(app_name) != -1:
            namespace = line.split()[0]
            break
    if namespace:
        print "find %s's namespace: %s" % (app_name, namespace)
    else:
        raise Exception("ns: %s is not existed" % namespace)
    return namespace


def restart_pod(app_name, app_namespace):
    output = ""
    pod_name_list = find_pod_name(app_name, app_namespace)
    for pod_name in pod_name_list:
        output = OC().delete_pod(pod_name, app_namespace)
        print output
    return output


def enable_executor():
    print "enable executor"
    output = OC().apply_file("alameda-executor-true.yaml")
    alameda_namespace = find_alameda_namespace("alameda-executor")
    get_executor_status(alameda_namespace, "true")
    return output


def disable_executor():
    print "disable executor"
    output = OC().apply_file("alameda-executor-false.yaml")
    alameda_namespace = find_alameda_namespace("alameda-executor")
    get_executor_status(alameda_namespace, "false")
    return output


def update_k8shpa_yaml(file_name, namespace, resource, value):
    try:
        tmp_file_name = "./%s.tmp" % file_name
        with open(file_name, "r") as f_r:
            output = yaml.load(f_r)
            output["metadata"]["name"] = resource
            output["metadata"]["namespace"] = namespace
            output["spec"]["metrics"][0]["pods"]["targetAverageUtilization"] = value
        with open(tmp_file_name, "w") as f_w:
            yaml.dump(output, f_w)
            f_w.close()
    except Exception as e:
        print "failed to update %s: %s" % (file_name, str(e))
        return -1
    os.rename(tmp_file_name, new_file_name)
    # print "success to update %s" % (new_file_name)
    return 0


def start_k8shpa(namespace, resource_type, resource, num_replica, value):
    output = ""
    print "=== Start K8sHPA: %s ===" % k8shpa_type
    if k8shpa_type == "cpu":
        print "=== Set up autoscale ==="
        output = OC().autoscale_replica(namespace, resource_type, resource, num_replica, value)
        print "%s" % output
    if k8shpa_type == "lag":
        file_name = "%s/consumer-hpa.yaml" % config_path
        print "=== Applying file: %s ===" % file_name
        output = OC().apply_file(file_name)
        print "%s" % output
        
    # elif k8shpa_type == "memory":
    #     file_name = "./k8shpa_memory.yaml"
    #     output = update_k8shpa_yaml(file_name, namespace, resource, value)
    #     output = OC().apply_file(file_name)
    # elif k8shpa_type == "consumergroup_lag":
    #     file_name = "./k8shpa_consumergrouplag.yaml"
    #     # output = update_k8shpa_yaml(file_name, namespace, resource, value)
    #     output = OC().apply_file(file_name)
    #     print output
    return output


def stop_k8shpa(namespace, resource):
    if k8shpa_type == "lag":
        file_name = "%s/consumer-hpa.yaml" % config_path
        output = OC().delete_file(file_name)
        print "%s" % output
    #output = OC().delete_hpa(namespace, resource)
    #return output


def wait_time():
    wait_time = warm_up*60
    #print "wait %s seconds" % wait_time
    time.sleep(wait_time)


def get_dir_name(term):
    timestamp = int(time.time())
    dt_object = str(datetime.fromtimestamp(timestamp)).split()[0]
    dir_list = os.listdir(".")
    count = 0
    for dir in dir_list:
        if dir.find(term) != -1 and not os.path.isfile(dir):
            count += 1
    dir_name = "%s_%s_%d" % (term, dt_object, count)
    return dir_name


def get_executor_status(namespace, desired_status):
    output = OC().get_configmap(namespace, "alameda-executor-config")
    if output.find(desired_status) == -1:
        raise Exception("executor must be %s" % desired_status)


def update_yaml(namespace, enable):
    ret = 0
    output = {}

    file_name = "./alameda-executor.yaml"
    new_file_name = "./alameda-executor-%s.yaml" % str(enable)
    tmp_file_name = "%s.tmp" % file_name

    old_address = "alameda-datahub.federatorai.svc"
    new_address = "alameda-datahub.%s.svc" % namespace
    old_enable_value = "enable: false"
    new_enable_value = "enable: %s" % str(enable)
    try:
        with open(file_name, "r") as f_r:
            output = yaml.load(f_r)
            output["data"]["config.yml"] = output["data"]["config.yml"].replace(old_address, new_address)
            output["data"]["config.yml"] = output["data"]["config.yml"].replace(old_enable_value, new_enable_value)
            output["metadata"]["namespace"] = namespace
        with open(tmp_file_name, "w") as f_w:
            yaml.dump(output, f_w)
            f_w.close()
    except Exception as e:
        print "failed to update %s: %s" % (file_name, str(e))
        ret = -1
        return ret
    os.rename(tmp_file_name, new_file_name)
    # print "success to update %s" % (new_file_name)
    return ret


def find_app_location(app_name, namespace=""):
    app_namespace = ""
    app_type = ""
    resource = ""
    app_list = []
    output = OC().get_deployments_all_namespace()
    if output.find(app_name) != -1:
        for line in output.split("\n"):
            if line.find(app_name) != -1:
                app_namespace = line.split()[0]
                app_type = "deployment"
                resource = line.split()[1]
                app = {}
                app["namespace"] = app_namespace
                app["resource_type"] = app_type
                app["resource"] = resource
                app_list.append(app)
    if not app_list:
        output = OC().get_deploymentconfigs_all_namespace()
        if output.find(app_name) != -1:
            for line in output.split("\n"):
                if line.find(app_name) != -1:
                    app_namespace = line.split()[0]
                    app_type = "deploymentconfig"
                    resource = line.split()[1]
                    app = {}
                    app["namespace"] = app_namespace
                    app["resource_type"] = app_type
                    app["resource"] = resource
                    app_list.append(app)
    if not app_list:
        raise Exception("app: %s is not existed" % app_name)

    # do not choose
    if namespace:
        for app in app_list:
            if app["namespace"] == namespace and app["resource"] == app_name:
                break
        return app_namespace, app_type, resource

    app_namespace = app["namespace"]
    app_type = app["resource_type"]
    resource = app["resource"]
    if query_mode:
        # show app
        i = 0
        print "\n"
        print "*******************************************************************"
        print "   Applications:"
        for app in app_list:
            print "    %d) namespace: %s   %s: %s" % (i, app["namespace"], app["resource_type"], app["resource"])
            i = i + 1
        print "*******************************************************************\n"
        sys.stdin = open('/dev/tty')
        try:
            x = raw_input("input prefered application (default:0): ")
            if not x:
                x = 0
        except Exception:
            x = 0
        x = int(x)
        app_namespace = app_list[x]["namespace"]
        app_type = app_list[x]["resource_type"]
        resource = app_list[x]["resource"]

    print "preferred application is %s/%s" % (app_namespace, resource)
    os.environ["NAMESPACE"] = app_namespace
    os.environ["RESOURCE"] = resource
    os.environ["RESOURCE_TYPE"] = app_type
    return app_namespace, app_type, resource


def get_image_name(app_namespace, app_type, resource):
    output = ""
    image_name = ""
    oc = OC()
    if app_type == "deploymentconfig":
        output = oc.get_specific_deploymentconfig(app_namespace, resource)
    elif app_type == "deployment":
        output = oc.get_specific_deployment(app_namespace, resource)
    if output:
        output = yaml.load(output)
        for container_info in output.get("spec").get("template").get("spec").get("containers"):
            if container_info.get("name") == resource:
                image_name = container_info.get("image")
                break
    return image_name


def update_app_limit(app_namespace, app_type, resource):
    output = {}
    file_name = "./resource.yaml"
    tmp_file_name = "%s.tmp" % file_name
    try:
        with open(file_name, "r") as f_r:
            output = yaml.load(f_r)
            output["spec"]["template"]["spec"]["containers"][0]["name"] = resource
            app_image = get_image_name(app_namespace, app_type, resource)
            if app_image:
                output["spec"]["template"]["spec"]["containers"][0]["image"] = app_image
            output["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["cpu"] = str(cpu_limit)+"m"
            output["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["cpu"] = str(cpu_limit)+"m"
            output["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["memory"] = str(memory_limit)+"Mi"
            output["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["memory"] = str(memory_limit)+"Mi"
        with open(tmp_file_name, "w") as f_w:
            yaml.dump(output, f_w)
            f_w.close()
    except Exception as e:
        print "failed to update %s: %s" % (file_name, str(e))
        return -1
    os.rename(tmp_file_name, file_name)
    if app_type == "deploymentconfig":
        OC().patch_deploymentconfig(app_namespace, resource, file_name)
    else:
        OC().patch_deployment(app_namespace, resource, file_name)
    print "success to update limits(cpu=%dm and memory=%dMi) for %s" % (cpu_limit, memory_limit, resource)
    return 0


def main(algo, action, namespace="", app_name=""):
    #alameda_namespace = find_alameda_namespace("alameda-executor")
    app_namespace = os.environ.get("NAMESPACE")
    app_type = os.environ.get("RESOURCE_TYPE")
    resource = os.environ.get("RESOURCE")
    create_directory()
    if app_name:
        app_namespace, app_type, resource = find_app_location(app_name, namespace)
    # update_app_limit(app_namespace, app_type, resource)
    if not resource or not app_namespace or not app_type:
        raise Exception("%s is not correct deployment/deploymentconfig" % resource)
    if algo == "federatoraihpa":
        if action == "start":
            clean_data(algo, app_namespace, app_type, resource)
            #wait_time()
            #enable_executor()
            #restart_pod("alameda-executor", alameda_namespace)
            #cmd = "python ./run_alameda_hpa.py 72 &"
            #ret = os.system(cmd)
        else:
            #disable_executor()
            #restart_pod("alameda-executor", alameda_namespace)
            dir_name = get_dir_name("federatoraihpa")
            change_directory_name(dir_name)
    elif algo == "k8shpa":
        if action == "start":
            clean_data(algo, app_namespace, app_type, resource)
            #wait_time()
            start_k8shpa(app_namespace, app_type, resource, partition_number, k8shpa_percent)
            #cmd = "python ./run_k8s_hpa.py 72 &"
            #ret = os.system(cmd)
        else:
            stop_k8shpa(app_namespace, resource)
            dir_name = get_dir_name("k8shpa")
            change_directory_name(dir_name)
    else: # algo == "nonhpa"
        if action == "start":
            clean_data(algo, app_namespace, app_type, resource)
            #wait_time()
            pass
        else:
            dir_name = get_dir_name("nonhpa")
            change_directory_name(dir_name)


if __name__ == "__main__":
    algo = sys.argv[1]
    action = sys.argv[2]
    if len(sys.argv) == 3:
        main(algo, action)
    else:
        namespace = sys.argv[3]
        app_name = sys.argv[4]
        main(algo, action, namespace, app_name)
