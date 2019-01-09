import tkinter as tk
import time
from datetime import datetime

import Adafruit_ADS1x15

import gpio

heater = gpio.DigitalPin(4)
adc = Adafruit_ADS1x15.ADS1115()
ref_voltage = gpio.AnalogPin(adc, 3)
thermistor = gpio.Thermistor(
    ref_voltage, gpio.AnalogPin(adc, 0),
    bias_resistance=1960,
    A=0.0010349722285233954,
    B=0.00022717987892035313,
    C=3.008424040777896e-07
)
temperature_report_interval = 0.5  # s
temperature_print_interval = int(15 / 0.5)  # number of reports between prints
control_loop_interval = 50  # ms
setpoint_reached_epsilon = 0.5  # deg C


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        # self.pack()
        self.grid()
        self.create_widgets()

        self.heater = heater
        self.heater_setpoint_1 = gpio.BinaryState()
        self.heater_setpoint_1.after_state_change = \
            self.on_heater_setpoint_1_state_change
        self.heater_setpoint_2 = gpio.BinaryState()
        self.heater_setpoint_2.after_state_change = \
            self.on_heater_setpoint_2_state_change
        self.last_temperature = None
        self.first_temperature_time = None
        self.last_temperature_index = None
        self.reporting_temperature = False
        self.setpoint_reached = False
        self.report_file = None

        self.updater()

    # define methods #
    def reset_temperature_reporting(self):
        self.last_temperature_index = None
        self.first_temperature_time = None
        self.reporting_temperature = True
        self.setpoint_reached = False
        if self.report_file is not None:
            self.report_file.close()
            self.report_file = None

    def on_heater_setpoint_1_state_change(self, state):
        if state:
            self.btn_heater_setpoint_1.config(relief='sunken')
            print('Heater setpoint 1 enabled!')
        else:
            self.btn_heater_setpoint_1.config(relief='raised')
            self.btn_heater_setpoint_1.config(fg='black')
            print('Heater setpoint 1 disabled!')
        self.reset_temperature_reporting()

    def on_heater_setpoint_2_state_change(self, state):
        if state:
            self.btn_heater_setpoint_2.config(relief='sunken')
            print('Heater setpoint 2 enabled!')
        else:
            self.btn_heater_setpoint_2.config(relief='raised')
            self.btn_heater_setpoint_2.config(fg='black')
            print('Heater setpoint 2 disabled!')
        self.reset_temperature_reporting()

    def toggle_heater_setpoint_1(self):
        self.heater_setpoint_1.toggle()
        if self.heater_setpoint_1.state:
            self.heater_setpoint_2.turn_off()

    def toggle_heater_setpoint_2(self):
        self.heater_setpoint_2.toggle()
        if self.heater_setpoint_2.state:
            self.heater_setpoint_1.turn_off()

    def updater(self):
        setpoint = None
        if self.heater_setpoint_1.state:
            setpoint = float(self.entry_heater_setpoint_1.get())
            btn_heater_setpoint = self.btn_heater_setpoint_1
        elif self.heater_setpoint_2.state:
            setpoint = float(self.entry_heater_setpoint_2.get())
            btn_heater_setpoint = self.btn_heater_setpoint_2

        temperature = thermistor.read()
        if temperature is not None:
            self.entry_heater_temp.config(text=format(temperature, '.2f'))

            if setpoint is not None:
                if temperature < setpoint:
                    btn_heater_setpoint.config(fg='red')
                    heater.turn_on()
                else:
                    btn_heater_setpoint.config(fg='blue')
                    heater.turn_off()
                if abs(temperature - setpoint) < setpoint_reached_epsilon:
                    self.setpoint_reached = True
                self.report_temperature(setpoint, temperature)
            else:
                self.btn_heater_setpoint_1.config(fg='black')
                self.btn_heater_setpoint_2.config(fg='black')
                heater.turn_off()

        else:
            self.entry_heater_temp.config(text='-')

        self.after(control_loop_interval, self.updater)

    def report_temperature(self, heater_setpoint, temperature):
        if not self.reporting_temperature:
            return

        if heater_setpoint is None:
            error = None
        else:
            error = heater_setpoint - temperature

        current_time = time.time()
        if (
            self.last_temperature_index is None
            or (
                current_time - self.first_temperature_time
                - self.last_temperature_index * temperature_report_interval
            ) > 0
        ):
            if self.first_temperature_time is None:
                self.first_temperature_time = current_time
                self.last_temperature_index = 0
                header_string = (
                    'Time (s),'
                    'Temperature (deg C),Setpoint (deg C),Error (deg C),'
                    'Heater PWM Duty,Setpoint Reached'
                )
                starting_timestamp = (
                    datetime.fromtimestamp(self.first_temperature_time)
                    .isoformat(sep='_')
                )
                filename = 'guipunchcard_{}_setpoint{:.1f}.csv'.format(
                    starting_timestamp, heater_setpoint
                )
                print('Logging to {}...'.format(filename))
                print(header_string)
                self.report_file = open(filename, 'w')
                print(header_string, file=self.report_file)
            report_string = '{:.2f},{:.1f},{:.1f},{:.1f},{},{}'.format(
                current_time - self.first_temperature_time,
                temperature, heater_setpoint, error,
                float(heater.state), self.setpoint_reached
            )
            if self.last_temperature_index % temperature_print_interval == 0:
                print(report_string)
            print(report_string, file=self.report_file)
            self.last_temperature_index += 1

    # create widgets #
    def create_widgets(self):
        # Heater 1 and Heater 2
        self.btn_heater_setpoint_1 = tk.Button(
            self, text="Heater Setpoint 1", fg="black",
            command=self.toggle_heater_setpoint_1
        )
        self.btn_heater_setpoint_2 = tk.Button(
            self, text="Heater Setpoint 2", fg="black",
            command=self.toggle_heater_setpoint_2
        )

        self.entry_heater_setpoint_1 = tk.Entry(self, width=5)
        self.entry_heater_setpoint_2 = tk.Entry(self, width=5)
        self.entry_heater_setpoint_1.insert(0, '90')
        self.entry_heater_setpoint_2.insert(0, '40')
        self.label_heater_temp = tk.Label(self, text='Temperature')
        self.entry_heater_temp = tk.Label(self, text='?', width=8)

        # quit
        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=root.destroy)
        # self.quit.pack(side="left")

        self.btn_heater_setpoint_1.grid(row=1, column=0)
        self.btn_heater_setpoint_2.grid(row=2, column=0)
        self.entry_heater_setpoint_1.grid(row=1, column=1)
        self.entry_heater_setpoint_2.grid(row=2, column=1)
        self.label_heater_temp.grid(row=3, column=0)
        self.entry_heater_temp.grid(row=3, column=1)


# create GUI
root = tk.Tk()
app = Application(master=root)
app.mainloop()

# exit routine
gpio.cleanup()
