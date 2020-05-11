import os
import time
import sys
from define import warm_up

def warmup_traffic(algo):
    print "--- Warm UP For %s Munites ---" % warm_up
    for i in range(warm_up):
        print "--- Warm UP %s/%sth workload ---" % (i, warm_up)
        start_time = time.time()
        cmd = "python ./run_kafka.py %s %d &" % (algo, 0)
        ret = os.system(cmd)
        count = 0
        while True:
            end_time = time.time()
            if end_time - start_time >= 60:
               break
            count += 1
            time.sleep(1)

def generate_traffic(algo, time_count):
    print "--- Generate Traffic For %d Munites ---" % time_count
    for i in range(time_count):
        start_time = time.time()
        cmd = "python ./run_kafka.py %s %d &" % (algo, i)
        ret = os.system(cmd)
        count = 0
        while True:
            end_time = time.time()
            if end_time - start_time >= 60:
                break
            count += 1
            time.sleep(1)


def main(algo, time_count):
    total_start_time = time.time()
    print "=== Generate Traffic for %d Minutes ===" % time_count
    warmup_traffic(algo)
    generate_traffic(algo, time_count)
    total_end_time = time.time()
    print "importing kafka traffic is completed!!!", (total_end_time - total_start_time)/60, "minutes"


if __name__ == "__main__":
    try:
        algo = sys.argv[1]
        time_count = int(sys.argv[2])
        main(algo, time_count)
    except Exception as e:
        print "failed to generate traffic: %s" % str(e)

