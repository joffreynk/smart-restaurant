/*
 * Waiter Robot - HTTP Polling Version
 * Configurable via Serial (USB) on first boot
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include "config.h"

HTTPClient http;

// Configuration stored in EEPROM-like storage (using NVS on ESP32)
#include <Preferences.h>
Preferences preferences;

String robotStatus = "idle";
unsigned long lastTelemetry = 0;
String configSSID, configPassword, configMasterHost;
bool configured = false;
IPAddress masterIP;  // Resolved IP address
bool ipResolved = false;

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("=== WAITER ROBOT START ===");
    
    // Initialize motor pins
    pinMode(MotorA1, OUTPUT);
    pinMode(MotorA2, OUTPUT);
    pinMode(MotorB1, OUTPUT);
    pinMode(MotorB2, OUTPUT);
    pinMode(MotorC1, OUTPUT);
    pinMode(MotorC2, OUTPUT);
    pinMode(MotorD1, OUTPUT);
    pinMode(MotorD2, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    
    // Initialize preferences
    preferences.begin("waiter-robot", false);
    
    // Check if configured
    configSSID = preferences.getString("ssid", "");
    configPassword = preferences.getString("password", "");
    configMasterHost = preferences.getString("master_host", "");
    
    if (configSSID.length() == 0) {
        // First boot - enter configuration mode
        Serial.println("NO CONFIGURATION FOUND");
        Serial.println("Enter WiFi credentials via Serial:");
        Serial.println("SSID:");
        while (!Serial.available()) delay(100);
        configSSID = Serial.readStringUntil('\n');
        configSSID.trim();
        
        Serial.println("Password:");
        while (!Serial.available()) delay(100);
        configPassword = Serial.readStringUntil('\n');
        configPassword.trim();
        
        Serial.println("Master hostname (e.g., smart-restaurant.local or IP):");
        Serial.println("Default: smart-restaurant");
        while (!Serial.available()) delay(100);
        configMasterHost = Serial.readStringUntil('\n');
        configMasterHost.trim();
        if (configMasterHost.length() == 0) {
            configMasterHost = "smart-restaurant";
        }
        
        // Save to preferences
        preferences.putString("ssid", configSSID);
        preferences.putString("password", configPassword);
        preferences.putString("master_host", configMasterHost);
        
        Serial.println("Configuration saved!");
        Serial.print("SSID: "); Serial.println(configSSID);
        Serial.print("Master: "); Serial.println(configMasterHost);
        delay(2000);
    } else {
        Serial.print("Loaded config - SSID: ");
        Serial.println(configSSID);
        Serial.print("Master: ");
        Serial.println(configMasterHost);
    }
    
    configured = true;
    connectWiFi();
}

void connectWiFi() {
    if (!configured) return;
    
    Serial.print("Connecting to WiFi: ");
    Serial.println(configSSID);
    WiFi.begin(configSSID.c_str(), configPassword.c_str());
    
    int count = 0;
    while (WiFi.status() != WL_CONNECTED && count < 30) {
        delay(500);
        Serial.print(".");
        count++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nOK!");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
        
        // Resolve master hostname to IP
        resolveMasterIP();
    } else {
        Serial.println("\nFAILED!");
        Serial.println("Restarting to reconfigure...");
        delay(2000);
        ESP.restart();
    }
}

void resolveMasterIP() {
    Serial.print("Resolving master host: ");
    Serial.println(configMasterHost);
    
    // Try to resolve hostname to IP
    IPAddress resolvedIP;
    if (WiFi.hostByName(configMasterHost.c_str(), resolvedIP)) {
        masterIP = resolvedIP;
        ipResolved = true;
        Serial.print("Master IP resolved: ");
        Serial.println(masterIP);
    } else {
        // Try with .local suffix for mDNS
        String hostnameWithLocal = configMasterHost + ".local";
        Serial.print("Trying mDNS: ");
        Serial.println(hostnameWithLocal);
        if (WiFi.hostByName(hostnameWithLocal.c_str(), resolvedIP)) {
            masterIP = resolvedIP;
            ipResolved = true;
            Serial.print("Master IP (mDNS) resolved: ");
            Serial.println(masterIP);
        } else {
            Serial.println("DNS resolution failed - using hostname directly in HTTP");
            ipResolved = false;
        }
    }
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        static unsigned long lastAttempt = 0;
        if (millis() - lastAttempt > 5000) {
            lastAttempt = millis();
            connectWiFi();
            ipResolved = false;  // Force re-resolve after reconnection
        }
    }
    
    // Send telemetry every 3s
    if (millis() - lastTelemetry > 3000 && WiFi.status() == WL_CONNECTED) {
        lastTelemetry = millis();
        
        // Resolve IP if needed (after WiFi connect or periodically in case of DHCP change)
        if (!ipResolved) {
            resolveMasterIP();
        }
        
        // Build master URL using resolved IP or hostname
        String masterAddr = ipResolved ? masterIP.toString() : configMasterHost;
        String url = "http://" + masterAddr + ":3000/api/robot/telemetry";
        
        http.begin(url);
        http.addHeader("Content-Type", "application/json");
        String payload = "{\"device_id\":\"" ROBOT_UNIQUE_ID "\",\"status\":\"" + robotStatus + "\"}";
        int code = http.POST(payload);
        Serial.print("POST telemetry: ");
        Serial.println(code);
        http.end();
        
        // GET commands from master
        url = "http://" + masterAddr + ":3000/api/robot/" ROBOT_UNIQUE_ID "/command";
        http.begin(url);
        code = http.GET();
        if (code > 0) {
            String response = http.getString();
            if (response.length() > 2) {
                Serial.print("CMD response: ");
                Serial.println(response);
                if (response.indexOf("deliver") >= 0) robotStatus = "delivering";
                else if (response.indexOf("return") >= 0) robotStatus = "returning";
                else if (response.indexOf("stop") >= 0) robotStatus = "stopped";
            }
        } else {
            Serial.print("GET command failed: ");
            Serial.println(code);
        }
        http.end();
    }
    
    delay(10);
}
