import pyvisa as visa
from time import sleep
import numpy as np
import collections
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import multiprocessing as mp
import tqdm
from threading import Thread
from pathos.multiprocessing import ProcessingPool as Pool

# visa.log_to_screen()
'''
#  osc.read osc.write osc.query
#  You can use visa-shell
#  To run visa-shell insert command: pyvisa-shell
#  After opening device You can talk to the device using "write", "read" or "query".
#  The default end of message is added to each message.
#  osc.query - method 621 string in pyvisa/resources/messagebased.py
device = rm.open_resource(rigol_device_id)  # open device to work with
print(f'QUERY returned answer = {device.query("*IDN?")}')  # Command to check ID of opened device
'''


class RigolAPI:
    def __init__(self):
        self.rm = visa.ResourceManager()
        if len(self.rm.list_resources()) > 0:
            self.rigol_device_id = self.rm.list_resources()[0]
            self.device = self.rm.open_resource(self.rigol_device_id)  # Now can self.device. -/read, -/write, -/query
            self.device.timeout = 13000
        else:
            self.rigol_device_id = None

    def device_id(self):
        return self.rigol_device_id

    def resources_list(self):
        return self.rm.list_resources()

    def opened_resources(self):
        return self.rm.list_opened_resources()

    # ---------- MAIN METHODS -----------

    def autoscale_func(self):
        """
        Enable the waveform auto setting function. The oscilloscope will automatically adjust the
        vertical scale, horizontal timebase, and trigger mode according to the input signal to
        realize optimum waveform display. This command is equivalent to pressing the AUTO key
        at the front panel.
        :param oscillator: opened device to connect
        """
        self.device.write(":AUToscale")
        return 0

    def range(self, channel=1):
        """
        :param channel: using selected channel
        :return: current range in selected channel
        """
        return self.device.query(f":CHANnel{channel}:RANGe?")  # TODO Остановка на 28 странице документации

    def get_rphase(self):
        """
        :return: current // front phase of channel 1 and 2 in degrees
        """
        return float(self.device.query(":MEASure:ITEM? RPHase"))

    def get_fphase(self):
        """
        :return: current \\ front phase of channel 1 and 2 in degrees
        """
        return float(self.device.query(":MEASure:ITEM? FPHase"))

    def get_data_premable(self):
        '''
        Get information about oscilloscope axes.

        Returns:
            dict: A dictionary containing general oscilloscope axes information.
        '''
        pre = self.device.query(':wav:pre?').split(',')
        pre_dict = {
            'format': int(pre[0]),
            'type': int(pre[1]),
            'points': int(pre[2]),
            'count': int(pre[3]),
            'xincrement': float(pre[4]),
            'xorigin': float(pre[5]),
            'xreference': float(pre[6]),
            'yincrement': float(pre[7]),
            'yorigin': float(pre[8]),
            'yreference': float(pre[9]),
        }
        return pre_dict






def draw_rphase(mute):
    # kek = RigolAPI()

    # function to update the data
    def my_function(i):
        # get data
        # a = input("Data input: ")
        rphase_data.popleft()
        mute.acquire()
        rphase_data.append(round(rigol.get_rphase(), 3))
        mute.release()
        # clear axis
        ax.cla()
        # plot rphase_data
        ax.plot(rphase_data)
        plt.title(label='Phase Delay')
        plt.xlabel("Time (100ns / 1_read)")
        plt.ylabel("Phase Delay (deg)")
        ax.scatter(len(rphase_data) - 1, rphase_data[-1])
        ax.text(len(rphase_data) - 1, rphase_data[-1] + 2, "{}°".format(rphase_data[-1]))
        ax.set_ylim(-180, 180)

    # start collections with zeros
    rphase_data = collections.deque(np.zeros(100))

    # define and adjust figure
    fig = plt.figure(figsize=(7, 5), facecolor='#DEDEDE')
    ax = plt.subplot(111)

    print(ax)
    ax.set_facecolor('#DEDEDE')

    # animate
    ani = FuncAnimation(fig, my_function, interval=100)
    plt.show()


rigol = RigolAPI()

if __name__ == "__main__":
    print(float(rigol.range(channel=1)))
    print(float(rigol.range(channel=2)))
    print("Main Statistic")
    # Creating process
    mutex = mp.Lock()
    proc1 = mp.Process(target=draw_rphase, daemon=False, args=(mutex,))
    proc1.start()




    print("Created new process")


    print(rigol.get_data_premable())
    print("------------END------------")
