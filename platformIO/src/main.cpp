/*
 * ============================================================
 *  DETECTOR EMF - VERSIÓN EC2
 *  ESP32 → WiFi → WebSocket → EC2 AWS (Apache proxy)
 * ============================================================
 *  Usa NimBLE en lugar de BLE nativo para reducir tamaño:
 *    BLE nativo  = ~1.2 MB
 *    NimBLE      = ~150 KB  ← 8x más liviano
 *
 *  platformio.ini:
 *    board_build.partitions = min_spiffs.csv
 *    lib_deps =
 *      bblanchon/ArduinoJson @ ^7.0.0
 *      links2004/WebSockets @ ^2.4.0
 *      h2zero/NimBLE-Arduino @ ^1.4.0
 *    build_flags = -Os -DCONFIG_BT_NIMBLE_ENABLED=1
 * ============================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// NimBLE — reemplaza al BLE nativo
#include <NimBLEDevice.h>
#include <NimBLEScan.h>
#include <NimBLEAdvertisedDevice.h>

// ─────────────────────────────────────────────
//  *** CONFIGURAR ANTES DE SUBIR ***
// ─────────────────────────────────────────────
#define WIFI_SSID       "tu_red"
#define WIFI_PASSWORD   "tu_password"
#define EC2_HOST        "IP_DEL_EC2"
#define EC2_PORT        8765
#define EC2_PATH        "/esp32"

// ─────────────────────────────────────────────
//  PINES
// ─────────────────────────────────────────────
#define PIN_BUZZER  26
#define PIN_LED     2

// ─────────────────────────────────────────────
//  MODELO LOG-DISTANCE PATH LOSS
// ─────────────────────────────────────────────
float TXPOWER_WIFI  = -59.0f;
float TXPOWER_BLE   = -59.0f;
float N_FACTOR      = 2.7f;
int   RSSI_CRITICAL = -50;
int   RSSI_WARNING  = -70;

// ─────────────────────────────────────────────
//  FORWARD DECLARATIONS
// ─────────────────────────────────────────────
void processCommand(const String& jsonStr);
void connectWifi();
void sendReport();

// ─────────────────────────────────────────────
//  MODELO MATEMÁTICO
// ─────────────────────────────────────────────
float rssiToDistance(int rssi, float txPower) {
  if (rssi == 0) return -1.0f;
  return pow(10.0f, (txPower - (float)rssi) / (10.0f * N_FACTOR));
}

String classifyLevel(int rssi, float dist, bool whitelisted) {
  if (whitelisted)                            return "INFO";
  if (rssi >= RSSI_CRITICAL || dist <= 2.0f) return "CRITICAL";
  if (rssi >= RSSI_WARNING  || dist <= 5.0f) return "WARNING";
  return "INFO";
}

// ─────────────────────────────────────────────
//  WHITELIST
// ─────────────────────────────────────────────
#define MAX_WL 20
String wifiWL[MAX_WL]; int wifiWLCount = 0;
String bleWL[MAX_WL];  int bleWLCount  = 0;

bool inWifiWL(const String& s) {
  for (int i = 0; i < wifiWLCount; i++) if (wifiWL[i] == s) return true;
  return false;
}
bool inBleWL(const String& s) {
  String sl = s; sl.toLowerCase();
  for (int i = 0; i < bleWLCount; i++) if (bleWL[i] == sl) return true;
  return false;
}

// ─────────────────────────────────────────────
//  WEBSOCKET
// ─────────────────────────────────────────────
WebSocketsClient ws;
bool wsConnected = false;

void onWsEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      wsConnected = true;
      Serial.println("[WS] Conectado al EC2");
      digitalWrite(PIN_LED, HIGH);
      break;
    case WStype_DISCONNECTED:
      wsConnected = false;
      Serial.println("[WS] Desconectado, reintentando...");
      digitalWrite(PIN_LED, LOW);
      break;
    case WStype_TEXT:
      processCommand(String((char*)payload));
      break;
    default: break;
  }
}

void sendJson(JsonDocument& doc) {
  if (!wsConnected) return;
  String out;
  serializeJson(doc, out);
  ws.sendTXT(out);
}

// ─────────────────────────────────────────────
//  RESULTADOS
// ─────────────────────────────────────────────
#define MAX_RESULTS 50
struct ScanResult {
  String ssid, mac, type, level;
  int    rssi, channel;
  float  distance;
  bool   whitelisted;
};
ScanResult results[MAX_RESULTS];
int resultCount = 0;

// ─────────────────────────────────────────────
//  NimBLE CALLBACKS
// ─────────────────────────────────────────────
NimBLEScan* pBLEScan = nullptr;

class BLECallbacks : public NimBLEAdvertisedDeviceCallbacks {
  void onResult(NimBLEAdvertisedDevice* dev) {
    if (resultCount >= MAX_RESULTS) return;
    String mac  = String(dev->getAddress().toString().c_str());
    String name = dev->haveName() ? String(dev->getName().c_str()) : "Desconocido";
    int    rssi = dev->getRSSI();
    float  dist = rssiToDistance(rssi, TXPOWER_BLE);
    bool   wl   = inBleWL(mac);
    results[resultCount++] = {name, mac, "BLE", classifyLevel(rssi,dist,wl), rssi, 0, dist, wl};
  }
} bleCallbacks;

// ─────────────────────────────────────────────
//  ESCANEO WIFI
// ─────────────────────────────────────────────
void doWifiScan() {
  WiFi.scanNetworks(true, true, false, 100);
  delay(2000);
  int n = WiFi.scanComplete();
  if (n < 0) n = 0;
  for (int i = 0; i < n && resultCount < MAX_RESULTS; i++) {
    String ssid = WiFi.SSID(i);
    String mac  = WiFi.BSSIDstr(i);
    int    rssi = WiFi.RSSI(i);
    int    ch   = WiFi.channel(i);
    float  dist = rssiToDistance(rssi, TXPOWER_WIFI);
    bool   wl   = inWifiWL(ssid);
    results[resultCount++] = {
      ssid.length() > 0 ? ssid : "[Oculto]",
      mac, "WIFI", classifyLevel(rssi,dist,wl),
      rssi, ch, dist, wl
    };
  }
  WiFi.scanDelete();
}

// ─────────────────────────────────────────────
//  ESCANEO BLE (NimBLE)
// ─────────────────────────────────────────────
void doBleScan() {
  if (!pBLEScan) return;
  pBLEScan->clearResults();
  pBLEScan->start(2, false);
}

// ─────────────────────────────────────────────
//  ENVIAR REPORTE
// ─────────────────────────────────────────────
void sendReport() {
  if (!wsConnected) return;

  int critCount = 0, warnCount = 0;
  String worstLevel = "INFO";
  for (int i = 0; i < resultCount; i++) {
    if (!results[i].whitelisted) {
      if      (results[i].level == "CRITICAL")                             { critCount++; worstLevel = "CRITICAL"; }
      else if (results[i].level == "WARNING" && worstLevel != "CRITICAL")  { warnCount++; worstLevel = "WARNING";  }
    }
  }

  if (critCount > 0) {
    for (int i = 0; i < 3; i++) { ledcWriteTone(0,2000); delay(100); ledcWriteTone(0,0); delay(80); }
  } else if (warnCount > 0) {
    ledcWriteTone(0,1200); delay(200); ledcWriteTone(0,0);
  }

  JsonDocument doc;
  doc["type"]           = "SCAN_REPORT";
  doc["timestamp"]      = millis();
  doc["uptime_s"]       = millis() / 1000;
  doc["total"]          = resultCount;
  doc["critical_count"] = critCount;
  doc["warning_count"]  = warnCount;
  doc["status"]         = worstLevel;
  doc["wifi_ip"]        = WiFi.localIP().toString();
  doc["rssi_wifi"]      = WiFi.RSSI();
  doc["model"]["txPower_wifi"] = TXPOWER_WIFI;
  doc["model"]["txPower_ble"]  = TXPOWER_BLE;
  doc["model"]["n"]            = N_FACTOR;

  JsonArray devs = doc["devices"].to<JsonArray>();
  for (int i = 0; i < resultCount; i++) {
    JsonObject d = devs.add<JsonObject>();
    d["ssid"]        = results[i].ssid;
    d["mac"]         = results[i].mac;
    d["rssi"]        = results[i].rssi;
    d["channel"]     = results[i].channel;
    d["distance"]    = String(results[i].distance, 2);
    d["type"]        = results[i].type;
    d["level"]       = results[i].level;
    d["whitelisted"] = results[i].whitelisted;
  }

  sendJson(doc);
  Serial.printf("[SCAN] %d dispositivos | %s\n", resultCount, worstLevel.c_str());
}

// ─────────────────────────────────────────────
//  COMANDOS
// ─────────────────────────────────────────────
void processCommand(const String& jsonStr) {
  JsonDocument doc;
  if (deserializeJson(doc, jsonStr)) return;
  String cmd = doc["cmd"].as<String>();

  if (cmd == "SET_MODEL") {
    if (doc["txPower_wifi"].is<float>()) TXPOWER_WIFI = doc["txPower_wifi"];
    if (doc["txPower_ble"].is<float>())  TXPOWER_BLE  = doc["txPower_ble"];
    if (doc["n"].is<float>())            N_FACTOR     = doc["n"];
    Serial.println("[CMD] Modelo actualizado");

  } else if (cmd == "SET_THRESHOLDS") {
    if (doc["rssi_critical"].is<int>()) RSSI_CRITICAL = doc["rssi_critical"];
    if (doc["rssi_warning"].is<int>())  RSSI_WARNING  = doc["rssi_warning"];
    Serial.println("[CMD] Umbrales actualizados");

  } else if (cmd == "ADD_WIFI_WL") {
    if (wifiWLCount < MAX_WL) wifiWL[wifiWLCount++] = doc["ssid"].as<String>();

  } else if (cmd == "ADD_BLE_WL") {
    if (bleWLCount < MAX_WL) {
      String m = doc["mac"].as<String>(); m.toLowerCase();
      bleWL[bleWLCount++] = m;
    }
  } else if (cmd == "CLEAR_WL") {
    wifiWLCount = 0; bleWLCount = 0;

  } else if (cmd == "CALIBRATE") {
    float  dist       = doc["distance"] | 1.0f;
    int    rssi       = doc["rssi"]     | -59;
    String tp         = doc["type"]     | "WIFI";
    float  newTxPower = rssi + 10.0f * N_FACTOR * log10(dist);
    if (tp == "WIFI") TXPOWER_WIFI = newTxPower;
    else              TXPOWER_BLE  = newTxPower;

    JsonDocument resp;
    resp["type"]        = "CALIBRATION_RESULT";
    resp["new_txPower"] = newTxPower;
    resp["rssi_at_1m"]  = (int)newTxPower;
    sendJson(resp);
  }
}

// ─────────────────────────────────────────────
//  CONEXIÓN WIFI
// ─────────────────────────────────────────────
void connectWifi() {
  Serial.printf("[WiFi] Conectando a %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 30) {
    delay(500); Serial.print("."); tries++;
    digitalWrite(PIN_LED, !digitalRead(PIN_LED));
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Conectado! IP: %s\n", WiFi.localIP().toString().c_str());
    digitalWrite(PIN_LED, LOW);
  } else {
    Serial.println("\n[WiFi] ERROR. Reintentando...");
  }
}

// ─────────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(PIN_LED, OUTPUT);
  ledcSetup(0, 2000, 8);
  ledcAttachPin(PIN_BUZZER, 0);

  connectWifi();

  ws.begin(EC2_HOST, EC2_PORT, EC2_PATH);
  ws.onEvent(onWsEvent);
  ws.setReconnectInterval(3000);
  ws.enableHeartbeat(15000, 3000, 2);

  // NimBLE — mismo API pero mucho más liviano
  NimBLEDevice::init("ESP32-EMF");
  pBLEScan = NimBLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(&bleCallbacks, false);
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);

  Serial.printf("[INFO] EC2: %s:%d%s\n", EC2_HOST, EC2_PORT, EC2_PATH);
  ledcWriteTone(0, 1000); delay(150); ledcWriteTone(0, 0);
}

// ─────────────────────────────────────────────
//  LOOP
// ─────────────────────────────────────────────
#define WIFI_SCAN_MS  4000
#define BLE_SCAN_MS   5000
#define HEARTBEAT_MS  2000
#define WIFI_CHECK_MS 10000

unsigned long lastWifi = 0, lastBle = 0, lastHB = 0, lastWifiCheck = 0;

void loop() {
  ws.loop();
  unsigned long now = millis();

  if (now - lastWifiCheck >= WIFI_CHECK_MS) {
    lastWifiCheck = now;
    if (WiFi.status() != WL_CONNECTED) connectWifi();
  }

  if (now - lastWifi >= WIFI_SCAN_MS) {
    lastWifi    = now;
    resultCount = 0;
    doWifiScan();
  }

  if (now - lastBle >= BLE_SCAN_MS) {
    lastBle = now;
    doBleScan();
    sendReport();
  }

  if (now - lastHB >= HEARTBEAT_MS) {
    lastHB = now;
    if (wsConnected) {
      JsonDocument hb;
      hb["type"]      = "HEARTBEAT";
      hb["ts"]        = millis();
      hb["heap"]      = ESP.getFreeHeap();
      hb["wifi_rssi"] = WiFi.RSSI();
      sendJson(hb);
    }
  }

  if (!wsConnected) {
    digitalWrite(PIN_LED, (now % 300 < 150) ? HIGH : LOW);
  }
}