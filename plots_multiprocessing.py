import os
import time

import matplotlib.pyplot
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
import psutil
import collections
from multiprocessing import Process, Pipe
from threading import Thread, Lock
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from base import Ui_MainWindow


# GLOBAL VARIABLES
signal_to_draw = 0
graph_amplitude = 1


#  КЛАСС нашего ОКНА, который запускается в ДОП процессе
class MyWin(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.conn_data_pipe2 = None
        self.current_distance = 0.  # Текущее расстояние (мм)
        self.current_step = 0.  # Шаг изменения расстояние (мм)
        self.current_amplitude = 1.0  # Диапозон напряжения на графиках (Вольт)

        # Здесь прописываем событие нажатия на кнопку
        self.ui.pushButton.clicked.connect(self.draw_graph)
        self.ui.pushButton_3.clicked.connect(self.set_current_distance)
        self.ui.pushButton_2.clicked.connect(self.set_current_step)
        self.ui.pushButton_4.clicked.connect(self.add_step)
        self.ui.pushButton_6.clicked.connect(self.change_amplitude)
        self.ui.pushButton_7.clicked.connect(self.write_info_to_file)
        self.ui.pushButton_11.clicked.connect(self.delete_from_file)
        self.ui.pushButton_5.clicked.connect(self.open_current_file)

        self.ui.pushButton_8.clicked.connect(self.draw_all)


    def draw_graph(self):
        # именно отправлять через pipe.send()
        self.conn_data_pipe2.send("start")
        return

    def set_current_distance(self):
        try:
            num = float(self.ui.lineEdit.text())
            self.current_distance = num
            self.ui.textBrowser.setText(f"Успешно введено текущее расстояние = {self.current_distance} мм")
        except Exception as exp:
            self.ui.textBrowser.setText(f"Введено НЕ числовое значение в текущее расстояние!\n{exp}")
        finally:
            return

    def set_current_step(self):
        try:
            num = float(self.ui.lineEdit_2.text())
            self.current_step = num
            self.ui.textBrowser.setText(f"Успешно введен шаг = {self.current_step} мм\n"
                                        f"Шаг можно добавлять к текущему расстоянию для его изменения")
            self.ui.label_7.setText(f"{self.current_step}")
        except Exception as exp:
            self.ui.textBrowser.setText(f"Введено НЕ числовое значение в ШАГ!\n{exp}")
        finally:
            return

    def add_step(self):
        if self.current_step == 0:
            self.ui.textBrowser.setText(f"Внимание, ШАГ = {self.current_step}, поэтому нельзя добавлять НОЛЬ\n"
                                        f"Измените текущий шаг!")
        else:
            res = round(self.current_distance + self.current_step, 4)
            self.ui.textBrowser.setText(f"Текущее расстояние изменено с {self.current_distance} "
                                        f"на\n{res} мм")
            self.current_distance = res
            self.ui.lineEdit.setText(f"{self.current_distance}")
        return

    def change_amplitude(self):
        try:
            num = float(self.ui.lineEdit_3.text())
            self.current_amplitude = num
            self.ui.textBrowser.setText(f"Диапазон напряжения на графиках изменился:\n"
                                        f"{self.current_amplitude} Вольт")
            self.conn_data_pipe2.send(f"a:{self.current_amplitude}")
        except Exception as exp:
            self.ui.textBrowser.setText(f"Введено НЕ числовое значение для диапазона!\n{exp}")
        finally:
            return

    def write_info_to_file(self):
        filename = "measurements.txt"
        try:
            file = open(filename, "r")
            file.close()
        except Exception as exp:
            print(f"При записи в файл произошла ошибка\n{exp}")
            file = open(filename, "w")
            file.close()
        finally:
            file = open(filename, "r")
            content = file.readlines()
            print(content)  # For debugging
            file.close()
            file = open(filename, "w")
            file.writelines(content)
            file.write("1:2:3:4\n")  # TODO ЗАПИСЫВАТЬ ИНФОРМАЦИЮ ОТСЮДА!!!
            file.close()
            self.ui.textBrowser.setText(f"Информация записана в файл!\n"
                                        f"....")
        return

    def delete_from_file(self):
        filename = "measurements.txt"
        file = open(filename, "w")
        file.close()
        self.ui.textBrowser.setText(f"Успешно удалены все данные из файла!")
        return

    def open_current_file(self):
        filename = "measurements.txt"
        try:
            os.startfile(filename)
            self.ui.textBrowser.setText(f"Успешно открыт файл\n{filename}")
        except Exception as exp:
            self.ui.textBrowser.setText(f"Файл не создан, создаю файл.")
            file = open(filename, "w")
            file.close()
        return

    # TODO ПРОПИСАТЬ МЕТОД! Помощь есть на сайте указанном в линии 32 файла с командами
    def draw_all(self):
        X = np.arange(0, 10, 0.1)

        # Using built-in trigonometric function we can directly plot
        # the given cosine wave for the given angles
        Y1 = np.sin(X)
        Y2 = np.cos(X)

        figure, axis = plt.subplots(1, 3, figsize=(15, 5), facecolor='#DEDEDE')
        # For Sine Function
        axis[0].plot(X, Y1, color='r', label="Channel 1")
        axis[0].plot(X, Y2, color='b', label="Channel 2")
        axis[0].set_title("Sine Function")
        axis[0].legend(loc='upper right', framealpha=0.5)

        # For Cosine Function
        axis[2].plot(X, Y2)
        axis[2].set_title("Cosine Function")

        # Combine all the operations and display
        plt.tight_layout()
        plt.show()

        self.ui.textBrowser.setText("Выведены графики зависимости")


#  Функция отрисовки Графиков, должна быть в основном ПОТОКЕ и ОСНОВНОМ ПРОЦЕССЕ
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

        ax1.set_ylim(-graph_amplitude, graph_amplitude)  # TODO Изменяем Амплитуду сигналов

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
    plt.tight_layout()
    plt.show()  # блок


#  Функция выполненная после создания ДОП. ПРОЦЕССА
def main(conn2):
    app = QtWidgets.QApplication(sys.argv)
    application = MyWin()
    application.show()
    application.conn_data_pipe2 = conn2
    print(f"App.conn_data = {application.conn_data_pipe2}")
    sys.exit(app.exec_())  # блок


#  Функция ОСНОВНОГО ПРОЦЕССА, как доп. поток, бесконечно принимает информацию от приложения(т.е. от доп. Процесса)
def connection(conn1):
    global signal_to_draw, graph_amplitude
    while True:
        time.sleep(0.1)
        print("Waiting for Data from Child Process")
        data: str = conn1.recv()
        print(data)
        # Принимаем запросы от Child процесса - это GUI приложение
        if data == "start":
            signal_to_draw = 1
        elif data.find("a:") != -1:
            data = data.replace("a:", '')
            graph_amplitude = float(data)
            print(f"Получена измененная амплитуда = {graph_amplitude}")


if __name__ == "__main__":
    Process1, Child_Process = Pipe()
    # starting()
    main_window_process = Process(target=main, daemon=False, args=(Child_Process,))
    main_window_process.start()
    connection_thread = Thread(target=connection, daemon=True, args=(Process1,))
    connection_thread.start()
    print("Started app")
    # Главный процесс и главный поток, тут проверяем информацию по сигналу для отрисовки приложения (доп поток изменяет)
    while True:
        time.sleep(0.1)
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
