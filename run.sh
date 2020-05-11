#!/usr/bin/env bash

show_usage()
{
    cat << __EOF__

    Usage:
        Requirement:
            [-i Initial consumer pod number] # e.g. -i 40
            [-t Partition number] # e.g. -t 40
        Optional options:
            [-c Native HPA cpu percent] # For Native HPA (CPU) test, run with -o option. e.g. -o 40 -c 20
            [-v Native HPA target average value] # For Native HPA (Lag) test, run with -g option. e.g. -g 40 -v 10000
            [-z] # Install Strimzi Kafka.
        Optional Tests: 
            #(Multiple choices supported)
            [-f Federator.ai HPA test duration(min)] # e.g. -f 60 
            [-n Non HPA test duration(min)] # e.g. -n 60
            [-o Native HPA (CPU) test duration(min)] # e.g. -o 40
            [-g Native HPA (Lag) test duration(min)] # e.g. -g 40
        Support only options:
            [-x Folder1,Folder2] # Display comparison table. e.g. -x native_hpa_folder,federatorai_hpa_folder


__EOF__
    exit 1
}

check_version()
{
    oc get clusterversion >/dev/null 2>&1
    if [ "$?" = "0" ];then
        openshift_version="4"
    else
        oc version|grep -q 'openshift v3.11'
        if [ "$?" = "0" ];then
            openshift_version="3"
        fi
    fi

    if [ "$openshift_version" = "" ]; then
        # not openshift 3.11 or openshift 4.x
        echo -e "\n$(tput setaf 10)Error! Only OpenShift version 3.11 and OpenShift version 4.x are supported.$(tput sgr 0)"
        exit 5
    fi
    echo "openshift_version=$openshift_version"
}

check_kafka_exist()
{
    kubectl get pods -n $strimzi_installed_ns 2> /dev/null|grep -iq kafka
    if [ "$?" != "0" ];then
        echo -e "\n$(tput setaf 1)Error! Kafka pod doesn't exist in namespace $strimzi_installed_ns. Please install Strimzi Kafka first (-z option) or check your strimzi_installed_ns setting.$(tput sgr 0)"
        exit 5
    fi
}

is_pod_ready()
{
  [[ "$(kubectl get po "$1" -n "$2" -o 'jsonpath={.status.conditions[?(@.type=="Ready")].status}')" == 'True' ]]
}

pods_ready()
{
  [[ "$#" == 0 ]] && return 0

  namespace="$1"

  kubectl get pod -n $namespace \
    -o=jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\t"}{.status.phase}{"\t"}{.status.reason}{"\n"}{end}' \
      | while read name status phase reason _junk; do
          if [ "$status" != "True" ]; then
            msg="Waiting pod $name in namespace $namespace to be ready."
            [ "$phase" != "" ] && msg="$msg phase: [$phase]"
            [ "$reason" != "" ] && msg="$msg reason: [$reason]"
            echo "$msg"
            return 1
          fi
        done || return 1

  return 0
}

wait_until_pods_ready()
{
  period="$1"
  interval="$2"
  namespace="$3"
  target_pod_number="$4"

  wait_pod_creating=1
  for ((i=0; i<$period; i+=$interval)); do

    if [[ "$wait_pod_creating" = "1" ]]; then
        # check if pods created
        if [[ "`kubectl get po -n $namespace 2>/dev/null|wc -l`" -ge "$target_pod_number" ]]; then
            wait_pod_creating=0
            echo -e "\nChecking pods..."
        else
            echo "Waiting for pods in namespace $namespace to be created..."
        fi
    else
        # check if pods running
        if pods_ready $namespace; then
            echo -e "\nAll $namespace pods are ready."
            return 0
        fi
        echo "Waiting for pods in namespace $namespace to be ready..."
    fi

    sleep "$interval"

  done

  echo -e "\n$(tput setaf 1)Warning!! Waited for $period seconds, but all pods are not ready yet. Please check $namespace namespace$(tput sgr 0)"
  leave_prog
  exit 4
}

leave_prog()
{
    if [ ! -z "$(ls -A $file_folder)" ]; then      
        echo -e "\n$(tput setaf 6)Test result files are located under $file_folder $(tput sgr 0)"
    fi
 
    cd $current_location > /dev/null
}

hpa_cleanup()
{
    for name in `kubectl get hpa -n $strimzi_installed_ns -o name`
    do

        kubectl delete $name -n $strimzi_installed_ns >/dev/null 2>&1

    done
}

