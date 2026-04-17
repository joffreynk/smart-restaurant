#ifndef CONFIG_H
#define CONFIG_H

// ================================================
// WiFi Configuration - CHANGE FOR YOUR NETWORK
// ================================================
// These defaults are only used if preferences are not yet configured
#define WIFI_SSID "YourWiFiSSID"
#define WIFI_PASSWORD "YourWiFiPassword"
// Default master hostname - robots will try to resolve this via DNS/mDNS
#define MASTER_HOSTNAME "smart-restaurant"
#define MASTER_PORT 3000

// ================================================
// Robot Configuration - UNIQUE ID FOR EACH ROBOT
// ================================================
#define ROBOT_UNIQUE_ID "ROBOT-001"  // Change to ROBOT-002 for second robot
#define ROBOT_NAME "Waiter Bot Alpha"

// ================================================
// SONICBOT/OMNIBOT MOTOR PINS (4 motors)
// ================================================
#define MotorA1 15  // Forward
#define MotorA2 23  // Backward
#define MotorB1 32    // Forward
#define MotorB2 33  // Backward
#define MotorC1 5   // Forward
#define MotorC2 4   // Backward
#define MotorD1 27  // Forward
#define MotorD2 14   // Backward

// Motor speeds
#define SPEED_SLOW 100
#define SPEED_MID 150
#define SPEED_FAST 250

// PWM setup
const int freq = 50;
const int resolution = 8;
const int PWM_A1 = 4;
const int PWM_A2 = 5;
const int PWM_B1 = 6;
const int PWM_B2 = 7;
const int PWM_C1 = 8;
const int PWM_C2 = 9;
const int PWM_D1 = 10;
const int PWM_D2 = 11;

// ================================================
// ULTRASONIC SENSOR (HC-SR04)
// ================================================
#define ULTRASONIC_TRIG 17
#define ULTRASONIC_ECHO 16
#define OBSTACLE_STOP_CM 10
#define OBSTACLE_ALERT_CM 30

// ================================================
// BATTERY CONFIGURATION
// ================================================
#define BATTERY_PIN 34
#define BATTERY_VOLTAGE_DIVIDER 2.0
#define MAX_BATTERY_VOLTAGE 4.2
#define MIN_BATTERY_VOLTAGE 3.0

// ================================================
// BUZZER
// ================================================
#define BUZZER_PIN 25

// Telemetry interval
#define TELEMETRY_INTERVAL 3000

// ================================================
// BACKWARD COMPATIBILITY ALIASES (for old motor.cpp, sensor.cpp)
// ================================================
#define LEFT_MOTOR_PIN1 MotorA1
#define LEFT_MOTOR_PIN2 MotorA2
#define LEFT_MOTOR_PWM MotorA1
#define RIGHT_MOTOR_PIN1 MotorB1
#define RIGHT_MOTOR_PIN2 MotorB2
#define RIGHT_MOTOR_PWM MotorB1
#define OBSTACLE_THRESHOLD_CM OBSTACLE_STOP_CM
#define FRONT_TRIG ULTRASONIC_TRIG
#define FRONT_ECHO ULTRASONIC_ECHO
#define LEFT_TRIG ULTRASONIC_TRIG
#define LEFT_ECHO ULTRASONIC_ECHO
#define RIGHT_TRIG ULTRASONIC_TRIG
#define RIGHT_ECHO ULTRASONIC_ECHO
#define MAX_DISTANCE_CM 200

#endif