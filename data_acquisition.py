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
sys.path.append(r"C:\Users\Mika Music\PycharmProjects\PAX1000-controller")
from pax1000_controller import *

result = None

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
        self.image_display = ImageDisplay(0)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.__measuring_thread = MeasuringThread()
        self.__measuring_thread.start()
        self.__rep_rate = 100
        time.sleep(1)

        self.result = np.empty((15, 256))
        self.counter_gs = 0

        while self._is_result_none():
            print('PAX1000 starting up')

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
            self.result[6][self.counter_gs] = measurement["s0"]
            self.result[7][self.counter_gs] = measurement["s1"]
            self.result[8][self.counter_gs] = measurement["s2"]
            self.result[9][self.counter_gs] = measurement["s3"]
            self.result[10][self.counter_gs] = measurement["dop"]
            self.result[11][self.counter_gs] = measurement["dolp"]
            self.result[12][self.counter_gs] = measurement["docp"]
            self.result[13][self.counter_gs] = measurement["power_pol"]
            self.result[14][self.counter_gs] = measurement["power_upol"]

            print(f'measurement {self.counter_gs+1}/256')

            self.counter_gs += 1
            self.after(rep_rate, self.get_data, self.__rep_rate)
        else:
            global result
            result = self.result.copy()
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

fig, ax = plt.subplots()
plt.plot(ls, result[2], label='S0')
plt.plot(ls, result[3], label='S1')
plt.plot(ls, result[4], label='S2')
plt.plot(ls, result[5], label='S3')
fig.suptitle('Stokes Parameter')
fig.supxlabel('grayscale value')
fig.supylabel('P[W]')
plt.legend()
fig.tight_layout()
plt.show()

fig, ax = plt.subplots()
plt.plot(ls, result[6], label='S0')
plt.plot(ls, result[7], label='S1')
plt.plot(ls, result[8], label='S2')
plt.plot(ls, result[9], label='S3')
fig.suptitle('normalized Stokes Parameter')
fig.supxlabel('grayscale value')
fig.supylabel('arb. value')
plt.legend()
fig.tight_layout()
plt.show()

fig, ax = plt.subplots()
plt.plot(ls, result[10])
fig.suptitle('Degree of Polarization (DOP)')
fig.supxlabel('grayscale value')
fig.supylabel('arb. value')
fig.tight_layout()
plt.show()

fig, ax = plt.subplots()
plt.plot(ls, result[11])
fig.suptitle('Degree of Linear Polarization (DOLP)')
fig.supxlabel('grayscale value')
fig.supylabel('arb. value')
fig.tight_layout()
plt.show()

fig, ax = plt.subplots()
plt.plot(ls, result[12])
fig.suptitle('Degree of Circular Polarization (DOCP)')
fig.supxlabel('grayscale value')
fig.supylabel('arb. value')
fig.tight_layout()
plt.show()

fig, ax = plt.subplots()
plt.plot(ls, result[11], label='DOLP')
plt.plot(ls, result[12], label='DOCP')
fig.suptitle('DOLP and DOCP')
fig.supxlabel('grayscale value')
fig.supylabel('arb. value')
plt.legend()
fig.tight_layout()
plt.show()

fig, ax = plt.subplots()
plt.plot(ls, result[13])
fig.suptitle('Polarized Power')
fig.supxlabel('grayscale value')
fig.supylabel('P[W]')
fig.tight_layout()
plt.show()

fig, ax = plt.subplots()
plt.plot(ls, result[14])
fig.suptitle('Unpolarized Power')
fig.supxlabel('grayscale value')
fig.supylabel('P[W]')
fig.tight_layout()
plt.show()

fig, ax = plt.subplots()
plt.plot(ls, result[13], label='P_pol')
plt.plot(ls, result[14], label='P_upol')
fig.suptitle('Polarized Power und Unpolarized Power')
fig.supxlabel('grayscale value')
fig.supylabel('P[W]')
plt.legend()
fig.tight_layout()
plt.show()