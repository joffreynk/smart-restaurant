/*
 * Restaurant Waiter Robot - Arduino Code
 * Line following robot with omni wheels
 * Connects to server via WiFi and Socket.IO
 * 
 * Hardware:
 * - ESP32 or ESP8266
 * - Line sensors (3x TCRT5000 or similar)
 * - Ultrasonic sensor (HC-SR04)
 * - Buzzer
 * - Motor drivers for omni wheels
 */

#include <WiFi.h>
#include <SocketIOClient.h>
#include <ArduinoJson.h>

// ==================== CONFIGURATION ====================
#define WIFI_SSID "Your_WiFi_SSID"
#define WIFI_PASSWORD "Your_WiFi_Password"
#define SERVER_HOST "192.168.1.100"  // Change to your server IP
#define SERVER_PORT 5000

// ==================== PIN DEFINITIONS ====================
// Line sensors (analog)
#define LEFT_SENSOR_PIN 34
#define CENTER_SENSOR_PIN 35
#define RIGHT_SENSOR_PIN 36

// Ultrasonic sensor
#define TRIG_PIN 5
#define ECHO_PIN 18

// Buzzer
#define BUZZER_PIN 4

// Motor pins (adjust for your setup)
#define MOTOR_A_PWM 12
#define MOTOR_A_DIR 14
#define MOTOR_B_PWM 27
#define MOTOR_B_DIR 26
#define MOTOR_C_PWM 33
#define MOTOR_C_DIR 25

// ==================== GLOBAL VARIABLES ====================
SocketIOClient socketClient;
WiFiClient wifiClient;

// Robot state
enum RobotState {
    IDLE,
    AT_KITCHEN,
    MOVING_TO_TABLE,
    AT_TABLE,
    WAITING_PICKUP,
    RETURNING_HOME,
    AT_HOME
};

RobotState currentState = IDLE;
String robotId = "";
String deviceId = "ROBOT_001";  // Unique robot identifier

// Delivery command data
struct DeliveryCommand {
    String commandId;
    int orderId;
    int tableId;
    int tableNumber;
    String tableName;
    String junctionTurn;  // "left", "straight", "right"
    String junctionReturn; // "opposite"
    int buzzerDuration;
    int loadingWait;
    int customerPickupWait;
    String homePattern;
};

DeliveryCommand currentDelivery;

// Line sensor thresholds (adjust based on your floor/line)
const int WHITE_LINE_THRESHOLD = 500;  // Below = line, Above = floor
const int RED_LINE_THRESHOLD = 800;    // High value = red line

// ==================== SETUP ====================
void setup() {
    Serial.begin(115200);
    
    // Initialize pins
    pinMode(LEFT_SENSOR_PIN, INPUT);
    pinMode(CENTER_SENSOR_PIN, INPUT);
    pinMode(RIGHT_SENSOR_PIN, INPUT);
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    
    pinMode(MOTOR_A_PWM, OUTPUT);
    pinMode(MOTOR_A_DIR, OUTPUT);
    pinMode(MOTOR_B_PWM, OUTPUT);
    pinMode(MOTOR_B_DIR, OUTPUT);
    pinMode(MOTOR_C_PWM, OUTPUT);
    pinMode(MOTOR_C_DIR, OUTPUT);
    
    digitalWrite(BUZZER_PIN, LOW);
    
    // Connect to WiFi
    connectWiFi();
    
    // Connect to server
    connectServer();
}

// ==================== MAIN LOOP ====================
void loop() {
    // Handle socket events
    if (socketClient.monitor()) {
        processServerMessage();
    }
    
    // Run robot based on state
    switch (currentState) {
        case IDLE:
            // Wait for commands
            break;
            
        case AT_KITCHEN:
            // Wait for delivery command
            break;
            
        case MOVING_TO_TABLE:
            followLineToTable();
            break;
            
        case AT_TABLE:
            // Wait for customer pickup
            waitForCustomerPickup();
            break;
            
        case RETURNING_HOME:
            followLineToHome();
            break;
            
        case AT_HOME:
            // Ready for next delivery
            currentState = AT_KITCHEN;
            break;
    }
    
    // Check ultrasonic sensor for obstacles
    checkObstacles();
    
    delay(10);  // Small delay
}

