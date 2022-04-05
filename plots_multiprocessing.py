import time
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
import psutil
import collections
from multiprocessing import Process, Pipe
from threading import Thread, Lock
from PyQt5 import QtCore, QtGui, QtWidgets
import sys, os
from untitled import Ui_MainWindow

signal_to_draw = 0


class MyWin(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.conn_data_pipe2 = None

        # Здесь прописываем событие нажатия на кнопку
        self.ui.pushButton.clicked.connect(self.draw_graph)

    def draw_graph(self):
        # TODO именно отправлять через pipe.send(1)
        self.conn_data_pipe2.send("1")
        return


def starting(main_proc: Process):
    # function to update the data
    def my_function(i):
        # get data
        # a = input("Data input: ")
        if not main_proc.is_alive():
            sys.exit()
        cpu.popleft()
        cpu.append(psutil.cpu_percent())
        ram.popleft()
        ram.append(psutil.virtual_memory().percent)
        # clear axis
        ax.cla()
        ax1.cla()
        # plot cpu
        ax.plot(cpu)
        ax.scatter(len(cpu) - 1, cpu[-1])
        ax.text(len(cpu) - 1, cpu[-1] + 2, "{}%".format(cpu[-1]))
        ax.set_ylim(0, 100)
        # plot memory
        ax1.plot(ram)
        ax1.scatter(len(ram) - 1, ram[-1])
        ax1.text(len(ram) - 1, ram[-1] + 2, "{}%".format(ram[-1]))
        ax1.set_ylim(0, 100)

    # start collections with zeros
    cpu = collections.deque(np.zeros(50))
    ram = collections.deque(np.zeros(50))

    # define and adjust figure
    fig = plt.figure(figsize=(12, 6), facecolor='#DEDEDE')
    ax = plt.subplot(121)
    ax1 = plt.subplot(122)
    ax.set_facecolor('#DEDEDE')
    ax1.set_facecolor('#DEDEDE')

    # animate
    ani = FuncAnimation(fig, my_function, interval=100)
    plt.show()


def main(conn2):
    # TODO Создаем сразу новый поток, в котором начнем обрабатывать конец ТРУБЫ
    app = QtWidgets.QApplication(sys.argv)
    application = MyWin()
    application.show()
    application.conn_data_pipe2 = conn2
    print(f"App.conn_data = {application.conn_data_pipe2}")
    sys.exit(app.exec_())


def connection(conn1, main_proc: Process):
    global signal_to_draw
    while True:
        print("Waiting for Data from Child Process")
        data = conn1.recv()
        print(data)
        if not main_proc.is_alive():
            print("EXIT!!")
            sys.exit()
        elif data == "1":
            signal_to_draw = 1


if __name__ == "__main__":
    Process1, Child_Process = Pipe()
    # starting()
    main_window_process = Process(target=main, daemon=False, args=(Child_Process,))
    main_window_process.start()
    connection_thread = Thread(target=connection, daemon=True, args=(Process1, main_window_process,))
    connection_thread.start()
    print("Started app")
    # TODO Создать поток для получения информации с pipe
    while True:
        print("still")
        if signal_to_draw == 1 and main_window_process.is_alive():
            starting(main_window_process)
            signal_to_draw = 0
        if not main_window_process.is_alive():
            sys.exit()

"""


import multiprocessing

def worker(conn):
    print conn.recv()
    conn.send("sent from child process")

conn1, conn2 = multiprocessing.Pipe()
process = multiprocessing.Process(target=worker, args=(conn2,))
process.start()

conn1.send("sent from main process")
print conn1.recv()


"""
