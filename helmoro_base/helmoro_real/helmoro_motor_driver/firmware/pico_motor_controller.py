"""
HelMoRo Pico 2W Motor Controller Firmware (MicroPython)

Hardware:
  - 2x BTS7960B H-Bridge drivers (left + right side)
  - 2x Quadrature encoders (one per side)
  - Raspberry Pi Pico 2W

Wiring (adjust GPIO pins to match your setup):
  BTS7960B Left:   RPWM=GP0, LPWM=GP1, R_EN=GP2, L_EN=GP3
  BTS7960B Right:  RPWM=GP4, LPWM=GP5, R_EN=GP6, L_EN=GP7
  Encoder Left:    A=GP10, B=GP11
  Encoder Right:   A=GP12, B=GP13

Protocol (JSON over USB serial at 115200 baud):
  RX: {"cmd": [left_vel, right_vel]}     # target m/s
  TX: {"enc": [left_pos, right_pos], "vel": [left_vel, right_vel]}

Upload this file as main.py to the Pico 2W.
"""

import json
import sys
import time
from machine import Pin, PWM


# ==========================================================================
# CONFIGURATION — adjust these to match your hardware
# ==========================================================================

# Wheel geometry
WHEEL_RADIUS = 0.045          # meters
WHEEL_CIRCUMFERENCE = 2.0 * 3.14159265 * WHEEL_RADIUS
ENCODER_CPR = 1320            # Counts per revolution (encoder CPR × gear ratio)

# PID gains (tune these for your motors)
KP = 1.0
KI = 0.5
KD = 0.05

# PWM
PWM_FREQ = 20000              # 20 kHz — above audible range
MAX_DUTY = 65535              # 16-bit PWM on Pico
MIN_DUTY = 3000               # Dead zone — minimum PWM to overcome friction

# Control loop
LOOP_RATE_HZ = 50             # PID loop frequency
LOOP_PERIOD = 1.0 / LOOP_RATE_HZ
CMD_TIMEOUT = 0.5             # seconds — stop if no command received

# GPIO pin assignments
LEFT_RPWM_PIN = 0
LEFT_LPWM_PIN = 1
LEFT_REN_PIN = 2
LEFT_LEN_PIN = 3

RIGHT_RPWM_PIN = 4
RIGHT_LPWM_PIN = 5
RIGHT_REN_PIN = 6
RIGHT_LEN_PIN = 7

LEFT_ENC_A_PIN = 10
LEFT_ENC_B_PIN = 11
RIGHT_ENC_A_PIN = 12
RIGHT_ENC_B_PIN = 13


# ==========================================================================
# BTS7960B H-BRIDGE DRIVER
# ==========================================================================

class BTS7960:
    """Single BTS7960B H-Bridge motor driver."""

    def __init__(self, rpwm_pin, lpwm_pin, ren_pin, len_pin):
        self.rpwm = PWM(Pin(rpwm_pin))
        self.lpwm = PWM(Pin(lpwm_pin))
        self.rpwm.freq(PWM_FREQ)
        self.lpwm.freq(PWM_FREQ)

        self.r_en = Pin(ren_pin, Pin.OUT)
        self.l_en = Pin(len_pin, Pin.OUT)

        # Enable both half-bridges
        self.r_en.value(1)
        self.l_en.value(1)

        self.stop()

    def set_speed(self, duty):
        """
        Set motor speed.
        duty > 0: forward, duty < 0: backward.
        duty range: -MAX_DUTY to +MAX_DUTY
        """
        duty = int(max(-MAX_DUTY, min(MAX_DUTY, duty)))

        if duty > 0:
            self.rpwm.duty_u16(duty)
            self.lpwm.duty_u16(0)
        elif duty < 0:
            self.rpwm.duty_u16(0)
            self.lpwm.duty_u16(-duty)
        else:
            self.stop()

    def stop(self):
        self.rpwm.duty_u16(0)
        self.lpwm.duty_u16(0)

    def disable(self):
        self.stop()
        self.r_en.value(0)
        self.l_en.value(0)


# ==========================================================================
# QUADRATURE ENCODER (interrupt-driven)
# ==========================================================================

class Encoder:
    """Quadrature encoder reader using GPIO interrupts."""

    def __init__(self, pin_a, pin_b):
        self._pin_a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self._pin_b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self._count = 0
        self._last_count = 0
        self._velocity = 0.0        # m/s
        self._last_time = time.ticks_us()

        # Attach interrupts on channel A (2x resolution)
        self._pin_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._isr)

    def _isr(self, pin):
        if self._pin_a.value() == self._pin_b.value():
            self._count += 1
        else:
            self._count -= 1

    def get_count(self):
        return self._count

    def get_position_rad(self):
        """Get position in radians."""
        return (self._count / ENCODER_CPR) * 2.0 * 3.14159265

    def get_position_m(self):
        """Get position in meters (linear distance)."""
        return (self._count / ENCODER_CPR) * WHEEL_CIRCUMFERENCE

    def compute_velocity(self):
        """
        Compute velocity in m/s.
        Call this at a fixed rate (LOOP_RATE_HZ).
        """
        now = time.ticks_us()
        dt = time.ticks_diff(now, self._last_time) / 1_000_000.0  # seconds
        if dt <= 0:
            return self._velocity

        delta_count = self._count - self._last_count
        revolutions = delta_count / ENCODER_CPR
        self._velocity = (revolutions * WHEEL_CIRCUMFERENCE) / dt

        self._last_count = self._count
        self._last_time = now
        return self._velocity

    def reset(self):
        self._count = 0
        self._last_count = 0
        self._velocity = 0.0


