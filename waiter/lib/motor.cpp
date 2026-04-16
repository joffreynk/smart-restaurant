#include "motor.h"

Motor::Motor(int p1, int p2, int pwm) {
    pin1 = p1;
    pin2 = p2;
    pwmPin = pwm;
    currentSpeed = 0;
}

void Motor::begin() {
    pinMode(pin1, OUTPUT);
    pinMode(pin2, OUTPUT);
    pinMode(pwmPin, OUTPUT);
    stop();
}

void Motor::forward(int speed) {
    currentSpeed = speed;
    digitalWrite(pin1, HIGH);
    digitalWrite(pin2, LOW);
    analogWrite(pwmPin, speed);
}

void Motor::backward(int speed) {
    currentSpeed = speed;
    digitalWrite(pin1, LOW);
    digitalWrite(pin2, HIGH);
    analogWrite(pwmPin, speed);
}

void Motor::stop() {
    currentSpeed = 0;
    digitalWrite(pin1, LOW);
    digitalWrite(pin2, LOW);
    analogWrite(pwmPin, 0);
}

void Motor::setSpeed(int speed) {
    currentSpeed = speed;
    analogWrite(pwmPin, speed);
}

int Motor::getSpeed() {
    return currentSpeed;
}

MotorController::MotorController() {
    leftMotor = new Motor(LEFT_MOTOR_PIN1, LEFT_MOTOR_PIN2, LEFT_MOTOR_PWM);
    rightMotor = new Motor(RIGHT_MOTOR_PIN1, RIGHT_MOTOR_PIN2, RIGHT_MOTOR_PWM);
}

void MotorController::begin() {
    leftMotor->begin();
    rightMotor->begin();
}

void MotorController::moveForward(int speed) {
    leftMotor->forward(speed);
    rightMotor->forward(speed);
}

void MotorController::moveBackward(int speed) {
    leftMotor->backward(speed);
    rightMotor->backward(speed);
}

void MotorController::turnLeft(int speed) {
    leftMotor->backward(speed);
    rightMotor->forward(speed);
}

void MotorController::turnRight(int speed) {
    leftMotor->forward(speed);
    rightMotor->backward(speed);
}

void MotorController::stop() {
    leftMotor->stop();
    rightMotor->stop();
}

void MotorController::pivotLeft(int speed) {
    leftMotor->backward(speed);
    rightMotor->forward(speed);
}

void MotorController::pivotRight(int speed) {
    leftMotor->forward(speed);
    rightMotor->backward(speed);
}