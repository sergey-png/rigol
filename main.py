import pyvisa as visa
from time import sleep
import numpy as np
import collections
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import multiprocessing as mp
from threading import Thread, Lock
import tqdm
from rigol1000z import rigol1000z

visa.log_to_screen()
'''
#  osc.read osc.write osc.query
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
            self.device.timeout = 30000
        else:
            self.rigol_device_id = None
            self.device = None

    def reconnect(self):
        self.device.write(":RUN")
        self.device.close()
        self.rm = visa.ResourceManager()
        if len(self.rm.list_resources()) > 0:
            self.rigol_device_id = self.rm.list_resources()[0]
            self.device = self.rm.open_resource(self.rigol_device_id)
            self.device.timeout = 10000
            self.device.write(":RUN")
        else:
            self.rigol_device_id = None
        return

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
        self.device.write(":RUN")
        return float(self.device.query(":MEASure:ITEM? RPHase"))

    def get_data(self, channel=1):
        self.device.write(f":WAV:SOUR CHAN{channel}")
        message = self.device.query(":WAV:DATA?")
        result = []
        for element in message[11:].split(','):
            result.append(float(element))
        return result


# --------------- GLOBAL VARIABLES ---------------
rigol = RigolAPI()
data_channel = [[], []]
phase_delay = collections.deque([0])


# --------------- GLOBAL VARIABLES ---------------


def get_data_thread(mute: Lock):
    global data_channel, phase_delay
    rigol.device.write(f":WAV:MODE NORMal")
    rigol.device.write(f":WAV:FORM ASCii")
    while True:
        rigol.device.write(":RUN")
        sleep(1)
        print('I am thread for channels')
        # mute.acquire()
        try:
            rigol.device.write(":STOP")
            data_channel[0] = rigol.get_data(1)
            sleep(0.05)
            data_channel[1] = rigol.get_data(2)
            sleep(0.05)
            data: float = rigol.get_rphase()
            sleep(0.05)
            phase_delay.append(data)
        except Exception as exp:
            print(f"ERROR = {exp}")
        finally:
            sleep(0.1)
            # mute.release()


def clearing_device(mute: Lock):
    while True:
        print("I am still here")
        sleep(5)
        mute.acquire()
        sleep(0.1)
        try:
            if rigol.rigol_device_id is None:
                continue
            else:
                print("RECONNECTED!")
        except Exception as exp:
            print(f"ОШИБКА ПОДКЛЮЧЕНИЯ = {exp}")
            sleep(0.5)
        finally:
            mute.release()


def draw_figures():
    # function to update the data
    def my_function(i):
        global data_channel, phase_delay
        # get data
        rphase_data.popleft()
        rphase_data.append(phase_delay[0])
        if len(phase_delay) > 1:
            phase_delay.popleft()
        y_axis_1 = data_channel[0]
        y_axis_2 = data_channel[1]
        # clear axis
        ax.cla()
        ax2.cla()
        # plot rphase_data
        ax.plot(rphase_data)
        plt.title(label='Phase Delay and Signals')
        plt.xlabel("Time (100ns / 1_read)")
        plt.ylabel("Phase Delay (deg)")
        ax.scatter(len(rphase_data) - 1, rphase_data[-1])
        ax.text(len(rphase_data) - 1, rphase_data[-1] + 2, "{}°".format(rphase_data[-1]))
        ax.set_ylim(-180, 180)

        # plot signals from Channel 1 and 2
        ax2.plot(y_axis_1, color='r', label='Channel 1')
        ax2.plot(y_axis_2, color='b', label='Channel 2')
        ax2.legend()
        print("-------------- UPDATED GRAPH --------------")

    # start collections with zeros
    rphase_data = collections.deque(np.zeros(100))

    # define and adjust figure
    fig = plt.figure(figsize=(10, 5), facecolor='#DEDEDE')
    ax = plt.subplot(121)
    ax2 = plt.subplot(122)

    ax.set_facecolor('#DEDEDE')
    ax2.set_facecolor('#DEDEDE')
    # animate
    ani = FuncAnimation(fig, my_function, interval=200)
    plt.show()

if __name__ == "__main__":
    print("Main Statistic")
    # Creating process
    mutex = Lock()
    # getting_data = Thread(target=get_data_thread, args=(mutex,), daemon=True)
    # clearing = Thread(target=clearing_device, args=(mutex,), daemon=True)
    # clearing.start()
    # getting_data.start()
    sleep(1)
    get_data_thread(mutex)

    draw_figures()

    print("Created new process")
    print("------------END------------")
