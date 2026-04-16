// Simple MPU6050 Test - No motors, just read angle

#include "I2Cdev.h"
#include "MPU6050_6Axis_MotionApps20.h"
#include "Wire.h"

MPU6050 mpu;

uint8_t fifoBuffer[64];
uint16_t fifoCount;
uint16_t packetSize = 42;

Quaternion q;
VectorFloat gravity;
float ypr[3];

void setup() {
  Serial.begin(115200);
  Wire.begin();
  
  Serial.println("Initializing MPU6050...");
  mpu.initialize();
  
  if (mpu.testConnection()) {
    Serial.println("MPU6050 OK!");
  } else {
    Serial.println("MPU6050 FAIL!");
    while(1);
  }
  
  // Initialize DMP
  mpu.dmpInitialize();
  mpu.setDMPEnabled(true);
  
  // Calibration offsets (you can adjust these)
  mpu.setXGyroOffset(45);
  mpu.setYGyroOffset(-38);
  mpu.setZGyroOffset(23);
  mpu.setZAccelOffset(1636);
  
  packetSize = mpu.dmpGetFIFOPacketSize();
  
  Serial.println("Starting... Tilt the robot to see angle changes.");
  Serial.println("");
}

void loop() {
  // Read from FIFO
  fifoCount = mpu.getFIFOCount();
  
  if (fifoCount >= packetSize) {
    mpu.getFIFOBytes(fifoBuffer, packetSize);
    fifoCount -= packetSize;
    
    mpu.dmpGetQuaternion(&q, fifoBuffer);
    mpu.dmpGetGravity(&gravity, &q);
    mpu.dmpGetYawPitchRoll(ypr, &q, &gravity);
    
    // Print all 3 angles
    Serial.print("Yaw: ");
    Serial.print(ypr[0] * 180 / PI, 1);
    Serial.print(" | Pitch: ");
    Serial.print(ypr[1] * 180 / PI, 1);
    Serial.print(" | Roll: ");
    Serial.println(ypr[2] * 180 / PI, 1);
  }
  
  delay(50);
}