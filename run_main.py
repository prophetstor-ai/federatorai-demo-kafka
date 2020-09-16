import sys
import os
import time
import argparse
from oc import OC
from client import Client
from define import traffic_interval, data_interval, number_k8shpa, number_alamedahpa
from define import warm_up, number_nonhpa, topic_name, group_name, traffic_path
from define import consumer_cpu_limit, consumer_memory_limit, query_mode, partition_number
from run_hpa import get_dir_name, disable_executor, find_app_location, update_yaml
from run_hpa import find_pod_name, find_alameda_namespace, restart_pod, stop_k8shpa
from run_kafka import update_consumer_yaml, apply_consumer_yaml, delete_consumer_yaml, apply_producer_yaml, update_producer_yaml


def start_algo(algo, app_name):
    print "start algorithm (%s) for %s" % (algo, app_name)
    cmd = "python ./run_hpa.py %s start & " % (algo)
    ret = os.system(cmd)
    return ret


def stop_algo(algo, app_name):
    print "stop algorithm (%s) for %s" % (algo, app_name)
    cmd = "python ./run_hpa.py %s stop & " % (algo)
    ret = os.system(cmd)
    return ret


def write_logs(algo, app_name):
    print "write logs for %s" % app_name
    cmd = "python ./write_kafka_log.py %s %s &" % (algo, data_interval)
    ret = os.system(cmd)
    return ret


def generate_traffic(algo, app_name):
    print "generate traffic for %s" % app_name
    cmd = "python ./generate_kafka_traffic.py %s %d &" % (algo, traffic_interval)
    ret = os.system(cmd)
    return ret


def wait_time(count):
    print "wait %d seconds" % count
    time.sleep(count)


def run_scenario(test_case, app_name, i):
    algo = test_case
    if test_case == "federator.ai":
        algo = "federatoraihpa"
    print "--- Start to Run HPA Test(%s): %d ---" % (algo, i)
    print "============== algo======="
    print "algo = %s" % algo
    print "============== algo======="
    start_algo(algo, app_name)
    #wait_time(300)  # already wait for consumer in initial_environment()
    generate_traffic(algo, app_name) # warmup + traffic

    wait_time(warm_up*60)   # warm up donot collect data
    algo_name = get_dir_name(algo)
    write_logs(algo_name, app_name) # start to collect data
    wait_time((data_interval)*60 +180)

    print "Stop to Run HPA Test(%s)" % (algo)
    stop_algo(algo, app_name)
    wait_time(300)


def get_test_case_list():
    test_case_list = []
    for i in range(number_k8shpa):
        test_case_list.insert(i,"k8shpa")
    for i in range(number_alamedahpa):
        #j = 2*i + 1
        test_case_list.insert(i, "federator.ai")
    for i in range(number_nonhpa):
        test_case_list.insert(i, "nonhpa")
    print "the order of algorithms is: ", ",".join(test_case_list)
    return test_case_list


def main(app_name):
    print "=== HPA Test ==="
    print "--- Start to Run K8sHPA Test x %d and Federator.ai Test x %d ---" % (number_k8shpa, number_alamedahpa)
    start_time = time.time()
    i = 0
    test_case_list = get_test_case_list()
    for test_case in test_case_list:
        run_scenario(test_case, app_name, i)

    # generate_report(["table"])
    end_time = time.time()
    duration = (end_time - start_time)/60
    print "It takes %d minutes" % duration
    print "Start time: %s" % start_time
    print "End time: %s" % end_time


def kill_process():
    kill_process_list = ["write_log.py", "generate_traffic1.py", "run_ab.py", "run_hpa.py", "train_traffic.py"]
    cmd = "ps aux | grep python"
    output = os.popen(cmd).read()
    for line in output.split("\n"):
        for process in kill_process_list:
            if line.find(process) != -1:
                pid = line.split()[1]
                cmd = "kill -9 %s" % pid
                # print cmd, process
                os.system(cmd)

    # delete consumer and topic
    delete_consumer_yaml()
    c = Client()
    c.delete_topic(topic_name)
    c.delete_topic_data(topic_name)
    # delete native lag hpa
    stop_k8shpa("","")
    # delete process
    cmd = "killall -9 python"
    os.system(cmd)