// ==================== WIFI CONNECTION ====================
void connectWiFi() {
    Serial.println("Connecting to WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected!");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nWiFi connection failed!");
    }
}

void connectServer() {
    Serial.println("Connecting to server...");
    
    if (socketClient.connect(SERVER_HOST, SERVER_PORT)) {
        Serial.println("Connected to server!");
        
        // Register robot
        socketClient.emit("robot_ready_for_delivery", "{\"device_id\": \"" + deviceId + "\"}");
        
        // Set namespace/room
        socketClient.emit("register", "{\"robot_id\": 1}");
    } else {
        Serial.println("Server connection failed!");
    }
}

// ==================== SOCKET MESSAGE HANDLING ====================
void processServerMessage() {
    // Get the event name and data
    String eventName = socketClient.getEventName();
    String eventData = socketClient.getData();
    
    Serial.print("Event: ");
    Serial.println(eventName);
    Serial.print("Data: ");
    Serial.println(eventData);
    
    // Parse JSON data
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, eventData);
    
    if (error) {
        Serial.println("JSON parse error!");
        return;
    }
    
    // Handle different events
    if (eventName == "delivery_command") {
        handleDeliveryCommand(doc.as<JsonObject>());
    }
    else if (eventName == "return_command") {
        handleReturnCommand(doc.as<JsonObject>());
    }
}

// ==================== DELIVERY COMMAND ====================
void handleDeliveryCommand(JsonObject data) {
    Serial.println("=== DELIVERY COMMAND RECEIVED ===");
    
    // Store delivery info
    currentDelivery.commandId = data["command_id"] | "";
    currentDelivery.orderId = data["order_id"] | 0;
    currentDelivery.tableId = data["table_id"] | 0;
    currentDelivery.tableNumber = data["table_number"] | 0;
    currentDelivery.tableName = data["table_name"] | "";
    currentDelivery.junctionTurn = data["junction_turn"] | "straight";
    currentDelivery.junctionReturn = data["junction_return"] | "opposite";
    currentDelivery.buzzerDuration = data["buzzer_duration"] | 3;
    currentDelivery.loadingWait = data["loading_wait"] | 5;
    currentDelivery.customerPickupWait = data["customer_pickup_wait"] | 10;
    
    Serial.print("Table: ");
    Serial.println(currentDelivery.tableName);
    Serial.print("Turn at junction: ");
    Serial.println(currentDelivery.junctionTurn);
    
    // Start delivery sequence
    startDeliveryToTable();
}

void startDeliveryToTable() {
    // 1. Buzzer at kitchen
    buzzer(currentDelivery.buzzerDuration);
    
    // 2. Wait for chef to load (5 seconds)
    delay(currentDelivery.loadingWait * 1000);
    
    // 3. Start moving to table
    currentState = MOVING_TO_TABLE;
}

// ==================== LINE FOLLOWING ====================
void followLineToTable() {
    int left = analogRead(LEFT_SENSOR_PIN);
    int center = analogRead(CENTER_SENSOR_PIN);
    int right = analogRead(RIGHT_SENSOR_PIN);
    
    Serial.print("Sensors - L: ");
    Serial.print(left);
    Serial.print(" C: ");
    Serial.print(center);
    Serial.print(" R: ");
    Serial.println(right);
    
    // Check for red line (table reached)
    if (right > RED_LINE_THRESHOLD || left > RED_LINE_THRESHOLD) {
        stopMotors();
        Serial.println("Red line detected - Table reached!");
        arrivedAtTable();
        return;
    }
    
    // Check for junction (all sensors on white - crossing point)
    bool atJunction = (left < WHITE_LINE_THRESHOLD && center < WHITE_LINE_THRESHOLD && right < WHITE_LINE_THRESHOLD);
    
    if (atJunction) {
        handleJunction(currentDelivery.junctionTurn);
    } else {
        // Normal line following
        if (center < WHITE_LINE_THRESHOLD) {
            // On line - go straight
            moveForward(150);
        } else if (left < WHITE_LINE_THRESHOLD && center > WHITE_LINE_THRESHOLD) {
            // Line is to left - turn left
            turnLeft(100);
        } else if (right < WHITE_LINE_THRESHOLD && center > WHITE_LINE_THRESHOLD) {
            // Line is to right - turn right
            turnRight(100);
        } else {
            // Lost line - stop and search
            stopMotors();
            searchForLine();
        }
    }
}

