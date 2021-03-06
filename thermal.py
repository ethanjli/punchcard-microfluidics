import sys
import time
from datetime import datetime

import numpy as np
from simple_pid import PID


# Components

class ProcessVariable(object):
    def read(self, unit=None):
        return None


class Thermistor(ProcessVariable):
    def __init__(
        self, reference_pin, thermistor_pin, bias_resistance=1962,
        A=1.125308852122e-03, B=2.34711863267e-04, C=8.5663516e-08
    ):
        self.reference_pin = reference_pin
        self.thermistor_pin = thermistor_pin
        self.reading = None
        self.referenced_reading = None
        self.bias_resistance = bias_resistance
        self.A = A
        self.B = B
        self.C = C

    def calibrate_steinhart_hart(self, temperature_resistance_pairs, unit='C'):
        (temperatures, resistances) = zip(*temperature_resistance_pairs)

        T = np.array(temperatures)
        if unit == 'K':
            pass
        elif unit == 'C':
            T = T + 273.15
        else:
            raise ValueError('Unknown temperature unit: {}'.format(unit))
        b = 1 / T

        R = np.expand_dims(np.array(resistances), axis=1)
        A = np.hstack((np.ones_like(R), np.log(R), np.power(np.log(R), 3)))
        (coeffs, residuals, rank, singular_values) = np.linalg.lstsq(A, b)
        (self.A, self.B, self.C) = coeffs
        return (coeffs, residuals)

    def read_voltage(self):
        ref = self.reference_pin.read_raw()
        reading = self.thermistor_pin.read_raw()
        self.reading = reading
        self.referenced_reading = ref - reading
        return (self.reading, self.referenced_reading)

    def read_resistance(self):
        (reading, referenced_reading) = self.read_voltage()
        if referenced_reading <= 0:
            return None

        return reading * self.bias_resistance / referenced_reading

    def read(self, unit='C'):
        R = self.read_resistance()
        if R is None:
            return None

        T_Kelvin = float(
            1 / (self.A + self.B * np.log(R) + self.C * np.power(np.log(R), 3))
        )
        if unit == 'K':
            return T_Kelvin
        elif unit == 'C':
            T_Celsius = T_Kelvin - 273.15
            return T_Celsius
        else:
            raise ValueError('Unknown temperature unit: {}'.format(unit))


# Feedback Control

class Control(object):
    """Generic feedback control interface. Implement compute_control_effort.
    """
    def __init__(
        self, initial_setpoint=None, min_output=0.0, max_output=1.0,
        setpoint_reached_epsilon=0, output_increases_process_variable=True,
    ):
        self.setpoint = initial_setpoint
        self.min_output = min_output
        self.max_output = max_output
        self.after_setpoint_change = None
        self.setpoint_reached = False
        self.setpoint_reached_epsilon = setpoint_reached_epsilon
        self.output_increases_pv = output_increases_process_variable
        self.enabled = True

    def reset_setpoint_reached(self):
        self.setpoint_reached = False

    def set_setpoint(self, setpoint):
        if setpoint == self.setpoint:
            return

        self.setpoint = setpoint
        self.reset_setpoint_reached()
        if callable(self.after_setpoint_change):
            self.after_setpoint_change(self.setpoint)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def compute_error(self, measurement):
        if self.setpoint is None or measurement is None:
            return None

        return self.setpoint - measurement

    def compute_setpoint_reached(self, measurement):
        error = self.compute_error(measurement)
        if error is None:
            return None

        return (
            abs(self.compute_error(measurement))
            < self.setpoint_reached_epsilon
        )

    def clamp_output(self, output):
        return max(self.min_output, min(self.max_output, output))

    def compute_control_effort(self, measurement):
        return None

    def update(self, measurement):
        if self.setpoint is None:
            self.setpoint_reached = None
        else:
            setpoint_reached = self.compute_setpoint_reached(measurement)
            if setpoint_reached:
                self.setpoint_reached = True


class InfiniteGainControl(Control):
    """Toggle control effort by comparing measurement with setpoint.

    Equivalent to proportional control with infinite gain.
    """
    def compute_control_effort(self, measurement):
        if self.setpoint is None or not self.enabled:
            return 0
        if measurement is None:
            return None

        error = self.compute_error(measurement)
        if self.output_increases_pv:
            if error > 0:
                return self.max_output
            else:
                return self.min_output
        else:
            if error < 0:
                return self.max_output
            else:
                return self.min_output


