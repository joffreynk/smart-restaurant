#include "sensor.h"
#include "config.h"

UltrasonicSensor::UltrasonicSensor(int tr, int ec) {
    trigPin = tr;
    echoPin = ec;
}

void UltrasonicSensor::begin() {
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
}

float UltrasonicSensor::getDistance() {
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    
    long duration = pulseIn(echoPin, HIGH, 30000);
    float distance = duration * 0.034 / 2;
    
    if (distance > MAX_DISTANCE_CM || distance == 0) {
        return MAX_DISTANCE_CM;
    }
    return distance;
}

bool UltrasonicSensor::isObstacle(int thresholdCm) {
    return getDistance() < thresholdCm;
}

SensorArray::SensorArray() {
    frontSensor = new UltrasonicSensor(FRONT_TRIG, FRONT_ECHO);
    leftSensor = new UltrasonicSensor(LEFT_TRIG, LEFT_ECHO);
    rightSensor = new UltrasonicSensor(RIGHT_TRIG, RIGHT_ECHO);
}

void SensorArray::begin() {
    frontSensor->begin();
    leftSensor->begin();
    rightSensor->begin();
}

float SensorArray::getFrontDistance() {
    return frontSensor->getDistance();
}

float SensorArray::getLeftDistance() {
    return leftSensor->getDistance();
}

float SensorArray::getRightDistance() {
    return rightSensor->getDistance();
}

bool SensorArray::isFrontObstacle() {
    return frontSensor->isObstacle(OBSTACLE_THRESHOLD_CM);
}

bool SensorArray::isLeftObstacle() {
    return leftSensor->isObstacle(OBSTACLE_THRESHOLD_CM);
}

bool SensorArray::isRightObstacle() {
    return rightSensor->isObstacle(OBSTACLE_THRESHOLD_CM);
}

bool SensorArray::anyObstacle(int thresholdCm) {
    return frontSensor->isObstacle(thresholdCm) || 
           leftSensor->isObstacle(thresholdCm) || 
           rightSensor->isObstacle(thresholdCm);
}

void SensorArray::getAllDistances(float& front, float& left, float& right) {
    front = getFrontDistance();
    left = getLeftDistance();
    right = getRightDistance();
}

BatteryMonitor::BatteryMonitor(int pin, float divider, float maxV, float minV) {
    batteryPin = pin;
    voltageDivider = divider;
    maxVoltage = maxV;
    minVoltage = minV;
}

void BatteryMonitor::begin() {
    pinMode(batteryPin, INPUT);
}

float BatteryMonitor::getVoltage() {
    int rawValue = analogRead(batteryPin);
    float voltage = (rawValue / 4095.0) * 3.3 * voltageDivider;
    return voltage;
}

int BatteryMonitor::getPercentage() {
    float voltage = getVoltage();
    float percentage = (voltage - minVoltage) / (maxVoltage - minVoltage) * 100;
    return constrain((int)percentage, 0, 100);
}

bool BatteryMonitor::isLow(int thresholdPercent) {
    return getPercentage() < thresholdPercent;
}