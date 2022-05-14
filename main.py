import pyvisa as visa
from time import sleep
import numpy as np
import collections
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import multiprocessing as mp
from threading import Thread, Lock
import sys
import os
from PyQt5 import QtWidgets
from base import Ui_MainWindow

# visa.log_to_screen()
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
            self.device.timeout = 2000
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
            self.device.timeout = 2000
            self.device.write(":RUN")
        else:
            self.rigol_device_id = None
        return self.rigol_device_id

    def get_device_id(self):
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
        """
        self.device.write(":AUToscale")
        return

    def range(self, channel=1):
        """
        :param channel: using selected channel
        :return: current range in selected channel
        """
        return self.device.query(f":CHANnel{channel}:RANGe?")

    def get_rphase(self):
        """
        :return: current // front phase of channel 1 and 2 in degrees
        """
        self.device.write(":RUN")
        return float(self.device.query(":MEASure:ITEM? RPHase"))

    def get_freq(self):
        data = [0, 0]
        data[0] = round(1 / float(self.device.query(":MEASure:ITEM? PERiod,CHANnel1")), 4)
        data[1] = round(1 / float(self.device.query(":MEASure:ITEM? PERiod,CHANnel2")), 4)
        return data

    def get_amplitude(self):
        data = [0, 0]
        data[0] = float(self.device.query(":MEASure:ITEM? VMAX,CHANnel1"))
        data[1] = float(self.device.query(":MEASure:ITEM? VMAX,CHANnel2"))
        return data

    def get_data(self, channel=1):
        self.device.write(f":WAV:SOUR CHAN{channel}")
        message = self.device.query(":WAV:DATA?")
        result = []
        for element in message[11:].split(','):
            result.append(float(element))
        return result


# --------------- GLOBAL VARIABLES ---------------
rigol = RigolAPI()  # Экзмепляр класса Rigol
# if rigol.device is None:
#     print("No device found")
#     sys.exit(0)
data_channel = [[], []]  # Массив, который хранит 1200 точек двух сигналов для отрисовки на графиках
signal_to_draw = 0  # Сигнал, что можно рисовать графики в реал тайме
graph_amplitude = 1  # Амплитуда графика, задается в Вольтах
get_data = 0  # Нужно ли треду получать информацию с осциллографа в бесконечном цикле?

phase_delay = 0  # Разность фаз двух сигналов
frequency = [0, 0]  # Частота двух сигналов
amplitude_data = [0, 0]  # Амплитуда двух сигналов


# --------------- GLOBAL VARIABLES ---------------


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
        self.ui.pushButton_9.clicked.connect(self.auto_scale)

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
        filename2 = "measurements_all_points.txt"
        try:
            with open(filename, "r") as file:
                file.close()
        except Exception as exp:
            self.ui.textBrowser.setText(f"При записи в файл произошла ошибка\n{exp}")
            with open(filename, "w") as file:
                file.close()
        try:
            with open(filename2, "r") as file:
                file.close()
        except Exception as exp:
            self.ui.textBrowser.setText(f"При записи в файл произошла ошибка\n{exp}")
            with open(filename2, "w") as file:
                file.close()

        finally:
            with open(filename, "r") as file:
                content = file.readlines()
                # print(content)  # For debugging
                if content:
                    with open("last_save.txt", "w") as file2:
                        file2.writelines(content)

            with open(filename2, "r") as file:
                content2 = file.readlines()
                # print(content)  # For debugging
                if content2:
                    with open("last_save_all_points.txt", "w") as file2:
                        file2.writelines(content2)
            measuring_data = []
            with open(filename2, "w") as file:
                for i in range(5):  # 5 раз считываем данные с осциллографа и записываем в measurements_all_points.txt
                    sleep(0.1)
                    self.conn_data_pipe2.send("get_info")
                    data_dict: dict = self.conn_data_pipe2.recv()
                    data_dict['Distance'] = float(self.ui.lineEdit.text())
                    print(f"data_dict = {data_dict}")
                    line = f"{data_dict['Phase']}:" \
                           f"{data_dict['Frequency'][0]}:{data_dict['Frequency'][1]}:" \
                           f"{data_dict['Amplitude'][0]}:{data_dict['Amplitude'][1]}:" \
                           f"{data_dict['Distance']}\n"
                    file.write(line)
                    measuring_data.append(float(data_dict['Amplitude'][0]))
                    self.ui.textBrowser.setText(f"Записано в файл {i + 1} измерений из 5")

            with open(filename, "w") as file:
                file.writelines(content)
                average = sum(measuring_data) / len(measuring_data)

                line = f"{data_dict['Phase']}:" \
                       f"{data_dict['Frequency'][0]}:{data_dict['Frequency'][1]}:" \
                       f"{average}:{data_dict['Amplitude'][1]}:" \
                       f"{data_dict['Distance']}\n"
                file.write(line)
                self.ui.textBrowser.setText(f"Информация записана в файл measurements.txt!\n"
                                            f"....")
        return

    def delete_from_file(self):
        filename = "measurements.txt"
        file = open(filename, "w")
        file.close()
        filename2 = "measurements_all_points.txt"
        file = open(filename2, "w")
        file.close()
        self.ui.textBrowser.setText(f"Файлы очищены!")
        return

    def open_current_file(self):
        filename = "measurements.txt"
        try:
            os.startfile(filename)
            self.ui.textBrowser.setText(f"Успешно открыт файл\n{filename}")
        except Exception as exp:
            self.ui.textBrowser.setText(f"Файл не создан, создаю файл.\n{exp}")
            file = open(filename, "w")
            file.close()
        return

    def auto_scale(self):
        self.conn_data_pipe2.send("auto_scale")

    def draw_all(self):
        filename = "measurements.txt"
        file = open(filename, "r")
        data = file.readlines()
        # X = np.arange(0, len(data), 1)
        y_phase, y_freq1, y_freq2, y_amp1, y_amp2, distance = [], [], [], [], [], []
        for element in data:
            element = element.replace("\n", "")
            data_el = list(map(float, element.split(":")))
            # print(data_el)
            y_phase.append(data_el[0])
            y_freq1.append(data_el[1])
            y_freq2.append(data_el[2])
            y_amp1.append(data_el[3])
            y_amp2.append(data_el[4])
            distance.append(data_el[5])
        distance.reverse()
        y_amp1.reverse()
        print(y_amp1)
        print(distance)

        figure, axis = plt.subplots(1, 3, figsize=(15, 5), facecolor='#DEDEDE')
        # Разность фаз
        axis[0].plot(distance, y_phase, color='b', label="Phase CH1 CH2")
        axis[0].set_title("Разность фаз от расстояния")
        axis[0].legend(loc='upper left', framealpha=0.5)

        # Частота от расстояния
        axis[1].plot(distance, y_freq1, color='b', label="Channel 1")
        axis[1].plot(distance, y_freq2, color='r', label="Channel 2")
        axis[1].set_title("Частота от расстояния")
        axis[1].legend(loc='upper left', framealpha=0.5)

        y_amp1 = [1.1389, 1.1304, 1.1215, 1.1134, 1.1044, 1.0955, 1.0866, 1.0781, 1.0687, 1.0599, 1.0510, 1.0412,
                  1.0314, 1.0225, 1.0125, 1.0028, 0.9932, 0.9831, 0.9712, 0.9623, 0.9536, 0.9422, 0.9323, 0.9206,
                  0.9105, 0.8985, 0.8861, 0.8751, 0.8629, 0.8501, 0.8377, 0.8256, 0.8126, 0.8005, 0.7861, 0.7723,
                  0.7589, 0.7446, 0.7298, 0.7144, 0.6988, 0.6823, 0.6651, 0.6481, 0.6301, 0.6102, 0.5906, 0.5695,
                  0.5481, 0.5250, 0.4989, 0.4711, 0.4391, 0.4021, 0.3598]

        distance = [14.00, 13.80, 13.60, 13.40, 13.20, 13.00, 12.80, 12.60, 12.40, 12.20, 12.00, 11.80, 11.60, 11.40,
                    11.20, 11.00, 10.80, 10.60, 10.40, 10.20, 10.00, 9.80, 9.60, 9.40, 9.20, 9.00, 8.80, 8.60, 8.40,
                    8.20, 8.00, 7.80, 7.60, 7.40, 7.20, 7.00, 6.80, 6.60, 6.40, 6.20, 6.00, 5.80, 5.60, 5.40, 5.20,
                    5.00, 4.80, 4.60, 4.40, 4.20, 4.00, 3.80, 3.60, 3.40, 3.20]
        print(len(distance) == len(y_amp1))
        distance.reverse()
        y_amp1.reverse()

        # Расстояние от напряжения
        axis[2].plot(y_amp1, distance, color='b', label="Channel 1")
        # axis[2].plot(distance, y_amp2, color='r', label="Channel 2")  # Второй сигнал не измеряется поэтому коммент
        axis[2].set_title("Расстояние от напряжения")
        axis[2].legend(loc='upper left', framealpha=0.5)
        axis[2].set_xlabel("Напряжение, В")
        axis[2].set_ylabel("Расстояние, мм")

        # Combine all the operations and display
        plt.tight_layout()
        plt.show()

        self.ui.textBrowser.setText("Выведены графики зависимости")

        # TODO Сделать экспорт в эксель
        return


# ----------------------------------------------------------------------------------------------------------
def auto_scale(mute: Lock):
    mute.acquire(timeout=12)
    rigol.autoscale_func()
    mute.release()
    return


def get_data_thread(mute: Lock):
    global data_channel, phase_delay, get_data
    rigol.device.write(f":WAV:MODE NORMal")
    rigol.device.write(f":WAV:FORM ASCii")
    while True:
        rigol.device.write(":RUN")
        sleep(1)
        if get_data == 0:
            continue
        # print('I am thread for channels')
        mute.acquire()
        while True:
            if get_data == 0:
                break
            try:
                rigol.device.write(":STOP")
                data_channel[0] = rigol.get_data(1)
                break
            except Exception as exp:
                print(f"Error: {exp}")
                clearing_device()

        while True:
            if get_data == 0:
                break
            try:
                data_channel[1] = rigol.get_data(2)
                break
            except Exception as exp:
                print(f"Error: {exp}")
                clearing_device()

        while True:
            if get_data == 0:
                break
            try:
                phase_delay = rigol.get_rphase()
                break
            except Exception as exp:
                print(f"Error: {exp}")
                clearing_device()

        mute.release()


def clearing_device():
    rigol.device.write(":RUN")
    while True:
        print("I am still here")
        sleep(0.1)
        if get_data == 0:
            continue
        try:
            if rigol.reconnect() is None:
                continue
            else:
                print("RECONNECTED!")
                break
        except Exception as exp:
            print(f"Error = {exp}")


def get_data_once(mute: Lock):
    global phase_delay, frequency, amplitude_data
    rigol.device.write(f":WAV:MODE NORMal")
    rigol.device.write(f":WAV:FORM ASCii")
    rigol.device.write(":RUN")
    mute.acquire()
    while True:
        try:
            rigol.device.write(":STOP")
            amplitude_data = rigol.get_amplitude()
            break
        except Exception as exp:
            print(f"Error: {exp}")
            clearing_device()

    # while True:
    #     try:
    #         frequency = rigol.get_freq()
    #         break
    #     except Exception as exp:
    #         print(f"Error: {exp}")
    #         clearing_device()

    # while True:
    #     try:
    #         phase_delay = rigol.get_rphase()
    #         break
    #     except Exception as exp:
    #         print(f"Error: {exp}")
    #         clearing_device()
    data = {
        'Phase': phase_delay,
        'Frequency': frequency,
        'Amplitude': amplitude_data,
        'Distance': 0
    }
    mute.release()
    return data


def draw_figures(main_proc: mp.Process):
    # function to update the data

    def my_function(i):
        global data_channel, phase_delay
        # get data
        if not main_proc.is_alive():
            sys.exit()
        rphase_data.popleft()
        rphase_data.append(phase_delay)  # phase_delay
        y_axis_1 = data_channel[0]  # Voltage for channel 1
        y_axis_2 = data_channel[1]  # Voltage for channel 2
        # clear axis
        ax.cla()
        ax2.cla()
        # plot rphase_data
        ax.plot(rphase_data)
        plt.title(label='Signals')
        plt.xlabel("Time (100ns / 1_read)")
        plt.ylabel("Voltage")
        ax.scatter(len(rphase_data) - 1, rphase_data[-1])
        ax.text(len(rphase_data) - 1, rphase_data[-1] + 2, "{}°".format(rphase_data[-1]))
        ax.set_ylim(-180, 180)
        ax.set_xlim(0, 120)
        ax2.set_ylim(-graph_amplitude, graph_amplitude)

        # plot signals from Channel 1 and 2
        ax2.plot(y_axis_1, color='r', label='Channel 1')
        ax2.plot(y_axis_2, color='b', label='Channel 2')
        ax2.legend()
        print("-------------- UPDATED GRAPH --------------")

    # start collections with zeros
    rphase_data = collections.deque(np.zeros(100))

    # define and adjust figure
    fig = plt.figure(figsize=(10, 6), facecolor='#DEDEDE')
    ax = plt.subplot(121)
    ax2 = plt.subplot(122)

    ax.set_facecolor('#DEDEDE')
    ax2.set_facecolor('#DEDEDE')
    # animate
    ani = FuncAnimation(fig, my_function, interval=200)
    plt.show()


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
    global signal_to_draw, graph_amplitude, mutex, get_data
    while True:
        sleep(0.1)
        print("Waiting for Data from Child Process")
        data: str = conn1.recv()
        # Принимаем запросы от Child процесса - это GUI приложение
        if data == "start":
            signal_to_draw = 1
        elif data.find("a:") != -1:
            data = data.replace("a:", '')
            graph_amplitude = float(data)
            print(f"Получена измененная амплитуда = {graph_amplitude}")
        elif data == "auto_scale":
            if get_data == 1:
                get_data = 0
                auto_scale(mutex)
                get_data = 1
            else:
                auto_scale(mutex)
        elif data == "get_info":
            data_dict = get_data_once(mutex)
            conn1.send(data_dict)


if __name__ == "__main__":
    print("Main Statistic")
    # Creating process
    mutex = Lock()
    getting_data = Thread(target=get_data_thread, args=(mutex,), daemon=True)
    getting_data.start()
    Process1, Child_Process = mp.Pipe()
    # starting()
    main_window_process = mp.Process(target=main, daemon=False, args=(Child_Process,))
    main_window_process.start()
    connection_thread = Thread(target=connection, daemon=True, args=(Process1,))
    connection_thread.start()
    print("Started app")

    # Главный процесс и главный поток, тут проверяем информацию по сигналу для отрисовки приложения (доп поток изменяет)
    while True:
        sleep(0.1)
        if signal_to_draw == 1 and main_window_process.is_alive():
            get_data = 1
            draw_figures(main_window_process)
            get_data = 0
            signal_to_draw = 0
        if not main_window_process.is_alive():
            rigol.device.write(":RUN")
            sys.exit()