class ProportionalControl(Control):
    """Scale control effort linearly with error."""
    def __init__(self, gain, *args, **kwargs):
        self.gain = gain
        super().__init__(*args, **kwargs)

    def compute_control_effort(self, measurement):
        if self.setpoint is None or not self.enabled:
            return 0
        if measurement is None:
            return None

        error = self.compute_error(measurement)
        gain = self.gain if self.output_increases_pv else -self.gain
        return self.clamp_output(gain * error)


class PIDControl(Control):
    """Comute control effort using PID algorithm."""
    def __init__(
        self, kp, ki, kd, *args,
        sample_time=None, proportional_on_measurement=False, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.pid = PID(
            Kp=kp, Ki=ki, Kd=kd, setpoint=self.setpoint,
            sample_time=sample_time,
            output_limits=(self.min_output, self.max_output),
            auto_mode=True,
            proportional_on_measurement=proportional_on_measurement
        )

    def set_setpoint(self, setpoint):
        super().set_setpoint(setpoint)
        if self.setpoint is not None:
            self.pid.setpoint = self.setpoint

    def compute_control_effort(self, measurement):
        if measurement is None:
            return None
        if self.setpoint is None or not self.enabled:
            return 0

        return self.pid(measurement)


# Control

class ControllerReporter(object):
    def __init__(
        self, interval=0.5,
        process_variable='Temperature', process_variable_units='deg C',
        control_efforts=('Thermal Control Effort',),
        file_prefix='', file_suffix=''
    ):
        self.interval = interval
        self.start_time = None
        self.next_report_index = None
        self.enabled = False
        self.process_variable = process_variable
        self.process_variable_units = process_variable_units
        self.control_efforts = control_efforts
        self.file_prefix = file_prefix
        self.file_suffix = file_suffix
        self.file = None

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def reset(self):
        self.start_time = None
        self.next_report_index = None
        self.close_report()
        self.enable()

    def close_report(self):
        if self.file is not None:
            self.file.close()
            self.file = None

    def update(
        self, process_variable, setpoint=None, setpoint_reached=None,
        control_efforts=[]
    ):
        if not self.enabled or process_variable is None:
            return

        current_time = time.time()
        if self.next_report_index is None:  # First report received!
            self.start_time = current_time
            self.next_report_index = 0
            self.open_report()
            self.report_header()
        next_report_time = (
            self.next_report_index * self.interval + self.start_time
        )
        if current_time >= next_report_time:
            self.report(
                current_time, process_variable,
                setpoint=setpoint, setpoint_reached=setpoint_reached,
                control_efforts=control_efforts
            )
            self.next_report_index += 1

    def open_report(self):
        filename = self.generate_filename()
        print('Logging to {}...'.format(filename))
        self.file = open(filename, 'w')

    def report_header(self):
        header_string = (
            'Time (s),'
            '{} ({}),Setpoint ({}),Error ({}),'
            '{}Setpoint Reached'
        ).format(
            self.process_variable, self.process_variable_units,
            self.process_variable_units, self.process_variable_units,
            '{},'.format(','.join(self.control_efforts))
            if self.control_efforts else ''
        )
        print(header_string, file=self.file)
        self.file.flush()

    def generate_timestamp(self, time):
        return datetime.fromtimestamp(time).isoformat(sep='_')

    def generate_filename(self):
        return '{}{}{}.csv'.format(
            self.file_prefix,
            self.generate_timestamp(self.start_time),
            self.file_suffix
        )

    def report(
        self, report_time, process_variable,
        setpoint=None, setpoint_reached=None, control_efforts=[]
    ):
        error = None
        if setpoint is not None:
            error = setpoint - process_variable

        control_efforts_string = self.format_control_efforts(control_efforts)
        report_string = '{:.2f},{:.1f},{},{},{}{}'.format(
            report_time - self.start_time,
            process_variable,
            '{:.1f}'.format(setpoint) if setpoint is not None else '',
            '{:.1f}'.format(error) if error is not None else '',
            '{},'.format(control_efforts_string)
            if control_efforts_string else '',
            setpoint_reached if setpoint_reached is not None else ''
        )

        print(report_string, file=self.file)
        self.file.flush()

    def format_control_efforts(self, control_efforts):
        formatted_control_efforts = [
            '{:.2f}'.format(float(effort)) if effort is not None else ''
            for effort in control_efforts
        ]
        return ','.join(formatted_control_efforts)


class ControllerPrinter(ControllerReporter):
    def __init__(
        self, interval=15, control_efforts=('Thermal Control Effort',),
    ):
        super().__init__(interval=interval, control_efforts=control_efforts)

    def close_report(self):
        pass

    def open_report(self):
        self.file = sys.stdout


class Controller(object):
    def __init__(self, controls, outputs, process_variable, reporters=[]):
        self.controls = [control for control in controls]
        self.outputs = [output for output in outputs]
        self.process_variable = process_variable
        self.reporters = [reporter for reporter in reporters]
        self.resettable_reporters = [reporter for reporter in reporters]
        self.disableable_reporters = [reporter for reporter in reporters]

        for reporter in self.reporters:
            if reporter is not None:
                reporter.control_efforts = self.output_effort_names

    @property
    def output_effort_names(self):
        return (
            'Output {} Effort'.format(i) for (i, _) in enumerate(self.outputs)
        )

    def set_setpoint(self, setpoint):
        for control in self.controls:
            control.set_setpoint(setpoint)

    @property
    def setpoint_reached(self):
        return self.controls[0].setpoint_reached

    def reset(self):
        self.reset_reporters()
        self.reset_controls()

    def reset_reporters(self):
        for reporter in self.resettable_reporters:
            if reporter is not None:
                reporter.reset()

    def enable_reporters(self):
        for reporter in self.disableable_reporters:
            if reporter is not None:
                reporter.enable()

    def disable_reporters(self):
        for reporter in self.disableable_reporters:
            if reporter is not None:
                reporter.disable()

    def reset_controls(self):
        for control in self.controls:
            control.reset_setpoint_reached()

    def update(self):
        process_variable = self.process_variable.read()
        if process_variable is None:
            return (None, (None,))

        control_efforts = self.compute_control_efforts(process_variable)
        for (output, control_effort) in zip(self.outputs, control_efforts):
            output.set_state(control_effort)

        self.report(process_variable, control_efforts)
        return (process_variable, control_efforts)

    def compute_control_efforts(self, process_variable):
        for control in self.controls:
            control.update(process_variable)
        return [
            control.compute_control_effort(process_variable)
            for control in self.controls
        ]

    def report(self, process_variable, control_efforts):
        for reporter in self.reporters:
            if reporter is not None:
                reporter.update(
                    process_variable, setpoint=self.controls[0].setpoint,
                    setpoint_reached=self.controls[0].setpoint_reached,
                    control_efforts=control_efforts
                )


# Lysis Heater Thermal Module Controllers

class HeaterController(Controller):
    def __init__(
        self, process_variable,
        heater_control, heater,
        additional_controls=[], additional_outputs=[],
        file_reporter=None, print_reporter=None
    ):
        super().__init__(
            [heater_control] + additional_controls,
            [heater] + additional_outputs,
            process_variable,
            [file_reporter, print_reporter]
        )
        self.heater = heater
        self.heater_control = heater_control
        self.file_reporter = file_reporter
        self.print_reporter = print_reporter

    @property
    def output_effort_names(self):
        return ('Heater PWM Duty',)


class HeaterFanController(HeaterController):
    def __init__(
            self, process_variable,
            heater_control, heater,
            fan_control, fan, fan_setpoint_offset=0.0,
            additional_controls=[], additional_outputs=[],
            **kwargs
    ):
        super().__init__(
            process_variable, heater_control, heater,
            additional_controls=[fan_control] + additional_controls,
            additional_outputs=[fan] + additional_outputs,
            **kwargs
        )
        self.fan = fan
        self.fan_control = fan_control
        self.fan_setpoint_offset = fan_setpoint_offset

    @property
    def output_effort_names(self):
        return ('Heater PWM Duty', 'Fan PWM Duty')

    def set_setpoint(self, setpoint):
        super().set_setpoint(setpoint)
        if setpoint is not None:
            self.fan_control.set_setpoint(setpoint + self.fan_setpoint_offset)

    @property
    def setpoint_reached(self):
        return self.heater_control.setpoint_reached
