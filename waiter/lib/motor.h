#ifndef MOTOR_H
#define MOTOR_H

#include <Arduino.h>

class Motor {
private:
    int pin1;
    int pin2;
    int pwmPin;
    int currentSpeed;
    
public:
    Motor(int p1, int p2, int pwm);
    void begin();
    void forward(int speed);
    void backward(int speed);
    void stop();
    void setSpeed(int speed);
    int getSpeed();
};

class MotorController {
public:
    Motor* leftMotor;
    Motor* rightMotor;
    
    MotorController();
    void begin();
    void moveForward(int speed);
    void moveBackward(int speed);
    void turnLeft(int speed);
    void turnRight(int speed);
    void stop();
    void pivotLeft(int speed);
    void pivotRight(int speed);
};

#endif