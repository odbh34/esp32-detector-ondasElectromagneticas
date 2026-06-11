# Detector Electromagnético ESP32 + Dashboard PC

**Alumno:** Oscar David Barrientos Huillca - 225419

Sistema IoT de detección de dispositivos electrónicos no autorizados mediante escaneo WiFi y BLE. El ESP32 escanea redes WiFi y dispositivos Bluetooth Low Energy, calcula distancias estimadas usando el modelo Log-Distance Path Loss, clasifica niveles de amenaza (INFO/WARNING/CRITICAL) y envía los resultados por Serial a un **dashboard PC** desarrollado en Python con CustomTkinter, diseñado para entornos de admisión y supervisión de exámenes.

---

## Capturas

> *(Agregar capturas aquí — dashboard, detección de dispositivos, alertas)*

---

## Estructura del Proyecto

```
detector-electromagnetico/
├── src/
│   └── main.cpp                       # Firmware ESP32 (PlatformIO)
│
├── dashboard.py                       # Dashboard PC v1 (CustomTkinter)
├── dashboard_v2.py                    # Dashboard PC v2 + OUI + MAC aleatorias
├── dashboard_v3.py                    # Dashboard PC v3 + detección ISP/Hotspot
├── oui_db.py                          # Base de datos OUI offline (~500 fabricantes)
│
├── platformio.ini                     # Configuración ESP32 + ArduinoJson + NimBLE
│
├── logs_emf/                          # Sesiones de escaneo (CSV + logs)
│   ├── scan_*.csv                     # Datos crudos de detecciones
│   └── session_*.txt                  # Registro de eventos en sesión
│
├── include/                           # PlatformIO placeholder
├── lib/                               # PlatformIO placeholder
└── test/                              # PlatformIO placeholder
```

---

## Arquitectura del Sistema

```
ESP32 (WiFi + BLE Scanner)
       │
       │ Serial (JSON) @ 115200 baud
       │ Protocolo: SCAN_REPORT, HEARTBEAT, BOOT, ACK, etc.
       │ Comandos: SET_MODEL, SET_THRESHOLDS, CALIBRATE, etc.
       ▼
┌──────────────────────────┐
│   Dashboard PC (Python)  │
│   CustomTkinter UI       │
│                          │
│   • Tabla de dispositivos│
│   • Alertas sonoras/visuales
│   • Exportación CSV      │
│   • Calibración en vivo  │
│   • Lista blanca (SSID/MAC)
│   • Identificación OUI   │
│   • Detección ISP/Hotspot│
│   • Perfil de riesgo     │
└──────────────────────────┘
```

| Capa | Tecnología |
|---|---|
| Hardware | ESP32 WROOM-32 DevKit |
| Firmware | C++ con Arduino Framework |
| Escaneo WiFi | Modo station + promiscuo (canales 1-13) |
| Escaneo BLE | NimBLE-Arduino (escaneo pasivo) |
| Modelo de distancia | Log-Distance Path Loss |
| Dashboard | Python 3.12 + CustomTkinter |
| Base de datos OUI | Offline (~500 fabricantes) |
| Comunicación | Serial (JSON asíncrono) |
| Logging | CSV por sesión + log de eventos |

---

## Firmware ESP32

El firmware implementa un escáner dual WiFi + BLE con clasificación en tiempo real:

| Componente | Descripción |
|---|---|
| WiFi Scan | Escaneo periódico de redes (canales 1-13), captura SSID, MAC, RSSI |
| BLE Scan | Escaneo pasivo de dispositivos Bluetooth Low Energy |
| Distancia estimada | Modelo Log-Distance Path Loss: `d = 10^((TxPower - RSSI) / (10 * n))` |
| Clasificación | CRITICAL (< -50 dBm / < 2m), WARNING (< -70 dBm / < 5m), INFO |
| Whitelist | Hasta 20 SSIDs WiFi + 20 MACs BLE (configurables desde dashboard) |
| Heartbeat | Envío periódico de estado cada 5s |
| Comunicación | JSON sobre Serial a 115200 baud |

### Pines

| Pin ESP32 | Función |
|---|---|
| GPIO 2 | LED de alerta |
| GPIO 4 | LED de estado |
| GPIO 26 | Buzzer |

---

## Dashboard PC (Python)

Tres versiones del dashboard con funcionalidad incremental:

### v1 — Básico
- UI oscura con CustomTkinter
- Conexión serial (auto-detección de puerto)
- Tabla de dispositivos con colores por nivel
- Alertas sonoras (tonos sintéticos con pygame)
- Panel de logs con exportación CSV
- Configuración de modelo, thresholds y whitelist

### v2 — Identificación de fabricantes
- **OUI Lookup**: identifica el fabricante desde la MAC
- **MAC aleatorias**: detecta MAC aleatorizadas (iOS 14+ / Android 10+)
- **Redes ocultas**: detecta SSIDs reportados como `[Oculto]`
- **Ventana de detalle**: doble clic en dispositivo para ver:
  - Información del dispositivo
  - Señal RF (gráfico de barras)
  - Análisis de riesgo
- **Perfil de riesgo**: HIGH / MEDIUM / LOW según fabricante

### v3 — Detección de ISP/Hotspot
- **Detección de ISP**: identifica SSID de operadores (Claro, Movistar, Entel, Bitel, Tigo, WOM, Izzi, Telmex, etc.)
- **Detección de Hotspot personal**: iPhone/iPad, Samsung Galaxy, Xiaomi/Redmi/POCO, Huawei, Honor, Motorola, Google Pixel, OnePlus, LG, Tecno, Infinix, Oppo, Vivo, etc.
- **Hotspot** se marca como **CRITICAL** (máxima alerta en contexto de examen)
- **OUI de ISP** como respaldo cuando la MAC es conocida

