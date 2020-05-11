# execution
query_mode = False

# application info
consumer_cpu_limit = 60  # mCore
consumer_memory_limit = 1000  # MB
initial_consumer = 40
partition_number = 40
number_group = 2

# yaml modification for node selector
consumer_pod_specified_node_key = "test"
consumer_pod_specified_node_value = "consumer"
producer_pod_specified_node_key = "test"
producer_pod_specified_node_value = "producer"
alameda_ai_pod_specified_node_key = "test"
alameda_ai_pod_specified_node_value = "ai"

# # test case
k8shpa_percent = 20
k8s_upscale_limit = 5
number_alamedahpa = 0
number_k8shpa = 0
number_nonhpa = 1
k8shpa_type = "cpu"  # cpu or lag

# configuration
traffic_path = "./traffic"
metrics_path = "./metrics"
picture_path = "./picture"
config_path = "./config"

# # traffic - ab info
traffic_ratio = 60000  # nginx: 4000
traffic_path = "./traffic"
traffic_interval = 60  # generate traffic per 1 minute during 72 minutes
data_interval = 70  # collect pods' resource utilization # init: 80 minutes
warm_up = 20
training_interval = 100
training_scale = 100
traffic_frequency = 6  # import traffic 6 times per second
message_size = 300  # bytes
workload_type = "vary"  # fix: fix workload; vary: vary workload
transaction_value = 100  # avg. workload = 74.8

# log
log_interval = 15  # collect data per 15 seconds
query_interval = 1
query_timeout = 15

# # picture
draw_picture = False
picture_x_axis = 288
picture_y_ratio = 1.3
show_details = True
comparision = "nonhpa40-30000_0"

# kafka
group_name = "group0001"
topic_name = "topic0001"

# prometheus
prometheus_operator_name = "prometheus-k8s"
