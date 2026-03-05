# Pico 2W Motor Controller Firmware

MicroPython firmware for the Raspberry Pi Pico 2W that controls BTS7960B H-Bridge motor drivers with encoder feedback and PID control.

## Hardware Wiring

```
 Pico 2W                    BTS7960B (Left)         BTS7960B (Right)
┌──────────┐               ┌─────────────┐         ┌─────────────┐
│ GP0  ────┼──── RPWM ────►│  RPWM       │         │  RPWM       │◄──── RPWM ──── GP4
│ GP1  ────┼──── LPWM ────►│  LPWM       │         │  LPWM       │◄──── LPWM ──── GP5
│ GP2  ────┼──── R_EN ────►│  R_EN       │         │  R_EN       │◄──── R_EN ──── GP6
│ GP3  ────┼──── L_EN ────►│  L_EN       │         │  L_EN       │◄──── L_EN ──── GP7
│          │               │             │         │             │
│ GP10 ────┼──── ENC_A ◄───│ Left Enc A  │         │ Right Enc A │───► ENC_A ──── GP12
│ GP11 ────┼──── ENC_B ◄───│ Left Enc B  │         │ Right Enc B │───► ENC_B ──── GP13
│          │               └─────────────┘         └─────────────┘
│ GND  ────┼──── GND (shared with BTS7960B + encoders)
│ VBUS ────┼──── 5V to encoder VCC (if needed)
│ USB  ────┼──── USB cable to Jetson Orin Nano (/dev/ttyACM0)
└──────────┘

Motor Power:
  BTS7960B VCC ← Battery (6-27V)
  BTS7960B B+  → Motor +
  BTS7960B B-  → Motor -
```

### Pin Summary

| Pico GPIO | Function           | Connected To          |
|-----------|--------------------|-----------------------|
| GP0       | Left RPWM (fwd)   | BTS7960B Left RPWM   |
| GP1       | Left LPWM (rev)   | BTS7960B Left LPWM   |
| GP2       | Left R_EN          | BTS7960B Left R_EN   |
| GP3       | Left L_EN          | BTS7960B Left L_EN   |
| GP4       | Right RPWM (fwd)  | BTS7960B Right RPWM  |
| GP5       | Right LPWM (rev)  | BTS7960B Right LPWM  |
| GP6       | Right R_EN         | BTS7960B Right R_EN  |
| GP7       | Right L_EN         | BTS7960B Right L_EN  |
| GP10      | Left Encoder A     | Left motor encoder A  |
| GP11      | Left Encoder B     | Left motor encoder B  |
| GP12      | Right Encoder A    | Right motor encoder A |
| GP13      | Right Encoder B    | Right motor encoder B |

## Installation

1. Install MicroPython on Pico 2W:
   - Hold BOOTSEL button and connect USB
   - Copy the `.uf2` file from [micropython.org](https://micropython.org/download/RPI_PICO2_W/)

2. Upload firmware:
   ```bash
   # Using mpremote (install via: pip install mpremote)
   mpremote connect /dev/ttyACM0 cp pico_motor_controller.py :main.py
   mpremote connect /dev/ttyACM0 reset
   ```

3. Or use Thonny IDE to copy `pico_motor_controller.py` as `main.py`

## Configuration

Edit the constants at the top of `pico_motor_controller.py`:

| Parameter     | Default | Description                               |
|---------------|---------|-------------------------------------------|
| WHEEL_RADIUS  | 0.045   | Wheel radius in meters                    |
| ENCODER_CPR   | 1320    | Encoder counts per wheel revolution       |
| KP            | 1.0     | PID proportional gain                     |
| KI            | 0.5     | PID integral gain                         |
| KD            | 0.05    | PID derivative gain                       |
| PWM_FREQ      | 20000   | PWM frequency (Hz)                        |
| LOOP_RATE_HZ  | 50      | PID loop rate                             |
| CMD_TIMEOUT   | 0.5     | Stop motors if no command (seconds)       |

## Serial Protocol

115200 baud, newline-delimited JSON.

**Command (Jetson → Pico):**
```json
{"cmd": [0.5, 0.5]}
```
Left and right target velocities in m/s.

**Response (Pico → Jetson):**
```json
{"enc": [3.14, 3.12], "vel": [0.49, 0.51]}
```
Encoder positions (radians) and measured velocities (m/s).

## PID Tuning

1. Start with `KP=1.0, KI=0.0, KD=0.0`
2. Increase KP until the wheel tracks velocity commands without oscillation
3. Add KI (start 0.1) to eliminate steady-state error
4. Add KD (start 0.01) to reduce overshoot
5. Monitor via: `ros2 topic echo /motors/odom`
