/*
 * ============================================================
 *  DETECTOR DE ONDAS ELECTROMAGNÉTICAS - ESP32
 *  Sistema de detección para concursos de admisión
 * ============================================================
 *  FIXES v1.1:
 *    - Prototipos de funciones agregados (fix error de orden)
 *    - ArduinoJson v7: StaticJsonDocument → JsonDocument
 *    - ArduinoJson v7: createNestedArray → doc[key].to<JsonArray>()
 *    - ArduinoJson v7: createNestedObject → array.add<JsonObject>()
 *    - ArduinoJson v7: containsKey → doc[key].is<T>()
 * ============================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <ArduinoJson.h>
#include <esp_wifi.h>
#include <esp_bt.h>

// ─────────────────────────────────────────────
//  CONFIGURACIÓN DE PINES
// ─────────────────────────────────────────────
#define PIN_BUZZER      26
#define PIN_LED_ALERT   2
#define PIN_LED_STATUS  4

// ─────────────────────────────────────────────
//  MODELO LOG-DISTANCE PATH LOSS
// ─────────────────────────────────────────────
struct PathLossModel {
  float txPower_wifi;
  float txPower_ble;
  float txPower_bt;
  float n_open;
  float n_indoor;
  float n_current;
};

PathLossModel model = {
  .txPower_wifi  = -59.0f,
  .txPower_ble   = -59.0f,
  .txPower_bt    = -59.0f,
  .n_open        = 2.0f,
  .n_indoor      = 3.0f,
  .n_current     = 2.7f
};

// ─────────────────────────────────────────────
//  UMBRALES DE ALERTA
// ─────────────────────────────────────────────
struct AlertThresholds {
  int   rssi_critical;
  int   rssi_warning;
  float dist_critical;
  float dist_warning;
  int   max_known_networks;
};

AlertThresholds thresholds = {
  .rssi_critical      = -50,
  .rssi_warning       = -70,
  .dist_critical      = 2.0f,
  .dist_warning       = 5.0f,
  .max_known_networks = 0
};

// ─────────────────────────────────────────────
//  WHITELIST
// ─────────────────────────────────────────────
#define MAX_WHITELIST 20
String wifiWhitelist[MAX_WHITELIST];
String bleWhitelist[MAX_WHITELIST];
int wifiWhitelistCount = 0;
int bleWhitelistCount  = 0;

// ─────────────────────────────────────────────
//  ESTADO GLOBAL
// ─────────────────────────────────────────────
enum SystemState { STATE_IDLE, STATE_SCANNING, STATE_ALERT_WARN, STATE_ALERT_CRITICAL, STATE_CALIBRATING };
SystemState currentState = STATE_IDLE;

struct ScanResult {
  String  ssid;
  String  mac;
  int     rssi;
  float   distance;
  String  type;
  String  level;
  bool    whitelisted;
};

#define MAX_RESULTS 50
ScanResult results[MAX_RESULTS];
int resultCount = 0;

// ─────────────────────────────────────────────
//  INTERVALOS
// ─────────────────────────────────────────────
#define WIFI_SCAN_INTERVAL_MS   3000
#define BLE_SCAN_DURATION_SEC   2
#define BLE_SCAN_INTERVAL_MS    4000
#define HEARTBEAT_INTERVAL_MS   1000

unsigned long lastWifiScan  = 0;
unsigned long lastBleScan   = 0;
unsigned long lastHeartbeat = 0;

// ─────────────────────────────────────────────
//  PROTOTIPOS — CRÍTICO: evita el error de orden
//  "not declared in this scope" en MyBLECallbacks
// ─────────────────────────────────────────────
float  rssiToDistance(int rssi, float txPower);
int    distanceToRSSI(float distance, float txPower);
String classifyLevel(int rssi, float dist, bool whitelisted);
bool   isWifiWhitelisted(const String& ssid);
bool   isBluetoothWhitelisted(const String& mac);
void   addWifiWhitelist(const String& ssid);
void   addBleWhitelist(const String& mac);
void   beepCritical();
void   beepWarning();
void   beepInfo();
void   updateLED();
void   doWifiScan();
void   doBleScan();
void   sendScanReport();
void   sendHeartbeat();
void   sendAck(const String& cmd, bool ok, const String& msg = "");
void   processCommand(const String& jsonStr);

// ─────────────────────────────────────────────
//  BLE SCANNER
// ─────────────────────────────────────────────
BLEScan* pBLEScan = nullptr;

class MyBLECallbacks : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    if (resultCount >= MAX_RESULTS) return;

    String mac  = String(advertisedDevice.getAddress().toString().c_str());
    String name = advertisedDevice.haveName() ?
                  String(advertisedDevice.getName().c_str()) : "Desconocido";
    int    rssi = advertisedDevice.getRSSI();
    float  dist = rssiToDistance(rssi, model.txPower_ble);
    bool   wl   = isBluetoothWhitelisted(mac);

    ScanResult r;
    r.ssid        = name;
    r.mac         = mac;
    r.rssi        = rssi;
    r.distance    = dist;
    r.type        = "BLE";
    r.whitelisted = wl;
    r.level       = classifyLevel(rssi, dist, wl);

    results[resultCount++] = r;
  }
};

MyBLECallbacks bleCallbacks;

// ─────────────────────────────────────────────
//  MODELO MATEMÁTICO
// ─────────────────────────────────────────────
float rssiToDistance(int rssi, float txPower) {
  if (rssi == 0) return -1.0f;
  float ratio = (txPower - (float)rssi) / (10.0f * model.n_current);
  return pow(10.0f, ratio);
}

int distanceToRSSI(float distance, float txPower) {
  if (distance <= 0) return 0;
  return (int)(txPower - 10.0f * model.n_current * log10(distance));
}

String classifyLevel(int rssi, float dist, bool whitelisted) {
  if (whitelisted) return "INFO";
  if (rssi >= thresholds.rssi_critical || dist <= thresholds.dist_critical) return "CRITICAL";
  if (rssi >= thresholds.rssi_warning  || dist <= thresholds.dist_warning)  return "WARNING";
  return "INFO";
}

// ─────────────────────────────────────────────
//  WHITELIST
// ─────────────────────────────────────────────
bool isWifiWhitelisted(const String& ssid) {
  for (int i = 0; i < wifiWhitelistCount; i++) {
    if (wifiWhitelist[i] == ssid) return true;
  }
  return false;
}

bool isBluetoothWhitelisted(const String& mac) {
  String macLower = mac;
  macLower.toLowerCase();
  for (int i = 0; i < bleWhitelistCount; i++) {
    if (bleWhitelist[i] == macLower) return true;
  }
  return false;
}

void addWifiWhitelist(const String& ssid) {
  if (wifiWhitelistCount < MAX_WHITELIST)
    wifiWhitelist[wifiWhitelistCount++] = ssid;
}

void addBleWhitelist(const String& mac) {
  if (bleWhitelistCount < MAX_WHITELIST) {
    String m = mac;
    m.toLowerCase();
    bleWhitelist[bleWhitelistCount++] = m;
  }
}

// ─────────────────────────────────────────────
//  ALERTAS
// ─────────────────────────────────────────────
void beepCritical() {
  for (int i = 0; i < 3; i++) {
    ledcWriteTone(0, 2000); delay(100);
    ledcWriteTone(0, 0);    delay(80);
  }
}

void beepWarning() {
  ledcWriteTone(0, 1200); delay(200);
  ledcWriteTone(0, 0);
}

void beepInfo() {
  ledcWriteTone(0, 800); delay(80);
  ledcWriteTone(0, 0);
}

void updateLED() {
  switch (currentState) {
    case STATE_ALERT_CRITICAL: digitalWrite(PIN_LED_ALERT, HIGH); break;
    case STATE_ALERT_WARN:     digitalWrite(PIN_LED_ALERT, millis() % 500 < 250); break;
    case STATE_SCANNING:       digitalWrite(PIN_LED_ALERT, millis() % 1000 < 100); break;
    default:                   digitalWrite(PIN_LED_ALERT, LOW); break;
  }
}

// ─────────────────────────────────────────────
//  ESCANEO WIFI
// ─────────────────────────────────────────────
void doWifiScan() {
  int n = WiFi.scanNetworks(false, true, false, 100);
  if (n <= 0) return;

  for (int i = 0; i < n && resultCount < MAX_RESULTS; i++) {
    String ssid = WiFi.SSID(i);
    String mac  = WiFi.BSSIDstr(i);
    int    rssi = WiFi.RSSI(i);
    float  dist = rssiToDistance(rssi, model.txPower_wifi);
    bool   wl   = isWifiWhitelisted(ssid);

    ScanResult r;
    r.ssid        = ssid.length() > 0 ? ssid : "[Oculto]";
    r.mac         = mac;
    r.rssi        = rssi;
    r.distance    = dist;
    r.type        = "WIFI";
    r.whitelisted = wl;
    r.level       = classifyLevel(rssi, dist, wl);

    results[resultCount++] = r;
  }
  WiFi.scanDelete();
}

// ─────────────────────────────────────────────
//  ESCANEO BLE
// ─────────────────────────────────────────────
void doBleScan() {
  if (pBLEScan == nullptr) return;
  pBLEScan->clearResults();
  pBLEScan->start(BLE_SCAN_DURATION_SEC, false);
}

// ─────────────────────────────────────────────
//  ENVÍO DE DATOS — ArduinoJson v7
// ─────────────────────────────────────────────
void sendScanReport() {
  String worstLevel = "INFO";
  int criticalCount = 0, warningCount = 0;

  for (int i = 0; i < resultCount; i++) {
    if (!results[i].whitelisted) {
      if (results[i].level == "CRITICAL") {
        criticalCount++;
        worstLevel = "CRITICAL";
      } else if (results[i].level == "WARNING" && worstLevel != "CRITICAL") {
        warningCount++;
        worstLevel = "WARNING";
      }
    }
  }

  if (criticalCount > 0) {
    if (currentState != STATE_ALERT_CRITICAL) beepCritical();
    currentState = STATE_ALERT_CRITICAL;
  } else if (warningCount > 0) {
    if (currentState != STATE_ALERT_WARN) beepWarning();
    currentState = STATE_ALERT_WARN;
  } else {
    currentState = STATE_SCANNING;
  }

  JsonDocument doc;
  doc["type"]           = "SCAN_REPORT";
  doc["timestamp"]      = millis();
  doc["total"]          = resultCount;
  doc["critical_count"] = criticalCount;
  doc["warning_count"]  = warningCount;
  doc["status"]         = worstLevel;
  doc["model"]["txPower_wifi"] = model.txPower_wifi;
  doc["model"]["txPower_ble"]  = model.txPower_ble;
  doc["model"]["n"]            = model.n_current;

  JsonArray devs = doc["devices"].to<JsonArray>();          // v7
  for (int i = 0; i < resultCount; i++) {
    JsonObject d = devs.add<JsonObject>();                  // v7
    d["ssid"]        = results[i].ssid;
    d["mac"]         = results[i].mac;
    d["rssi"]        = results[i].rssi;
    d["distance"]    = serialized(String(results[i].distance, 2));
    d["type"]        = results[i].type;
    d["level"]       = results[i].level;
    d["whitelisted"] = results[i].whitelisted;
  }

  serializeJson(doc, Serial);
  Serial.println();
}

void sendHeartbeat() {
  JsonDocument doc;
  doc["type"]      = "HEARTBEAT";
  doc["timestamp"] = millis();
  doc["state"]     = (int)currentState;
  doc["free_heap"] = ESP.getFreeHeap();
  serializeJson(doc, Serial);
  Serial.println();
}

void sendAck(const String& cmd, bool ok, const String& msg) {
  JsonDocument doc;
  doc["type"] = "ACK";
  doc["cmd"]  = cmd;
  doc["ok"]   = ok;
  if (msg.length() > 0) doc["msg"] = msg;
  serializeJson(doc, Serial);
  Serial.println();
}

// ─────────────────────────────────────────────
//  COMANDOS DESDE PC
// ─────────────────────────────────────────────
void processCommand(const String& jsonStr) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, jsonStr);
  if (err) { sendAck("PARSE_ERROR", false, err.c_str()); return; }

  String cmd = doc["cmd"].as<String>();

  if (cmd == "SET_MODEL") {
    if (doc["txPower_wifi"].is<float>()) model.txPower_wifi = doc["txPower_wifi"]; // v7
    if (doc["txPower_ble"].is<float>())  model.txPower_ble  = doc["txPower_ble"];
    if (doc["n"].is<float>())            model.n_current    = doc["n"];
    sendAck(cmd, true, "Modelo actualizado");

  } else if (cmd == "SET_THRESHOLDS") {
    if (doc["rssi_critical"].is<int>())   thresholds.rssi_critical = doc["rssi_critical"];
    if (doc["rssi_warning"].is<int>())    thresholds.rssi_warning  = doc["rssi_warning"];
    if (doc["dist_critical"].is<float>()) thresholds.dist_critical = doc["dist_critical"];
    if (doc["dist_warning"].is<float>())  thresholds.dist_warning  = doc["dist_warning"];
    sendAck(cmd, true, "Umbrales actualizados");

  } else if (cmd == "ADD_WIFI_WL") {
    addWifiWhitelist(doc["ssid"].as<String>());
    sendAck(cmd, true, "SSID agregado a whitelist");

  } else if (cmd == "ADD_BLE_WL") {
    addBleWhitelist(doc["mac"].as<String>());
    sendAck(cmd, true, "MAC BLE agregada a whitelist");

  } else if (cmd == "CLEAR_WL") {
    wifiWhitelistCount = 0;
    bleWhitelistCount  = 0;
    sendAck(cmd, true, "Whitelist limpiada");

  } else if (cmd == "CALIBRATE") {
    float  distance   = doc["distance"] | 1.0f;
    int    rssi       = doc["rssi"]     | -59;
    String type       = doc["type"]     | "WIFI";
    float  newTxPower = rssi + 10.0f * model.n_current * log10(distance);

    if      (type == "WIFI") model.txPower_wifi = newTxPower;
    else if (type == "BLE")  model.txPower_ble  = newTxPower;
    else if (type == "BT")   model.txPower_bt   = newTxPower;

    JsonDocument resp;
    resp["type"]          = "CALIBRATION_RESULT";
    resp["new_txPower"]   = newTxPower;
    resp["distance_used"] = distance;
    resp["rssi_used"]     = rssi;
    resp["signal_type"]   = type;
    resp["rssi_at_1m"]    = distanceToRSSI(1.0f, newTxPower);
    serializeJson(resp, Serial);
    Serial.println();

  } else if (cmd == "GET_STATUS") {
    JsonDocument resp;
    resp["type"]  = "STATUS";
    resp["state"] = (int)currentState;
    resp["model"]["txPower_wifi"] = model.txPower_wifi;
    resp["model"]["txPower_ble"]  = model.txPower_ble;
    resp["model"]["n"]            = model.n_current;
    resp["thresholds"]["rssi_critical"] = thresholds.rssi_critical;
    resp["thresholds"]["rssi_warning"]  = thresholds.rssi_warning;
    resp["whitelist"]["wifi_count"] = wifiWhitelistCount;
    resp["whitelist"]["ble_count"]  = bleWhitelistCount;
    serializeJson(resp, Serial);
    Serial.println();

  } else {
    sendAck(cmd, false, "Comando desconocido");
  }
}

// ─────────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(PIN_LED_ALERT, OUTPUT);
  pinMode(PIN_LED_STATUS, OUTPUT);
  ledcSetup(0, 2000, 8);
  ledcAttachPin(PIN_BUZZER, 0);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  BLEDevice::init("ESP32-EMF-Detector");
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(&bleCallbacks, false);
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);

  JsonDocument boot;
  boot["type"]    = "BOOT";
  boot["version"] = "1.1.0";
  boot["msg"]     = "ESP32 EMF Detector listo";
  serializeJson(boot, Serial);
  Serial.println();

  beepInfo();
  digitalWrite(PIN_LED_STATUS, HIGH);
  currentState = STATE_SCANNING;
}

// ─────────────────────────────────────────────
//  LOOP PRINCIPAL
// ─────────────────────────────────────────────
void loop() {
  unsigned long now = millis();

  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0 && line[0] == '{') {
      processCommand(line);
    }
  }

  if (now - lastWifiScan >= WIFI_SCAN_INTERVAL_MS) {
    lastWifiScan = now;
    resultCount  = 0;
    doWifiScan();
  }

  if (now - lastBleScan >= BLE_SCAN_INTERVAL_MS) {
    lastBleScan = now;
    doBleScan();
    sendScanReport();
  }

  if (now - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeat = now;
    sendHeartbeat();
  }

  updateLED();
  delay(10);
}