def check_execution(app_name):
    ret = 0
    print "\n"
    print "*******************************************************************"
    print "  Notice:                                                        "
    print "    The script would do the following actions:           "
    print "    1) Update %s cpu/memory limit to %sm/%sMB                  " % (app_name, consumer_cpu_limit, consumer_memory_limit)
    print "    2) Scale up/down %s replicas by K8s HPA or Federator.ai    " % app_name
    print "    3) Use Kafka Benchmark to forward traffic to %s's service " % app_name
    print "    4) Collect data and write logs to %s                " % traffic_path
    print "    5) Generate the summary and related pictures to ./pictures "
    print "*******************************************************************\n"

    x = raw_input("Are you sure to run the test? (y/n): ")
    if x not in ["y", "Y"]:
        ret = -1
    print "\n"
    return ret


def check_environment(app_name):
    app_namespace, app_type, resource = find_app_location(app_name)
    #stop_k8shpa(app_namespace, resource)
    #alameda_namespace = find_alameda_namespace("alameda-executor")
    #pod_name = find_pod_name("alameda-executor", alameda_namespace)[0]
    #pod_name = find_pod_name("alameda-recommender", alameda_namespace)[0]
    #update_yaml(alameda_namespace, "true")
    #update_yaml(alameda_namespace, "false")
    #disable_executor()
    #restart_pod("alameda-executor", alameda_namespace)


def initial_environment():
    update_producer_yaml()
    apply_producer_yaml()
    update_consumer_yaml()
    apply_consumer_yaml()
    wait_time(180)
    c = Client()
    c.modify_topic(topic_name, partition_number)
    c.set_log_retention_to_topic(topic_name)


def do_main(args):
    app_name = args.app_name[0]
    ret = OC().check_platform()
    # if ret == 0: #OpenShift
    #     user = args.user[0]
    #     passwd = args.password[0]
    #     OC().login(user, passwd)
    # ask users to check execution or not
    if query_mode:
        ret = check_execution(app_name)
        if ret != 0:
            print "exit"
            return 0
    try:
        initial_environment()
        check_environment(app_name)
        main(app_name)
    except KeyboardInterrupt:
        print "pgogram exit with keyboard interrupt"
        kill_process()
    except Exception as e:
        print "failed to test HPA: %s" % str(e)
        kill_process()
    kill_process()
    return 0


def main_proc(argv):
    # ret = OC().check_platform()
    # if ret == 0:
    #     commands = [(do_main, "hpa", "Run HPA Test", [("app_name", "application name (deployment/deploymentconfig name)"), ("user", "login user name"), ("password", "password for login user")])]
    # else:
    commands = [(do_main, "hpa", "Run HPA Test", [("app_name", "application name (deployment/deploymentconfig name)")])]

    try:
        parser = argparse.ArgumentParser(prog="", usage=None, description="Federator.ai management tool", version=None, add_help=True)
        parser.print_usage = parser.print_help
        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)

        # subparsers for commands
        subparsers = parser.add_subparsers(help="commands")

        for function, title, desc, args_list in commands:
            # format: (function_name, parser_name, parser_desc, [(args1, args1_desc), (args2, args2_desc), ...])
            # Add command parser
            p = subparsers.add_parser(title, help=desc)
            p.set_defaults(function=function)
            for arg, arg_desc in args_list:
                p.add_argument(arg, nargs=1, help=arg_desc)

        # Run the function
        args = parser.parse_args()
        retcode = args.function(args)  # args.function is the function that was set for the particular subparser
    except ValueError as e:
        print("Error in argument parsing. [%s]" % e)
        sys.exit(-1)

    sys.exit(retcode)


if __name__ == "__main__":
    main_proc(sys.argv)
