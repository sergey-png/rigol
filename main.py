import pyvisa as visa
from time import sleep
import numpy as np

visa.log_to_screen()
rm = visa.ResourceManager()
# print(rm.list_resources())
rigol_device_id = rm.list_resources()[0]

#  osc.read osc.write osc.query
#  You can use visa-shell
#  To run visa-shell insert command: pyvisa-shell
#  After opening device You can talk to the device using "write", "read" or "query".
#  The default end of message is added to each message.
#  osc.query - method 621 string in pyvisa/resources/messagebased.py
osc = rm.open_resource(rigol_device_id)  # open device to work with
print(f'QUERY returned answer = {osc.query("*IDN?")}')  # Command to check ID of opened device
print(f"Opened res = {rm.list_opened_resources()}")


def autoscale(oscillator):
    """
    Enable the waveform auto setting function. The oscilloscope will automatically adjust the
    vertical scale, horizontal timebase, and trigger mode according to the input signal to
    realize optimum waveform display. This command is equivalent to pressing the AUTO key
    at the front panel.
    :param oscillator: opened device to connect
    """
    command = ":AUToscale"
    oscillator.write(command)
    return 0


print(f"Write to osc = {autoscale(osc)}")
