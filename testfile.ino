#include "I2Cdev.h"
#include "PID_v1.h"
#include "MPU6050_6Axis_MotionApps20.h"
#include "Wire.h"
#define INTERRUPT_PIN 13

// REX 8in1 Motor Pins (V4)
#define ENA 15   // Motor A PWM (forward)
#define IN1 23   // Motor A direction
#define ENB 4    // Motor C PWM (forward)
#define IN3 5    // Motor C direction

double speedFactor = 0.6;  // 0.0-1.0, lower = slower/smoother

void moveMotors(int speed, int minSpeed) {
  if (abs(speed) < minSpeed) {
    analogWrite(ENA, 0);
    analogWrite(ENB, 0);
    return;
  }
  speed = (int)(abs(speed) * speedFactor) * (speed > 0 ? 1 : -1);
  if (speed > 0) {
    analogWrite(ENA, speed);
    digitalWrite(IN1, LOW);
    analogWrite(ENB, speed);
    digitalWrite(IN3, LOW);
  } else {
    analogWrite(ENA, abs(speed));
    digitalWrite(IN1, HIGH);
    analogWrite(ENB, abs(speed));
    digitalWrite(IN3, HIGH);
  }
}

MPU6050 mpu;

bool dmpReady = false;

uint8_t mpuIntStatus;
uint8_t devStatus;
uint16_t packetSize;
uint16_t fifoCount = 0;
uint8_t fifoBuffer[64];

Quaternion q;
VectorFloat gravity;
float ypr[3];

double setpoint = 0.0;  // MPU flat on top = level
double Kp = 80;
double Kd = 2.5;
double Ki = 200;

double input, output;
PID pid(&input, &output, &setpoint, Kp, Ki, Kd, DIRECT);

volatile bool mpuInterrupt = false;

void dmpDataReady() {
  mpuInterrupt = true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Wire.begin(21, 22);
  Wire.setClock(400000);
  
  Serial.println("Starting...");
  mpu.initialize();
  Serial.println("MPU initialized");
  delay(100);

  if (!mpu.testConnection()) {
    Serial.println("MPU6050 FAILED");
    while(1);
  }
  Serial.println("MPU6050 OK");
  delay(100);

  mpu.setXGyroOffset(45);
  mpu.setYGyroOffset(-38);
  mpu.setZGyroOffset(23);
  mpu.setZAccelOffset(1636);
  Serial.println("Offsets set");

  devStatus = mpu.dmpInitialize();
  Serial.print("DMP init: ");
  Serial.println(devStatus);

  if (devStatus == 0) {
    Serial.println("Enabling DMP...");
    mpu.setDMPEnabled(true);

    Serial.println("Setup interrupt...");
    attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), dmpDataReady, RISING);
    
    mpuIntStatus = mpu.getIntStatus();
    Serial.println("DMP ready!");
    dmpReady = true;

    packetSize = mpu.dmpGetFIFOPacketSize();
    Serial.print("Packet size: ");
    Serial.println(packetSize);

    pid.SetMode(AUTOMATIC);
    pid.SetSampleTime(10);
    pid.SetOutputLimits(-255, 255);
  }
  else {
    Serial.print("DMP failed: ");
    Serial.println(devStatus);
  }

  pinMode(INTERRUPT_PIN, INPUT_PULLUP);
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  
  Serial.println("Waiting for first interrupt...");
  delay(5000);
}

void loop() {
  if (!dmpReady) {
    Serial.println("DMP not ready!");
    delay(1000);
    return;
  }

  mpuInterrupt = false;
  mpuIntStatus = mpu.getIntStatus();
  fifoCount = mpu.getFIFOCount();

  if ((mpuIntStatus & 0x10) || fifoCount == 1024) {
    mpu.resetFIFO();
    Serial.println("FIFO overflow!");
  }
  else if (mpuIntStatus & 0x02) {
    while (fifoCount < packetSize) fifoCount = mpu.getFIFOCount();

    mpu.getFIFOBytes(fifoBuffer, packetSize);
    fifoCount -= packetSize;

    mpu.dmpGetQuaternion(&q, fifoBuffer);
    mpu.dmpGetGravity(&gravity, &q);
    mpu.dmpGetYawPitchRoll(ypr, &q, &gravity);
    input = ypr[1] * 180 / M_PI;
    if (input > 180) input -= 360;
    
    Serial.print("YPR: ");
    Serial.print(ypr[0]); Serial.print(" ");
    Serial.print(ypr[1]); Serial.print(" ");
    Serial.println(ypr[2]);

    pid.Compute();

    Serial.print(input);
    Serial.print(" => ");
    Serial.println(output);

    moveMotors(output, 30);
  }
  else {
    Serial.print("No data. Status: ");
    Serial.print(mpuIntStatus);
    Serial.print(" FIFO: ");
    Serial.println(fifoCount);
    delay(100);
  }
}