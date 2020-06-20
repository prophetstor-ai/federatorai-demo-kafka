import sys
import argparse
import numpy as np
import pylab as plt
import random
from scipy.interpolate import interp1d


class DataExpansion:

    def __init__(self, transaction, scale, noise=0):
        self.transaction = transaction
        self.scale = scale
        self.noise = noise

    def expand(self):
        expansion = np.array([])

        for index in range(len(self.transaction) - 1):
            start = self.transaction[index]
            end = self.transaction[index + 1]

            # generate expanded transaction data
            data = self.gen_data(start, end)

            # generate noise data, but keep start and end without noise
            noise = self.gen_noise(abs(start - end))
            noise[0] = 0.0
            noise[-1] = 0.0

            # combine the transaction data with noise
            data = data + noise

            # normalize data
            self.normalize(data, max(start, end), min(start, end))

            # append to result
            expansion = np.append(expansion, data[0:-1])

            if index == len(self.transaction) - 2:
                expansion = np.append(expansion, data[-1])

        return expansion

    def gen_data(self, start, end):
        time = np.linspace(0, 1, 2)
        value = np.array([start, end])
        f1 = interp1d(time, value)
        x = np.linspace(0, 1, self.scale + 2)
        y = f1(x)
        return y

    def gen_noise(self, differ):
        noise = list()
        for i in range(self.scale + 2):
            percentage = random.randint(self.noise*(-1), self.noise)/100.0
            result = differ * percentage
            noise.append(result)
        return noise

    def normalize(self, data, upper, lower):
        for index in range(len(data)):
            if data[index] > upper:
                data[index] = upper
            if data[index] < lower:
                data[index] = lower


def read_file(file_name):
    array = list()
    try:
        with open(file_name, "r") as f:
            for line in f.readlines():
                if line:
                    array.append(float(line.strip("\n")))
    except Exception as e:
        print "failed to read %s: %s" % (file_name, str(e))
    return array


def write_file(data, path):
    try:
        with open(path, "wb+") as f:
            for value in data:
                f.write("%.8f\n" % value)
    except Exception as e:
        print "failed to write producer latency(%s): %s" % (path, str(e))
        return -1


def draw_graph(transaction, expansion):
    length_transaction = len(transaction)
    length_expansion = len(expansion)

    plt.figure(figsize=(16, 8))

    time = np.linspace(0, length_expansion, length_expansion)
    plt.plot(time, expansion, label='expansion')
    plt.legend(loc=1, ncol=3)

    time = np.linspace(0, length_expansion, length_transaction)
    plt.plot(time, transaction, label='transaction')
    plt.legend(loc=0)

    plt.show()


def expand_transaction(args):
    transaction = list()
    expansion = list()

    # do transaction expansion
    if args.transaction:
        transaction = read_file(args.transaction)
        data = DataExpansion(transaction, args.scale, args.noise)
        expansion = data.expand()

    # write expanded transaction to file
    if args.file_path:
        write_file(expansion, args.file_path)

    # draw graph if necessary
    if args.draw:
        draw_graph(transaction, expansion)


def main():
    parser = argparse.ArgumentParser(prog="expand", description="transaction data expansion utility", version="1.0", add_help=True)
    parser.print_usage = parser.print_help

    parser.add_argument("-t", "--transaction", type=str, help="transaction data file path", required=True, dest="transaction", default="")
    parser.add_argument("-f", "--file_path", type=str, help="new scaled transaction data file path", required=False, dest="file_path", default="")
    parser.add_argument("-s", "--scale", type=int, help="scale up", required=False, dest="scale", default=1)
    parser.add_argument("-n", "--noise", type=int, help="noise in percentage", required=False, dest="noise", default=0)
    parser.add_argument("-d", "--draw", type=bool, help="draw the graph", required=False, dest="draw", default=False)
    parser.set_defaults(function=expand_transaction)

    # Run the function
    args = parser.parse_args()
    retcode = args.function(args)

    sys.exit(retcode)


if __name__ == "__main__":
    main()
