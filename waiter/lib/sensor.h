#ifndef SENSOR_H
#define SENSOR_H

#include <Arduino.h>

class UltrasonicSensor {
private:
    int trigPin;
    int echoPin;
    
public:
    UltrasonicSensor(int tr, int ec);
    void begin();
    float getDistance();
    bool isObstacle(int thresholdCm);
};

class SensorArray {
public:
    UltrasonicSensor* frontSensor;
    UltrasonicSensor* leftSensor;
    UltrasonicSensor* rightSensor;
    
    SensorArray();
    void begin();
    float getFrontDistance();
    float getLeftDistance();
    float getRightDistance();
    bool isFrontObstacle();
    bool isLeftObstacle();
    bool isRightObstacle();
    bool anyObstacle(int thresholdCm);
    void getAllDistances(float& front, float& left, float& right);
};

class BatteryMonitor {
private:
    int batteryPin;
    float voltageDivider;
    float maxVoltage;
    float minVoltage;
    
public:
    BatteryMonitor(int pin, float divider, float maxV, float minV);
    void begin();
    float getVoltage();
    int getPercentage();
    bool isLow(int thresholdPercent);
};

#endif