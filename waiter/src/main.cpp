/*
 * Waiter Robot Main Application
 * Omni-Directional Robot with ESP32-WROOM
 * 
 * Features:
 * - WiFi/WebSocket communication with master
 * - Ultrasonic obstacle avoidance (HC-SR04)
 * - Omni-directional motor control
 * - Battery monitoring
 * - Real-time telemetry
 * 
 * Motor Configuration:
 * - Motor Left: GPIO5 (FWD), GPIO4 (BWD)
 * - Motor Right: GPIO15 (FWD), GPIO23 (BWD)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebSockets.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Servo.h>

#define ROBOT_NUMBER 1

const char* WIFI_SSID = "RestaurantWiFi";
const char* WIFI_PASSWORD = "restaurant2026";
const char* MASTER_IP = "192.168.1.100";
const uint16_t MASTER_PORT = 8765;

#if ROBOT_NUMBER == 1
const char* ROBOT_UNIQUE_ID = "ROBOT-001";
const char* ROBOT_NAME = "Waiter Bot Alpha";
#else
const char* ROBOT_UNIQUE_ID = "ROBOT-002";
const char* ROBOT_NAME = "Waiter Bot Beta";
#endif

// Motor Pins
const int LEFT_MOTOR_FWD = 5;
const int LEFT_MOTOR_BWD = 4;
const int RIGHT_MOTOR_FWD = 15;
const int RIGHT_MOTOR_BWD = 23;

// Ultrasonic Pin (1 sensor - REX board shared with servo headers)
const int ULTRASONIC_TRIG = 17;
const int ULTRASONIC_ECHO = 16;

// Servo1 for ultrasonic scanning
const int SERVO1_PIN = 2;  // GPIO 2 - Servo 1 header

// Other pins
const int BUZZER_PIN = 25;
const int BATTERY_PIN = 34;
const int LED_RED_PIN = 26;   // Red LED for table arrival indication

// Servo angles for scanning
const int SERVO_CENTER = 90;
const int SERVO_LEFT = 160;
const int SERVO_RIGHT = 20;

const int OBSTACLE_THRESHOLD_CM = 30;
const int MAX_SPEED = 150;
const int MIN_OBSTACLE_CM = 15;

const int SPEED_ZONE_FAR = 100;
const int SPEED_ZONE_MEDIUM = 50;
const int SPEED_ZONE_CLOSE = 30;

// ============= Global Variables =============
Servo ultrasonicServo;
WebSocketsClient webSocket;

float currentX = 0.0;
float currentY = 0.0;
float currentAngle = 0.0;
String currentStatus = "idle";
int currentDeliveryId = -1;

unsigned long lastTelemetryTime = 0;
unsigned long lastHeartbeatTime = 0;
unsigned long lastPositionUpdate = 0;

bool motorsEnabled = true;
String pendingTurnDirection = "";
unsigned long obstacleRequestTime = 0;
const unsigned long OBSTACLE_REQUEST_TIMEOUT = 5000;

// Omni drive state
float omniSpeed = 0.0;
float omniAngle = 0.0;
float omniRotation = 0.0;

// ============= Motor Control =============
void initMotors() {
    pinMode(LEFT_MOTOR_FWD, OUTPUT);
    pinMode(LEFT_MOTOR_BWD, OUTPUT);
    pinMode(RIGHT_MOTOR_FWD, OUTPUT);
    pinMode(RIGHT_MOTOR_BWD, OUTPUT);
    
    digitalWrite(LEFT_MOTOR_FWD, LOW);
    digitalWrite(LEFT_MOTOR_BWD, LOW);
    digitalWrite(RIGHT_MOTOR_FWD, LOW);
    digitalWrite(RIGHT_MOTOR_BWD, LOW);
    
    Serial.println("Motors initialized (omni-directional)");
}

void setLeftMotor(int speed) {
    if (speed > 0) {
        digitalWrite(LEFT_MOTOR_FWD, HIGH);
        digitalWrite(LEFT_MOTOR_BWD, LOW);
    } else if (speed < 0) {
        digitalWrite(LEFT_MOTOR_FWD, LOW);
        digitalWrite(LEFT_MOTOR_BWD, HIGH);
    } else {
        digitalWrite(LEFT_MOTOR_FWD, LOW);
        digitalWrite(LEFT_MOTOR_BWD, LOW);
    }
}

void setRightMotor(int speed) {
    if (speed > 0) {
        digitalWrite(RIGHT_MOTOR_FWD, HIGH);
        digitalWrite(RIGHT_MOTOR_BWD, LOW);
    } else if (speed < 0) {
        digitalWrite(RIGHT_MOTOR_FWD, LOW);
        digitalWrite(RIGHT_MOTOR_BWD, HIGH);
    } else {
        digitalWrite(RIGHT_MOTOR_FWD, LOW);
        digitalWrite(RIGHT_MOTOR_BWD, LOW);
    }
}

// ============= Omni-Directional Drive =============
// OmniMove: Drive forward/backward (positive = forward)
void omniMove(int speed) {
    setLeftMotor(-speed);
    setRightMotor(speed);
}

// OmniStrafe: Strafe left/right (positive = left strafe)
void omniStrafe(int speed) {
    setLeftMotor(-speed);
    setRightMotor(-speed);
}

// OmniRotate: Rotate in place (positive = counter-clockwise)
void omniRotate(int speed) {
    setLeftMotor(speed);
    setRightMotor(speed);
}

// OmniStop: Stop all motors
void omniStop() {
    setLeftMotor(0);
    setRightMotor(0);
}

// OmniDrive: Combined omni-directional movement
// Move forward/backward + strafe + rotate simultaneously
void omniDrive(int moveSpeed, int strafeSpeed, int rotateSpeed) {
    int leftSpeed = -moveSpeed - strafeSpeed + rotateSpeed;
    int rightSpeed = moveSpeed - strafeSpeed - rotateSpeed;
    
    setLeftMotor(leftSpeed);
    setRightMotor(rightSpeed);
}

// ============= AI-Based Speed Control =============
int calculateSpeedAI(long obstacleDistance) {
    if (obstacleDistance >= SPEED_ZONE_FAR) {
        return MAX_SPEED;
    }
    else if (obstacleDistance >= SPEED_ZONE_MEDIUM) {
        return (int)(MAX_SPEED * 0.7f);
    }
    else if (obstacleDistance >= SPEED_ZONE_CLOSE) {
        return (int)(MAX_SPEED * 0.4f);
    }
    else if (obstacleDistance >= MIN_OBSTACLE_CM) {
        return (int)(MAX_SPEED * 0.2f);
    }
    return 0;
}

String getSpeedZone(long obstacleDistance) {
    if (obstacleDistance >= SPEED_ZONE_FAR) return "FAR";
    else if (obstacleDistance >= SPEED_ZONE_MEDIUM) return "MEDIUM";
    else if (obstacleDistance >= SPEED_ZONE_CLOSE) return "CLOSE";
    else if (obstacleDistance >= MIN_OBSTACLE_CM) return "DANGER";
    return "STOP";
}

// ============= Ultrasonic Sensor (1x HC-SR04 on Servo1) =============
void initUltrasonic() {
    pinMode(ULTRASONIC_TRIG, OUTPUT);
    pinMode(ULTRASONIC_ECHO, INPUT);
    
    ultrasonicServo.attach(SERVO1_PIN);
    ultrasonicServo.write(SERVO_CENTER);
    
    Serial.println("Ultrasonic + Servo1 initialized");
}

long getDistance() {
    digitalWrite(ULTRASONIC_TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(ULTRASONIC_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(ULTRASONIC_TRIG, LOW);
    
    long duration = pulseIn(ULTRASONIC_ECHO, HIGH, 30000);
    long distance = duration * 0.034 / 2;
    
    if (distance > 200 || distance == 0) return 200;
    return distance;
}

// Front reading (servo center)
long getFrontDistance() {
    ultrasonicServo.write(SERVO_CENTER);
    delay(150);
    return getDistance();
}

// Left scan (servo left position)
long getLeftDistance() {
    ultrasonicServo.write(SERVO_LEFT);
    delay(200);
    return getDistance();
}

// Right scan (servo right position)
long getRightDistance() {
    ultrasonicServo.write(SERVO_RIGHT);
    delay(200);
    return getDistance();
}

// Reset servo to center
void resetServo() {
    ultrasonicServo.write(SERVO_CENTER);
    delay(150);
}

bool isObstacleDetected() {
    return getFrontDistance() < OBSTACLE_THRESHOLD_CM;
}

long getObstacleDistance() {
    return getFrontDistance();
}

// Scan all 3 directions using servo
void scanAllDirections(long& left, long& front, long& right) {
    left = getLeftDistance();
    front = getFrontDistance();
    right = getRightDistance();
    resetServo();
}

// ============= Battery Monitoring =============
float getBatteryVoltage() {
    int raw = analogRead(BATTERY_PIN);
    float voltage = (raw / 4095.0) * 3.3 * 2.0;
    return voltage;
}

int getBatteryPercentage() {
    float voltage = getBatteryVoltage();
    float percentage = (voltage - 3.0) / (4.2 - 3.0) * 100;
    return constrain((int)percentage, 0, 100);
}

// ============= WebSocket Communication =============
void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("WebSocket Disconnected");
            currentStatus = "offline";
            break;
            
        case WStype_CONNECTED:
            Serial.println("WebSocket Connected");
            {
                JsonDocument doc;
                doc["type"] = "register";
                doc["device_id"] = ROBOT_UNIQUE_ID;
                doc["device_type"] = "robot";
                String output;
                serializeJson(doc, output);
                webSocket.sendTXT(output);
            }
            break;
            
        case WStype_TEXT:
            Serial.printf("Message: %s\n", payload);
            {
                JsonDocument doc;
                DeserializationError error = deserializeJson(doc, payload);
                if (!error) {
                    String msgType = doc["type"].as<String>();
                    
                    if (msgType == "COMMAND") {
                        String action = doc["data"]["action"].as<String>();
                        float targetX = doc["data"]["target_x"].as<float>();
                        float targetY = doc["data"]["target_y"].as<float>();
                        
                        Serial.printf("Command: %s, Target: (%.2f, %.2f)\n", action.c_str(), targetX, targetY);
                        
                        if (action == "navigate_to_table") {
                            currentStatus = "delivering";
                            currentDeliveryId = doc["data"]["delivery_id"].as<int>();
                            motorsEnabled = true;
                        }
                        else if (action == "return_to_kitchen") {
                            currentStatus = "returning";
                            motorsEnabled = true;
                        }
                        else if (action == "stop") {
                            omniStop();
                            currentStatus = "idle";
                            motorsEnabled = false;
                        }
                        else if (action == "pause") {
                            omniStop();
                            motorsEnabled = false;
                        }
                        else if (action == "resume") {
                            motorsEnabled = true;
                        }
                        else if (action == "move_forward") {
                            omniMove(MAX_SPEED);
                        }
                        else if (action == "move_backward") {
                            omniMove(-MAX_SPEED);
                        }
                        else if (action == "strafe_left") {
                            omniStrafe(MAX_SPEED);
                        }
                        else if (action == "strafe_right") {
                            omniStrafe(-MAX_SPEED);
                        }
                        else if (action == "rotate_left") {
                            omniRotate(MAX_SPEED);
                        }
                        else if (action == "rotate_right") {
                            omniRotate(-MAX_SPEED);
                        }
                        
                        JsonDocument ackDoc;
                        ackDoc["type"] = "ACK";
                        ackDoc["device_id"] = ROBOT_UNIQUE_ID;
                        ackDoc["data"]["original_type"] = "COMMAND";
                        ackDoc["data"]["command_id"] = doc["command_id"];
                        ackDoc["data"]["success"] = true;
                        String ackOutput;
                        serializeJson(ackDoc, ackOutput);
                        webSocket.sendTXT(ackOutput);
                    }
                    else if (msgType == "request_state_sync") {
                        JsonDocument syncDoc;
                        syncDoc["type"] = "STATE_SYNC";
                        syncDoc["device_id"] = ROBOT_UNIQUE_ID;
                        syncDoc["data"]["status"] = currentStatus;
                        syncDoc["data"]["battery_voltage"] = getBatteryVoltage();
                        syncDoc["data"]["battery_percentage"] = getBatteryPercentage();
                        syncDoc["data"]["current_x"] = currentX;
                        syncDoc["data"]["current_y"] = currentY;
                        syncDoc["data"]["current_angle"] = currentAngle;
                        String syncOutput;
                        serializeJson(syncDoc, syncOutput);
                        webSocket.sendTXT(syncOutput);
                    }
                    else if (msgType == "OBSTACLE_RESPONSE") {
                        pendingTurnDirection = doc["data"]["turn"].as<String>();
                        Serial.printf("Received turn direction: %s\n", pendingTurnDirection.c_str());
                    }
                    else if (msgType == "customer_pickup_confirmed") {
                        String status = doc["status"].as<String>();
                        Serial.printf("Customer pickup confirmed: %s\n", status.c_str());
                        if (status == "picked_up") {
                            currentStatus = "returning";
                            sendDeliveryUpdate("completed");
                        }
                    }
                }
            }
            break;
            
        default:
            break;
    }
}

void sendTelemetry() {
    JsonDocument doc;
    doc["type"] = "TELEMETRY";
    doc["device_id"] = ROBOT_UNIQUE_ID;
    doc["timestamp"] = millis();
    doc["data"]["battery_voltage"] = getBatteryVoltage();
    doc["data"]["battery_percentage"] = getBatteryPercentage();
    doc["data"]["current_x"] = currentX;
    doc["data"]["current_y"] = currentY;
    doc["data"]["current_angle"] = currentAngle;
    doc["data"]["status"] = currentStatus;
    doc["data"]["velocity"] = omniSpeed;
    doc["data"]["ultrasonic_front"] = getFrontDistance();
    doc["data"]["ai_speed"] = calculateSpeedAI(getFrontDistance());
    doc["data"]["speed_zone"] = getSpeedZone(getFrontDistance());
    
    String output;
    serializeJson(doc, output);
    webSocket.sendTXT(output);
}

void sendDeliveryUpdate(String status) {
    if (currentDeliveryId < 0) return;
    
    JsonDocument doc;
    doc["type"] = "delivery_update";
    doc["device_id"] = ROBOT_UNIQUE_ID;
    doc["delivery_id"] = currentDeliveryId;
    doc["status"] = status;
    
    String output;
    serializeJson(doc, output);
    webSocket.sendTXT(output);
}

void sendObstacleRequest() {
    JsonDocument doc;
    doc["type"] = "OBSTACLE_REQUEST";
    doc["device_id"] = ROBOT_UNIQUE_ID;
    doc["delivery_id"] = currentDeliveryId;
    doc["obstacle_distance"] = getObstacleDistance();
    doc["current_x"] = currentX;
    doc["current_y"] = currentY;
    
    String output;
    serializeJson(doc, output);
    webSocket.sendTXT(output);
}

// ============= Navigation Logic =============
void navigateToTarget(float targetX, float targetY) {
    while (motorsEnabled) {
        long distance = getObstacleDistance();
        
        if (distance < OBSTACLE_THRESHOLD_CM && pendingTurnDirection == "") {
            Serial.println("Obstacle ahead - requesting turn direction");
            sendObstacleRequest();
            delay(500);
            continue;
        }
        
        if (pendingTurnDirection != "") {
            if (pendingTurnDirection == "left") {
                omniRotate(MAX_SPEED);
            } else {
                omniRotate(-MAX_SPEED);
            }
            delay(500);
            omniStop();
            pendingTurnDirection = "";
        }
        
        float dx = targetX - currentX;
        float dy = targetY - currentY;
        float distToTarget = sqrt(dx * dx + dy * dy);
        
        if (distToTarget < 0.2) {
            Serial.println("Arrived at target!");
            omniStop();
            
            digitalWrite(LED_RED_PIN, HIGH);
            Serial.println("RED LED ON - Table arrival indication");
            
            sendDeliveryUpdate("delivered");
            currentStatus = "serving";
            
            Serial.println("Waiting 20 seconds for customer pickup...");
            for (int i = 0; i < 20; i++) {
                delay(1000);
                Serial.printf("Wait time: %d/20\n", i + 1);
            }
            
            Serial.println("Return timeout - returning to kitchen");
            currentStatus = "returning";
            sendDeliveryUpdate("customer_no_pickup");
            returnToKitchen();
            return;
        }
        
        long obstacleDist = getFrontDistance();
        int aiSpeed = calculateSpeedAI(obstacleDist);
        Serial.printf("AI Speed: %d, Zone: %s\n", aiSpeed, getSpeedZone(obstacleDist).c_str());
        
        omniMove(aiSpeed);
        
        currentX += 0.01;
        currentY += 0.005;
        
        delay(100);
    }
}

void returnToKitchen() {
    navigateToTarget(0.0, 0.0);
    currentStatus = "idle";
    sendDeliveryUpdate("completed");
}

// ============= Setup =============
void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("===========================================");
    Serial.println("  Waiter Robot - Omni-Directional Drive");
    Serial.printf("  Robot ID: %s\n", ROBOT_UNIQUE_ID);
    Serial.printf("  Robot Name: %s\n", ROBOT_NAME);
    Serial.println("===========================================");
    
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);
    
    pinMode(LED_RED_PIN, OUTPUT);
    digitalWrite(LED_RED_PIN, LOW);
    
    initMotors();
    initUltrasonic();
    
    pinMode(BATTERY_PIN, INPUT);
    
    Serial.println("Hardware initialized");
    
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting to WiFi");
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    Serial.println();
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.print("WiFi connected! IP: ");
        Serial.println(WiFi.localIP());
        
        webSocket.begin(MASTER_IP, MASTER_PORT, "/");
        webSocket.onEvent(webSocketEvent);
        webSocket.setReconnectInterval(5000);
    } else {
        Serial.println("WiFi connection FAILED!");
    }
    
    Serial.println("=== Robot Ready (Omni-Drive) ===");
    Serial.println("  Left Motor: GPIO5(FWD), GPIO4(BWD)");
    Serial.println("  Right Motor: GPIO15(FWD), GPIO23(BWD)");
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
}

// ============= Main Loop =============
void loop() {
    webSocket.loop();
    
    if (motorsEnabled && (currentStatus == "delivering" || currentStatus == "returning")) {
        long distance = getFrontDistance();
        int aiSpeed = calculateSpeedAI(distance);
        
        if (distance < OBSTACLE_THRESHOLD_CM && pendingTurnDirection == "") {
            Serial.println("Obstacle detected - requesting turn direction");
            omniStop();
            sendObstacleRequest();
            obstacleRequestTime = millis();
        }
        
        if (pendingTurnDirection != "") {
            Serial.printf("Turning %s to avoid\n", pendingTurnDirection.c_str());
            if (pendingTurnDirection == "left") {
                omniRotate(MAX_SPEED);
            } else {
                omniRotate(-MAX_SPEED);
            }
            delay(500);
            omniStop();
            pendingTurnDirection = "";
        }
        
        if (pendingTurnDirection == "" && millis() - obstacleRequestTime > OBSTACLE_REQUEST_TIMEOUT) {
            Serial.println("Obstacle request timeout - default turn right");
            omniRotate(-MAX_SPEED);
            delay(500);
            omniStop();
            obstacleRequestTime = 0;
        }
        
        if (pendingTurnDirection == "" && aiSpeed > 0) {
            omniMove(aiSpeed);
            currentX += 0.01;
            currentY += 0.005;
        }
    }
    
    if (getBatteryPercentage() < 20) {
        Serial.println("LOW BATTERY - Returning to dock");
        currentStatus = "charging";
        returnToKitchen();
    }
    
    if (millis() - lastTelemetryTime > 2000) {
        sendTelemetry();
        lastTelemetryTime = millis();
    }
    
    if (millis() - lastPositionUpdate > 1000) {
        currentX += 0.01;
        if (currentX > 6.0) currentX = 0.0;
        currentY += 0.005;
        if (currentY > 4.0) currentY = 0.0;
        currentAngle = (currentAngle + 1.0) < 360.0 ? currentAngle + 1.0 : 0.0;
        lastPositionUpdate = millis();
    }
    
    delay(50);
}