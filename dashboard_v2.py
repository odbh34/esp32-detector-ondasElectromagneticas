#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   DASHBOARD v2 - DETECTOR EMF ESP32                             ║
║   Sistema de detección para concursos de admisión               ║
║   + Identificación de fabricante por OUI                        ║
║   + Detección de MAC aleatoria (privacidad)                     ║
║   + Análisis de redes ocultas                                   ║
║   + Panel de detalle por dispositivo                            ║
╚══════════════════════════════════════════════════════════════════╝
Requiere:
    pip install pyserial customtkinter pygame

Archivos necesarios en la misma carpeta:
    oui_db.py   (base de datos de fabricantes)

Uso:
    python dashboard_v2.py
    python dashboard_v2.py --port COM3
    python dashboard_v2.py --port /dev/ttyUSB0
"""

import sys, os, json, time, csv, threading, argparse, math
from datetime import datetime
from collections import deque
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

# ── OUI database (debe estar en la misma carpeta) ──────────────
try:
    from oui_db import lookup_manufacturer, get_device_risk_profile
    OUI_OK = True
except ImportError:
    OUI_OK = False
    def lookup_manufacturer(mac): return "Desconocido", False
    def get_device_risk_profile(m, r, t): return {"device_type":"?","risk":"MEDIUM","note":"Sin OUI DB"}

try:
    import serial, serial.tools.list_ports
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False

try:
    import pygame
    SOUND_OK = True
except ImportError:
    SOUND_OK = False

# ──────────────────────────────────────────────
#  COLORES
# ──────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

C_BG        = "#0D1117"
C_SURFACE   = "#161B22"
C_SURFACE2  = "#1C2128"
C_BORDER    = "#30363D"
C_TEXT      = "#E6EDF3"
C_MUTED     = "#8B949E"
C_CRITICAL  = "#FF4444"
C_WARNING   = "#FFA500"
C_INFO      = "#3FB950"
C_ACCENT    = "#58A6FF"
C_WHITELIST = "#7C8CF8"
C_RANDOM    = "#FF6B9D"   # Color especial para MAC aleatoria
C_HIDDEN    = "#C9A227"   # Color para redes ocultas

# ──────────────────────────────────────────────
#  MODELO MATEMÁTICO
# ──────────────────────────────────────────────
def rssi_to_distance(rssi, tx_power, n):
    if rssi == 0: return -1.0
    return round(10 ** ((tx_power - rssi) / (10.0 * n)), 2)

def distance_to_rssi(distance, tx_power, n):
    if distance <= 0: return 0
    return int(tx_power - 10.0 * n * math.log10(distance))

# ──────────────────────────────────────────────
#  SONIDO
# ──────────────────────────────────────────────
class SoundSystem:
    def __init__(self):
        self.enabled = SOUND_OK
        if SOUND_OK:
            try: pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            except: self.enabled = False

    def _tone(self, freq, ms, vol=0.7):
        if not self.enabled: return
        try:
            sr = 44100
            samples = int(sr * ms / 1000)
            buf = bytes()
            for i in range(samples):
                s = int(vol * 32767 * math.sin(2 * math.pi * freq * i / sr))
                s = max(-32768, min(32767, s))
                buf += s.to_bytes(2, 'little', signed=True)
            pygame.mixer.Sound(buffer=buf).play()
        except: pass

    def alert_critical(self):
        def _p():
            for _ in range(3):
                self._tone(1800, 120); time.sleep(0.2)
        threading.Thread(target=_p, daemon=True).start()

    def alert_warning(self):
        threading.Thread(target=lambda: self._tone(1200, 250), daemon=True).start()

# ──────────────────────────────────────────────
#  LOGGER
# ──────────────────────────────────────────────
class Logger:
    def __init__(self):
        os.makedirs("logs_emf", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = f"logs_emf/scan_{ts}.csv"
        self.txt_path = f"logs_emf/session_{ts}.txt"
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "timestamp","datetime","type","ssid_name","mac",
                "rssi_dbm","distance_m","level","whitelisted",
                "manufacturer","mac_random","device_type","hidden_network"
            ])
        with open(self.txt_path, "a", encoding="utf-8") as f:
            f.write(f"=== Sesión EMF iniciada {ts} ===\n")

    def log_device(self, d):
        ts = time.time()
        dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                ts, dt, d.get("type",""), d.get("ssid",""), d.get("mac",""),
                d.get("rssi",""), d.get("distance",""), d.get("level",""),
                d.get("whitelisted",False), d.get("manufacturer",""),
                d.get("mac_random",False), d.get("device_type",""),
                d.get("hidden",False)
            ])

    def log_event(self, text, level="INFO"):
        with open(self.txt_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {text}\n")

    def get_csv_path(self): return self.csv_path

# ──────────────────────────────────────────────
#  ENRIQUECIMIENTO DE DISPOSITIVOS
# ──────────────────────────────────────────────
def enrich_device(d: dict) -> dict:
    """
    Agrega información de fabricante, tipo de dispositivo,
    detección de MAC aleatoria y red oculta.
    """
    mac = d.get("mac", "")
    sig_type = d.get("type", "WIFI")
    ssid = d.get("ssid", "")

    # Fabricante y MAC aleatoria
    manufacturer, is_random = lookup_manufacturer(mac)
    profile = get_device_risk_profile(manufacturer, is_random, sig_type)

    # Red oculta: SSID vacío o "[Oculto]" o "[Hidden]"
    is_hidden = (ssid in ("", "[Oculto]", "[Hidden]", "Hidden") or
                 ssid.startswith("[") and "culto" in ssid.lower())

    d["manufacturer"]  = manufacturer
    d["mac_random"]    = is_random
    d["device_type"]   = profile["device_type"]
    d["risk_note"]     = profile["note"]
    d["hidden"]        = is_hidden
    d["device_risk"]   = profile["risk"]

    return d

# ──────────────────────────────────────────────
#  COMUNICACIÓN SERIAL
# ──────────────────────────────────────────────
class SerialReader:
    def __init__(self, port, baud=115200):
        self.port = port; self.baud = baud
        self.ser = None; self.running = False
        self.callbacks = []; self.error_cb = None

    def add_callback(self, fn): self.callbacks.append(fn)
    def set_error_callback(self, fn): self.error_cb = fn

    def connect(self):
        if not SERIAL_OK: return False
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            self.running = True
            threading.Thread(target=self._loop, daemon=True).start()
            return True
        except Exception as e:
            if self.error_cb: self.error_cb(str(e))
            return False

    def disconnect(self):
        self.running = False
        if self.ser and self.ser.is_open: self.ser.close()

    def send(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write((json.dumps(cmd)+"\n").encode())

    def _loop(self):
        while self.running:
            try:
                if self.ser.in_waiting:
                    raw = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    if raw.startswith("{"):
                        data = json.loads(raw)
                        for cb in self.callbacks: cb(data)
            except json.JSONDecodeError: pass
            except Exception as e:
                if self.error_cb: self.error_cb(str(e)); break
            time.sleep(0.01)

# ──────────────────────────────────────────────
#  VENTANA DE DETALLE (popup al hacer clic)
# ──────────────────────────────────────────────
class DeviceDetailWindow:
    def __init__(self, parent, device: dict):
        self.win = ctk.CTkToplevel(parent)
        self.win.title("Detalle del Dispositivo")
        self.win.geometry("520x580")
        self.win.configure(fg_color=C_BG)
        self.win.grab_set()
        self._build(device)

    def _build(self, d):
        # Header con nivel de alerta
        level = d.get("level", "INFO")
        wl    = d.get("whitelisted", False)
        is_rand = d.get("mac_random", False)
        is_hid  = d.get("hidden", False)

        if wl:
            header_color = C_WHITELIST
            status_icon  = "✅"
            status_text  = "AUTORIZADO (Whitelist)"
        elif level == "CRITICAL":
            header_color = C_CRITICAL
            status_icon  = "🚨"
            status_text  = "ALERTA CRÍTICA"
        elif level == "WARNING":
            header_color = C_WARNING
            status_icon  = "⚠️"
            status_text  = "ADVERTENCIA"
        else:
            header_color = C_INFO
            status_icon  = "ℹ️"
            status_text  = "INFORMACIÓN"

        hdr = ctk.CTkFrame(self.win, fg_color=header_color, corner_radius=0, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=f"{status_icon}  {status_text}",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="white").pack(expand=True)

        # Cuerpo con tabs
        tabs = ctk.CTkTabview(self.win, fg_color=C_SURFACE)
        tabs.pack(fill="both", expand=True, padx=12, pady=10)
        tabs.add("Dispositivo")
        tabs.add("Señal RF")
        tabs.add("Análisis")

        self._tab_device(tabs.tab("Dispositivo"), d)
        self._tab_signal(tabs.tab("Señal RF"), d)
        self._tab_analysis(tabs.tab("Análisis"), d, is_rand, is_hid)

        ctk.CTkButton(self.win, text="Cerrar", command=self.win.destroy,
                      fg_color=C_BORDER).pack(pady=8)

    def _row(self, parent, row, label, value, value_color=None):
        ctk.CTkLabel(parent, text=label+":", font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).grid(row=row, column=0, sticky="w", padx=14, pady=4)
        ctk.CTkLabel(parent, text=str(value),
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=value_color or C_TEXT).grid(row=row, column=1, sticky="w", padx=8)

    def _tab_device(self, parent, d):
        parent.columnconfigure(1, weight=1)
        mfr = d.get("manufacturer", "Desconocido")
        is_rand = d.get("mac_random", False)
        mfr_color = C_RANDOM if is_rand else C_TEXT

        rows = [
            ("Tipo de señal",    d.get("type",""),      C_ACCENT),
            ("SSID / Nombre",    d.get("ssid","") or "—", C_TEXT),
            ("MAC Address",      d.get("mac",""),        C_TEXT),
            ("Fabricante (OUI)", mfr,                    mfr_color),
            ("Tipo dispositivo", d.get("device_type",""), C_TEXT),
            ("En whitelist",     "Sí ✅" if d.get("whitelisted") else "No", C_INFO if d.get("whitelisted") else C_MUTED),
        ]
        for i, (lbl, val, col) in enumerate(rows):
            self._row(parent, i, lbl, val, col)

        if is_rand:
            note = ctk.CTkLabel(parent,
                text="⚠ MAC aleatoria detectada\niOS 14+, Android 10+, Windows 10+ cambian la MAC\npara ocultar su identidad real.",
                font=ctk.CTkFont(size=10), text_color=C_RANDOM, justify="left")
            note.grid(row=len(rows), column=0, columnspan=2, padx=14, pady=8, sticky="w")

        if d.get("hidden"):
            note2 = ctk.CTkLabel(parent,
                text="🔒 Red WiFi oculta\nEl router no transmite su nombre (SSID),\npero la señal sigue siendo detectable.",
                font=ctk.CTkFont(size=10), text_color=C_HIDDEN, justify="left")
            note2.grid(row=len(rows)+1, column=0, columnspan=2, padx=14, pady=4, sticky="w")

    def _tab_signal(self, parent, d):
        parent.columnconfigure(1, weight=1)
        rssi = d.get("rssi", 0)
        dist = d.get("distance", 0)
        try: dist_f = float(dist)
        except: dist_f = 0.0

        # Barra visual de intensidad
        bar_frame = ctk.CTkFrame(parent, fg_color=C_SURFACE2, corner_radius=8)
        bar_frame.grid(row=0, column=0, columnspan=2, padx=12, pady=8, sticky="ew")

        ctk.CTkLabel(bar_frame, text=f"Intensidad de señal: {rssi} dBm",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(pady=(8,4))

        # Escala: -30 (muy fuerte) a -100 (muy débil)
        pct = max(0, min(100, (rssi + 100) / 70 * 100))
        bar_color = C_CRITICAL if pct > 70 else (C_WARNING if pct > 40 else C_INFO)

        ctk.CTkProgressBar(bar_frame, width=400, height=16,
                           fg_color=C_BORDER, progress_color=bar_color
        ).pack(padx=16, pady=(0, 4)).set(pct/100)

        labels = ["-100 dBm\n(Muy débil)", "-70 dBm\n(Débil)", "-50 dBm\n(Fuerte)", "-30 dBm\n(Muy fuerte)"]
        lf = ctk.CTkFrame(bar_frame, fg_color="transparent")
        lf.pack(fill="x", padx=16, pady=(0,8))
        for i, lbl in enumerate(labels):
            ctk.CTkLabel(lf, text=lbl, font=ctk.CTkFont(size=8),
                         text_color=C_MUTED).pack(side="left", expand=True)

        signal_quality = "Excelente" if rssi >= -50 else ("Buena" if rssi >= -65 else ("Regular" if rssi >= -75 else "Débil"))

        rows = [
            ("RSSI",             f"{rssi} dBm",                  C_TEXT),
            ("Calidad señal",    signal_quality,                  C_INFO if rssi >= -65 else C_WARNING),
            ("Distancia est.",   f"~{dist_f:.1f} metros",         C_ACCENT),
            ("Nivel de alerta",  d.get("level","INFO"),           C_CRITICAL if d.get("level")=="CRITICAL" else C_WARNING if d.get("level")=="WARNING" else C_INFO),
        ]
        for i, (lbl, val, col) in enumerate(rows):
            self._row(parent, i+1, lbl, val, col)

        ctk.CTkLabel(parent,
            text="Nota: la distancia es una estimación basada en el\nmodelo Log-Distance Path Loss. Puede variar por\nobstáculos, reflexiones y tipo de dispositivo.",
            font=ctk.CTkFont(size=9), text_color=C_MUTED, justify="left"
        ).grid(row=len(rows)+2, column=0, columnspan=2, padx=14, pady=8, sticky="w")

    def _tab_analysis(self, parent, d, is_rand, is_hid):
        note = d.get("risk_note", "Sin análisis disponible.")
        risk = d.get("device_risk", "MEDIUM")
        risk_color = C_CRITICAL if risk == "HIGH" else (C_WARNING if risk == "MEDIUM" else C_INFO)
        risk_icon  = "🔴" if risk == "HIGH" else ("🟡" if risk == "MEDIUM" else "🟢")

        ctk.CTkLabel(parent, text=f"Perfil de Riesgo",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=14, pady=(12,4))

        risk_frame = ctk.CTkFrame(parent, fg_color=C_SURFACE2, corner_radius=8)
        risk_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(risk_frame, text=f"{risk_icon}  Riesgo: {risk}",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=risk_color).pack(pady=(8,4))
        ctk.CTkLabel(risk_frame, text=note,
                     font=ctk.CTkFont(size=11), text_color=C_TEXT,
                     wraplength=440, justify="left").pack(padx=14, pady=(0,10))

        ctk.CTkLabel(parent, text="¿Qué significa esto en el contexto del examen?",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=14, pady=(12,4))

        # Interpretación contextual
        mfr = d.get("manufacturer", "")
        sig = d.get("type", "")

        interpretations = []
        if is_rand:
            interpretations.append("• MAC ALEATORIA: El dispositivo está usando una dirección MAC temporal/falsa. Esto es una característica de privacidad de smartphones modernos (iPhone, Android reciente). Indica fuertemente que hay un celular activo en el área.")
        if is_hid:
            interpretations.append("• RED OCULTA: El router/dispositivo no transmite su nombre, pero su señal es detectable. Puede ser un hotspot personal configurado para pasar desapercibido.")
        if "Apple" in mfr:
            interpretations.append("• DISPOSITIVO APPLE: iPhone, iPad o MacBook. Alta probabilidad de ser un celular de estudiante.")
        if "Samsung" in mfr or "Xiaomi" in mfr or "Huawei" in mfr:
            interpretations.append(f"• SMARTPHONE {mfr.upper()}: Teléfono Android activo en el área.")
        if sig == "BLE":
            interpretations.append("• SEÑAL BLE: Bluetooth Low Energy. Típico de audífonos inalámbricos, relojes inteligentes o dispositivos de comunicación corta distancia.")
        if not interpretations:
            interpretations.append("• Dispositivo detectado sin características especiales de riesgo. Monitorear si la señal persiste o se intensifica.")

        for interp in interpretations:
            ctk.CTkLabel(parent, text=interp,
                         font=ctk.CTkFont(size=10), text_color=C_TEXT,
                         wraplength=460, justify="left").pack(anchor="w", padx=14, pady=2)

# ──────────────────────────────────────────────
#  DASHBOARD PRINCIPAL
# ──────────────────────────────────────────────
class EMFDashboard:
    def __init__(self, root, port=None):
        self.root   = root
        self.port   = port
        self.serial = None
        self.logger = Logger()
        self.sound  = SoundSystem()
        self.running = True

        self.model      = {"txPower_wifi": -59.0, "txPower_ble": -59.0, "n": 2.7}
        self.thresholds = {"rssi_critical": -50, "rssi_warning": -70}
        self.scan_count = 0
        self.event_log  = deque(maxlen=300)

        # Cache de dispositivos enriquecidos para el panel de detalle
        self._last_devices = []

        self._build_ui()
        self._auto_connect()
        self.root.after(500, self._update_loop)

    # ─── UI ──────────────────────────────────
    def _build_ui(self):
        self.root.title("EMF DETECTOR v2 — Con análisis OUI y MAC aleatoria")
        self.root.geometry("1380x860")
        self.root.configure(fg_color=C_BG)
        self.root.minsize(1200, 700)

        # Header
        hdr = ctk.CTkFrame(self.root, fg_color=C_SURFACE, corner_radius=0, height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⚡ EMF DETECTOR v2",
                     font=ctk.CTkFont(family="Courier New", size=20, weight="bold"),
                     text_color=C_ACCENT).pack(side="left", padx=20)
        ctk.CTkLabel(hdr, text="Detección electromagnética + OUI + MAC privada + Redes ocultas",
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(side="left", padx=4)
        self.lbl_conn = ctk.CTkLabel(hdr, text="● DESCONECTADO",
                                     font=ctk.CTkFont(size=12, weight="bold"),
                                     text_color=C_CRITICAL)
        self.lbl_conn.pack(side="right", padx=20)

        # Body
        body = ctk.CTkFrame(self.root, fg_color=C_BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color=C_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,6))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        self._build_metrics(left)
        self._build_table(left)

        right = ctk.CTkFrame(body, fg_color=C_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_log(right)
        self._build_controls(right)
        self._build_statusbar()

    def _build_metrics(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_BG)
        frame.grid(row=0, column=0, sticky="ew", pady=(0,8))
        for i in range(5): frame.columnconfigure(i, weight=1)

        cards = [
            ("ESTADO",       "IDLE",  "lbl_estado",   C_MUTED),
            ("CRÍTICOS",     "0",     "lbl_critical",  C_CRITICAL),
            ("ADVERTENCIAS", "0",     "lbl_warning",   C_WARNING),
            ("MAC RANDOM",   "0",     "lbl_random",    C_RANDOM),
            ("OCULTAS",      "0",     "lbl_hidden",    C_HIDDEN),
        ]
        for i, (title, val, attr, color) in enumerate(cards):
            card = ctk.CTkFrame(frame, fg_color=C_SURFACE, corner_radius=10)
            card.grid(row=0, column=i, padx=3, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=9),
                         text_color=C_MUTED).pack(pady=(7,1))
            lbl = ctk.CTkLabel(card, text=val,
                               font=ctk.CTkFont(family="Courier New", size=20, weight="bold"),
                               text_color=color)
            lbl.pack(pady=(0,7))
            setattr(self, attr, lbl)

    def _build_table(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_SURFACE, corner_radius=10)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        # Header de la tabla con leyenda
        hf = ctk.CTkFrame(frame, fg_color=C_BG, corner_radius=6)
        hf.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
        ctk.CTkLabel(hf, text="📡 DISPOSITIVOS DETECTADOS",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(side="left", padx=10, pady=4)
        # Leyenda compacta
        legend = [("Crítico", C_CRITICAL), ("Aviso", C_WARNING),
                  ("Normal", C_INFO), ("Auth", C_WHITELIST),
                  ("MAC Rand", C_RANDOM), ("Oculta", C_HIDDEN)]
        for lbl, col in legend:
            ctk.CTkLabel(hf, text=f"● {lbl}", font=ctk.CTkFont(size=9),
                         text_color=col).pack(side="right", padx=4)

        # Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("EMF2.Treeview",
                        background=C_SURFACE, foreground=C_TEXT,
                        fieldbackground=C_SURFACE, borderwidth=0,
                        rowheight=24, font=("Courier New", 9))
        style.configure("EMF2.Treeview.Heading",
                        background=C_BG, foreground=C_MUTED,
                        relief="flat", font=("Courier New", 9, "bold"))
        style.map("EMF2.Treeview",
                  background=[("selected","#1F3A5F")],
                  foreground=[("selected", C_TEXT)])

        cols = ("tipo","ssid","fabricante","mac","rssi","dist","nivel","flags")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                  style="EMF2.Treeview", selectmode="browse")

        hdrs = {
            "tipo":      ("TIPO",       52),
            "ssid":      ("SSID/NOMBRE",145),
            "fabricante":("FABRICANTE", 125),
            "mac":       ("MAC",        130),
            "rssi":      ("RSSI",       60),
            "dist":      ("DIST(m)",    60),
            "nivel":     ("NIVEL",      75),
            "flags":     ("FLAGS",      75),
        }
        for col,(h,w) in hdrs.items():
            self.tree.heading(col, text=h)
            anchor = "w" if col in ("ssid","fabricante") else "center"
            self.tree.column(col, width=w, anchor=anchor, minwidth=40)

        for tag, color in [("CRITICAL",C_CRITICAL),("WARNING",C_WARNING),
                            ("INFO",C_INFO),("WHITELIST",C_WHITELIST),
                            ("RANDOM",C_RANDOM),("HIDDEN",C_HIDDEN)]:
            self.tree.tag_configure(tag, foreground=color)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(8,0), pady=(0,8))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0,8))

        # Doble clic → detalle
        self.tree.bind("<Double-1>", self._on_row_double_click)

        ctk.CTkLabel(frame,
            text="💡 Doble clic en una fila para ver análisis detallado",
            font=ctk.CTkFont(size=9), text_color=C_MUTED
        ).grid(row=2, column=0, columnspan=2, pady=(0,4))

    def _build_log(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_SURFACE, corner_radius=10)
        frame.grid(row=0, column=0, sticky="nsew", pady=(0,6))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        hf = ctk.CTkFrame(frame, fg_color=C_BG, corner_radius=6)
        hf.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ctk.CTkLabel(hf, text="📋 LOG DE EVENTOS",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(side="left", padx=10, pady=4)
        ctk.CTkButton(hf, text="Limpiar", width=65, height=24,
                      fg_color=C_BORDER, command=self._clear_log).pack(side="right", padx=4)
        ctk.CTkButton(hf, text="Exportar CSV", width=95, height=24,
                      fg_color=C_ACCENT, command=self._export_csv).pack(side="right", padx=2)

        self.log_text = ctk.CTkTextbox(frame, fg_color=C_BG, text_color=C_TEXT,
                                        font=ctk.CTkFont(family="Courier New", size=10),
                                        corner_radius=6, wrap="word")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))
        self.log_text.configure(state="disabled")

    def _build_controls(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_SURFACE, corner_radius=10)
        frame.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(frame, text="⚙️ CONFIGURACIÓN Y CALIBRACIÓN",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=14, pady=(10,4))

        tabs = ctk.CTkTabview(frame, fg_color=C_BG, segmented_button_fg_color=C_BG)
        tabs.pack(fill="both", expand=True, padx=8, pady=(0,8))
        for t in ("Modelo","Calibrar","Whitelist","Conexión"):
            tabs.add(t)

        self._tab_model(tabs.tab("Modelo"))
        self._tab_calibrate(tabs.tab("Calibrar"))
        self._tab_whitelist(tabs.tab("Whitelist"))
        self._tab_conn(tabs.tab("Conexión"))

    def _tab_model(self, parent):
        params = [
            ("TxPower WiFi (dBm)", "txpower_wifi", "-59"),
            ("TxPower BLE (dBm)",  "txpower_ble",  "-59"),
            ("Exp. trayectoria n", "n_exp",         "2.7"),
            ("RSSI Crítico (dBm)", "rssi_crit",    "-50"),
            ("RSSI Aviso (dBm)",   "rssi_warn",    "-70"),
        ]
        self._model_entries = {}
        for i, (lbl, key, default) in enumerate(params):
            ctk.CTkLabel(parent, text=lbl, font=ctk.CTkFont(size=11),
                         text_color=C_MUTED).grid(row=i, column=0, sticky="w", padx=10, pady=3)
            e = ctk.CTkEntry(parent, width=80, font=ctk.CTkFont(size=11))
            e.insert(0, default); e.grid(row=i, column=1, padx=6, pady=3)
            self._model_entries[key] = e
        ctk.CTkButton(parent, text="Aplicar al ESP32", height=30,
                      command=self._apply_model).grid(
            row=len(params), column=0, columnspan=2, padx=10, pady=8, sticky="ew")

    def _tab_calibrate(self, parent):
        ctk.CTkLabel(parent,
            text="Coloca dispositivo a distancia conocida.\nMide el RSSI promedio y calibra.",
            font=ctk.CTkFont(size=10), text_color=C_MUTED, justify="left"
        ).pack(anchor="w", padx=10, pady=4)

        for label, attr, default in [
            ("Distancia (m):", "cal_dist", "1.0"),
            ("RSSI medido:",   "cal_rssi", "-59"),
        ]:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11),
                         text_color=C_MUTED).pack(side="left")
            e = ctk.CTkEntry(row, width=65); e.insert(0, default); e.pack(side="left", padx=6)
            setattr(self, attr, e)

        row3 = ctk.CTkFrame(parent, fg_color="transparent")
        row3.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(row3, text="Tipo:", font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).pack(side="left")
        self.cal_type = ctk.CTkOptionMenu(row3, values=["WIFI","BLE"], width=80)
        self.cal_type.pack(side="left", padx=6)

        ctk.CTkButton(parent, text="Calibrar ESP32", height=30,
                      fg_color="#238636", command=self._send_calibration
        ).pack(padx=10, pady=6, fill="x")
        self.cal_result = ctk.CTkLabel(parent, text="", font=ctk.CTkFont(size=10),
                                        text_color=C_INFO)
        self.cal_result.pack(padx=10)

    def _tab_whitelist(self, parent):
        for lbl, placeholder, attr, cmd in [
            ("SSID WiFi autorizado:", "Nombre red WiFi", "wl_ssid", self._add_wifi_wl),
            ("MAC BLE autorizada:",   "aa:bb:cc:dd:ee:ff", "wl_mac", self._add_ble_wl),
        ]:
            ctk.CTkLabel(parent, text=lbl, font=ctk.CTkFont(size=11),
                         text_color=C_MUTED).pack(anchor="w", padx=10, pady=(6,2))
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=8)
            e = ctk.CTkEntry(row, placeholder_text=placeholder, width=155)
            e.pack(side="left"); setattr(self, attr, e)
            ctk.CTkButton(row, text="Agregar", width=70, height=28,
                          fg_color="#238636", command=cmd).pack(side="left", padx=4)

        ctk.CTkButton(parent, text="Limpiar whitelist", height=28,
                      fg_color=C_CRITICAL, command=self._clear_wl
        ).pack(padx=10, pady=8, fill="x")

    def _tab_conn(self, parent):
        ctk.CTkLabel(parent, text="Puerto Serial:", font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).pack(anchor="w", padx=10, pady=(8,2))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8)
        self.port_entry = ctk.CTkEntry(row, placeholder_text="COM3 o /dev/ttyUSB0", width=155)
        if self.port: self.port_entry.insert(0, self.port)
        self.port_entry.pack(side="left")
        ctk.CTkButton(row, text="Detectar", width=70, height=28,
                      command=self._detect_ports).pack(side="left", padx=4)
        ctk.CTkButton(parent, text="Conectar", height=30, fg_color=C_ACCENT,
                      command=self._connect_serial).pack(padx=10, pady=6, fill="x")
        ctk.CTkButton(parent, text="Desconectar", height=30, fg_color=C_BORDER,
                      command=self._disconnect_serial).pack(padx=10, fill="x")

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self.root, fg_color=C_SURFACE, corner_radius=0, height=26)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self.lbl_status = ctk.CTkLabel(bar, text="Listo. Conecta el ESP32.",
                                        font=ctk.CTkFont(size=10), text_color=C_MUTED)
        self.lbl_status.pack(side="left", padx=12)
        ctk.CTkLabel(bar, text=f"Log: {self.logger.get_csv_path()}",
                     font=ctk.CTkFont(size=9), text_color=C_MUTED).pack(side="right", padx=12)

    # ─── DATOS ───────────────────────────────
    def _on_data(self, data):
        t = data.get("type","")
        if   t == "SCAN_REPORT":       self._process_scan(data)
        elif t == "HEARTBEAT":         self._process_heartbeat(data)
        elif t == "BOOT":              self._add_log(f"ESP32 listo: {data.get('msg','')}", "INFO")
        elif t == "ACK":
            ok = data.get("ok", False)
            self._add_log(f"ACK [{data.get('cmd','')}]: {data.get('msg','')}", "INFO" if ok else "WARNING")
        elif t == "CALIBRATION_RESULT":
            tp = data.get("new_txPower", 0)
            self.cal_result.configure(text=f"✓ TxPower={tp:.1f} dBm | RSSI@1m≈{data.get('rssi_at_1m',0)} dBm")
            self._add_log(f"Calibración OK: TxPower={tp:.1f}dBm", "INFO")

    def _process_scan(self, data):
        self.scan_count += 1
        devices = [enrich_device(d) for d in data.get("devices", [])]
        self._last_devices = devices

        crit  = [d for d in devices if not d.get("whitelisted") and d.get("level")=="CRITICAL"]
        warn  = [d for d in devices if not d.get("whitelisted") and d.get("level")=="WARNING"]
        rands = [d for d in devices if d.get("mac_random") and not d.get("whitelisted")]
        hids  = [d for d in devices if d.get("hidden") and not d.get("whitelisted")]

        if crit:
            self.sound.alert_critical()
            self._add_log(f"🚨 CRÍTICO: {len(crit)} dispositivo(s) muy cerca!", "CRITICAL")
            for d in crit:
                self._add_log(
                    f"  [{d['type']}] {d.get('ssid','?')} | {d.get('manufacturer','')} | "
                    f"MAC:{d.get('mac','')} | RSSI:{d.get('rssi')}dBm | ~{d.get('distance')}m",
                    "CRITICAL"
                )
        elif warn:
            self.sound.alert_warning()
            self._add_log(f"⚠ AVISO: {len(warn)} dispositivo(s) en rango.", "WARNING")

        if rands:
            self._add_log(f"🔵 {len(rands)} dispositivo(s) con MAC aleatoria (celular/laptop moderno).", "WARNING")
        if hids:
            self._add_log(f"🔒 {len(hids)} red(es) WiFi oculta(s) detectada(s).", "WARNING")

        for d in devices:
            if not d.get("whitelisted") and d.get("level") in ("WARNING","CRITICAL"):
                self.logger.log_device(d)

        self.root.after(0, lambda: self._update_table(devices, crit, warn, rands, hids))

    def _process_heartbeat(self, data):
        heap = data.get("free_heap", 0)
        self.lbl_status.configure(
            text=f"ESP32 activo | Heap: {heap//1024}KB | Escaneos: {self.scan_count}"
        )

    def _update_table(self, devices, crit, warn, rands, hids):
        for row in self.tree.get_children():
            self.tree.delete(row)

        order = {"CRITICAL":0,"WARNING":1,"INFO":2}
        sorted_devs = sorted(devices,
            key=lambda d: (order.get(d.get("level","INFO"),2), -(d.get("rssi",0) or 0))
            if not d.get("whitelisted") else (3, 0)
        )

        for d in sorted_devs:
            wl       = d.get("whitelisted", False)
            is_rand  = d.get("mac_random", False)
            is_hid   = d.get("hidden", False)
            level    = d.get("level", "INFO")

            # Tag de color
            if wl:      tag = "WHITELIST"
            elif is_rand: tag = "RANDOM"
            elif is_hid:  tag = "HIDDEN"
            elif level == "CRITICAL": tag = "CRITICAL"
            elif level == "WARNING":  tag = "WARNING"
            else:                     tag = "INFO"

            # Flags
            flags = []
            if is_rand: flags.append("🔵RAND")
            if is_hid:  flags.append("🔒OCL")
            if wl:      flags.append("✅AUTH")
            flags_str = " ".join(flags) if flags else "—"

            mfr = d.get("manufacturer","")
            if len(mfr) > 14: mfr = mfr[:13]+"…"
            ssid = d.get("ssid","") or "[Oculto]"
            if len(ssid) > 18: ssid = ssid[:17]+"…"

            try:   dist_s = f"{float(d.get('distance',0)):.1f}"
            except: dist_s = "?"

            self.tree.insert("","end",
                values=(d.get("type",""), ssid, mfr, d.get("mac",""),
                        d.get("rssi",""), dist_s,
                        "✓Auth" if wl else level, flags_str),
                tags=(tag,)
            )

        # Métricas
        status_text  = "CRÍTICO" if crit else ("AVISO" if warn else "NORMAL")
        status_color = C_CRITICAL if crit else (C_WARNING if warn else C_INFO)
        self.lbl_estado.configure(text=status_text, text_color=status_color)
        self.lbl_critical.configure(text=str(len(crit)))
        self.lbl_warning.configure(text=str(len(warn)))
        self.lbl_random.configure(text=str(len(rands)))
        self.lbl_hidden.configure(text=str(len(hids)))

    def _on_row_double_click(self, event):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        if idx < len(self._last_devices):
            DeviceDetailWindow(self.root, self._last_devices[idx])

    # ─── LOG ─────────────────────────────────
    def _add_log(self, text, level="INFO"):
        ts   = datetime.now().strftime("%H:%M:%S")
        icon = {"CRITICAL":"🔴","WARNING":"🟡","INFO":"🟢"}.get(level,"⚪")
        line = f"{icon} [{ts}] {text}\n"
        self.event_log.append(line)
        self.logger.log_event(text, level)
        def _ins():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _ins)

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0","end")
        self.log_text.configure(state="disabled")

    def _export_csv(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            initialfile=f"emf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if p:
            import shutil; shutil.copy(self.logger.get_csv_path(), p)
            messagebox.showinfo("Exportado", f"Log guardado en:\n{p}")

    # ─── COMANDOS ────────────────────────────
    def _apply_model(self):
        if not self.serial: self._add_log("Sin conexión.", "WARNING"); return
        try:
            self.serial.send({"cmd":"SET_MODEL",
                "txPower_wifi": float(self._model_entries["txpower_wifi"].get()),
                "txPower_ble":  float(self._model_entries["txpower_ble"].get()),
                "n":            float(self._model_entries["n_exp"].get())})
            self.serial.send({"cmd":"SET_THRESHOLDS",
                "rssi_critical": int(self._model_entries["rssi_crit"].get()),
                "rssi_warning":  int(self._model_entries["rssi_warn"].get())})
            self._add_log("Modelo y umbrales enviados.", "INFO")
        except ValueError as e:
            self._add_log(f"Error: {e}", "WARNING")

    def _send_calibration(self):
        if not self.serial: self._add_log("Sin conexión.", "WARNING"); return
        try:
            self.serial.send({"cmd":"CALIBRATE",
                "distance": float(self.cal_dist.get()),
                "rssi":     int(self.cal_rssi.get()),
                "type":     self.cal_type.get()})
            self._add_log(f"Calibración enviada: {self.cal_dist.get()}m / {self.cal_rssi.get()}dBm", "INFO")
        except ValueError as e:
            self._add_log(f"Error calibración: {e}", "WARNING")

    def _add_wifi_wl(self):
        ssid = self.wl_ssid.get().strip()
        if ssid and self.serial:
            self.serial.send({"cmd":"ADD_WIFI_WL","ssid":ssid})
            self._add_log(f"Whitelist WiFi: '{ssid}'", "INFO")
            self.wl_ssid.delete(0,"end")

    def _add_ble_wl(self):
        mac = self.wl_mac.get().strip()
        if mac and self.serial:
            self.serial.send({"cmd":"ADD_BLE_WL","mac":mac})
            self._add_log(f"Whitelist BLE: {mac}", "INFO")
            self.wl_mac.delete(0,"end")

    def _clear_wl(self):
        if self.serial: self.serial.send({"cmd":"CLEAR_WL"})

    def _detect_ports(self):
        if not SERIAL_OK: return
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            self.port_entry.delete(0,"end")
            self.port_entry.insert(0,ports[0])
            self._add_log(f"Puertos: {', '.join(ports)}", "INFO")
        else:
            self._add_log("No se encontraron puertos.", "WARNING")

    def _auto_connect(self):
        if not SERIAL_OK:
            self._add_log("pyserial no instalado: pip install pyserial", "WARNING"); return
        port = self.port
        if not port:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            if ports:
                port = ports[0]
                self.port_entry.delete(0,"end")
                self.port_entry.insert(0,port)
        if port: self._do_connect(port)

    def _connect_serial(self):
        p = self.port_entry.get().strip()
        if p: self._do_connect(p)

    def _do_connect(self, port):
        self.serial = SerialReader(port)
        self.serial.add_callback(self._on_data)
        self.serial.set_error_callback(lambda e: self._add_log(f"Error serial: {e}","WARNING"))
        if self.serial.connect():
            self.lbl_conn.configure(text=f"● {port}", text_color=C_INFO)
            self._add_log(f"Conectado a {port}", "INFO")
        else:
            self.lbl_conn.configure(text="● ERROR", text_color=C_CRITICAL)
            self._add_log(f"No pudo conectar a {port}", "WARNING")

    def _disconnect_serial(self):
        if self.serial: self.serial.disconnect(); self.serial = None
        self.lbl_conn.configure(text="● DESCONECTADO", text_color=C_CRITICAL)
        self._add_log("Desconectado.", "INFO")

    def _update_loop(self):
        if self.running:
            self.root.after(500, self._update_loop)

    def on_close(self):
        self.running = False
        if self.serial: self.serial.disconnect()
        self.root.destroy()

# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="EMF Detector Dashboard v2")
    parser.add_argument("--port", default=None, help="Puerto serial (COM3, /dev/ttyUSB0)")
    args = parser.parse_args()
    root = ctk.CTk()
    app  = EMFDashboard(root, port=args.port)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
