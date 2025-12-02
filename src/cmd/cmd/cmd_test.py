import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
import math

class Vacuum180Bot(Node):
    def __init__(self):
        super().__init__("vacuum_180_bot")

        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.scan_sub = self.create_subscription(
            LaserScan, "/scan", self.scan_callback, 10
        )

        self.timer = self.create_timer(0.1, self.timer_callback)

        # 상태 변수
        self.obstacle = False
        self.mode = "GO"          # GO: 직진, TURN: 회전, STOP: 영구 정지
        self.turn_angle = math.pi # 180도 회전 (radians)
        self.angular_speed = 1.0  # rad/s
        self.turned_angle = 0.0
        self.turn_direction = 1.0

        # 장애물 감지 누적
        self.obstacle_count = 0
        self.max_obstacle_count = 5  # 5회 감지 시 정지

    def scan_callback(self, msg):
        center = len(msg.ranges) // 2
        dist = msg.ranges[center]

        if dist < 0.25:   # 25cm 이내 장애물
            self.obstacle = True
        else:
            self.obstacle = False

    def timer_callback(self):
        cmd = Twist()

        # 이미 정지 상태이면 계속 멈춤
        if self.mode == "STOP":
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
            self.cmd_pub.publish(cmd)
            return

        # ====================================================
        # GO 모드: 직진
        # ====================================================
        if self.mode == "GO":
            if self.obstacle:
                self.obstacle_count += 1
                self.get_logger().info(f"⚠ 장애물 감지 횟수: {self.obstacle_count}")
                
                # 누적 5회 감지 시 STOP 모드
                if self.obstacle_count >= self.max_obstacle_count:
                    self.get_logger().warn("⛔ 장애물 5회 감지 → 영구 정지")
                    self.mode = "STOP"
                else:
                    self.get_logger().info("⚠ 장애물 발견 → 180도 회전 모드")
                    self.mode = "TURN"
                    self.turned_angle = 0.0
                    # 회전 방향 랜덤 선택
                    self.turn_direction = 1.0 if (self.get_clock().now().nanoseconds % 2 == 0) else -1.0
            else:
                cmd.linear.x = 0.15
                cmd.angular.z = 0.0

        # ====================================================
        # TURN 모드: 180도 회전
        # ====================================================
        elif self.mode == "TURN":
            cmd.linear.x = 0.0
            cmd.angular.z = self.turn_direction * self.angular_speed

            # 누적 각도 계산 (0.1s timer 기준)
            self.turned_angle += self.angular_speed * 0.1
            if self.turned_angle >= self.turn_angle:
                self.get_logger().info("▶ 180도 회전 완료 → 직진 모드")
                self.mode = "GO"

        # ====================================================
        self.cmd_pub.publish(cmd)


def main():
    rclpy.init()
    node = Vacuum180Bot()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
