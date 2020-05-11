import os
import sys
import time
from define import log_interval, query_interval, query_timeout

def main(algo, num_time):
    interval = num_time* int(60/log_interval)
    print "=== Write Logs for %d Intervals ===" % interval
    for i in range(interval):
        print "--- %s start to collect logs at %d/%d intervals (in %d sec)" % (algo, i, interval, log_interval)
        start_time = time.time()
        cmd = "python ./producer.py %s &" % (algo)
        ret = os.system(cmd)
        cmd = "python ./consumer.py %s &" % (algo)
        ret = os.system(cmd)
        #cmd = "python ./broker.py %s &" % (algo)
        #ret = os.system(cmd)
        #cmd = "python ./zookeeper.py %s &" % (algo)
        #ret = os.system(cmd)
        #cmd = "python ./prometheus.py %s &" % (algo)
        #ret = os.system(cmd)
        cmd = "python ./prometheus_query.py %s &" % (algo)
        ret = os.system(cmd)
        while True:
            end_time = time.time()
            diff_time = end_time - start_time
            if diff_time >= query_timeout:
                print "write kafka logs is completed", diff_time
                break
            time.sleep(query_interval)         


if __name__ == "__main__":
    algo = sys.argv[1]
    num_time = int(sys.argv[2])
    main(algo, num_time)