void handleJunction(String turnDirection) {
    Serial.print("At junction - turning: ");
    Serial.println(turnDirection);
    
    // Stop briefly at junction
    stopMotors();
    delay(200);
    
    // Turn based on direction
    if (turnDirection == "left") {
        rotate90Left();
    } else if (turnDirection == "right") {
        rotate90Right();
    } else {
        // Straight - continue
        moveForward(150);
    }
    
    delay(500);
}

void arriveAtTable() {
    currentState = AT_TABLE;
    
    // Notify server
    socketClient.emit("delivery_arrived", 
        "{\"robot_id\": 1, \"order_id\": " + String(currentDelivery.orderId) + 
        ", \"table_id\": " + String(currentDelivery.tableId) + "}");
    
    // Start wait timer
    startPickupWaitTimer();
}

void startPickupWaitTimer() {
    Serial.print("Waiting ");
    Serial.print(currentDelivery.customerPickupWait);
    Serial.println(" seconds for customer pickup...");
    
    delay(currentDelivery.customerPickupWait * 1000);
    
    // Pickup time complete
    completeDelivery();
}

void completeDelivery() {
    Serial.println("Delivery complete - returning to kitchen");
    
    currentState = RETURNING_HOME;
    
    // Notify server
    socketClient.emit("delivery_completed",
        "{\"robot_id\": 1, \"order_id\": " + String(currentDelivery.orderId) + "}");
}

// ==================== RETURN HOME ====================
void followLineToHome() {
    int left = analogRead(LEFT_SENSOR_PIN);
    int center = analogRead(CENTER_SENSOR_PIN);
    int right = analogRead(RIGHT_SENSOR_PIN);
    
    Serial.print("Return - L: ");
    Serial.print(left);
    Serial.print(" C: ");
    Serial.print(center);
    Serial.print(" R: ");
    Serial.println(right);
    
    // Check for home pattern: black/blue then white twice
    static int homePatternCount = 0;
    static bool lastWasBlack = false;
    
    bool isBlackOrBlue = (left > 700 && center > 700 && right > 700);  // Dark color
    bool isWhite = (left < 300 && center < 300 && right < 300);       // White line
    
    if (isBlackOrBlue) {
        lastWasBlack = true;
    } else if (lastWasBlack && isWhite) {
        homePatternCount++;
        lastWasBlack = false;
        Serial.print("Home pattern: ");
        Serial.println(homePatternCount);
        
        if (homePatternCount >= 2) {
            arrivedAtHome();
            return;
        }
    }
    
    // Check for junction
    bool atJunction = (left < WHITE_LINE_THRESHOLD && center < WHITE_LINE_THRESHOLD && right < WHITE_LINE_THRESHOLD);
    
    if (atJunction) {
        // Turn opposite of forward direction
        if (currentDelivery.junctionReturn == "opposite") {
            if (currentDelivery.junctionTurn == "left") {
                rotate90Right();
            } else if (currentDelivery.junctionTurn == "right") {
                rotate90Left();
            }
            // straight stays straight
        }
        delay(500);
    } else {
        // Normal line following (reverse)
        if (center < WHITE_LINE_THRESHOLD) {
            moveForward(150);
        } else if (left < WHITE_LINE_THRESHOLD && center > WHITE_LINE_THRESHOLD) {
            turnRight(100);
        } else if (right < WHITE_LINE_THRESHOLD && center > WHITE_LINE_THRESHOLD) {
            turnLeft(100);
        }
    }
}

void arrivedAtHome() {
    stopMotors();
    Serial.println("=== HOME REACHED ===");
    
    currentState = AT_HOME;
    
    // Notify server
    socketClient.emit("robot_home_arrived", "{\"robot_id\": 1}");
}

// ==================== MOTOR CONTROL ====================
void moveForward(int speed) {
    digitalWrite(MOTOR_A_DIR, HIGH);
    analogWrite(MOTOR_A_PWM, speed);
    digitalWrite(MOTOR_B_DIR, HIGH);
    analogWrite(MOTOR_B_PWM, speed);
    digitalWrite(MOTOR_C_DIR, HIGH);
    analogWrite(MOTOR_C_PWM, speed);
}