---

## Base de Datos OUI

`oui_db.py` contiene una base de datos offline con más de **1500 OUIs** mapeados a fabricantes:

| Fabricante | OUIs cubiertos |
|---|---|
| Apple | ~200 |
| Samsung | ~150 |
| Huawei | ~120 |
| Xiaomi | ~32 |
| Intel | ~130 |
| Qualcomm/Atheros | ~80 |
| Realtek | ~60 |
| MediaTek | ~30 |
| Espressif (ESP32) | ~15 |
| Motorola, OnePlus, Google, Lenovo, Dell, HP, ASUS, etc. | Varios |

Funciones principales:
- `lookup_manufacturer(mac)` → `(fabricante, es_mac_aleatoria)`
- `infer_from_ssid(ssid, fabricante)` → inferencia desde nombre de red
- `get_device_risk_profile(mac, mac_aleatoria, tipo_señal)` → perfil de riesgo contextual

---

## Clasificación de Amenazas

| Nivel | RSSI | Distancia | Color | Interpretación |
|---|---|---|---|---|
| **CRITICAL** | < -50 dBm | < 2 m | 🔴 Rojo | Dispositivo muy cercano — alta probabilidad de uso no autorizado |
| **WARNING** | < -70 dBm | < 5 m | 🟡 Amarillo | Dispositivo cercano — posible riesgo |
| **INFO** | ≥ -70 dBm | ≥ 5 m | 🟢 Verde/Info | Dispositivo lejano o de baja prioridad |
| **WHITELIST** | — | — | ⚪ Blanco | Dispositivo en lista blanca (ignorado) |
| **HOTSPOT** | — | — | 🔴 Rojo | Hotspot personal — máximo riesgo en examen |

---

## Protocolo de Comunicación (Serial)

### Mensajes ESP32 → PC

| Tipo | Descripción |
|---|---|
| `BOOT` | Inicio del ESP32 con firmware versión |
| `SCAN_REPORT` | Resultado de escaneo WiFi/BLE con lista de dispositivos |
| `HEARTBEAT` | Estado periódico (cada 5s) |
| `ACK` | Confirmación de comando recibido |
| `CALIBRATION_RESULT` | Resultado de calibración de TxPower/n |
| `STATUS` | Estado actual del sistema |

### Comandos PC → ESP32

| Comando | Descripción |
|---|---|
| `SET_MODEL` | Configurar TxPower y exponente `n` |
| `SET_THRESHOLDS` | Configurar umbrales RSSI/distancia |
| `ADD_WIFI_WL` | Agregar SSID a whitelist |
| `ADD_BLE_WL` | Agregar MAC BLE a whitelist |
| `CLEAR_WL` | Limpiar whitelist |
| `CALIBRATE` | Iniciar calibración |
| `GET_STATUS` | Solicitar estado actual |

---

## Instalación y Uso

### Firmware ESP32 (PlatformIO)

```bash
# Clonar repositorio y abrir en VS Code con PlatformIO
git clone <repo-url>
cd detector-electromagnetico

# Compilar y subir
pio run --target upload

# Monitor serial
pio device monitor --baud 115200
```

### Dashboard PC

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows

# Instalar dependencias
pip install customtkinter pyserial pygame Pillow

# Ejecutar (última versión recomendada)
python dashboard_v3.py
```

---

## Dependencias

### Firmware (PlatformIO)

```ini
lib_deps =
    bblanchon/ArduinoJson @ ^7.4.3
    h2zero/NimBLE-Arduino
```

### Dashboard (Python)

```
customtkinter >= 5.2.0
pyserial >= 3.5
pygame >= 2.5
Pillow >= 10.0
```

---

## Comandos Útiles

```bash
# Monitor serial directo
pio device monitor --baud 115200

# Logs de escaneo (últimas detecciones)
tail -f logs_emf/scan_$(date +%Y%m%d)*.csv

# Exportar CSV manualmente (desde dashboard: botón Export)
```

---

## Características

- Escaneo simultáneo WiFi + BLE desde un solo ESP32
- Modelo Log-Distance Path Loss con TxPower y exponente `n` configurables
- Clasificación CRITICAL / WARNING / INFO con umbrales ajustables
- Whitelist de hasta 20 SSIDs + 20 MACs
- Dashboard con tabla en tiempo real, alertas sonoras y visuales
- Identificación de fabricante por OUI (~1500 entradas)
- Detección de MAC aleatorizadas (iOS 14+ / Android 10+)
- Detección de redes ocultas
- Detección de ISP y Hotspot personal para contexto de examen
- Perfil de riesgo contextual (HIGH / MEDIUM / LOW)
- Exportación CSV por sesión
- Ventana de detalle con análisis de señal y riesgo
- Filtro por nivel de amenaza en tabla

---

## Limitaciones y Pendientes

- Comunicación por Serial (no WiFi/remoto)
- Sin almacenamiento persistente en el ESP32
- Rango limitado del escaneo BLE (~10 m en interiores)
- Sin autenticación ni cifrado
- Sin historial persistente en dashboard (solo CSV)
- Sin app móvil (por ahora solo dashboard PC)
- Sin soporte multi-ESP32
- Sin integración cloud (pendiente para AWS)
- Sin HTTPS ni API REST (planeado para versión cloud)
