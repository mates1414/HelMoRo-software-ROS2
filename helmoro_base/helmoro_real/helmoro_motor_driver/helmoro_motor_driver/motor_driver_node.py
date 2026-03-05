"""
HelMoRo Motor Driver Node — BTS7960B + Pico 2W

Replaces the RoboClaw-based helmoro_motors_node.
Same ROS interface: subscribes cmd_vel, publishes odom + joint_states.

Communicates with Pico 2W over USB serial, which handles:
  - PID control for each motor
  - PWM generation for BTS7960B H-Bridge
  - Quadrature encoder reading
"""

import math
import time

import numpy as np
import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist, TwistStamped, Pose, Point, Quaternion
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from std_msgs.msg import Header

from helmoro_motor_driver.pico_serial import PicoSerial


class MotorDriverNode(Node):
    def __init__(self):
        super().__init__('helmoro_motor_driver_node')

        # ── Declare parameters ───────────────────────────────────────────
        self.declare_parameter('serial_port', '/dev/ttyACM0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('wheel_separation', 0.195)  # meters (track width)
        self.declare_parameter('wheel_radius', 0.045)      # meters
        self.declare_parameter('max_linear_vel', 1.1)       # m/s
        self.declare_parameter('max_angular_vel', 10.5)     # rad/s
        self.declare_parameter('update_rate', 20.0)         # Hz
        self.declare_parameter('cmd_vel_timeout', 0.5)      # seconds
        self.declare_parameter('watchdog_timeout', 1.0)     # seconds — stop if no Pico data

        # ── Read parameters ──────────────────────────────────────────────
        self.serial_port = self.get_parameter('serial_port').value
        self.baud_rate = self.get_parameter('baud_rate').value
        self.wheel_sep = self.get_parameter('wheel_separation').value
        self.wheel_rad = self.get_parameter('wheel_radius').value
        self.max_lin_vel = self.get_parameter('max_linear_vel').value
        self.max_ang_vel = self.get_parameter('max_angular_vel').value
        self.update_rate = self.get_parameter('update_rate').value
        self.cmd_vel_timeout = self.get_parameter('cmd_vel_timeout').value
        self.watchdog_timeout = self.get_parameter('watchdog_timeout').value

        self.wheel_circumference = 2.0 * math.pi * self.wheel_rad

        # ── State variables ──────────────────────────────────────────────
        self.vx_cmd = 0.0
        self.yaw_cmd = 0.0
        self.last_cmd_time = 0.0

        # Wheel state: [left_front, right_front, left_back, right_back]
        self.wheel_pos = [0.0, 0.0, 0.0, 0.0]
        self.wheel_vel = [0.0, 0.0, 0.0, 0.0]

        # Odometry accumulator
        self.odom = Odometry()
        self.odom.header.frame_id = 'odom'
        self.odom.child_frame_id = 'base_link'
        cov_diag = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0,
                    0.0, 0.1, 0.0, 0.0, 0.0, 0.0,
                    0.0, 0.0, 0.1, 0.0, 0.0, 0.0,
                    0.0, 0.0, 0.0, 0.1, 0.0, 0.0,
                    0.0, 0.0, 0.0, 0.0, 0.1, 0.0,
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.1]
        self.odom.pose.covariance = cov_diag
        self.odom.twist.covariance = cov_diag

        # ── Subscribers ──────────────────────────────────────────────────
        self.cmd_vel_sub = self.create_subscription(
            TwistStamped,
            '/diff_drive_controller/cmd_vel_out',
            self.cmd_vel_callback,
            10,
        )

        # ── Publishers ───────────────────────────────────────────────────
        self.odom_pub = self.create_publisher(Odometry, '/motors/odom', 10)
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)

        # ── Serial connection to Pico 2W ─────────────────────────────────
        self.pico = PicoSerial(
            port=self.serial_port,
            baud=self.baud_rate,
        )

        if not self.pico.open():
            self.get_logger().error(
                f'Failed to connect to Pico 2W on {self.serial_port}. '
                'Will retry on each update cycle.'
            )
        else:
            self.get_logger().info(
                f'Connected to Pico 2W on {self.serial_port} @ {self.baud_rate}'
            )

        # ── Timer ────────────────────────────────────────────────────────
        self.update_timer = self.create_timer(1.0 / self.update_rate, self.update)
        self.get_logger().info('MotorDriverNode started')

    # ═════════════════════════════════════════════════════════════════════
    # Callbacks
    # ═════════════════════════════════════════════════════════════════════

    def cmd_vel_callback(self, msg: TwistStamped):
        self.vx_cmd = msg.twist.linear.x
        self.yaw_cmd = msg.twist.angular.z
        self.last_cmd_time = time.time()

    # ═════════════════════════════════════════════════════════════════════
    # Main update loop (runs at update_rate Hz)
    # ═════════════════════════════════════════════════════════════════════

    def update(self):
        # Reconnect if needed
        if not self.pico.connected:
            if self.pico.open():
                self.get_logger().info('Reconnected to Pico 2W')
            else:
                return

        # Timeout: zero command if no cmd_vel received recently
        if time.time() - self.last_cmd_time > self.cmd_vel_timeout:
            self.vx_cmd = 0.0
            self.yaw_cmd = 0.0

        # Diff-drive kinematics: convert (vx, wz) → (left_vel, right_vel)
        left_vel = self.vx_cmd - self.yaw_cmd * self.wheel_sep / 2.0
        right_vel = self.vx_cmd + self.yaw_cmd * self.wheel_sep / 2.0

        # Send to Pico and receive encoder feedback
        ok = self.pico.send_velocity_command(left_vel, right_vel)

        if ok:
            enc_pos = self.pico.get_encoder_positions()
            enc_vel = self.pico.get_wheel_velocities()

            # Map 2-side data to 4-wheel arrays:
            # [left_front, right_front, left_back, right_back]
            self.wheel_pos = [enc_pos[0], enc_pos[1], enc_pos[0], enc_pos[1]]
            self.wheel_vel = [enc_vel[0], enc_vel[1], enc_vel[0], enc_vel[1]]
        else:
            # Watchdog: if too long without data, emergency stop
            if self.pico.get_last_rx_age() > self.watchdog_timeout:
                self.get_logger().warn('Pico communication timeout — stopping motors')
                self.pico.send_stop()

        self.publish_joint_state()
        self.update_and_publish_odom()

    # ═════════════════════════════════════════════════════════════════════
    # Joint state publisher
    # ═════════════════════════════════════════════════════════════════════

    def publish_joint_state(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = [
            'base_link_to_LEFT_FRONT_WHEEL',
            'base_link_to_RIGHT_FRONT_WHEEL',
            'base_link_to_LEFT_BACK_WHEEL',
            'base_link_to_RIGHT_BACK_WHEEL',
        ]
        msg.position = self.wheel_pos
        msg.velocity = self.wheel_vel
        msg.effort = []
        self.joint_pub.publish(msg)

    # ═════════════════════════════════════════════════════════════════════
    # Odometry computation (same logic as original helmoro_motors_node)
    # ═════════════════════════════════════════════════════════════════════

    def update_and_publish_odom(self):
        dt = 1.0 / self.update_rate

        # Average velocities per side
        vel_left = (self.wheel_vel[0] + self.wheel_vel[2]) / 2.0
        vel_right = (self.wheel_vel[1] + self.wheel_vel[3]) / 2.0
        vel_linear = (vel_left + vel_right) / 2.0
        vel_angular = (vel_right - vel_left) / self.wheel_sep

        # Twist
        twist = Twist()
        twist.linear.x = vel_linear
        twist.angular.z = vel_angular

        # Integrate pose
        prev_orient = self.odom.pose.pose.orientation
        roll, pitch, yaw = self._euler_from_quaternion(prev_orient)

        # Update heading
        yaw += vel_angular * dt

        # Update position
        dx = vel_linear * math.cos(yaw) * dt
        dy = vel_linear * math.sin(yaw) * dt

        pose = Pose()
        pose.position.x = self.odom.pose.pose.position.x + dx
        pose.position.y = self.odom.pose.pose.position.y + dy
        pose.position.z = 0.0
        pose.orientation = self._quaternion_from_euler(0.0, 0.0, yaw)

        # Publish
        self.odom.header.stamp = self.get_clock().now().to_msg()
        self.odom.twist.twist = twist
        self.odom.pose.pose = pose
        self.odom_pub.publish(self.odom)

    # ═════════════════════════════════════════════════════════════════════
    # Quaternion helpers
    # ═════════════════════════════════════════════════════════════════════

    @staticmethod
    def _euler_from_quaternion(q: Quaternion):
        sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
        cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)

        sinp = 2.0 * (q.w * q.y - q.z * q.x)
        pitch = np.arcsin(np.clip(sinp, -1.0, 1.0))

        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)

        return roll, pitch, yaw

    @staticmethod
    def _quaternion_from_euler(roll: float, pitch: float, yaw: float) -> Quaternion:
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        q = Quaternion()
        q.w = cr * cp * cy + sr * sp * sy
        q.x = sr * cp * cy - cr * sp * sy
        q.y = cr * sp * cy + sr * cp * sy
        q.z = cr * cp * sy - sr * sp * cy
        return q

    # ═════════════════════════════════════════════════════════════════════
    # Shutdown
    # ═════════════════════════════════════════════════════════════════════

    def destroy_node(self):
        self.pico.send_stop()
        self.pico.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MotorDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
