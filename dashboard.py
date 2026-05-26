#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║   DASHBOARD - DETECTOR EMF ESP32                            ║
║   Sistema de detección para concursos de admisión           ║
╚══════════════════════════════════════════════════════════════╝
Requiere:
    pip install pyserial customtkinter pygame

Uso:
    python dashboard.py                    # auto-detecta puerto
    python dashboard.py --port COM3        # Windows
    python dashboard.py --port /dev/ttyUSB0  # Linux/Mac
"""

import sys
import os
import json
import time
import csv
import threading
import argparse
import math
from datetime import datetime
from collections import deque
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk   # pip install customtkinter

try:
    import serial
    import serial.tools.list_ports
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False
    print("[WARN] pyserial no instalado. Ejecuta: pip install pyserial")

try:
    import pygame
    SOUND_OK = True
except ImportError:
    SOUND_OK = False
    print("[WARN] pygame no instalado. Sin sonido. Ejecuta: pip install pygame")

# ──────────────────────────────────────────────
#  CONFIGURACIÓN DE APARIENCIA
# ──────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Paleta de colores
C_BG        = "#0D1117"
C_SURFACE   = "#161B22"
C_BORDER    = "#30363D"
C_TEXT      = "#E6EDF3"
C_MUTED     = "#8B949E"
C_CRITICAL  = "#FF4444"
C_WARNING   = "#FFA500"
C_INFO      = "#3FB950"
C_ACCENT    = "#58A6FF"
C_WHITELIST = "#7C8CF8"

# ──────────────────────────────────────────────
#  MODELO MATEMÁTICO (espejo del ESP32)
# ──────────────────────────────────────────────
def rssi_to_distance(rssi: int, tx_power: float, n: float) -> float:
    """
    Log-Distance Path Loss:
    d = 10 ^ ((TxPower - RSSI) / (10 * n))
    """
    if rssi == 0:
        return -1.0
    exponent = (tx_power - rssi) / (10.0 * n)
    return round(10 ** exponent, 2)

def distance_to_rssi(distance: float, tx_power: float, n: float) -> int:
    """
    Inverso: RSSI = TxPower - 10 * n * log10(d)
    """
    if distance <= 0:
        return 0
    return int(tx_power - 10.0 * n * math.log10(distance))

# ──────────────────────────────────────────────
#  SISTEMA DE SONIDO
# ──────────────────────────────────────────────
class SoundSystem:
    def __init__(self):
        self.enabled = SOUND_OK
        if SOUND_OK:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

    def _generate_tone(self, freq: int, duration_ms: int, volume: float = 0.7):
        """Genera tono sintético sin archivo de audio."""
        if not self.enabled:
            return
        import numpy as np
        sample_rate = 44100
        samples = int(sample_rate * duration_ms / 1000)
        t = [i / sample_rate for i in range(samples)]
        wave = [int(volume * 32767 * math.sin(2 * math.pi * freq * x)) for x in t]
        sound_array = bytes()
        for s in wave:
            s = max(-32768, min(32767, s))
            sound_array += s.to_bytes(2, byteorder='little', signed=True)
        sound = pygame.mixer.Sound(buffer=sound_array)
        sound.play()

    def alert_critical(self):
        """3 beeps agudos urgentes."""
        def _play():
            for _ in range(3):
                self._generate_tone(1800, 120)
                time.sleep(0.2)
        threading.Thread(target=_play, daemon=True).start()

    def alert_warning(self):
        """1 beep medio."""
        threading.Thread(
            target=lambda: self._generate_tone(1200, 250),
            daemon=True
        ).start()

    def alert_info(self):
        threading.Thread(
            target=lambda: self._generate_tone(800, 80),
            daemon=True
        ).start()

# ──────────────────────────────────────────────
#  LOGGER
# ──────────────────────────────────────────────
class Logger:
    def __init__(self):
        self.log_dir  = "logs_emf"
        os.makedirs(self.log_dir, exist_ok=True)
        session_ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = os.path.join(self.log_dir, f"scan_{session_ts}.csv")
        self.txt_path = os.path.join(self.log_dir, f"session_{session_ts}.txt")
        self._init_csv()
        self._write_txt(f"=== Sesión iniciada {session_ts} ===\n")

    def _init_csv(self):
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "timestamp", "datetime", "type", "ssid_name", "mac",
                "rssi_dbm", "distance_m", "level", "whitelisted"
            ])

    def _write_txt(self, text: str):
        with open(self.txt_path, "a", encoding="utf-8") as f:
            f.write(text)

    def log_device(self, device: dict):
        ts  = time.time()
        dt  = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                ts, dt,
                device.get("type", ""),
                device.get("ssid", ""),
                device.get("mac", ""),
                device.get("rssi", ""),
                device.get("distance", ""),
                device.get("level", ""),
                device.get("whitelisted", False)
            ])

    def log_event(self, event: str, level: str = "INFO"):
        dt  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{dt}] [{level}] {event}\n"
        self._write_txt(line)

    def get_csv_path(self):
        return self.csv_path

# ──────────────────────────────────────────────
#  COMUNICACIÓN SERIAL
# ──────────────────────────────────────────────
class SerialReader:
    def __init__(self, port: str, baud: int = 115200):
        self.port      = port
        self.baud      = baud
        self.ser       = None
        self.running   = False
        self.callbacks = []
        self.error_cb  = None

    def add_callback(self, fn):
        self.callbacks.append(fn)

    def set_error_callback(self, fn):
        self.error_cb = fn

    def connect(self) -> bool:
        if not SERIAL_OK:
            return False
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            self.running = True
            threading.Thread(target=self._reader_loop, daemon=True).start()
            return True
        except Exception as e:
            if self.error_cb:
                self.error_cb(str(e))
            return False

    def disconnect(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send_command(self, cmd_dict: dict):
        if self.ser and self.ser.is_open:
            line = json.dumps(cmd_dict) + "\n"
            self.ser.write(line.encode("utf-8"))

    def _reader_loop(self):
        while self.running:
            try:
                if self.ser.in_waiting:
                    raw = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    if raw.startswith("{"):
                        data = json.loads(raw)
                        for cb in self.callbacks:
                            cb(data)
            except json.JSONDecodeError:
                pass
            except serial.SerialException as e:
                if self.error_cb:
                    self.error_cb(str(e))
                break
            except Exception:
                pass
            time.sleep(0.01)

# ──────────────────────────────────────────────
#  VENTANA PRINCIPAL DEL DASHBOARD
# ──────────────────────────────────────────────
class EMFDashboard:
    def __init__(self, root: ctk.CTk, port: str = None):
        self.root    = root
        self.port    = port
        self.serial  = None
        self.logger  = Logger()
        self.sound   = SoundSystem()
        self.running = True

        # Estado del modelo (sincronizado con ESP32)
        self.model = {"txPower_wifi": -59.0, "txPower_ble": -59.0, "n": 2.7}
        self.thresholds = {"rssi_critical": -50, "rssi_warning": -70}
        self.last_status = "IDLE"
        self.scan_count  = 0
        self.critical_count = 0
        self.warning_count  = 0

        # Historial de eventos (para panel de log)
        self.event_log = deque(maxlen=200)
        # Historial de nivel para gráfico simple
        self.rssi_history = deque(maxlen=60)

        self._build_ui()
        self._auto_connect()
        self._update_loop()

    # ─── CONSTRUCCIÓN UI ─────────────────────
    def _build_ui(self):
        self.root.title("EMF DETECTOR — Sistema de Detección Electromagnética")
        self.root.geometry("1300x820")
        self.root.configure(fg_color=C_BG)
        self.root.minsize(1100, 700)

        # ── Header ──────────────────────────
        header = ctk.CTkFrame(self.root, fg_color=C_SURFACE, corner_radius=0, height=60)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⚡ EMF DETECTOR",
            font=ctk.CTkFont(family="Courier New", size=20, weight="bold"),
            text_color=C_ACCENT
        ).pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            header, text="Sistema de Detección de Señales Electromagnéticas",
            font=ctk.CTkFont(size=12), text_color=C_MUTED
        ).pack(side="left", padx=5)

        # Estado conexión
        self.lbl_conn = ctk.CTkLabel(
            header, text="● DESCONECTADO",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_CRITICAL
        )
        self.lbl_conn.pack(side="right", padx=20)

        # ── Cuerpo principal ─────────────────
        body = ctk.CTkFrame(self.root, fg_color=C_BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # ── Panel izquierdo ──────────────────
        left = ctk.CTkFrame(body, fg_color=C_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        # Tarjetas de métricas
        self._build_metrics(left)

        # Tabla de dispositivos detectados
        self._build_device_table(left)

        # ── Panel derecho ────────────────────
        right = ctk.CTkFrame(body, fg_color=C_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_log_panel(right)
        self._build_controls(right)

        # ── Barra de estado inferior ─────────
        self._build_statusbar()

    def _build_metrics(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_BG)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for i in range(4):
            frame.columnconfigure(i, weight=1)

        cards = [
            ("ESTADO",       "IDLE",   "lbl_estado",    C_MUTED),
            ("CRÍTICOS",     "0",      "lbl_critical",  C_CRITICAL),
            ("ADVERTENCIAS", "0",      "lbl_warning",   C_WARNING),
            ("ESCANEOS",     "0",      "lbl_scans",     C_INFO),
        ]
        for i, (title, val, attr, color) in enumerate(cards):
            card = ctk.CTkFrame(frame, fg_color=C_SURFACE, corner_radius=10)
            card.grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10),
                         text_color=C_MUTED).pack(pady=(8, 2))
            lbl = ctk.CTkLabel(card, text=val,
                               font=ctk.CTkFont(family="Courier New", size=22, weight="bold"),
                               text_color=color)
            lbl.pack(pady=(0, 8))
            setattr(self, attr, lbl)

    def _build_device_table(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_SURFACE, corner_radius=10)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="📡 DISPOSITIVOS DETECTADOS",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT
        ).grid(row=0, column=0, sticky="w", padx=14, pady=8)

        # Tabla (usando ttk.Treeview con estilo personalizado)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("EMF.Treeview",
                        background=C_SURFACE, foreground=C_TEXT,
                        fieldbackground=C_SURFACE, borderwidth=0,
                        rowheight=26, font=("Courier New", 10))
        style.configure("EMF.Treeview.Heading",
                        background=C_BG, foreground=C_MUTED,
                        relief="flat", font=("Courier New", 10, "bold"))
        style.map("EMF.Treeview",
                  background=[("selected", "#264F78")],
                  foreground=[("selected", C_TEXT)])

        cols = ("tipo", "nombre", "mac", "rssi", "distancia", "nivel")
        self.tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            style="EMF.Treeview", selectmode="browse"
        )
        headers = {
            "tipo":      ("TIPO",       60),
            "nombre":    ("SSID/NOMBRE", 160),
            "mac":       ("MAC",         140),
            "rssi":      ("RSSI (dBm)",  80),
            "distancia": ("DIST (m)",    75),
            "nivel":     ("NIVEL",       85),
        }
        for col, (h, w) in headers.items():
            self.tree.heading(col, text=h)
            self.tree.column(col, width=w, anchor="center" if col != "nombre" else "w")

        self.tree.tag_configure("CRITICAL",  foreground=C_CRITICAL)
        self.tree.tag_configure("WARNING",   foreground=C_WARNING)
        self.tree.tag_configure("INFO",      foreground=C_INFO)
        self.tree.tag_configure("WHITELIST", foreground=C_WHITELIST)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 8))

    def _build_log_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_SURFACE, corner_radius=10)
        frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(frame, fg_color=C_BG, corner_radius=6)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ctk.CTkLabel(hdr, text="📋 LOG DE EVENTOS",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(side="left", padx=10, pady=4)
        ctk.CTkButton(hdr, text="Limpiar", width=70, height=24,
                      fg_color=C_BORDER, hover_color=C_MUTED,
                      command=self._clear_log).pack(side="right", padx=6)
        ctk.CTkButton(hdr, text="Exportar CSV", width=100, height=24,
                      fg_color=C_ACCENT, hover_color="#1f6feb",
                      command=self._export_csv).pack(side="right", padx=2)

        self.log_text = ctk.CTkTextbox(
            frame, fg_color=C_BG, text_color=C_TEXT,
            font=ctk.CTkFont(family="Courier New", size=10),
            corner_radius=6, wrap="none"
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.log_text.configure(state="disabled")

    def _build_controls(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_SURFACE, corner_radius=10)
        frame.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(frame, text="⚙️ CONFIGURACIÓN Y CALIBRACIÓN",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=14, pady=(10, 4))

        # Tabs
        tabs = ctk.CTkTabview(frame, fg_color=C_BG, segmented_button_fg_color=C_BG)
        tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        tabs.add("Modelo")
        tabs.add("Calibrar")
        tabs.add("Whitelist")
        tabs.add("Conexión")

        self._build_tab_model(tabs.tab("Modelo"))
        self._build_tab_calibrate(tabs.tab("Calibrar"))
        self._build_tab_whitelist(tabs.tab("Whitelist"))
        self._build_tab_conn(tabs.tab("Conexión"))

    def _build_tab_model(self, parent):
        params = [
            ("TxPower WiFi (dBm)", "txpower_wifi", "-59"),
            ("TxPower BLE (dBm)",  "txpower_ble",  "-59"),
            ("Exp. trayectoria n", "n_exp",         "2.7"),
            ("RSSI Crítico (dBm)", "rssi_crit",    "-50"),
            ("RSSI Aviso (dBm)",   "rssi_warn",    "-70"),
        ]
        self._model_entries = {}
        for i, (label, key, default) in enumerate(params):
            ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=11),
                         text_color=C_MUTED).grid(row=i, column=0, sticky="w", padx=10, pady=3)
            e = ctk.CTkEntry(parent, width=80, font=ctk.CTkFont(size=11))
            e.insert(0, default)
            e.grid(row=i, column=1, padx=6, pady=3)
            self._model_entries[key] = e

        ctk.CTkButton(parent, text="Aplicar al ESP32", height=30,
                      command=self._apply_model).grid(
            row=len(params), column=0, columnspan=2, padx=10, pady=8, sticky="ew")

    def _build_tab_calibrate(self, parent):
        ctk.CTkLabel(parent,
                     text="Coloca un dispositivo a distancia\nconocida y mide el RSSI promedio.",
                     font=ctk.CTkFont(size=10), text_color=C_MUTED, justify="left"
        ).pack(anchor="w", padx=10, pady=4)

        row1 = ctk.CTkFrame(parent, fg_color="transparent")
        row1.pack(fill="x", padx=8)
        ctk.CTkLabel(row1, text="Distancia (m):", font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).pack(side="left")
        self.cal_dist = ctk.CTkEntry(row1, width=65)
        self.cal_dist.insert(0, "1.0")
        self.cal_dist.pack(side="left", padx=6)

        row2 = ctk.CTkFrame(parent, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(row2, text="RSSI medido:", font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).pack(side="left")
        self.cal_rssi = ctk.CTkEntry(row2, width=65)
        self.cal_rssi.insert(0, "-59")
        self.cal_rssi.pack(side="left", padx=6)

        row3 = ctk.CTkFrame(parent, fg_color="transparent")
        row3.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(row3, text="Tipo:", font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).pack(side="left")
        self.cal_type = ctk.CTkOptionMenu(row3, values=["WIFI", "BLE"], width=80)
        self.cal_type.pack(side="left", padx=6)

        ctk.CTkButton(parent, text="Calibrar ESP32", height=30,
                      fg_color="#238636", hover_color="#2ea043",
                      command=self._send_calibration).pack(padx=10, pady=6, fill="x")

        self.cal_result = ctk.CTkLabel(parent, text="", font=ctk.CTkFont(size=10),
                                       text_color=C_INFO)
        self.cal_result.pack(padx=10)

    def _build_tab_whitelist(self, parent):
        ctk.CTkLabel(parent, text="Agregar SSID WiFi autorizado:",
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(anchor="w", padx=10, pady=(6, 2))

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8)
        self.wl_ssid = ctk.CTkEntry(row, placeholder_text="Nombre red WiFi", width=160)
        self.wl_ssid.pack(side="left")
        ctk.CTkButton(row, text="Agregar", width=70, height=28,
                      fg_color="#238636",
                      command=self._add_wifi_wl).pack(side="left", padx=4)

        ctk.CTkLabel(parent, text="Agregar MAC BLE/BT autorizada:",
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(anchor="w", padx=10, pady=(8, 2))

        row2 = ctk.CTkFrame(parent, fg_color="transparent")
        row2.pack(fill="x", padx=8)
        self.wl_mac = ctk.CTkEntry(row2, placeholder_text="aa:bb:cc:dd:ee:ff", width=160)
        self.wl_mac.pack(side="left")
        ctk.CTkButton(row2, text="Agregar", width=70, height=28,
                      fg_color="#238636",
                      command=self._add_ble_wl).pack(side="left", padx=4)

        ctk.CTkButton(parent, text="Limpiar toda la whitelist", height=28,
                      fg_color=C_CRITICAL, hover_color="#b91c1c",
                      command=self._clear_wl).pack(padx=10, pady=8, fill="x")

    def _build_tab_conn(self, parent):
        ctk.CTkLabel(parent, text="Puerto Serial:",
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(anchor="w", padx=10, pady=(8, 2))

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8)
        self.port_entry = ctk.CTkEntry(row, placeholder_text="COM3 o /dev/ttyUSB0", width=160)
        if self.port:
            self.port_entry.insert(0, self.port)
        self.port_entry.pack(side="left")
        ctk.CTkButton(row, text="Detectar", width=70, height=28,
                      command=self._detect_ports).pack(side="left", padx=4)

        ctk.CTkButton(parent, text="Conectar", height=30,
                      fg_color=C_ACCENT, command=self._connect_serial).pack(padx=10, pady=6, fill="x")
        ctk.CTkButton(parent, text="Desconectar", height=30,
                      fg_color=C_BORDER, command=self._disconnect_serial).pack(padx=10, fill="x")

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self.root, fg_color=C_SURFACE, corner_radius=0, height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.lbl_status = ctk.CTkLabel(
            bar, text="Listo. Conecta el ESP32 para comenzar.",
            font=ctk.CTkFont(size=10), text_color=C_MUTED
        )
        self.lbl_status.pack(side="left", padx=12)

        self.lbl_log_path = ctk.CTkLabel(
            bar, text=f"Log: {self.logger.get_csv_path()}",
            font=ctk.CTkFont(size=10), text_color=C_MUTED
        )
        self.lbl_log_path.pack(side="right", padx=12)

    # ─── LÓGICA DE DATOS ─────────────────────
    def _on_data(self, data: dict):
        """Callback cuando llega JSON del ESP32."""
        msg_type = data.get("type", "")

        if msg_type == "SCAN_REPORT":
            self._process_scan(data)
        elif msg_type == "HEARTBEAT":
            self._process_heartbeat(data)
        elif msg_type == "BOOT":
            self._add_log(f"ESP32 iniciado: {data.get('msg', '')}", "INFO")
        elif msg_type == "ACK":
            ok  = data.get("ok", False)
            cmd = data.get("cmd", "")
            msg = data.get("msg", "")
            self._add_log(f"ACK [{cmd}]: {msg}", "INFO" if ok else "WARNING")
        elif msg_type == "CALIBRATION_RESULT":
            new_tp = data.get("new_txPower", 0)
            dist   = data.get("distance_used", 0)
            rssi   = data.get("rssi_used", 0)
            self.cal_result.configure(
                text=f"✓ TxPower={new_tp:.1f} dBm  |  RSSI@1m≈{data.get('rssi_at_1m',0)} dBm"
            )
            self._add_log(
                f"Calibración: dist={dist}m, RSSI={rssi}dBm → TxPower={new_tp:.1f}dBm", "INFO"
            )

    def _process_scan(self, data: dict):
        self.scan_count    += 1
        total_crit          = data.get("critical_count", 0)
        total_warn          = data.get("warning_count", 0)
        status              = data.get("status", "INFO")
        devices             = data.get("devices", [])

        # Actualizar métricas
        self.critical_count = max(self.critical_count, total_crit)
        self.warning_count  = max(self.warning_count, total_warn)
        self.last_status    = status

        # Sonido y log de alerta
        if status == "CRITICAL":
            self.sound.alert_critical()
            self._add_log(f"⚠ ALERTA CRÍTICA: {total_crit} dispositivo(s) muy cerca!", "CRITICAL")
        elif status == "WARNING":
            self.sound.alert_warning()
            self._add_log(f"⚡ ADVERTENCIA: {total_warn} dispositivo(s) en rango medio.", "WARNING")

        # Actualizar tabla
        self.root.after(0, lambda: self._update_table(devices))

        # Log CSV de cada dispositivo no whitelisted no INFO
        for d in devices:
            if not d.get("whitelisted") and d.get("level") in ("WARNING", "CRITICAL"):
                self.logger.log_device(d)
                self._add_log(
                    f"[{d['type']}] {d.get('ssid','?')} | MAC:{d.get('mac','?')} | "
                    f"RSSI:{d.get('rssi')}dBm | Dist:~{d.get('distance')}m | {d.get('level')}",
                    d.get("level", "INFO")
                )

    def _process_heartbeat(self, data: dict):
        heap = data.get("free_heap", 0)
        self.lbl_status.configure(
            text=f"ESP32 activo | Heap libre: {heap//1024}KB | Escaneos: {self.scan_count}"
        )

    def _update_table(self, devices: list):
        # Limpiar tabla
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Ordenar: críticos primero
        order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        devices_sorted = sorted(
            devices,
            key=lambda d: (order.get(d.get("level", "INFO"), 2), d.get("rssi", -100)) if not d.get("whitelisted") else (3, 0)
        )

        for d in devices_sorted:
            wl    = d.get("whitelisted", False)
            level = "WHITELIST" if wl else d.get("level", "INFO")
            tag   = level

            dist_str = f"{float(d.get('distance', 0)):.1f}" if not wl else "WL"
            level_str = "✓ Auth" if wl else d.get("level", "INFO")

            self.tree.insert("", "end",
                values=(
                    d.get("type", ""),
                    d.get("ssid", "")[:22],
                    d.get("mac", ""),
                    d.get("rssi", ""),
                    dist_str,
                    level_str
                ),
                tags=(tag,)
            )

        # Actualizar métricas UI
        crit_devs  = [d for d in devices if not d.get("whitelisted") and d.get("level") == "CRITICAL"]
        warn_devs  = [d for d in devices if not d.get("whitelisted") and d.get("level") == "WARNING"]

        status_color = C_CRITICAL if crit_devs else (C_WARNING if warn_devs else C_INFO)
        status_text  = "CRÍTICO" if crit_devs else ("AVISO" if warn_devs else "NORMAL")

        self.lbl_estado.configure(text=status_text, text_color=status_color)
        self.lbl_critical.configure(text=str(len(crit_devs)))
        self.lbl_warning.configure(text=str(len(warn_devs)))
        self.lbl_scans.configure(text=str(self.scan_count))

    # ─── LOG ─────────────────────────────────
    def _add_log(self, text: str, level: str = "INFO"):
        ts    = datetime.now().strftime("%H:%M:%S")
        icons = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🟢"}
        icon  = icons.get(level, "⚪")
        line  = f"{icon} [{ts}] {text}\n"

        self.event_log.append(line)
        self.logger.log_event(text, level)

        def _insert():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _insert)

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"emf_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if path:
            import shutil
            shutil.copy(self.logger.get_csv_path(), path)
            messagebox.showinfo("Exportado", f"Log guardado en:\n{path}")

    # ─── COMANDOS AL ESP32 ───────────────────
    def _apply_model(self):
        if not self.serial:
            self._add_log("Sin conexión serial.", "WARNING"); return
        try:
            cmd = {
                "cmd": "SET_MODEL",
                "txPower_wifi": float(self._model_entries["txpower_wifi"].get()),
                "txPower_ble":  float(self._model_entries["txpower_ble"].get()),
                "n":            float(self._model_entries["n_exp"].get()),
            }
            self.serial.send_command(cmd)
            cmd2 = {
                "cmd": "SET_THRESHOLDS",
                "rssi_critical": int(self._model_entries["rssi_crit"].get()),
                "rssi_warning":  int(self._model_entries["rssi_warn"].get()),
            }
            self.serial.send_command(cmd2)
            self._add_log("Modelo y umbrales enviados al ESP32.", "INFO")
        except ValueError as e:
            self._add_log(f"Error en valores: {e}", "WARNING")

    def _send_calibration(self):
        if not self.serial:
            self._add_log("Sin conexión serial.", "WARNING"); return
        try:
            cmd = {
                "cmd":      "CALIBRATE",
                "distance": float(self.cal_dist.get()),
                "rssi":     int(self.cal_rssi.get()),
                "type":     self.cal_type.get(),
            }
            self.serial.send_command(cmd)
            self._add_log(f"Calibración enviada: {cmd['distance']}m / {cmd['rssi']}dBm / {cmd['type']}", "INFO")
        except ValueError as e:
            self._add_log(f"Error calibración: {e}", "WARNING")

    def _add_wifi_wl(self):
        ssid = self.wl_ssid.get().strip()
        if ssid and self.serial:
            self.serial.send_command({"cmd": "ADD_WIFI_WL", "ssid": ssid})
            self._add_log(f"Whitelist WiFi: '{ssid}'", "INFO")
            self.wl_ssid.delete(0, "end")

    def _add_ble_wl(self):
        mac = self.wl_mac.get().strip()
        if mac and self.serial:
            self.serial.send_command({"cmd": "ADD_BLE_WL", "mac": mac})
            self._add_log(f"Whitelist BLE: {mac}", "INFO")
            self.wl_mac.delete(0, "end")

    def _clear_wl(self):
        if self.serial:
            self.serial.send_command({"cmd": "CLEAR_WL"})

    # ─── CONEXIÓN ────────────────────────────
    def _detect_ports(self):
        if not SERIAL_OK:
            return
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            self.port_entry.delete(0, "end")
            self.port_entry.insert(0, ports[0])
            self._add_log(f"Puertos encontrados: {', '.join(ports)}", "INFO")
        else:
            self._add_log("No se encontraron puertos seriales.", "WARNING")

    def _auto_connect(self):
        if not SERIAL_OK:
            self._add_log("pyserial no instalado. Instala con: pip install pyserial", "WARNING")
            return
        port = self.port
        if not port:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            if ports:
                port = ports[0]
                self.port_entry.delete(0, "end")
                self.port_entry.insert(0, port)
        if port:
            self._do_connect(port)

    def _connect_serial(self):
        port = self.port_entry.get().strip()
        if port:
            self._do_connect(port)

    def _do_connect(self, port: str):
        self.serial = SerialReader(port)
        self.serial.add_callback(self._on_data)
        self.serial.set_error_callback(
            lambda e: self._add_log(f"Error serial: {e}", "WARNING")
        )
        ok = self.serial.connect()
        if ok:
            self.lbl_conn.configure(text=f"● {port}", text_color=C_INFO)
            self._add_log(f"Conectado a {port} @ 115200", "INFO")
        else:
            self.lbl_conn.configure(text="● ERROR", text_color=C_CRITICAL)
            self._add_log(f"No se pudo conectar a {port}", "WARNING")

    def _disconnect_serial(self):
        if self.serial:
            self.serial.disconnect()
            self.serial = None
        self.lbl_conn.configure(text="● DESCONECTADO", text_color=C_CRITICAL)
        self._add_log("Desconectado.", "INFO")

    # ─── LOOP UI ─────────────────────────────
    def _update_loop(self):
        if self.running:
            self.root.after(500, self._update_loop)

    def on_close(self):
        self.running = False
        if self.serial:
            self.serial.disconnect()
        self.root.destroy()


# ──────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="EMF Detector Dashboard")
    parser.add_argument("--port", help="Puerto serial (ej: COM3, /dev/ttyUSB0)", default=None)
    args = parser.parse_args()

    root = ctk.CTk()
    app  = EMFDashboard(root, port=args.port)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
