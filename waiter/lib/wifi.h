#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

class WiFiClient {
private:
    WebSocketsClient* wsClient;
    const char* ssid;
    const char* password;
    const char* serverIP;
    uint16_t serverPort;
    bool connected;
    void (*messageCallback)(String);
    void (*statusCallback)(String);
    
public:
    WiFiClient(const char* ssid, const char* password, const char* serverIP, uint16_t port);
    void begin();
    bool connectToWiFi();
    void setWebSocketCallbacks(void (*msgCb)(String), void (*statusCb)(String));
    void sendTelemetry(float battery, int percentage, float x, float y, float angle, String status);
    void sendStatus(String status, int orderId = -1, String currentAction = "");
    void sendDeliveryUpdate(int deliveryId, String status);
    void sendCommandAck(String commandId, bool success);
    void handleEvents();
    bool isConnected();
};

class RobotCommunication {
private:
    WiFiClient* wifi;
    String deviceId;
    String deviceName;
    unsigned long lastHeartbeat;
    unsigned long heartbeatInterval;
    bool registered;
    
public:
    RobotCommunication(String id, String name);
    void begin();
    bool connect();
    void update(float battery, int percentage, float x, float y, float angle, String status);
    void sendCommandResponse(String commandId, bool success, String message = "");
    void sendDeliveryStatus(int deliveryId, String status);
    void processMessage(String message);
    bool isReady();
};

class StateSync {
private:
    String lastKnownState;
    unsigned long lastSyncTime;
    bool needsSync;
    
public:
    StateSync();
    void updateState(String newState);
    bool shouldSync();
    void markSynced();
    String getLastState();
};

class RobotProtocol {
public:
    static String createTelemetryMessage(String deviceId, float battery, int percentage, float x, float y, float angle, String status);
    static String createStatusMessage(String deviceId, String status, int orderId, String action);
    static String createDeliveryMessage(String deviceId, int deliveryId, String status);
    static String createAckMessage(String commandId, bool success);
    static String createRegisterMessage(String deviceId, String deviceType);
    static bool parseCommand(String json, String& action, float& targetX, float& targetY, String& pathJson);
};