void moveBackward(int speed) {
    digitalWrite(MOTOR_A_DIR, LOW);
    analogWrite(MOTOR_A_PWM, speed);
    digitalWrite(MOTOR_B_DIR, LOW);
    analogWrite(MOTOR_B_PWM, speed);
    digitalWrite(MOTOR_C_DIR, LOW);
    analogWrite(MOTOR_C_PWM, speed);
}

void turnLeft(int speed) {
    digitalWrite(MOTOR_A_DIR, LOW);
    analogWrite(MOTOR_A_PWM, speed);
    digitalWrite(MOTOR_B_DIR, HIGH);
    analogWrite(MOTOR_B_PWM, speed);
    digitalWrite(MOTOR_C_DIR, HIGH);
    analogWrite(MOTOR_C_PWM, speed / 2);
}

void turnRight(int speed) {
    digitalWrite(MOTOR_A_DIR, HIGH);
    analogWrite(MOTOR_A_PWM, speed);
    digitalWrite(MOTOR_B_DIR, LOW);
    analogWrite(MOTOR_B_PWM, speed);
    digitalWrite(MOTOR_C_DIR, LOW);
    analogWrite(MOTOR_C_PWM, speed / 2);
}

void rotate90Left() {
    // Rotate 90 degrees left using omni wheels
    digitalWrite(MOTOR_A_DIR, LOW);
    analogWrite(MOTOR_A_PWM, 150);
    digitalWrite(MOTOR_B_DIR, HIGH);
    analogWrite(MOTOR_B_PWM, 150);
    digitalWrite(MOTOR_C_DIR, HIGH);
    analogWrite(MOTOR_C_PWM, 0);
    delay(400);  // Adjust timing for 90 degrees
    stopMotors();
}

void rotate90Right() {
    // Rotate 90 degrees right using omni wheels
    digitalWrite(MOTOR_A_DIR, HIGH);
    analogWrite(MOTOR_A_PWM, 150);
    digitalWrite(MOTOR_B_DIR, LOW);
    analogWrite(MOTOR_B_PWM, 150);
    digitalWrite(MOTOR_C_DIR, LOW);
    analogWrite(MOTOR_C_PWM, 0);
    delay(400);  // Adjust timing for 90 degrees
    stopMotors();
}

void stopMotors() {
    analogWrite(MOTOR_A_PWM, 0);
    analogWrite(MOTOR_B_PWM, 0);
    analogWrite(MOTOR_C_PWM, 0);
}

void searchForLine() {
    // Simple search - rotate and look for line
    Serial.println("Searching for line...");
    for (int i = 0; i < 20; i++) {
        turnRight(80);
        delay(50);
        if (analogRead(CENTER_SENSOR_PIN) < WHITE_LINE_THRESHOLD) {
            stopMotors();
            return;
        }
    }
    stopMotors();
}

// ==================== ULTRASONIC ====================
void checkObstacles() {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);
    
    long duration = pulseIn(ECHO_PIN, HIGH);
    int distance = duration * 0.034 / 2;
    
    if (distance < 10 && distance > 0) {
        Serial.print("OBSTACLE DETECTED at ");
        Serial.print(distance);
        Serial.println("cm");
        
        // Stop and alert
        stopMotors();
        
        // Notify server
        socketClient.emit("ultrasonic_alert", 
            "{\"robot_id\": 1, \"distance\": " + String(distance) + "}");
        
        // Wait for obstacle to clear
        delay(1000);
    }
}

// ==================== BUZZER ====================
void buzzer(int durationSeconds) {
    Serial.print("Buzzer: ");
    Serial.print(durationSeconds);
    Serial.println(" seconds");
    
    for (int i = 0; i < durationSeconds; i++) {
        for (int j = 0; j < 10; j++) {
            digitalWrite(BUZZER_PIN, HIGH);
            delay(100);
            digitalWrite(BUZZER_PIN, LOW);
            delay(100);
        }
    }
}

// ==================== SOCKET RECONNECT ====================
void handleReturnCommand(JsonObject data) {
    Serial.println("=== RETURN COMMAND RECEIVED ===");
    
    currentDelivery.junctionReturn = data["junction_return"] | "opposite";
    
    // Start returning home
    currentState = RETURNING_HOME;
}

// Reconnection check
void checkConnection() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi disconnected - reconnecting...");
        connectWiFi();
    }
    
    // Heartbeat to server
    socketClient.emit("ping", "{\"robot_id\": 1}");
}