find_test_result_folder_name()
{
    if [ "$test_type" = "federatoraihpa" ]; then 
        result_folder_name=`find . -maxdepth 1 -type d -name 'federatoraihpa*'|head -n 1|awk -F '/' '{print $NF}'`
    elif [ "$test_type" = "k8shpa_cpu" ] || [ "$test_type" = "k8shpa_lag" ]; then
        result_folder_name=`find . -maxdepth 1 -type d -name 'k8shpa*'|head -n 1|awk -F '/' '{print $NF}'`
    elif [ "$test_type" = "nonhpa" ]; then
        result_folder_name=`find . -maxdepth 1 -type d -name 'nonhpa*'|head -n 1|awk -F '/' '{print $NF}'`
    fi

    if [ "$result_folder_name" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Can't find HPA test result folder.$(tput sgr 0)"
        leave_prog
        exit 4
    fi
}

set_alamedascaler_execution_value()
{
    enable_value="$1"
    current_value=`kubectl get alamedascaler test-kafka -n $strimzi_installed_ns -o jsonpath='{.spec.enableExecution}'`
    if [ "$enable_value" = "$current_value" ]; then
        return
    fi

    kubectl patch alamedascaler test-kafka -n $strimzi_installed_ns --type merge --patch "{\"spec\":{\"enableExecution\": ${enable_value}}}"
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to patch alamedascaler \"test-kafka\".$(tput sgr 0)"
        leave_prog
        exit 8
    fi

}

modify_define_parameter()
{
    run_duration="$1"
    data_duration=$((run_duration+5))
    sed -i "s/traffic_interval.*/traffic_interval = $run_duration # generate traffic per 1 minute during 72 minutes/g" define.py
    sed -i "s/data_interval.*/data_interval = $data_duration # collect pods' resource utilization # init: 80 minutes/g" define.py

    sed -i "s/initial_consumer.*/initial_consumer = $initial_consumer_number/g" define.py
    sed -i "s/partition_number.*/partition_number = $partition_number/g" define.py

    if [ "$cpu_percent_specified" = "y" ]; then
        sed -i "s/k8shpa_percent.*/k8shpa_percent = $cpu_percent /g" define.py
    fi

    if [ "$target_average_value_specified" = "y" ]; then
        sed -i "s/targetAverageValue.*/targetAverageValue: $target_average_value /g" config/consumer-hpa.yaml
        sed -i "s/maxReplicas.*/maxReplicas: $partition_number /g" config/consumer-hpa.yaml
    fi

    if [ "$test_type" = "federatoraihpa" ]; then 
        sed -i "s/number_alamedahpa.*/number_alamedahpa = 1/g" define.py
        sed -i "s/number_k8shpa.*/number_k8shpa = 0/g" define.py
        sed -i "s/number_nonhpa.*/number_nonhpa = 0/g" define.py
    elif [ "$test_type" = "k8shpa_cpu" ]; then
        sed -i "s/number_alamedahpa.*/number_alamedahpa = 0/g" define.py
        sed -i "s/number_k8shpa.*/number_k8shpa = 1/g" define.py
        sed -i "s/number_nonhpa.*/number_nonhpa = 0/g" define.py
        sed -i "s/k8shpa_type.*/k8shpa_type = \"cpu\" #cpu or lag/g" define.py
    elif [ "$test_type" = "k8shpa_lag" ]; then
        sed -i "s/number_alamedahpa.*/number_alamedahpa = 0/g" define.py
        sed -i "s/number_k8shpa.*/number_k8shpa = 1/g" define.py
        sed -i "s/number_nonhpa.*/number_nonhpa = 0/g" define.py
        sed -i "s/k8shpa_type.*/k8shpa_type = \"lag\" #cpu or lag/g" define.py
    elif [ "$test_type" = "nonhpa" ]; then
        sed -i "s/number_alamedahpa.*/number_alamedahpa = 0/g" define.py
        sed -i "s/number_k8shpa.*/number_k8shpa = 0/g" define.py
        sed -i "s/number_nonhpa.*/number_nonhpa = 1/g" define.py
    fi

}

restart_recommender_pod()
{
    recommender_pod_name=`kubectl get pods -n $install_namespace -o name |grep "alameda-recommender-"|cut -d '/' -f2`
    kubectl delete pod $recommender_pod_name -n $install_namespace
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to delete recommender_pod_name pod $recommender_pod_name$(tput sgr 0)"
        leave_prog
        exit 8
    fi
    wait_until_pods_ready $max_wait_pods_ready_time 30 $install_namespace 5
}

collect_results()
{
    target_folder="$1"
    target_folder_short_name="$2"
    target_start="$3"
    target_end="$4"

    target_duration=$((target_end-target_start))

    find_test_result_folder_name
    echo "test_result_folder= $result_folder_name"
    mv $result_folder_name $target_folder_short_name
    python -u count_kafka.py $target_folder_short_name|tee -i $file_folder/$target_folder/result_statistics
    echo "" >> $file_folder/$target_folder/result_statistics
    echo "Test start - $target_start" >> $file_folder/$target_folder/result_statistics
    echo "Test end   - $target_end" >> $file_folder/$target_folder/result_statistics
    echo "It takes $(convertsecs $target_duration) to finish test." >> $file_folder/$target_folder/result_statistics

    lag_result=`grep "avg. prom. query lag = " $file_folder/$target_folder/result_statistics |awk '{print $NF}'`
    if [ "$lag_result" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to parse average consumer lag result.\n$(tput sgr 0)"
        # continue test without exit
    fi
    replica_result=`grep "\-\-\- consumer" -A10 $file_folder/$target_folder/result_statistics |grep "avg. replicas"|awk '{print $NF}'`
    if [ "$replica_result" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to parse average replica(s) result.\n$(tput sgr 0)"
        # continue test without exit
    fi

    # Get recommender & prediction log
    mkdir -p $file_folder/$target_folder/recommender
    mkdir -p $file_folder/$target_folder/prediction/log
    mkdir -p $file_folder/$target_folder/prediction/model

    recommender_pod_name=`kubectl get pods -n $install_namespace -o name |grep "alameda-recommender-"|cut -d '/' -f2`
    ai_pod_name=`kubectl get pods -n $install_namespace -o name |grep "alameda-ai-"|grep -v "alameda-ai-dispatcher"|cut -d '/' -f2`
    kubectl logs $recommender_pod_name -n $install_namespace > $file_folder/$target_folder/recommender/log
    kubectl exec $ai_pod_name -n $install_namespace -- tar -zcvf - /var/log/alameda/alameda-ai > $file_folder/$target_folder/prediction/log/log.tar.gz
    kubectl exec $ai_pod_name -n $install_namespace -- tar -zcvf - /var/lib/alameda/alameda-ai/models/online/workload_prediction > $file_folder/$target_folder/prediction/model/model.tar.gz

    mv $target_folder_short_name picture $file_folder/$target_folder
    cp $node_list_file $file_folder/$target_folder
    cp define.py $file_folder/$target_folder

}

run_federatorai_hpa_test()
{
    # Federator.ai test
    cd $current_location

    # Do clean up
    hpa_cleanup
    ./cleanup.sh

    test_type="federatoraihpa"
    modify_define_parameter $federatorai_test_duration
    federatorai_test_folder_name="federatorai_hpa_${run_duration}min_${initial_consumer_number}con_${partition_number}par_`date +%s`"
    federatorai_test_folder_short_name="fedai${run_duration}m${initial_consumer_number}i${partition_number}p${alameda_version}B"
    mkdir -p $file_folder/$federatorai_test_folder_name
    set_alamedascaler_execution_value "true"

    start=`date +%s`
    python -u run_main.py hpa consumer |tee -i $file_folder/$federatorai_test_folder_name/console_output.log
    end=`date +%s`

    collect_results "$federatorai_test_folder_name" "$federatorai_test_folder_short_name" "$start" "$end"
    federatorai_avg_lag=$lag_result
    federatorai_avg_replicas=$replica_result
    echo -e "\n$(tput setaf 6)Federator.ai HPA test is finished.$(tput sgr 0)"
    echo -e "$(tput setaf 6)Average Consumer Group Lag is $(tput sgr 0)$(tput setaf 10)\"$federatorai_avg_lag\"$(tput sgr 0)"
    echo -e "$(tput setaf 6)Average Replica is $(tput sgr 0)$(tput setaf 10)\"$federatorai_avg_replicas\"$(tput sgr 0)"
    echo -e "$(tput setaf 6)Result files are under $file_folder/$federatorai_test_folder_name $(tput sgr 0)"
}

run_nonhpa_hpa_test()
{
    # Non HPA test
    cd $current_location

    # Do clean up
    hpa_cleanup
    ./cleanup.sh

    test_type="nonhpa"
    modify_define_parameter $nonhpa_test_duration
    nonhpa_test_folder_name="non_hpa_${run_duration}min_${initial_consumer_number}con_${partition_number}par_`date +%s`"
    nonhpa_test_folder_short_name="nonhpa${run_duration}m${initial_consumer_number}i${partition_number}p${alameda_version}B"
    mkdir -p $file_folder/$nonhpa_test_folder_name
    set_alamedascaler_execution_value "false"

    start=`date +%s`
    python -u run_main.py hpa consumer |tee -i $file_folder/$nonhpa_test_folder_name/console_output.log
    end=`date +%s`

    collect_results "$nonhpa_test_folder_name" "$nonhpa_test_folder_short_name" "$start" "$end"
    nonhpa_avg_lag=$lag_result
    nonhpa_avg_replicas=$replica_result
    echo -e "\n$(tput setaf 6)NonHPA test is finished.$(tput sgr 0)"
    echo -e "$(tput setaf 6)Average Consumer Group Lag is $(tput sgr 0)$(tput setaf 10)\"$nonhpa_avg_lag\"$(tput sgr 0)"
    echo -e "$(tput setaf 6)Average Replica is $(tput sgr 0)$(tput setaf 10)\"$nonhpa_avg_replicas\"$(tput sgr 0)"
    echo -e "$(tput setaf 6)Result files are under $file_folder/$nonhpa_test_folder_name $(tput sgr 0)"
}

run_native_k8s_hpa_cpu_test()
{
    # Native HPA (CPU) test
    cd $current_location

    # Do clean up
    hpa_cleanup
    ./cleanup.sh

    test_type="k8shpa_cpu"
    modify_define_parameter $native_cpu_test_duration
    native_hpa_test_folder_name="native_hpa_cpu${cpu_percent}_${run_duration}min_${initial_consumer_number}con_${partition_number}par_`date +%s`"
    native_hpa_test_folder_short_name="k8shpa${cpu_percent}c${run_duration}m${initial_consumer_number}i${partition_number}p${alameda_version}B"
    mkdir -p $file_folder/$native_hpa_test_folder_name
    set_alamedascaler_execution_value "false"

    start=`date +%s`
    python -u run_main.py hpa consumer |tee -i $file_folder/$native_hpa_test_folder_name/console_output.log
    end=`date +%s`

    echo "Collecting statistics..."
    collect_results "$native_hpa_test_folder_name" "$native_hpa_test_folder_short_name" "$start" "$end"
    native_hpa_cpu_test_avg_lag=$lag_result
    native_hpa_cpu_test_avg_replicas=$replica_result
    echo -e "\n$(tput setaf 6)Native HPA (CPU) is finished.$(tput sgr 0)"
    echo -e "$(tput setaf 6)Average Consumer Group Lag is $(tput sgr 0)$(tput setaf 10)\"$native_hpa_cpu_test_avg_lag\"$(tput sgr 0)"
    echo -e "$(tput setaf 6)Average Replica is $(tput sgr 0)$(tput setaf 10)\"$native_hpa_cpu_test_avg_replicas\"$(tput sgr 0)"
    echo -e "Result files are under $file_folder/$native_hpa_test_folder_name $(tput sgr 0)"
}

run_native_k8s_hpa_lag_test()
{
    # Native HPA (Lag) test
    cd $current_location

    # Do clean up
    hpa_cleanup
    ./cleanup.sh

    test_type="k8shpa_lag"
    modify_define_parameter $native_lag_test_duration
    native_hpa_test_folder_name="native_hpa_lag_target${target_average_value}_${run_duration}min_${initial_consumer_number}con_${partition_number}par_`date +%s`"
    native_hpa_test_folder_short_name="k8shpa${target_average_value}t${run_duration}m${initial_consumer_number}i${partition_number}p${alameda_version}B"
    mkdir -p $file_folder/$native_hpa_test_folder_name
    set_alamedascaler_execution_value "false"

    start=`date +%s`
    python -u run_main.py hpa consumer |tee -i $file_folder/$native_hpa_test_folder_name/console_output.log
    end=`date +%s`

    echo "Collecting statistics..."
    collect_results "$native_hpa_test_folder_name" "$native_hpa_test_folder_short_name" "$start" "$end"
    native_hpa_lag_test_avg_lag=$lag_result
    native_hpa_lag_test_avg_replicas=$replica_result
    echo -e "\n$(tput setaf 6)Native HPA (Lag) is finished.$(tput sgr 0)"
    echo -e "$(tput setaf 6)Average Consumer Group Lag is $(tput sgr 0)$(tput setaf 10)\"$native_hpa_lag_test_avg_lag\"$(tput sgr 0)"
    echo -e "$(tput setaf 6)Average Replica is $(tput sgr 0)$(tput setaf 10)\"$native_hpa_lag_test_avg_replicas\"$(tput sgr 0)"
    echo -e "Result files are under $file_folder/$native_hpa_test_folder_name $(tput sgr 0)"
}

display_final_result_if_available()
{
    if [[ $native_cpu_test = "y" && "$federatorai_test" = "y" ]]; then
        echo ""

        [ "$federatorai_avg_lag" = "" ] && federatorai_avg_lag="N/A"
        [ "$federatorai_avg_replicas" = "" ] && federatorai_avg_replicas="N/A"
        [ "$native_hpa_cpu_test_avg_lag" = "" ] && native_hpa_cpu_test_avg_lag="N/A"
        [ "$native_hpa_cpu_test_avg_replicas" = "" ] && native_hpa_cpu_test_avg_replicas="N/A"
        echo "----------------------------------------------------------------------"
        echo -e "$(tput setaf 6)                           Benchmark results     $(tput sgr 0)"
        echo "----------------------------------------------------------------------"
        printf "%30s%20s%20s\n" "Metrics" "Native HPA(CPU)" "Federator.ai"
        echo "----------------------------------------------------------------------"
        printf "%30s%20s%20s\n" "Average Consumer Group Lag" "$native_hpa_cpu_test_avg_lag" "$federatorai_avg_lag"
        echo "----------------------------------------------------------------------"
        printf "%30s%20s%20s\n" "Average Replica(s)" "$native_hpa_cpu_test_avg_replicas" "$federatorai_avg_replicas"
        echo "----------------------------------------------------------------------"

        if [ "$native_hpa_cpu_test_avg_lag" != "N/A" ] && [ "$federatorai_avg_lag" != "N/A" ]; then
            result=`echo "$native_hpa_cpu_test_avg_lag $federatorai_avg_lag" | awk '{printf "%.2f", (($1-$2)/$1*100)}'`
            percentage="${result}%"
            echo -e "Performance improvement by Federator.ai vs. Native HPA(CPU) is $(tput setaf 10)\"$percentage\"$(tput sgr 0)"
        fi
    fi
}

compare_result_folders()
{
    first_lag_result=`grep "avg. prom. query lag = " $file_folder/$first_folder/result_statistics |awk '{print $NF}'`
    if [ "$first_lag_result" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to get lag value from $file_folder/$first_folder/result_statistics \n$(tput sgr 0)"
        exit
    fi

    second_lag_result=`grep "avg. prom. query lag = " $file_folder/$second_folder/result_statistics |awk '{print $NF}'`
    if [ "$second_lag_result" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to get lag value from $file_folder/$second_folder/result_statistics \n$(tput sgr 0)"
        exit
    fi

    echo ""
    result=`echo "$first_lag_result $second_lag_result" | awk '{printf "%.2f", (($1-$2)/$1*100)}'`
    percentage="${result}%"
    echo "------------------------------------------------------------------------------------------"
    echo -e "$(tput setaf 6)            Comparison of two folders             $(tput sgr 0)"
    echo "------------------------------------------------------------------------------------------"
    printf "%30s%60s\n" "Algorithm1" "$first_folder"
    echo "------------------------------------------------------------------------------------------"
    printf "%30s%60s\n" "Average Consumer Group Lag" "$first_lag_result"
    echo "------------------------------------------------------------------------------------------"
    printf "%30s%60s\n" "Algorithm2" "$second_folder"
    echo "------------------------------------------------------------------------------------------"
    printf "%30s%60s\n" "Average Consumer Group Lag" "$second_lag_result"
    echo "------------------------------------------------------------------------------------------"
    printf "%30s%60s\n" "Comparison"  "$percentage"
    echo "------------------------------------------------------------------------------------------"
}

convertsecs() 
{
    ((h=${1}/3600))
    ((m=(${1}%3600)/60))
    ((s=${1}%60))
    printf "%02d:%02d:%02d\n" $h $m $s
}

get_alamedaservice_version()
{
    alameda_version=`kubectl get alamedaservice --all-namespaces|grep -v 'EXECUTION'|awk '{print $4}'|awk -F'.' '{print $NF}'`
}

patch_alamedaservice_broker_address()
{
    kubectl get alamedaservice $alamedaservice_name -n $install_namespace -o yaml | grep "kafka:" -A3 | grep "brokerAddresses" -A1 | grep -q "my-cluster-kafka-brokers.$strimzi_installed_ns"
    if [ "$?" != "0" ]; then
        alamedaservice_file="patch.alamedaservice.yaml"
        cat > ${alamedaservice_file} << __EOF__
spec:
  kafka:
    brokerAddresses:
      - my-cluster-kafka-brokers.${strimzi_installed_ns}.svc.cluster.local:9092
__EOF__
        echo "Patching alamedaservice for setting up broker address..."
        kubectl patch alamedaservice $alamedaservice_name -n $install_namespace --type merge --patch "$(cat $alamedaservice_file)"
        if [ "$?" != "0" ];then
            echo -e "\n$(tput setaf 1)Error! Failed to patch alamedaservice $alamedaservice_name.$(tput sgr 0)"
            exit 8
        fi
        wait_until_pods_ready $max_wait_pods_ready_time 30 $install_namespace 5
        echo "Done."
    fi
}

get_variables_from_define_file()
{
    # String
    consumer_pod_specified_node_key=`grep "consumer_pod_specified_node_key" define.py| awk -F '"' '{print $2}'`
    consumer_pod_specified_node_value=`grep "consumer_pod_specified_node_value" define.py| awk -F '"' '{print $2}'`
    producer_pod_specified_node_key=`grep "producer_pod_specified_node_key" define.py| awk -F '"' '{print $2}'`
    producer_pod_specified_node_value=`grep "producer_pod_specified_node_value" define.py| awk -F '"' '{print $2}'`
    alameda_ai_pod_specified_node_key=`grep "alameda_ai_pod_specified_node_key" define.py| awk -F '"' '{print $2}'`
    alameda_ai_pod_specified_node_value=`grep "alameda_ai_pod_specified_node_value" define.py| awk -F '"' '{print $2}'`
    # Number
    consumer_memory_limit=`grep "consumer_memory_limit" define.py| awk -F '=' '{print $NF}'| egrep -o "[0-9]*"`


    if [ "$consumer_pod_specified_node_key" = "" ] || [ "$consumer_pod_specified_node_value" = "" ] ||
    [ "$producer_pod_specified_node_key" = "" ] || [ "$producer_pod_specified_node_value" = "" ] ||
    [ "$alameda_ai_pod_specified_node_key" = "" ] || [ "$alameda_ai_pod_specified_node_value" = "" ]
    [ "$consumer_memory_limit" = "" ] ; then
        echo -e "\n$(tput setaf 1)Error! Some values in define.py is empty. Please double check.$(tput sgr 0)"
        exit 8
    fi
}

node_label_failure_check()
{
    if [ "$label_failed_but_continue" != "y" ]; then
        default="n"
        read -r -p "$(tput setaf 2)Do you want to ignore the node label failure and continue the test? [default: n]: $(tput sgr 0)" label_failed_but_continue </dev/tty
        label_failed_but_continue=${label_failed_but_continue:-$default}
        if [ "$label_failed_but_continue" != "y" ]; then
            exit 8
        fi
    fi
}

check_up_env()
{
    get_variables_from_define_file

    compute_node_num=`oc get nodes|awk '{print $3}'|egrep -i 'compute|worker'|wc -l`
    if [ "$compute_node_num" -lt "3" ]; then
        echo -e "\n$(tput setaf 1)Error! At least three compute nodes are needed for test.$(tput sgr 0)"
        exit 8
    fi

    node_list_file="compute_nodes_list.output"
    > $node_list_file
    sleep 1
    true > $node_list_file
    sleep 1
    while read name status roles _junk
    do
        if [[ $roles == *"compute"* ]] || [[ $roles == *"worker"* ]]; then
            mem=`kubectl get node $name -o 'jsonpath={.status.capacity.memory}'|egrep -o "[0-9]*"`
            echo "$name $mem" >> $node_list_file
        fi
    done <<< "$(kubectl get nodes|grep -v ROLES)"
    sleep 1

    # Check at least one node contain memory larger than (consumer_memory_limit * (partition_number+6) * 1000 ) KByte
    required_memory_in_kbyte="$((consumer_memory_limit * (partition_number+6) * 1000 ))" # Give extra 6GB

    max_memory=`sort -n -r -k 2 $node_list_file |head -1|awk '{print $NF}'`
    max_memory_node=`sort -n -r -k 2 $node_list_file |head -1|awk '{print $1}'`

    if [ "$max_memory" -lt "$required_memory_in_kbyte" ]; then
        echo -e "\n$(tput setaf 1)Error! Make sure at least one compute node has memory capacity larger than $required_memory_in_kbyte KByte. (Rule: consumer_memory_limit * (partition_number+6) * 1000).$(tput sgr 0)"
        exit 8
    fi

    # Find second large memory compute nodes
    second_large_node=`sort -n -r -k 2 $node_list_file |tail -n +2|head -1|awk '{print $1}'`
    # Find third large memory compute nodes
    third_large_node=`sort -n -r -k 2 $node_list_file |tail -n +3|head -1|awk '{print $1}'`
    # Find rest compute nodes
    rest_compute_nodes=`sort -n -r -k 2 $node_list_file |tail -n +4|awk '{print $1}'`

    echo "Current compute nodes customized labels..."
    while read name status roles age version labels _junk
    do
        if [[ $roles == *"compute"* ]] || [[ $roles == *"worker"* ]]; then
            node_label=`echo $labels |sed 's/,/\n/g'| egrep "$consumer_pod_specified_node_key|$producer_pod_specified_node_key|$alameda_ai_pod_specified_node_key"`
            echo "$name $node_label"
        fi
    done <<< "$(kubectl get nodes --show-labels |grep -v ROLES)"
    echo ""

    echo "Labeling compute nodes..."
    # Label compute node for consumer pods
    echo "Setting $max_memory_node to $consumer_pod_specified_node_key=$consumer_pod_specified_node_value" | tee -a $node_list_file
    oc get node $max_memory_node --show-labels|grep -q "$consumer_pod_specified_node_key=$consumer_pod_specified_node_value"
    if [ "$?" != "0" ];then
        oc label node $max_memory_node $consumer_pod_specified_node_key=$consumer_pod_specified_node_value
        if [ "$?" != "0" ];then
            echo -e "\n$(tput setaf 1)Error! Failed to label node $max_memory_node with key=value [$consumer_pod_specified_node_key=$consumer_pod_specified_node_value].$(tput sgr 0)"
            node_label_failure_check
        fi
    fi

    # Label compute node for Federator.ai
    echo "Setting $second_large_node to $alameda_ai_pod_specified_node_key=$alameda_ai_pod_specified_node_value" | tee -a $node_list_file
    oc get node $second_large_node --show-labels|grep -q "$alameda_ai_pod_specified_node_key=$alameda_ai_pod_specified_node_value"
    if [ "$?" != "0" ];then
        oc label node $second_large_node $alameda_ai_pod_specified_node_key=$alameda_ai_pod_specified_node_value
        if [ "$?" != "0" ];then
            echo -e "\n$(tput setaf 1)Error! Failed to label node $second_large_node with key=value [$alameda_ai_pod_specified_node_key=$alameda_ai_pod_specified_node_value].$(tput sgr 0)"
            node_label_failure_check
        fi
    fi

    # Label compute node for producer pod
    echo "Setting $third_large_node to $producer_pod_specified_node_key=$producer_pod_specified_node_value" | tee -a $node_list_file
    oc get node $third_large_node --show-labels|grep -q "$producer_pod_specified_node_key=$producer_pod_specified_node_value"
    if [ "$?" != "0" ];then
        oc label node $third_large_node $producer_pod_specified_node_key=$producer_pod_specified_node_value
        if [ "$?" != "0" ];then
            echo -e "\n$(tput setaf 1)Error! Failed to label node $third_large_node with key=value [$producer_pod_specified_node_key=$producer_pod_specified_node_value].$(tput sgr 0)"
            node_label_failure_check
        fi
    fi

    # Label rest compute nodes for consumer pods
    for rest_node in `echo $rest_compute_nodes`
    do
        echo "Setting $rest_node to $consumer_pod_specified_node_key=$consumer_pod_specified_node_value" | tee -a $node_list_file
        oc get node $rest_node --show-labels|grep -q "$consumer_pod_specified_node_key=$consumer_pod_specified_node_value"
        if [ "$?" != "0" ];then
            oc label node $rest_node $consumer_pod_specified_node_key=$consumer_pod_specified_node_value
            if [ "$?" != "0" ];then
                echo -e "\n$(tput setaf 1)Error! Failed to label node $rest_node with key=value [$consumer_pod_specified_node_key=$consumer_pod_specified_node_value].$(tput sgr 0)"
                node_label_failure_check
            fi
        fi
    done
    echo "Done"
}

patch_nodeselector_for_federatorai_deployment()
{
    kubectl get deploy alameda-ai -n $install_namespace -o yaml|grep -i nodeselector -A1|grep $alameda_ai_pod_specified_node_key|grep -q $alameda_ai_pod_specified_node_value
    if [ "$?" = "0" ];then
        return
    fi

    nodeselector_file="patch.nodeselector.yaml"
    cat > ${nodeselector_file} << __EOF__
spec:
  template:
    spec:
      nodeSelector:
        test: ai
__EOF__

    echo "Patching all Federator.ai deployments..."
    for deployment in `kubectl get deploy -n $install_namespace|grep -v "UP-TO-DATE"|awk '{print $1}'`
    do
        kubectl patch deploy $deployment -n $install_namespace --type merge --patch "$(cat $nodeselector_file)"
        if [ "$?" != "0" ];then
            echo -e "\n$(tput setaf 1)Error! Failed to patch $deployment deployment in ns $install_namespace $(tput sgr 0)"
            exit 8
        fi
    done

    wait_until_pods_ready $max_wait_pods_ready_time 30 $install_namespace 5
    echo "Done"
    
}

apply_alamedascaler()
{
    sed -i "s/  namespace:.*/  namespace: $strimzi_installed_ns/g" $alamedascaler_file
    sed -i "s/    exporterNamespace:.*/    exporterNamespace: $strimzi_installed_ns/g" $alamedascaler_file
    kubectl apply -f $alamedascaler_file -n $strimzi_installed_ns
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to apply $alamedascaler_file $(tput sgr 0)"
        leave_prog
        exit 8
    fi
}

install_strimzi()
{
    kubectl get svc -n $strimzi_installed_ns | grep -iq kafka
    retValue="$?"

    if [ "$retValue" != "0" ]; then
        oc new-project $strimzi_installed_ns

        # Install Kafka cluster operator
        echo -e "\n$(tput setaf 2)Installing Strimzi Kafka cluster operator...$(tput sgr 0)"
        for file in `ls strimzi_kafka/cluster-operator/*.yaml`
        do
            oc apply -n $strimzi_installed_ns -f $file
            if [ "$?" != "0" ]; then
                echo -e "\n$(tput setaf 1)Error! Failed to apply $file in namespace $strimzi_installed_ns $(tput sgr 0)"
                exit 1
            fi
        done
        wait_until_pods_ready $max_wait_pods_ready_time 30 $strimzi_installed_ns 1
        echo -e "\n$(tput setaf 2)Done.$(tput sgr 0)"

        # Create kafka cluster
        echo -e "\n$(tput setaf 2)Installing Kafka cluster...$(tput sgr 0)"
        oc apply -n $strimzi_installed_ns -f strimzi_kafka/kafka-metrics.yaml
        if [ "$?" != "0" ]; then
            echo -e "\n$(tput setaf 1)Error! Failed to apply strimzi_kafka/kafka-metrics.yaml in namespace $strimzi_installed_ns $(tput sgr 0)"
            exit 1
        fi
        wait_until_pods_ready $max_wait_pods_ready_time 30 $strimzi_installed_ns 5
        echo -e "\n$(tput setaf 2)Done.$(tput sgr 0)"

        # Create service monitor in openshift-monitoring namespace
        echo -e "\n$(tput setaf 2)Creating servicemonitor for Prometheus...$(tput sgr 0)"
        oc apply -f strimzi_kafka/strimzi-service-monitor.yaml
        if [ "$?" != "0" ]; then
            echo -e "\n$(tput setaf 1)Error! Failed to apply strimzi_kafka/strimzi-service-monitor.yaml $(tput sgr 0)"
            exit 1
        fi
        oc adm policy add-cluster-role-to-user cluster-admin "system:serviceaccount:openshift-monitoring:prometheus-k8s"
        for pod in `oc get pods -n openshift-monitoring -o name|grep "prometheus-k8s-"`
        do
            oc delete $pod -n openshift-monitoring
            if [ "$?" != "0" ]; then
                echo -e "\n$(tput setaf 1)Error! Failed to delete pod $pod in namespace openshift-monitoring $(tput sgr 0)"
                exit 1
            fi
        done
        wait_until_pods_ready $max_wait_pods_ready_time 30 openshift-monitoring 5
        echo -e "\n$(tput setaf 2)Done.$(tput sgr 0)"
    fi
}

configure_native_hpa()
{
    oc get secret cm-adapter-serving-certs -n default >/dev/null 2>&1
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 2)Applying config/cm-adapter-serving-certs.yaml...$(tput sgr 0)"
        oc apply -f config/cm-adapter-serving-certs.yaml
        if [ "$?" != "0" ]; then
            echo -e "\n$(tput setaf 1)Error! Failed to apply config/cm-adapter-serving-certs.yaml $(tput sgr 0)"
            exit 1
        fi
        echo -e "\n$(tput setaf 2)Done.$(tput sgr 0)"
    fi
    oc get deployment prometheus-adapter -n default >/dev/null 2>&1
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 2)Applying config/prometheus-adapter.yaml...$(tput sgr 0)"
        oc apply -f config/prometheus-adapter.yaml
        if [ "$?" != "0" ]; then
            echo -e "\n$(tput setaf 1)Error! Failed to apply config/prometheus-adapter.yaml $(tput sgr 0)"
            exit 1
        fi
        if [ "$openshift_version" = "3" ]; then
            wait_until_pods_ready $max_wait_pods_ready_time 30 default 4
        else
            #OpenShift 4
            wait_until_pods_ready $max_wait_pods_ready_time 30 default 1
        fi

        echo -e "\n$(tput setaf 2)Done.$(tput sgr 0)"
    fi
}

check_python_command()
{
    which python > /dev/null 2>&1
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to locate python command. Pls make sure \"python\" command exist.$(tput sgr 0)"
        exit 1
    fi
}

sleep_interval_func()
{
    # Always restart recommender before testing
    restart_recommender_pod

    # Sleep 10 minutes to avoid metrics interfere
    if [ "$previous_test" = "y" ]; then
        sleep $avoid_metrics_interferece_sleep
    fi
}

nonhpa_test_func()
{
    if [ "$nonhpa_test" = "y" ]; then
        sleep_interval_func
        previous_test="y"
        start=`date +%s`
        run_nonhpa_hpa_test
        end=`date +%s`
        duration=$((end-start))
        echo -e "\n$(tput setaf 6)It takes $(convertsecs $duration) to finish Non HPA test.$(tput sgr 0)"
    fi
}

native_hpa_cpu_test_func()
{
    if [ "$native_cpu_test" = "y" ]; then
        sleep_interval_func
        previous_test="y"
        start=`date +%s`
        run_native_k8s_hpa_cpu_test
        end=`date +%s`
        duration=$((end-start))
        echo -e "\n$(tput setaf 6)It takes $(convertsecs $duration) to finish native HPA (CPU) test.$(tput sgr 0)"
    fi
}

native_hpa_lag_test_func()
{
    if [ "$native_lag_test" = "y" ]; then
        sleep_interval_func
        previous_test="y"
        start=`date +%s`
        run_native_k8s_hpa_lag_test
        end=`date +%s`
        duration=$((end-start))
        echo -e "\n$(tput setaf 6)It takes $(convertsecs $duration) to finish native HPA (Lag) test.$(tput sgr 0)"
    fi
}

federatorai_hpa_test_func()
{
    if [ "$federatorai_test" = "y" ]; then
        sleep_interval_func
        previous_test="y"
        start=`date +%s`
        run_federatorai_hpa_test
        end=`date +%s`
        duration=$((end-start))
        echo -e "\n$(tput setaf 6)It takes $(convertsecs $duration) to finish Federator.ai HPA test.$(tput sgr 0)"
    fi
}

if [ "$#" -eq "0" ]; then
    show_usage
    exit
fi

[ "$max_wait_pods_ready_time" = "" ] && max_wait_pods_ready_time=900  # maximum wait time for pods become ready
[ "$avoid_metrics_interferece_sleep" = "" ] && avoid_metrics_interferece_sleep=600  # maximum wait time for pods become ready

while getopts "i:t:f:n:o:hc:v:g:zx:s:" o; do
    case "${o}" in
        # u)
        #     username_specified="y"
        #     username=${OPTARG}
        #     ;;
        # p)
        #     password_specified="y"
        #     password=${OPTARG}
        #     ;;
        s)
            sorting_specified="y"
            sorting_sequence=${OPTARG}
            if [ "$sorting_sequence" != "fk" ] && [ "$sorting_sequence" != "kf" ]; then
                echo -e "\n$(tput setaf 1)Error! Wrong sorting sequence.$(tput sgr 0)"
                show_usage
                exit
            fi
            ;;
        i)
            initial_consumer_number_specified="y"
            initial_consumer_number=${OPTARG}
            ;;
        t)
            partition_number_specified="y"
            partition_number=${OPTARG}
            ;;
        f)
            federatorai_test="y"
            federatorai_test_duration=${OPTARG}
            ;;
        n)
            nonhpa_test="y"
            nonhpa_test_duration=${OPTARG}
            ;;
        o)
            native_cpu_test="y"
            native_cpu_test_duration=${OPTARG}
            ;;
        g)
            native_lag_test="y"
            native_lag_test_duration=${OPTARG}
            ;;
        c)
            cpu_percent_specified="y"
            cpu_percent=${OPTARG}
            ;;
        v)
            target_average_value_specified="y"
            target_average_value=${OPTARG}
            ;;
        x)
            comparison_specified="y"
            comparison_folders=${OPTARG}
            ;;
        z)
            prepare_env_specified="y"
            ;;
        h)
            show_usage
            exit
            ;;
        *)
            echo "Warning! wrong paramter."
            show_usage
            ;;
    esac
