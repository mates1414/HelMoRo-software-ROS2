"""
Pico 2W Serial Communication Interface

Protocol (JSON over USB serial):
  Jetson → Pico:  {"cmd": [left_vel, right_vel]}     # target wheel velocities in m/s
  Pico → Jetson:  {"enc": [lp, rp], "vel": [lv, rv]} # encoder positions (rad) and velocities (m/s)

The Pico 2W handles:
  - PID control loop for each motor
  - PWM generation for BTS7960B H-Bridge drivers
  - Encoder reading (quadrature)
  - Velocity/position computation
"""

import json
import time
import threading
import serial
from typing import Optional, Tuple


class PicoSerial:
    """Serial communication with Pico 2W motor controller."""

    def __init__(
        self,
        port: str = '/dev/ttyACM0',
        baud: int = 115200,
        timeout: float = 0.05,
        max_retries: int = 3,
    ):
        self._port_name = port
        self._baud = baud
        self._timeout = timeout
        self._max_retries = max_retries
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()

        # Latest state from Pico
        self._encoder_positions = [0.0, 0.0]   # [left, right] in radians
        self._wheel_velocities = [0.0, 0.0]    # [left, right] in m/s
        self._last_rx_time = 0.0
        self._connected = False

    def open(self) -> bool:
        """Open serial connection to Pico 2W."""
        try:
            self._serial = serial.Serial(
                port=self._port_name,
                baudrate=self._baud,
                timeout=self._timeout,
            )
            time.sleep(0.5)  # Wait for Pico to reset after serial connect
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            self._connected = True
            return True
        except serial.SerialException as e:
            print(f"[PicoSerial] Failed to open {self._port_name}: {e}")
            self._connected = False
            return False

    def close(self):
        """Close serial connection."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def send_velocity_command(self, left_vel: float, right_vel: float) -> bool:
        """
        Send target wheel velocities to Pico.

        Args:
            left_vel:  Left side target velocity in m/s
            right_vel: Right side target velocity in m/s

        Returns:
            True if command was sent and response received
        """
        if not self._connected or not self._serial:
            return False

        cmd = {"cmd": [round(left_vel, 4), round(right_vel, 4)]}
        return self._send_and_receive(cmd)

    def send_stop(self) -> bool:
        """Emergency stop — zero velocity."""
        return self.send_velocity_command(0.0, 0.0)

    def get_encoder_positions(self) -> Tuple[float, float]:
        """Get latest encoder positions [left, right] in radians."""
        return tuple(self._encoder_positions)

    def get_wheel_velocities(self) -> Tuple[float, float]:
        """Get latest wheel velocities [left, right] in m/s."""
        return tuple(self._wheel_velocities)

    def get_last_rx_age(self) -> float:
        """Seconds since last successful data reception."""
        if self._last_rx_time == 0.0:
            return float('inf')
        return time.time() - self._last_rx_time

    def _send_and_receive(self, cmd: dict) -> bool:
        """Send a JSON command and read the response."""
        with self._lock:
            for attempt in range(self._max_retries):
                try:
                    # Send command
                    msg = json.dumps(cmd) + '\n'
                    self._serial.write(msg.encode('ascii'))
                    self._serial.flush()

                    # Read response line
                    line = self._serial.readline().decode('ascii').strip()
                    if not line:
                        continue

                    data = json.loads(line)
                    self._parse_response(data)
                    return True

                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                except serial.SerialException as e:
                    print(f"[PicoSerial] Serial error: {e}")
                    self._connected = False
                    return False
                except Exception as e:
                    print(f"[PicoSerial] Unexpected error: {e}")
                    continue

        return False

    def _parse_response(self, data: dict):
        """Parse encoder/velocity data from Pico response."""
        if 'enc' in data and len(data['enc']) >= 2:
            self._encoder_positions = [float(data['enc'][0]), float(data['enc'][1])]
        if 'vel' in data and len(data['vel']) >= 2:
            self._wheel_velocities = [float(data['vel'][0]), float(data['vel'][1])]
        self._last_rx_time = time.time()
