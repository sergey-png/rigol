import pyvisa as visa
from time import sleep
import numpy as np
from pyvisa import Resource

visa.log_to_screen()
rm = visa.ResourceManager()
# print(rm.list_resources())
rigol = rm.list_resources()[0]

#  osc.read osc.write osc.query
#  You can use visa-shell
#  To run visa-shell insert command: pyvisa-shell
#  After opening device You can talk to the device using "write", "read" or "query".
#  The default end of message is added to each message.
#  osc.query - method 621 string in pyvisa/resources/messagebased.py
osc = rm.open_resource(rigol)  # open device to work with
print(f'QUERY returned answer = {osc.query("*IDN?")}')  # Command to check ID of opened device
print(f"Opened res = {rm.list_opened_resources()}")


def autoscale(oscillator):
    command = ":AUToscale"
    oscillator.write(command)


print(f"Write to osc = {autoscale(osc)}")
