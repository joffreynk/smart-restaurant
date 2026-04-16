#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration
#define WIFI_SSID "RestaurantWiFi"
#define WIFI_PASSWORD "restaurant2026"
#define MASTER_IP "192.168.1.100"
#define MASTER_PORT 8765

// Robot Configuration
#define ROBOT_UNIQUE_ID "ROBOT-001"
#define ROBOT_NAME "Waiter Bot Alpha"

// Motor Configuration (REX MAIN V5.3 - L9110S Driver)
// Motor-C (Left Motor - drives backward): M_C1=5, M_C2=4
#define LEFT_MOTOR_FWD 5
#define LEFT_MOTOR_BWD 4

// Motor-A (Right Motor - drives backward): M_A1=15, M_A2=23
#define RIGHT_MOTOR_FWD 15
#define RIGHT_MOTOR_BWD 23

#define MOTOR_SPEED_MAX 200
#define MOTOR_SPEED_MIN 0

// Ultrasonic Sensor Configuration (HC-SR04 on REX board)
#define ULTRASONIC_TRIG 17
#define ULTRASONIC_ECHO 16

#define OBSTACLE_THRESHOLD_CM 30
#define MAX_DISTANCE_CM 200

// IMU Configuration (MPU6050 - REX built-in)
#define MPU_SDA 21
#define MPU_SCL 22
#define MPU6050_ADDR 0x68
#define MPU_INT 13

// Battery Configuration
#define BATTERY_PIN 34
#define BATTERY_VOLTAGE_DIVIDER 2.0
#define MAX_BATTERY_VOLTAGE 4.2
#define MIN_BATTERY_VOLTAGE 3.0

// Buzzer Pin (REX built-in)
#define BUZZER_PIN 25
#define BUZZER_ON HIGH
#define BUZZER_OFF LOW

// Self-Balancing PID Parameters
#define BALANCE_KP 50.0
#define BALANCE_KI 0.0
#define BALANCE_KD 900.0
#define TARGET_ANGLE 0.0

// Navigation Parameters
#define MAX_SPEED 0.3
#define ACCELERATION 0.1
#define TURN_SPEED 0.15

// State Machine States
enum RobotState {
    STATE_IDLE = 0,
    STATE_ASSIGNED,
    STATE_PICKING_UP,
    STATE_DELIVERING,
    STATE_SERVING,
    STATE_RETURNING,
    STATE_CHARGING,
    STATE_ERROR,
    STATE_MAINTENANCE
};

#endif