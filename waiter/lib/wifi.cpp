#include <Arduino.h>
#include <WiFi.h>
#include <WebSockets.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

void webSocketEvent(WStype_t type, uint8_t* payload, size_t length);

class WaiterWiFi {
private:
    WebSocketsClient ws;
    const char* ssid;
    const char* password;
    const char* serverIP;
    uint16_t serverPort;
    
public:
    WaiterWiFi(const char* ssid, const char* password, const char* serverIP, uint16_t port)
        : ws(), ssid(ssid), password(password), serverIP(serverIP), serverPort(port) {}
    
    bool begin() {
        WiFi.begin(ssid, password);
        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 30) {
            delay(500);
            attempts++;
        }
        
        if (WiFi.status() == WL_CONNECTED) {
            ws.begin(serverIP, serverPort, "/");
            ws.onEvent(webSocketEvent);
            ws.setReconnectInterval(5000);
            return true;
        }
        return false;
    }
    
    void loop() {
        ws.loop();
    }
    
    bool isConnected() {
        return WiFi.status() == WL_CONNECTED;
    }
    
    void sendMessage(const String& message) {
        ws.sendTXT(message);
    }
    
    void sendTelemetry(float voltage, int percentage, float x, float y, float angle, const String& status) {
        JsonDocument doc;
        doc["type"] = "TELEMETRY";
        doc["device_id"] = ROBOT_UNIQUE_ID;
        doc["data"]["battery_voltage"] = voltage;
        doc["data"]["battery_percentage"] = percentage;
        doc["data"]["current_x"] = x;
        doc["data"]["current_y"] = y;
        doc["data"]["current_angle"] = angle;
        doc["data"]["status"] = status;
        
        String output;
        serializeJson(doc, output);
        ws.sendTXT(output);
    }
    
    void sendDeliveryUpdate(int deliveryId, const String& status) {
        JsonDocument doc;
        doc["type"] = "delivery_update";
        doc["device_id"] = ROBOT_UNIQUE_ID;
        doc["delivery_id"] = deliveryId;
        doc["status"] = status;
        
        String output;
        serializeJson(doc, output);
        ws.sendTXT(output);
    }
};

WaiterWiFi* wifiClient = nullptr;

void initWiFi(const char* ssid, const char* password, const char* serverIP, uint16_t port) {
    wifiClient = new WaiterWiFi(ssid, password, serverIP, port);
    if (wifiClient->begin()) {
        Serial.println("WiFi and WebSocket connected");
    }
}

void loopWiFi() {
    if (wifiClient) {
        wifiClient->loop();
    }
}