import numpy as np
import math
import sys


class Data:
    f0 = 4.0  # number of wave
    fs = 120.0  # number of data
    A = 50.0  # amp and initial_value
    is_noise = 0

    def __init__(self, wave, data, amp, noise=0):
        if wave:
            self.f0 = wave*1.0
        if data:
            self.fs = data*1.0
        if amp:
            self.A = amp*1.0
        if int(noise) > 0:
            self.is_noise = noise/10.0
        self.t = np.arange(self.fs)

    def gen_sine_wave(self):
        sinusoid = np.sin(2*math.pi*self.t*(self.f0/self.fs))
        sinusoid = self.normalize(sinusoid)
        return sinusoid

    def gen_noise(self):
        noise = np.random.normal(0, 1, int(self.fs))
        noise = self.normalize(noise)
        return noise

    def normalize(self, data):
        max_data = float(max(data))
        amp = math.floor((self.A/max_data))
        norm = np.zeros(len(data))
        for i in range(len(data)):
            norm[i] = amp*data[i]+self.A
        return norm

    def gen_data(self):
        sinusoid = self.gen_sine_wave()
        noise = self.gen_noise()
        new_data = sinusoid
        if self.is_noise != 0:
            new_data = sinusoid + noise*self.is_noise
        self.write_data(new_data)

    def write_data(self, data):
        file_name = "transaction-%s-%s-%s.txt" % (int(self.f0), int(self.fs), int(self.A))
        if self.is_noise:
            file_name = "transaction-noise-%s-%s-%s.txt" % (int(self.f0), int(self.fs), int(self.A))
        try:
            with open(file_name, "w") as f:
                for i in range(len(data)):
                    value = data[i]
                    f.write("%s\n" % value)
        except Exception as e:
            print("failed to write data: %s" % str(e))
        print("success to write %s" % (file_name))


def main(wave, data, amp, noise):
    d = Data(wave, data, amp, noise)
    d.gen_data()


if __name__ == "__main__":
    wave = int(sys.argv[1])
    data = int(sys.argv[2])
    amp = int(sys.argv[3])
    noise = 0
    if len(sys.argv) > 4:
        noise = int(sys.argv[4])
    main(wave, data, amp, noise)
