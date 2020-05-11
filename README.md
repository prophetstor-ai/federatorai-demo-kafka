*  it simulates that a producer generates messages to a topic of kafka, and a consumer group receives messages from the topic of kafka and scales consumers based on 3 scaling algorithms
   - algo1: nonhpa
   - algo2: k8s native hpa - lag
   - algo3: federator.ai


*  the script includes 3 components:
   - client.py: scripts for kafka commands and kafka benchmark tools
   - generate_kafla_traffic.py: generate traffic pattern based on transaction.txt and kafka benchmark tools 
   - write_kafka_log.py: collect all related tracefiles and write into "./traffic" directory

*  operation flows:
   - clean gabarge data and restart recommender pod
   - run scripts to modify parameters in define.py such as initial consumers, topic partitions, execution time, algo_name,..., and so on
   - scripts will be executed based on these parameters in define.py and collect related tracefile in ./traffic
   - finally, ./traffic will be renamed as <algo_name>_<kafka_conf>_<build>, then move to ./test_result/<algo_name>_<duration>_<kafka_conf>_<time_stamp>: e.g., federatorai_hpa_120min_5con_40par_1587143679
   - the script will collect related recommender and alameda-ai logs to the the "federatorai_hpa_120min_5con_40par_1587143679" directory