# ==========================================================================
# PID CONTROLLER
# ==========================================================================

class PID:
    """Simple PID controller."""

    def __init__(self, kp=KP, ki=KI, kd=KD, output_limit=MAX_DUTY):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limit = output_limit
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, setpoint, measured, dt):
        error = setpoint - measured

        self._integral += error * dt
        # Anti-windup
        self._integral = max(-self.output_limit, min(self.output_limit, self._integral))

        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error

        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(-self.output_limit, min(self.output_limit, output))

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0


# ==========================================================================
# SERIAL COMMUNICATION
# ==========================================================================

def read_serial_command():
    """
    Non-blocking read of a JSON command from USB serial (stdin).
    Returns (left_vel, right_vel) or None.
    """
    try:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip()
            if line:
                data = json.loads(line)
                if 'cmd' in data and len(data['cmd']) >= 2:
                    return (float(data['cmd'][0]), float(data['cmd'][1]))
    except Exception:
        pass
    return None


def send_serial_response(enc_left, enc_right, vel_left, vel_right):
    """Send encoder + velocity data as JSON to USB serial (stdout)."""
    resp = {
        "enc": [round(enc_left, 4), round(enc_right, 4)],
        "vel": [round(vel_left, 4), round(vel_right, 4)],
    }
    print(json.dumps(resp))


# ==========================================================================
# MAIN CONTROL LOOP
# ==========================================================================

def main():
    # Initialize hardware
    motor_left = BTS7960(LEFT_RPWM_PIN, LEFT_LPWM_PIN, LEFT_REN_PIN, LEFT_LEN_PIN)
    motor_right = BTS7960(RIGHT_RPWM_PIN, RIGHT_LPWM_PIN, RIGHT_REN_PIN, RIGHT_LEN_PIN)

    enc_left = Encoder(LEFT_ENC_A_PIN, LEFT_ENC_B_PIN)
    enc_right = Encoder(RIGHT_ENC_A_PIN, RIGHT_ENC_B_PIN)

    pid_left = PID()
    pid_right = PID()

    target_left = 0.0   # m/s
    target_right = 0.0  # m/s
    last_cmd_time = time.ticks_ms()

    print('{"status": "ready"}')

    while True:
        loop_start = time.ticks_us()

        # ── Read command from Jetson ─────────────────────────────────
        try:
            line = sys.stdin.readline()
            if line:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    if 'cmd' in data and len(data['cmd']) >= 2:
                        target_left = float(data['cmd'][0])
                        target_right = float(data['cmd'][1])
                        last_cmd_time = time.ticks_ms()
        except Exception:
            pass

        # ── Command timeout safety ───────────────────────────────────
        if time.ticks_diff(time.ticks_ms(), last_cmd_time) > CMD_TIMEOUT * 1000:
            target_left = 0.0
            target_right = 0.0
            pid_left.reset()
            pid_right.reset()

        # ── Read encoders ────────────────────────────────────────────
        vel_left = enc_left.compute_velocity()
        vel_right = enc_right.compute_velocity()

        # ── PID control ──────────────────────────────────────────────
        duty_left = pid_left.compute(target_left, vel_left, LOOP_PERIOD)
        duty_right = pid_right.compute(target_right, vel_right, LOOP_PERIOD)

        # Apply dead zone
        if abs(target_left) < 0.01:
            duty_left = 0
            pid_left.reset()
        elif abs(duty_left) < MIN_DUTY and duty_left != 0:
            duty_left = MIN_DUTY if duty_left > 0 else -MIN_DUTY

        if abs(target_right) < 0.01:
            duty_right = 0
            pid_right.reset()
        elif abs(duty_right) < MIN_DUTY and duty_right != 0:
            duty_right = MIN_DUTY if duty_right > 0 else -MIN_DUTY

        # ── Drive motors ─────────────────────────────────────────────
        motor_left.set_speed(int(duty_left))
        motor_right.set_speed(int(duty_right))

        # ── Send feedback to Jetson ──────────────────────────────────
        send_serial_response(
            enc_left.get_position_rad(),
            enc_right.get_position_rad(),
            vel_left,
            vel_right,
        )

        # ── Fixed-rate loop timing ───────────────────────────────────
        elapsed = time.ticks_diff(time.ticks_us(), loop_start) / 1_000_000.0
        sleep_time = LOOP_PERIOD - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        # Emergency stop on Ctrl+C
        BTS7960(LEFT_RPWM_PIN, LEFT_LPWM_PIN, LEFT_REN_PIN, LEFT_LEN_PIN).disable()
        BTS7960(RIGHT_RPWM_PIN, RIGHT_LPWM_PIN, RIGHT_REN_PIN, RIGHT_LEN_PIN).disable()
