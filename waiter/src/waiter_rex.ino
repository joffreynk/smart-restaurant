/*
 * Waiter Robot - REX Edition (Line Follow)
 * Using REX 8in1 Board (ESP32-WROOM)
 * 
 * Hardware: REX 8in1 Educational Robot Kit
 * 
 * Motor Pin Configuration (REX 8in1):
 * ================ Motors (4x Omni) ===============
 * | Motor | GPIO (FWD) | GPIO (BWD) |
 * |-------|-----------|-----------|
 * | A     | 15        | 23        |
 * | B     | 32        | 33        |
 * | C     | 5         | 4         |
 * | D     | 27        | 14        |
 * 
 * ================ Line Following (IR Sensors) ===============
 * | Sensor | GPIO | Description |
 * |-------|------|-----------|
 * | IR_LEFT | 35 | Left IR (white tape) |
 * | IR_CENTER| 36 | Center IR (white tape) |
 * | IR_RIGHT| 39 | Right IR (white tape) |
 * 
 * ================ Color Sensor (Junction) ===============
 * | Sensor | GPIO | Description |
 * |-------|------|-----------|
 * | COLOR_SENSOR | 34 | TCS3200 Color Sensor |
 * 
 * Floor Layout (White Tape + Single Color Junction):
 * ==========================================
 * 
 *           [Kitchen]
 *              |
 *         WHITE LINE
 *              |
 *         [JUNCTION] ← ONE COLOR marker
 *            /    \
 *       LEFT      RIGHT
 *         |        |
 *    Table 1   Table 2
 * 
 * Junction Detection:
 * - ONE color patch (e.g., blue or black) after white line
 * - At junction: uses originTable to decide turn
 *   - origin = table_1 → turn LEFT
 *   - origin = table_2 → turn RIGHT
 *   - going to table_1 → turn LEFT
 *   - going to table_2 → turn RIGHT
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebSockets.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <DabbleESP32.h>

// Robot number: Change to 1 or 2
#define ROBOT_NUMBER 2

// WiFi Configuration
const char* WIFI_SSID = "RestaurantWiFi";
const char* WIFI_PASSWORD = "restaurant2026";
const char* MASTER_IP = "192.168.1.100";
const uint16_t MASTER_PORT = 8765;

#if ROBOT_NUMBER == 1
const char* ROBOT_UNIQUE_ID = "ROBOT-001";
#else
const char* ROBOT_UNIQUE_ID = "ROBOT-002";
#endif

// ============= Motor Pins (REX 8in1) =============
const int MotorA1 = 15;
const int MotorA2 = 23;
const int MotorB1 = 32;
const int MotorB2 = 33;
const int MotorC1 = 5;
const int MotorC2 = 4;
const int MotorD1 = 27;
const int MotorD2 = 14;

// Line Following IR Sensors
const int IR_LEFT = 35;
const int IR_CENTER = 36;
const int IR_RIGHT = 39;

// Color Sensor (TCS3200 or analog)
const int COLOR_SENSOR = 34;
const int S0 = 26;
const int S1 = 27;
const int S2 = 14;
const int S3 = 12;
const int OUTPUT_PIN = 13;

// Ultrasonic Pins
const int ULTRASONIC_TRIG = 17;
const int ULTRASONIC_ECHO = 16;

// Other Pins
const int BUZZER_PIN = 25;
const int BATTERY_PIN = 34;

// PWM Configuration
const int PWM_FREQ = 50;
const int PWM_RES = 8;
const int PWM_CH_A1 = 0;
const int PWM_CH_A2 = 1;
const int PWM_CH_B1 = 2;
const int PWM_CH_B2 = 3;
const int PWM_CH_C1 = 4;
const int PWM_CH_C2 = 5;
const int PWM_CH_D1 = 6;
const int PWM_CH_D2 = 7;

// Speed Constants
const int SPEED_BASE = 150;
const int SPEED_TURN = 120;
const int MAX_SPEED = 250;

const int OBSTACLE_THRESHOLD_CM = 30;
const int MIN_OBSTACLE_CM = 15;
const int SPEED_ZONE_FAR = 100;
const int SPEED_ZONE_MEDIUM = 50;
const int SPEED_ZONE_CLOSE = 30;

// ============= Global Variables =============
WebSocketsClient webSocket;
float currentX = 0.0;
float currentY = 0.0;
float currentAngle = 0.0;
String currentStatus = "idle";
int currentDeliveryId = -1;

unsigned long lastTelemetryTime = 0;
bool motorsEnabled = true;

// Line Following State
bool lineFollowingEnabled = true;
String currentDestination = "none";
bool isReturning = false;
int lineLostCounter = 0;

// Junction State
bool atJunction = false;
bool junctionHandled = false;
bool shouldTurnLeft = false;
bool shouldTurnRight = false;

// Destination flags
bool atTable1 = false;
bool atTable2 = false;
bool atKitchen = false;

// Origin tracking for return journey
String originTable = "none";  // "table_1" or "table_2"

// Line search state
bool searchingLine = false;
bool stopCommandReceived = false;

// ============= Motor Control =============
void initMotors() {
    ledcSetup(PWM_CH_A1, PWM_FREQ, PWM_RES);
    ledcAttachPin(MotorA1, PWM_CH_A1);
    ledcSetup(PWM_CH_A2, PWM_FREQ, PWM_RES);
    ledcAttachPin(MotorA2, PWM_CH_A2);
    
    ledcSetup(PWM_CH_B1, PWM_FREQ, PWM_RES);
    ledcAttachPin(MotorB1, PWM_CH_B1);
    ledcSetup(PWM_CH_B2, PWM_FREQ, PWM_RES);
    ledcAttachPin(MotorB2, PWM_CH_B2);
    
    ledcSetup(PWM_CH_C1, PWM_FREQ, PWM_RES);
    ledcAttachPin(MotorC1, PWM_CH_C1);
    ledcSetup(PWM_CH_C2, PWM_FREQ, PWM_RES);
    ledcAttachPin(MotorC2, PWM_CH_C2);
    
    ledcSetup(PWM_CH_D1, PWM_FREQ, PWM_RES);
    ledcAttachPin(MotorD1, PWM_CH_D1);
    ledcSetup(PWM_CH_D2, PWM_FREQ, PWM_RES);
    ledcAttachPin(MotorD2, PWM_CH_D2);
    
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);
    
    Serial.println("REX Motors initialized");
}

void stopMotors() {
    ledcWrite(PWM_CH_A1, 0); ledcWrite(PWM_CH_A2, 0);
    ledcWrite(PWM_CH_B1, 0); ledcWrite(PWM_CH_B2, 0);
    ledcWrite(PWM_CH_C1, 0); ledcWrite(PWM_CH_C2, 0);
    ledcWrite(PWM_CH_D1, 0); ledcWrite(PWM_CH_D2, 0);
}

// Simple forward movement
void omniForward(int speed) {
    ledcWrite(PWM_CH_A1, speed); ledcWrite(PWM_CH_A2, 0);
    ledcWrite(PWM_CH_B1, speed); ledcWrite(PWM_CH_B2, 0);
    ledcWrite(PWM_CH_C1, speed); ledcWrite(PWM_CH_C2, 0);
    ledcWrite(PWM_CH_D1, speed); ledcWrite(PWM_CH_D2, 0);
}

void omniBackward(int speed) {
    ledcWrite(PWM_CH_A1, 0); ledcWrite(PWM_CH_A2, speed);
    ledcWrite(PWM_CH_B1, 0); ledcWrite(PWM_CH_B2, speed);
    ledcWrite(PWM_CH_C1, 0); ledcWrite(PWM_CH_C2, speed);
    ledcWrite(PWM_CH_D1, 0); ledcWrite(PWM_CH_D2, speed);
}

void omniRotateLeft(int speed) {
    ledcWrite(PWM_CH_A1, speed); ledcWrite(PWM_CH_A2, 0);
    ledcWrite(PWM_CH_B1, 0); ledcWrite(PWM_CH_B2, speed);
    ledcWrite(PWM_CH_C1, 0); ledcWrite(PWM_CH_C2, speed);
    ledcWrite(PWM_CH_D1, speed); ledcWrite(PWM_CH_D2, 0);
}

void omniRotateRight(int speed) {
    ledcWrite(PWM_CH_A1, 0); ledcWrite(PWM_CH_A2, speed);
    ledcWrite(PWM_CH_B1, speed); ledcWrite(PWM_CH_B2, 0);
    ledcWrite(PWM_CH_C1, speed); ledcWrite(PWM_CH_C2, 0);
    ledcWrite(PWM_CH_D1, 0); ledcWrite(PWM_CH_D2, speed);
}

// ============= Line Following (IR Sensors) =============
void initLineSensors() {
    pinMode(IR_LEFT, INPUT);
    pinMode(IR_CENTER, INPUT);
    pinMode(IR_RIGHT, INPUT);
    
    // Color sensor pins
    pinMode(S0, OUTPUT);
    pinMode(S1, OUTPUT);
    pinMode(S2, OUTPUT);
    pinMode(S3, OUTPUT);
    pinMode(OUTPUT_PIN, INPUT);
    
    // Set frequency scaling to 20%
    digitalWrite(S0, LOW);
    digitalWrite(S1, HIGH);
    
    Serial.println("Line Following Sensors initialized");
    Serial.printf("  IR Left: GPIO%d\n", IR_LEFT);
    Serial.printf("  IR Center: GPIO%d\n", IR_CENTER);
    Serial.printf("  IR Right: GPIO%d\n", IR_RIGHT);
    Serial.println("  Color Sensor: TCS3200");
}

// Read color value from TCS3200
long readColorValue() {
    digitalWrite(S2, LOW);
    digitalWrite(S3, LOW);
    long red = pulseIn(OUTPUT_PIN, LOW, 10000);
    
    digitalWrite(S2, HIGH);
    digitalWrite(S3, HIGH);
    long green = pulseIn(OUTPUT_PIN, LOW, 10000);
    
    digitalWrite(S2, LOW);
    digitalWrite(S3, HIGH);
    long blue = pulseIn(OUTPUT_PIN, LOW, 10000);
    
    return (red + green + blue) / 3;
}

// Detect if on blue/black junction (lower values than white)
bool isOnJunction() {
    long colorVal = readColorValue();
    // White tape = high ~5000-30000
    // Blue/Black = low ~1000-3000
    return colorVal < 4000;
}

int readIRSensor(int pin) {
    return digitalRead(pin);
}

bool isOnLine(int pin) {
    // IR sensors read LOW when on white tape (active low)
    return digitalRead(pin) == LOW;
}

// Line Following Algorithm with Junction Detection
void followLine() {
    bool leftOnLine = isOnLine(IR_LEFT);
    bool centerOnLine = isOnLine(IR_CENTER);
    bool rightOnLine = isOnLine(IR_RIGHT);
    
    long distance = getObstacleDistance();
    int aiSpeed = calculateSpeedAI(distance);
    
    if (aiSpeed == 0) {
        stopMotors();
        return;
    }
    
    // Junction Detection - blue/black marker on floor
    bool onJunction = isOnJunction();
    
    if (onJunction && !junctionHandled) {
        atJunction = true;
        stopMotors();
        
        Serial.printf("Junction! Dest: %s, Origin: %s\n", currentDestination.c_str(), originTable.c_str());
        
        // At junction - decide turn based on origin
        if (isReturning) {
            // Returning home - turn based on where we came from
            if (originTable == "table_1") {
                // Came from table 1 - turn LEFT
                omniRotateLeft(SPEED_TURN);
                delay(800);
            } else if (originTable == "table_2") {
                // Came from table 2 - turn RIGHT
                omniRotateRight(SPEED_TURN);
                delay(800);
            }
        } else {
            // Going to deliver
            if (currentDestination == "table_1") {
                // Go to table 1 - turn LEFT
                omniRotateLeft(SPEED_TURN);
                delay(800);
            } else if (currentDestination == "table_2") {
                // Go to table 2 - turn RIGHT
                omniRotateRight(SPEED_TURN);
                delay(800);
            } else if (currentDestination == "kitchen") {
                // Return to kitchen - go straight
            }
        }
        
        stopMotors();
        junctionHandled = true;
        delay(500);
        return;
    }
    
    // Reset junction flag when leaving junction (on white line again)
    if (centerOnLine && junctionHandled) {
        atJunction = false;
    }
    
    // End of line detection - all three IRs see line + we're at destination
    if (leftOnLine && centerOnLine && rightOnLine) {
        // Check destination
        if (currentDestination == "table_1") {
            stopMotors();
            atTable1 = true;
            currentStatus = "arrived_table1";
            sendDeliveryUpdate("delivered");
            digitalWrite(BUZZER_PIN, HIGH);
            delay(200);
            digitalWrite(BUZZER_PIN, LOW);
            currentDestination = "none";
            return;
        }
        else if (currentDestination == "table_2") {
            stopMotors();
            atTable2 = true;
            currentStatus = "arrived_table2";
            sendDeliveryUpdate("delivered");
            digitalWrite(BUZZER_PIN, HIGH);
            delay(200);
            digitalWrite(BUZZER_PIN, LOW);
            currentDestination = "none";
            return;
        }
        else if (currentDestination == "kitchen") {
            stopMotors();
            atKitchen = true;
            currentStatus = "arrived_kitchen";
            sendDeliveryUpdate("completed");
            digitalWrite(BUZZER_PIN, HIGH);
            delay(200);
            digitalWrite(BUZZER_PIN, LOW);
            currentDestination = "none";
            isReturning = false;
            return;
        }
    }
    
    // No line detected
    if (!leftOnLine && !centerOnLine && !rightOnLine) {
        lineLostCounter++;
        
        if (lineLostCounter > 50) {
            // Line lost - search or reverse
            omniBackward(SPEED_TURN);
            delay(200);
            stopMotors();
            lineLostCounter = 0;
        }
        return;
    }
    
    lineLostCounter = 0;
    
    // PID-like line following
    if (centerOnLine) {
        // Perfect - go straight
        omniForward(aiSpeed);
    }
    else if (leftOnLine && !rightOnLine) {
        // Line to the left - turn left
        omniRotateLeft(SPEED_TURN);
    }
    else if (!leftOnLine && rightOnLine) {
        // Line to the right - turn right
        omniRotateRight(SPEED_TURN);
    }
    else if (leftOnLine && rightOnLine) {
        // Intersection - go straight
        omniForward(aiSpeed);
    }
    else {
        // No clear direction - go forward slowly
        omniForward(SPEED_BASE / 2);
    }
}

// ============= Ultrasonic Sensor =============
void initUltrasonic() {
    pinMode(ULTRASONIC_TRIG, OUTPUT);
    pinMode(ULTRASONIC_ECHO, INPUT);
    Serial.println("Ultrasonic initialized");
}

long getDistance() {
    digitalWrite(ULTRASONIC_TRIG, LOW);
    delayMicroseconds(5);
    digitalWrite(ULTRASONIC_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(ULTRASONIC_TRIG, LOW);
    
    long duration = pulseIn(ULTRASONIC_ECHO, HIGH, 30000);
    long distance = duration / 2 / 29.1;
    
    if (distance == 0 || distance > 200) return 200;
    return distance;
}

long getObstacleDistance() {
    return getDistance();
}

bool isObstacleDetected() {
    return getDistance() < OBSTACLE_THRESHOLD_CM;
}

// ============= AI Speed Control =============
int calculateSpeedAI(long distance) {
    if (distance >= SPEED_ZONE_FAR) return MAX_SPEED;
    else if (distance >= SPEED_ZONE_MEDIUM) return (int)(MAX_SPEED * 0.7);
    else if (distance >= SPEED_ZONE_CLOSE) return (int)(MAX_SPEED * 0.4);
    else if (distance >= MIN_OBSTACLE_CM) return (int)(MAX_SPEED * 0.2);
    return 0;
}

String getSpeedZone(long distance) {
    if (distance >= SPEED_ZONE_FAR) return "FAR";
    else if (distance >= SPEED_ZONE_MEDIUM) return "MEDIUM";
    else if (distance >= SPEED_ZONE_CLOSE) return "CLOSE";
    else if (distance >= MIN_OBSTACLE_CM) return "DANGER";
    return "STOP";
}

// ============= Battery Monitoring =============
float getBatteryVoltage() {
    int raw = analogRead(BATTERY_PIN);
    return (raw / 4095.0) * 3.3 * 2.0;
}

int getBatteryPercentage() {
    float voltage = getBatteryVoltage();
    float percentage = (voltage - 6.0) / (8.4 - 6.0) * 100;
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
                        Serial.printf("Command: %s\n", action.c_str());
                        
                        if (action == "navigate_to_table") {
                            currentDestination = doc["data"]["table_id"].as<String>();
                            currentStatus = "delivering";
                            currentDeliveryId = doc["data"]["delivery_id"].as<int>();
                            motorsEnabled = true;
                            lineFollowingEnabled = true;
                            
                            atStation = false;
                            atTable1 = false;
                            atTable2 = false;
                            
                            digitalWrite(BUZZER_PIN, HIGH);
                            delay(100);
                            digitalWrite(BUZZER_PIN, LOW);
                        }
                        else if (action == "return_to_kitchen") {
                            currentDestination = "kitchen";
                            currentStatus = "returning";
                            motorsEnabled = true;
                            lineFollowingEnabled = true;
                            isReturning = true;
                            junctionHandled = false;
                            
                            atStation = false;
                            atTable1 = false;
                            atTable2 = false;
                            atKitchen = false;
                        }
                        else if (action == "go_to_table_1") {
                            currentDestination = "table_1";
                            originTable = "table_1";
                            currentStatus = "delivering";
                            currentDeliveryId = doc["data"]["delivery_id"].as<int>();
                            motorsEnabled = true;
                            lineFollowingEnabled = true;
                            isReturning = false;
                            junctionHandled = false;
                            stopCommandReceived = false;
                            
                            atTable1 = false;
                            atTable2 = false;
                            digitalWrite(BUZZER_PIN, HIGH);
                            delay(100);
                            digitalWrite(BUZZER_PIN, LOW);
                        }
                        else if (action == "go_to_table_2") {
                            currentDestination = "table_2";
                            originTable = "table_2";
                            currentStatus = "delivering";
                            currentDeliveryId = doc["data"]["delivery_id"].as<int>();
                            motorsEnabled = true;
                            lineFollowingEnabled = true;
                            isReturning = false;
                            junctionHandled = false;
                            stopCommandReceived = false;
                            
                            atTable1 = false;
                            atTable2 = false;
                            digitalWrite(BUZZER_PIN, HIGH);
                            delay(100);
                            digitalWrite(BUZZER_PIN, LOW);
                        }
                        else if (action == "stop") {
                            // Pi command: rotate 360 and wait for line
                            currentStatus = "searching";
                            stopCommandReceived = true;
                            lineFollowingEnabled = false;
                            
                            // Rotate 360 to find line
                            for (int i = 0; i < 4; i++) {
                                omniRotateRight(SPEED_TURN);
                                delay(500);
                            }
                            stopMotors();
                            searchingLine = true;
                            
                            digitalWrite(BUZZER_PIN, HIGH);
                            delay(300);
                            digitalWrite(BUZZER_PIN, LOW);
                        }
                        else if (action == "pause") {
                            stopMotors();
                            motorsEnabled = false;
                            lineFollowingEnabled = false;
                        }
                        else if (action == "resume") {
                            stopCommandReceived = false;
                            searchingLine = false;
                            motorsEnabled = true;
                            
                            // After stop: track line + head back
                            if (originTable != "none" && currentDestination == "kitchen") {
                                lineFollowingEnabled = true;
                            } else {
                                lineFollowingEnabled = true;
                            }
                        }
                        else if (action == "go_home") {
                            // Return to origin table
                            currentDestination = originTable;
                            currentStatus = "returning";
                            motorsEnabled = true;
                            lineFollowingEnabled = true;
                            isReturning = true;
                            junctionHandled = false;
                            
                            digitalWrite(BUZZER_PIN, HIGH);
                            delay(100);
                            digitalWrite(BUZZER_PIN, LOW);
                        }
                        
                        JsonDocument ackDoc;
                        ackDoc["type"] = "ACK";
                        ackDoc["device_id"] = ROBOT_UNIQUE_ID;
                        ackDoc["data"]["original_type"] = "COMMAND";
                        ackDoc["data"]["success"] = true;
                        String ackOutput;
                        serializeJson(ackDoc, ackOutput);
                        webSocket.sendTXT(ackOutput);
                    }
                }
            }
            break;
            
        default:
            break;
    }
}

void sendTelemetry() {
    long distance = getObstacleDistance();
    JsonDocument doc;
    doc["type"] = "TELEMETRY";
    doc["device_id"] = ROBOT_UNIQUE_ID;
    doc["data"]["battery_voltage"] = getBatteryVoltage();
    doc["data"]["battery_percentage"] = getBatteryPercentage();
    doc["data"]["current_x"] = currentX;
    doc["data"]["current_y"] = currentY;
    doc["data"]["current_angle"] = currentAngle;
    doc["data"]["status"] = currentStatus;
    doc["data"]["destination"] = currentDestination;
    doc["data"]["ultrasonic_distance"] = distance;
    doc["data"]["ai_speed"] = calculateSpeedAI(distance);
    doc["data"]["speed_zone"] = getSpeedZone(distance);
    doc["data"]["line_following"] = lineFollowingEnabled;
    doc["data"]["at_station"] = atStation;
    doc["data"]["at_table1"] = atTable1;
    doc["data"]["at_table2"] = atTable2;
    
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

// ============= Setup =============
void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("===========================================");
    Serial.println("  Waiter Robot - REX Edition (Line Follow)");
    Serial.println("  Using REX 8in1 Board");
    Serial.printf("  Robot ID: %s\n", ROBOT_UNIQUE_ID);
    Serial.println("===========================================");
    
    Dabble.begin("REX_ROBOT");
    
    initMotors();
    initLineSensors();
    initUltrasonic();
    pinMode(BATTERY_PIN, INPUT);
    
    Serial.println("Hardware initialized");
    
    // WiFi Connection
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
    
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    
    Serial.println("=== Robot Ready (Line Following) ===");
    Serial.println("  Motors: GPIO15,23,32,33,5,4,27,14");
    Serial.println("  Line Sensors: GPIO35,36,39");
    Serial.println("  Ultrasonic: GPIO17,16");
}

// ============= Main Loop =============
void loop() {
    Dabble.processInput();
    webSocket.loop();
    
    // Gamepad control (Dabble)
    if (GamePad.getRadius() >= 1) {
        int angle = GamePad.getAngle();
        int radius = GamePad.getRadius();
        int speed = (radius <= 3) ? SPEED_BASE : (radius <= 5) ? SPEED_TURN : MAX_SPEED;
        
        if (angle > 60 && angle < 120) {
            omniForward(speed);
        } else if (angle > 240 && angle < 300) {
            omniBackward(speed);
        } else if ((angle >= 0 && angle < 30) || (angle > 330 && angle < 360)) {
            omniRotateRight(speed);
        } else if (angle > 150 && angle < 210) {
            omniRotateLeft(speed);
        } else {
            stopMotors();
        }
    }
    // Line following mode
    else if (lineFollowingEnabled && (currentStatus == "delivering" || currentStatus == "returning" || currentStatus == "searching")) {
        // If searching for line after stop command
        if (searchingLine && !stopCommandReceived) {
            bool leftOnLine = isOnLine(IR_LEFT);
            bool centerOnLine = isOnLine(IR_CENTER);
            bool rightOnLine = isOnLine(IR_RIGHT);
            
            if (leftOnLine || centerOnLine || rightOnLine) {
                // Found line - resume following
                searchingLine = false;
                if (originTable != "none") {
                    currentDestination = originTable;
                    isReturning = true;
                    currentStatus = "returning";
                }
            } else {
                // Keep rotating to find line
                omniRotateRight(SPEED_TURN);
            }
        } else {
            followLine();
        }
        
        currentX += 0.005;
        currentY += 0.005;
    }
    else if (stopCommandReceived && searchingLine) {
        // Just rotating to find line
        bool leftOnLine = isOnLine(IR_LEFT);
        bool centerOnLine = isOnLine(IR_CENTER);
        bool rightOnLine = isOnLine(IR_RIGHT);
        
        if (leftOnLine || centerOnLine || rightOnLine) {
            // Found line - stop and wait for next command
            stopMotors();
            searchingLine = false;
            currentStatus = "line_found";
            
            // Send alert to Pi
            webSocket.sendTXT("{\"type\":\"LINE_FOUND\",\"device_id\":\"" + String(ROBOT_UNIQUE_ID) + "\"}");
        } else {
            omniRotateRight(SPEED_TURN);
            delay(100);
            stopMotors();
            delay(50);
        }
    }
    else {
        stopMotors();
    }
    
    // Battery monitoring
    if (getBatteryPercentage() < 20) {
        currentStatus = "charging";
        currentDestination = "kitchen";
        lineFollowingEnabled = true;
    }
    
    // Telemetry
    if (millis() - lastTelemetryTime > 2000) {
        sendTelemetry();
        lastTelemetryTime = millis();
    }
    
    delay(20);
}