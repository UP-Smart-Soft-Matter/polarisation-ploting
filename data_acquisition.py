import sys
import time
from PIL.Image import fromarray
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
import screeninfo
import threading
sys.path.append(r"C:\Users\SSMAdmin\PycharmProjects\PAX1000-controller")
from pax1000_controller import *
import  faulthandler

faulthandler.enable()

result_dict_list = None

def init_pax():
    while True:
        try:
            pax = PAX1000()
            return pax
        except Exception:
            messagebox.showerror("Error", "No PAX 1000 found, please connect device and try again")
            continue


class ImageDisplay(tk.Toplevel):
    def __init__(self, monitor: int):
        assert isinstance(monitor, int) and monitor >= 0, "Monitor must be a non-negative integer!"

        super().__init__()

        monitors = screeninfo.get_monitors()


        if len(monitors) <= monitor:
            raise Exception(f"Monitor index {monitor} is out of range. Found {len(monitors)} monitors.")

        # Select the specified monitor
        selected_monitor = monitors[monitor]
        self.width, self.height = selected_monitor.width, selected_monitor.height

        self.geometry(f"{self.width}x{self.height}+{selected_monitor.x}+{selected_monitor.y}")
        self.configure(background='black')

        self.overrideredirect(True)

        # Initialize the label to None
        self.label = None

    def show_image(self, image_object):
        assert isinstance(image_object, Image.Image), "Image must be a PIL Image object"

        photo = ImageTk.PhotoImage(image_object)

        if self.label is None:
            # Create a label to hold the image
            self.label = tk.Label(self, image=photo)
            self.label.image = photo  # Keep a reference to avoid garbage collection
            self.label.pack()
        else:
            self.__update_image(photo)

    def __update_image(self, photo):
        assert isinstance(photo, ImageTk.PhotoImage), "Image must be a PhotoImage object"

        # Update the image in the existing label
        self.label.configure(image=photo)
        self.label.image = photo  # Update the reference to avoid garbage collection

    class NoSecondMonitorError(Exception):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.image_display = ImageDisplay(1)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.__measuring_thread = MeasuringThread()
        self.__measuring_thread.start()
        self.__rep_rate = 100
        time.sleep(1)

        self.result = np.empty((11, 256))
        self.counter_gs = 0

        print('PAX1000 starting up')
        while self._is_result_none():
            pass
        print('PAX1000 start up finished')

        self.get_data(self.__rep_rate)

    def close(self):
        with self.__measuring_thread.kill_flag_lock:
            self.__measuring_thread.kill_flag = True
        self.destroy()

    def get_data(self, rep_rate):
        if self.counter_gs <= 255:
            img = fromarray(np.full((self.image_display.height, self.image_display.width), self.counter_gs, dtype=np.uint8))
            self.image_display.show_image(img)

            with self.__measuring_thread.result_dict_lock:
                measurement = self.__measuring_thread.result_dict

            self.result[0][self.counter_gs] = measurement["azimuth"]
            self.result[1][self.counter_gs] = measurement["ellipticity"]
            self.result[2][self.counter_gs] = measurement["S0"]
            self.result[3][self.counter_gs] = measurement["S1"]
            self.result[4][self.counter_gs] = measurement["S2"]
            self.result[5][self.counter_gs] = measurement["S3"]
            self.result[6][self.counter_gs] = measurement["dop"]
            self.result[7][self.counter_gs] = measurement["dolp"]
            self.result[8][self.counter_gs] = measurement["docp"]
            self.result[9][self.counter_gs] = measurement["power_pol"]
            self.result[10][self.counter_gs] = measurement["power_upol"]

            print(f'measurement {self.counter_gs+1}/256')

            self.counter_gs += 1
            self.after(rep_rate, self.get_data, self.__rep_rate)
        else:
            global result_dict_list
            result_dict_list = self.result.copy()
            self.close()

    def _is_result_none(self):
        with (self.__measuring_thread.result_dict_lock):
            result = self.__measuring_thread.result_dict

        time.sleep(0.2)

        if result is None:
            return True
        else:
            return False


class MeasuringThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.kill_flag = False
        self.kill_flag_lock = threading.Lock()

        self.result_dict = None
        self.result_dict_lock = threading.Lock()

        self.__pax = None

    def run(self):
        self.__pax = init_pax()
        while not self.kill_flag:
            measurement = self.__pax.measure()
            with self.result_dict_lock:
                self.result_dict = measurement
        self.__pax.close()


app = App()
app.mainloop()

ls = np.linspace(0,256, 256)

azimuth = []
for i, datapoint in enumerate(result_dict_list[0]):
    datapoint = (datapoint - 90) * (- 1)
    azimuth.append(datapoint)

fig3, ax3 = plt.subplots()
plt.plot(ls, azimuth)
fig3.suptitle('Azimuth')
fig3.supxlabel('grayscale value')
fig3.supylabel('angle[°]')
fig3.tight_layout()
plt.show()

fig1, ax1 = plt.subplots()
plt.plot(ls, result_dict_list[2], label='S0')
plt.plot(ls, result_dict_list[3], label='S1')
plt.plot(ls, result_dict_list[4], label='S2')
plt.plot(ls, result_dict_list[5], label='S3')
fig1.suptitle('Stokes Parameter')
fig1.supxlabel('grayscale value')
fig1.supylabel('P[W]')
plt.legend()
fig1.tight_layout()
plt.show()

if result_dict_list[2].all() != 0:
    s0 = np.full(255, 1)
    s1 = result_dict_list[3]/result_dict_list[2]
    s2 = result_dict_list[4]/result_dict_list[2]
    s3 = result_dict_list[5]/result_dict_list[2]

    fig2, ax2 = plt.subplots()
    plt.plot(ls, s0, label='S0')
    plt.plot(ls, s1, label='S1')
    plt.plot(ls, s2, label='S2')
    plt.plot(ls, s3, label='S3')
    fig2.suptitle('normalized Stokes Parameter')
    fig2.supxlabel('grayscale value')
    fig2.supylabel('arb. value')
    plt.legend()
    fig2.tight_layout()
    plt.show()

fig3, ax3 = plt.subplots()
plt.plot(ls, result_dict_list[6])
fig3.suptitle('Degree of Polarization (DOP)')
fig3.supxlabel('grayscale value')
fig3.supylabel('arb. value')
fig3.tight_layout()
plt.show()

fig4, ax4 = plt.subplots()
plt.plot(ls, result_dict_list[7])
fig4.suptitle('Degree of Linear Polarization (DOLP)')
fig4.supxlabel('grayscale value')
fig4.supylabel('arb. value')
fig4.tight_layout()
plt.show()

fig5, ax = plt.subplots()
plt.plot(ls, result_dict_list[8])
fig5.suptitle('Degree of Circular Polarization (DOCP)')
fig5.supxlabel('grayscale value')
fig5.supylabel('arb. value')
fig5.tight_layout()
plt.show()

fig6, ax6 = plt.subplots()
plt.plot(ls, result_dict_list[7], label='DOLP')
plt.plot(ls, result_dict_list[8], label='DOCP')
fig6.suptitle('DOLP and DOCP')
fig6.supxlabel('grayscale value')
fig6.supylabel('arb. value')
plt.legend()
fig6.tight_layout()
plt.show()

fig7, ax7 = plt.subplots()
plt.plot(ls, result_dict_list[9])
fig7.suptitle('Polarized Power')
fig7.supxlabel('grayscale value')
fig7.supylabel('P[W]')
fig7.tight_layout()
plt.show()

fig8, ax8 = plt.subplots()
plt.plot(ls, result_dict_list[10])
fig8.suptitle('Unpolarized Power')
fig8.supxlabel('grayscale value')
fig8.supylabel('P[W]')
fig8.tight_layout()
plt.show()

fig9, ax9 = plt.subplots()
plt.plot(ls, result_dict_list[9], label='P_pol')
plt.plot(ls, result_dict_list[10], label='P_upol')
fig9.suptitle('Polarized Power und Unpolarized Power')
fig9.supxlabel('grayscale value')
fig9.supylabel('P[W]')
plt.legend()
fig9.tight_layout()
plt.show()
