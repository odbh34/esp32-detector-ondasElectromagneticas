"""
Servidor EMF en EC2
- Puerto 8765: recibe datos del relay.py (PC local con ESP32)
- Puerto 80:   Apache sirve el HTML estático
- El HTML se conecta también al 8765 para recibir datos en tiempo real
"""
import asyncio, json, time, os
from datetime import datetime
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

# ── Estado global ──────────────────────────────
class State:
    def __init__(self):
        self.relay_ws    = None        # conexión del relay.py (PC)
        self.browsers: Set[WebSocket] = set()
        self.last_scan   = {}
        self.scan_count  = 0
        self.relay_online = False
        os.makedirs("logs", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = f"logs/session_{ts}.jsonl"

    def log(self, data):
        with open(self.log_path, "a") as f:
            f.write(json.dumps({"ts": time.time(), **data}) + "\n")

state = State()

async def broadcast(msg: str):
    dead = set()
    for ws in state.browsers:
        try:    await ws.send_text(msg)
        except: dead.add(ws)
    state.browsers -= dead

# ── Relay (PC con ESP32) se conecta aquí ──────
@app.websocket("/esp32")
async def relay_endpoint(ws: WebSocket):
    await ws.accept()
    state.relay_ws     = ws
    state.relay_online = True
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Relay conectado desde {ws.client.host}")
    await broadcast(json.dumps({"type":"RELAY_STATUS","online":True,"ts":time.time()}))
    try:
        while True:
            raw  = await ws.receive_text()
            data = json.loads(raw)
            if data.get("type") == "SCAN_REPORT":
                state.scan_count += 1
                state.last_scan   = data
                state.log(data)
                data["scan_number"] = state.scan_count
                data["server_ts"]   = time.time()
            await broadcast(json.dumps(data))
    except (WebSocketDisconnect, Exception) as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Relay desconectado: {e}")
    finally:
        state.relay_ws     = None
        state.relay_online = False
        await broadcast(json.dumps({"type":"RELAY_STATUS","online":False,"ts":time.time()}))

# ── Navegadores se conectan aquí ──────────────
@app.websocket("/ws")
async def browser_endpoint(ws: WebSocket):
    await ws.accept()
    state.browsers.add(ws)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🖥  Navegador: {ws.client.host}")
    # Enviar estado actual
    await ws.send_text(json.dumps({
        "type":         "SERVER_HELLO",
        "relay_online": state.relay_online,
        "scan_count":   state.scan_count,
        "last_scan":    state.last_scan,
        "ts":           time.time()
    }))
    try:
        while True:
            # Comandos del dashboard → reenviar al relay → ESP32
            raw = await ws.receive_text()
            if state.relay_ws:
                try:    await state.relay_ws.send_text(raw)
                except: pass
            else:
                await ws.send_text(json.dumps({"type":"ERROR","msg":"Relay no conectado"}))
    except WebSocketDisconnect:
        pass
    finally:
        state.browsers.discard(ws)

# ── API estado ────────────────────────────────
@app.get("/api/status")
async def status():
    return {
        "relay_online": state.relay_online,
        "scan_count":   state.scan_count,
        "browsers":     len(state.browsers),
        "last_scan_ts": state.last_scan.get("timestamp"),
    }

if __name__ == "__main__":
    print("="*50)
    print("  EMF RELAY SERVER - EC2")
    print("="*50)
    print("  Puerto 8765 → relay.py (tu PC) + navegadores")
    print("  Puerto 80   → Apache sirve el HTML")
    print("="*50)
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")