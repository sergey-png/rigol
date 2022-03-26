import pyvisa as visa
from time import sleep
import numpy as np

visa.log_to_screen()
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

    def kek(self):
        return self.device.query(":CHANnel1:RANGe?")  # TODO Остановка на 28 странице документации


if __name__ == "__main__":
    rigol = RigolAPI()
    print(rigol.kek())
    print("------------END------------")