done

file_folder="./test_result"
strimzi_installed_ns="myproject"
alamedascaler_file="config/sample_alamedascaler.yaml"

# if [ "$username_specified" != "y" ]; then
#     echo -e "\n$(tput setaf 1)Error! Need to use \"-u\" to specify openshift admin account name.$(tput sgr 0)" && show_usage
# fi

# if [ "$password_specified" != "y" ]; then
#     echo -e "\n$(tput setaf 1)Error! Need to use \"-p\" to specify openshift admin account password   .$(tput sgr 0)" && show_usage
# fi

if [ "$native_cpu_test" = "y" ]; then
    if [ "$cpu_percent_specified" != "y" ] || [ "$cpu_percent" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Need to use \"-c\" to specify cpu percent for native HPA (CPU) test.$(tput sgr 0)" && show_usage
    fi
fi

if [ "$native_lag_test" = "y" ]; then
    if [ "$target_average_value_specified" != "y" ] || [ "$target_average_value" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Need to use \"-v\" to specify target average value.$(tput sgr 0)" && show_usage
    fi
fi

if [ "$federatorai_test" = "y" ] || [ "$nonhpa_test" = "y" ] || [ "$native_cpu_test" = "y" ] || [ "$native_lag_test" = "y" ]; then
    if [ "$initial_consumer_number_specified" != "y" ]; then
        echo -e "\n$(tput setaf 1)Error! Need to use \"-i\" to specify initial consumer pod number.$(tput sgr 0)" && show_usage
    fi

    if [ "$partition_number_specified" != "y" ]; then
        echo -e "\n$(tput setaf 1)Error! Need to use \"-t\" to specify partition number.$(tput sgr 0)" && show_usage
    fi
fi

if [ "$comparison_specified" = "y" ]; then
    first_folder=`echo $comparison_folders|cut -s -d ',' -f1`
    second_folder=`echo $comparison_folders|cut -s -d ',' -f2`
    if [ "$first_folder" = "" ] || [ "$second_folder" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Specify correct folders format for option -x. e.g. -x folder1,folder2 $(tput sgr 0)" && show_usage
    fi
    if [ ! -d "$file_folder/$first_folder" ] || [ ! -d "$file_folder/$second_folder" ]; then
        echo -e "\n$(tput setaf 1)Error! Make sure comparision folder names ($first_folder and $second_folder) do exist inside $file_folder $(tput sgr 0)"
        exit
    fi
    compare_result_folders
    exit
fi

# Check if kubectl connect to server.
result="`echo ""|kubectl cluster-info 2>/dev/null`"
if [ "$?" != "0" ];then
    echo -e "\n$(tput setaf 1)Error! Please login into OpenShift cluster first.$(tput sgr 0)"
    exit
fi
current_server="`echo $result|sed 's/.*at //'|awk '{print $1}'`"
echo "You are connecting to cluster: $current_server"

echo "Checking OpenShift version..."
check_version
echo "...Passed"

if [ ! -f "requirements.done" ]; then
    default="n"
    read -r -p "$(tput setaf 2)It seems install.sh has not been executed. Do you want to continue? [default: n]: $(tput sgr 0)" continue_anyway </dev/tty
    continue_anyway=${continue_anyway:-$default}
    if [ "$continue_anyway" = "y" ]; then
        touch requirements.done
    else
        exit 0
    fi
fi

echo "Checking environment..."
check_up_env
check_python_command

install_namespace="`kubectl get pods --all-namespaces |grep "alameda-ai-"|awk '{print $1}'|head -1`"

if [ "$install_namespace" = "" ];then
    echo -e "\n$(tput setaf 1)Error! Please install Federatorai before running this script.$(tput sgr 0)"
    exit 3
fi

alamedaservice_name="`kubectl get alamedaservice -n $install_namespace -o jsonpath='{range .items[*]}{.metadata.name}'`"
if [ "$alamedaservice_name" = "" ]; then
    echo -e "\n$(tput setaf 1)Error! Failed to get alamedaservice name.$(tput sgr 0)"
    exit 8
fi

# Patch Federator.ai deployments
patch_nodeselector_for_federatorai_deployment

patch_alamedaservice_broker_address
get_alamedaservice_version

mkdir -p /data
mkdir -p $file_folder
current_location=`pwd`

if [ "$prepare_env_specified" = "y" ]; then
    install_strimzi
fi

check_kafka_exist
apply_alamedascaler
configure_native_hpa

previous_test="n"
nonhpa_test_func

if [ "$sorting_sequence" = "kf" ]; then
    # K8S lag test first, Federator.ai test later
    native_hpa_lag_test_func
    federatorai_hpa_test_func
else # sorting_sequence=fk, or sorting_specified="n"
    # Federator.ai test first, K8S lag test later.
    federatorai_hpa_test_func
    native_hpa_lag_test_func
fi

native_hpa_cpu_test_func

# Final Result
display_final_result_if_available
