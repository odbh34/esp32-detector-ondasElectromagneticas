"""
Base de datos OUI (Organizationally Unique Identifier) offline.
Los primeros 3 bytes de una MAC identifican al fabricante.
Fuente: IEEE - subset de los fabricantes más comunes en dispositivos móviles/IoT.
"""

# Formato: "XX:XX:XX" (mayúsculas, sin guiones) -> "Fabricante"
OUI_DB = {
    # ── Apple ──────────────────────────────────
    "00:03:93": "Apple", "00:05:02": "Apple", "00:0A:27": "Apple",
    "00:0A:95": "Apple", "00:0D:93": "Apple", "00:11:24": "Apple",
    "00:14:51": "Apple", "00:16:CB": "Apple", "00:17:F2": "Apple",
    "00:19:E3": "Apple", "00:1B:63": "Apple", "00:1C:B3": "Apple",
    "00:1D:4F": "Apple", "00:1E:52": "Apple", "00:1E:C2": "Apple",
    "00:1F:5B": "Apple", "00:1F:F3": "Apple", "00:21:E9": "Apple",
    "00:22:41": "Apple", "00:23:12": "Apple", "00:23:32": "Apple",
    "00:23:6C": "Apple", "00:23:DF": "Apple", "00:24:36": "Apple",
    "00:25:00": "Apple", "00:25:4B": "Apple", "00:25:BC": "Apple",
    "00:26:08": "Apple", "00:26:4A": "Apple", "00:26:B9": "Apple",
    "00:26:BB": "Apple", "00:30:65": "Apple", "00:3E:E1": "Apple",
    "00:50:E4": "Apple", "00:56:CD": "Apple", "00:61:71": "Apple",
    "04:0C:CE": "Apple", "04:15:52": "Apple", "04:1E:64": "Apple",
    "04:26:65": "Apple", "04:52:F3": "Apple", "04:54:53": "Apple",
    "04:69:F8": "Apple", "04:D3:CF": "Apple", "04:F1:3E": "Apple",
    "08:00:07": "Apple", "08:6D:41": "Apple", "08:70:45": "Apple",
    "08:74:02": "Apple", "0C:15:39": "Apple", "0C:30:21": "Apple",
    "0C:3E:9F": "Apple", "0C:4D:E9": "Apple", "0C:51:01": "Apple",
    "0C:74:C2": "Apple", "0C:BC:9F": "Apple", "0C:D7:46": "Apple",
    "10:1C:0C": "Apple", "10:40:F3": "Apple", "10:41:7F": "Apple",
    "10:9A:DD": "Apple", "14:5A:05": "Apple", "14:8F:C6": "Apple",
    "14:99:E2": "Apple", "18:20:32": "Apple", "18:34:51": "Apple",
    "18:65:90": "Apple", "18:81:0E": "Apple", "18:9E:FC": "Apple",
    "1C:1A:C0": "Apple", "1C:36:BB": "Apple", "20:76:93": "Apple",
    "20:78:F0": "Apple", "24:1E:EB": "Apple", "24:A0:74": "Apple",
    "28:37:37": "Apple", "28:5A:EB": "Apple", "28:6A:BA": "Apple",
    "2C:BE:08": "Apple", "2C:F0:EE": "Apple", "30:10:E4": "Apple",
    "34:08:BC": "Apple", "34:15:9E": "Apple", "34:36:3B": "Apple",
    "38:0F:4A": "Apple", "3C:07:54": "Apple", "3C:15:C2": "Apple",
    "40:30:04": "Apple", "40:4D:7F": "Apple", "40:A6:D9": "Apple",
    "44:00:10": "Apple", "44:2A:60": "Apple", "48:BF:6B": "Apple",
    "4C:57:CA": "Apple", "4C:74:BF": "Apple", "50:EA:D6": "Apple",
    "54:26:96": "Apple", "54:AE:27": "Apple", "58:1F:AA": "Apple",
    "5C:59:48": "Apple", "5C:95:AE": "Apple", "5C:AD:CF": "Apple",
    "60:03:08": "Apple", "60:69:44": "Apple", "60:C5:47": "Apple",
    "60:D9:C7": "Apple", "60:F4:45": "Apple", "64:20:0C": "Apple",
    "64:76:BA": "Apple", "64:9A:BE": "Apple", "64:B0:A6": "Apple",
    "68:09:27": "Apple", "68:5B:35": "Apple", "68:96:7B": "Apple",
    "6C:19:C0": "Apple", "6C:4D:73": "Apple", "6C:72:20": "Apple",
    "6C:94:F8": "Apple", "70:11:24": "Apple", "70:3E:AC": "Apple",
    "70:56:81": "Apple", "70:81:EB": "Apple", "70:A2:B3": "Apple",
    "70:CD:60": "Apple", "70:DE:E2": "Apple", "70:EC:E4": "Apple",
    "74:1B:B2": "Apple", "74:E1:B6": "Apple", "78:31:C1": "Apple",
    "78:4F:43": "Apple", "78:6C:1C": "Apple", "78:7B:8A": "Apple",
    "78:D7:5F": "Apple", "7C:01:91": "Apple", "7C:6D:62": "Apple",
    "7C:C3:A1": "Apple", "80:00:6E": "Apple", "80:92:9F": "Apple",
    "80:E6:50": "Apple", "84:29:99": "Apple", "84:38:35": "Apple",
    "84:78:8B": "Apple", "84:85:06": "Apple", "84:B1:53": "Apple",
    "88:19:08": "Apple", "88:53:2E": "Apple", "88:63:DF": "Apple",
    "88:C6:63": "Apple", "8C:2D:AA": "Apple", "8C:58:77": "Apple",
    "8C:7C:92": "Apple", "8C:85:90": "Apple", "8C:FA:BA": "Apple",
    "90:27:E4": "Apple", "90:3C:92": "Apple", "90:72:40": "Apple",
    "90:B9:31": "Apple", "90:FD:61": "Apple", "94:BF:2D": "Apple",
    "94:E9:6A": "Apple", "94:F6:A3": "Apple", "98:01:A7": "Apple",
    "98:03:D8": "Apple", "98:10:E8": "Apple", "98:FE:94": "Apple",
    "9C:04:EB": "Apple", "9C:20:7B": "Apple", "9C:84:BF": "Apple",
    "9C:F3:87": "Apple", "A0:3B:E3": "Apple", "A0:99:9B": "Apple",
    "A0:D7:95": "Apple", "A4:5E:60": "Apple", "A4:B8:05": "Apple",
    "A4:C3:61": "Apple", "A4:D9:31": "Apple", "A4:F1:E8": "Apple",
    "A8:20:66": "Apple", "A8:5C:2C": "Apple", "A8:88:08": "Apple",
    "A8:96:75": "Apple", "AC:1F:74": "Apple", "AC:3C:0B": "Apple",
    "AC:61:EA": "Apple", "AC:87:A3": "Apple", "AC:BC:32": "Apple",
    "B0:19:C6": "Apple", "B0:34:95": "Apple", "B0:65:BD": "Apple",
    "B0:70:2D": "Apple", "B0:9F:BA": "Apple", "B4:18:D1": "Apple",
    "B4:4B:D2": "Apple", "B4:F6:1C": "Apple", "B8:09:8A": "Apple",
    "B8:17:C2": "Apple", "B8:53:AC": "Apple", "B8:63:4D": "Apple",
    "B8:78:2E": "Apple", "B8:8D:12": "Apple", "BC:3B:AF": "Apple",
    "BC:52:B7": "Apple", "BC:67:1C": "Apple", "BC:92:6B": "Apple",
    "C0:63:94": "Apple", "C0:9F:42": "Apple", "C0:CE:CD": "Apple",
    "C4:2C:03": "Apple", "C8:2A:14": "Apple", "C8:6F:1D": "Apple",
    "C8:B5:B7": "Apple", "C8:BC:C8": "Apple", "C8:D0:83": "Apple",
    "CC:08:8D": "Apple", "CC:25:EF": "Apple", "CC:44:63": "Apple",
    "D0:03:4B": "Apple", "D0:23:DB": "Apple", "D0:25:98": "Apple",
    "D0:33:11": "Apple", "D0:4F:7E": "Apple", "D4:61:9D": "Apple",
    "D4:9A:20": "Apple", "D4:DC:CD": "Apple", "D8:00:4D": "Apple",
    "D8:1D:72": "Apple", "D8:96:95": "Apple", "D8:9E:3F": "Apple",
    "D8:BB:C1": "Apple", "DC:2B:2A": "Apple", "DC:37:14": "Apple",
    "DC:41:5F": "Apple", "DC:9B:9C": "Apple", "DC:A4:CA": "Apple",
    "E0:33:8E": "Apple", "E0:AC:CB": "Apple", "E0:B5:2D": "Apple",
    "E0:C9:7A": "Apple", "E0:F5:C6": "Apple", "E4:25:E7": "Apple",
    "E4:98:D6": "Apple", "E4:CE:8F": "Apple", "E4:E4:AB": "Apple",
    "E8:04:0B": "Apple", "E8:06:88": "Apple", "E8:80:2E": "Apple",
    "EC:35:86": "Apple", "EC:85:2F": "Apple", "F0:18:98": "Apple",
    "F0:24:75": "Apple", "F0:7B:CB": "Apple", "F0:B4:79": "Apple",
    "F0:C1:F1": "Apple", "F0:CB:A1": "Apple", "F0:D1:A9": "Apple",
    "F0:DB:E2": "Apple", "F0:DC:E2": "Apple", "F0:F6:1C": "Apple",
    "F4:0F:24": "Apple", "F4:1B:A1": "Apple", "F4:5C:89": "Apple",
    "F4:F1:5A": "Apple", "F8:1E:DF": "Apple", "F8:27:93": "Apple",
    "F8:62:14": "Apple", "F8:7B:7A": "Apple", "FC:25:3F": "Apple",
    "FC:E9:98": "Apple",
    # ── Samsung ─────────────────────────────────
    "00:00:F0": "Samsung", "00:02:78": "Samsung", "00:07:AB": "Samsung",
    "00:12:47": "Samsung", "00:13:77": "Samsung", "00:15:99": "Samsung",
    "00:15:B9": "Samsung", "00:16:32": "Samsung", "00:16:6B": "Samsung",
    "00:16:6C": "Samsung", "00:17:C9": "Samsung", "00:17:D5": "Samsung",
    "00:18:AF": "Samsung", "00:1A:8A": "Samsung", "00:1B:98": "Samsung",
    "00:1C:43": "Samsung", "00:1D:25": "Samsung", "00:1D:F6": "Samsung",
    "00:1E:7D": "Samsung", "00:21:19": "Samsung", "00:21:D1": "Samsung",
    "00:21:D2": "Samsung", "00:23:39": "Samsung", "00:23:3A": "Samsung",
    "00:24:54": "Samsung", "00:24:91": "Samsung", "00:25:66": "Samsung",
    "00:25:67": "Samsung", "00:26:37": "Samsung", "00:E3:B2": "Samsung",
    "04:18:0F": "Samsung", "04:1B:BA": "Samsung", "04:FE:31": "Samsung",
    "08:08:C2": "Samsung", "08:D4:2B": "Samsung", "08:EE:8B": "Samsung",
    "08:FC:88": "Samsung", "0C:14:20": "Samsung", "0C:71:5D": "Samsung",
    "10:1D:C0": "Samsung", "10:30:47": "Samsung", "10:D5:42": "Samsung",
    "14:49:E0": "Samsung", "14:89:FD": "Samsung", "18:22:7E": "Samsung",
    "18:3A:2D": "Samsung", "18:83:BF": "Samsung", "1C:62:B8": "Samsung",
    "1C:66:AA": "Samsung", "20:13:E0": "Samsung", "20:6E:9C": "Samsung",
    "24:4B:03": "Samsung", "24:92:0E": "Samsung", "28:27:BF": "Samsung",
    "28:98:7B": "Samsung", "2C:AE:2B": "Samsung", "30:19:66": "Samsung",
    "34:14:5F": "Samsung", "34:23:87": "Samsung", "34:AA:8B": "Samsung",
    "38:16:D1": "Samsung", "38:2D:E8": "Samsung", "3C:5A:37": "Samsung",
    "40:0E:85": "Samsung", "44:78:3E": "Samsung", "48:13:7E": "Samsung",
    "48:44:F7": "Samsung", "4C:3C:16": "Samsung", "4C:BC:A5": "Samsung",
    "50:01:BB": "Samsung", "50:32:75": "Samsung", "50:A4:C8": "Samsung",
    "50:CC:F8": "Samsung", "54:88:0E": "Samsung", "54:9B:12": "Samsung",
    "58:C3:8B": "Samsung", "5C:0A:5B": "Samsung", "5C:49:7D": "Samsung",
    "5C:E8:EB": "Samsung", "60:6B:FF": "Samsung", "64:77:91": "Samsung",
    "68:EB:AE": "Samsung", "6C:83:36": "Samsung", "6C:F3:73": "Samsung",
    "70:F9:27": "Samsung", "74:45:8A": "Samsung", "78:25:AD": "Samsung",
    "78:40:E4": "Samsung", "78:59:5E": "Samsung", "78:9E:D0": "Samsung",
    "7C:0B:C6": "Samsung", "7C:61:93": "Samsung", "80:57:19": "Samsung",
    "84:11:9E": "Samsung", "84:25:DB": "Samsung", "84:38:38": "Samsung",
    "84:55:A5": "Samsung", "88:32:9B": "Samsung", "88:6A:E3": "Samsung",
    "8C:71:F8": "Samsung", "8C:77:12": "Samsung", "90:18:7C": "Samsung",
    "90:F1:AA": "Samsung", "94:01:C2": "Samsung", "94:63:D1": "Samsung",
    "98:52:B1": "Samsung", "98:6C:F5": "Samsung", "9C:02:98": "Samsung",
    "9C:3A:AF": "Samsung", "A0:0B:BA": "Samsung", "A0:21:95": "Samsung",
    "A0:82:1F": "Samsung", "A0:B4:A5": "Samsung", "A4:07:B6": "Samsung",
    "A8:06:00": "Samsung", "A8:7D:12": "Samsung", "AC:36:13": "Samsung",
    "AC:5F:3E": "Samsung", "B0:47:BF": "Samsung", "B0:D0:9C": "Samsung",
    "B4:07:F9": "Samsung", "B4:3A:28": "Samsung", "B4:79:A7": "Samsung",
    "B8:5E:7B": "Samsung", "BC:20:A4": "Samsung", "BC:44:86": "Samsung",
    "BC:72:B1": "Samsung", "BC:8C:CD": "Samsung", "C0:BD:D1": "Samsung",
    "C4:42:02": "Samsung", "C4:88:E5": "Samsung", "C4:9A:02": "Samsung",
    "C8:19:F7": "Samsung", "C8:D1:5E": "Samsung", "CC:07:AB": "Samsung",
    "D0:17:6A": "Samsung", "D0:22:BE": "Samsung", "D0:59:E4": "Samsung",
    "D0:DF:C7": "Samsung", "D4:E8:B2": "Samsung", "D8:57:EF": "Samsung",
    "DC:71:96": "Samsung", "E0:99:71": "Samsung", "E4:12:1D": "Samsung",
    "E4:40:E2": "Samsung", "E4:92:FB": "Samsung", "E8:03:9A": "Samsung",
    "E8:4E:84": "Samsung", "EC:1F:72": "Samsung", "EC:9B:F3": "Samsung",
    "F0:5A:09": "Samsung", "F0:6B:CA": "Samsung", "F4:42:8F": "Samsung",
    "F8:04:2E": "Samsung", "F8:3F:51": "Samsung", "FC:A1:3E": "Samsung",
    # ── Xiaomi ──────────────────────────────────
    "00:9E:C8": "Xiaomi", "04:CF:8C": "Xiaomi", "0C:1D:AF": "Xiaomi",
    "10:2A:B3": "Xiaomi", "18:59:36": "Xiaomi", "20:82:C0": "Xiaomi",
    "28:6C:07": "Xiaomi", "34:80:B3": "Xiaomi", "38:A4:ED": "Xiaomi",
    "3C:BD:D8": "Xiaomi", "40:31:3C": "Xiaomi", "50:64:2B": "Xiaomi",
    "58:44:98": "Xiaomi", "5C:E8:EB": "Xiaomi", "64:09:80": "Xiaomi",
    "64:B4:73": "Xiaomi", "68:DF:DD": "Xiaomi", "74:23:44": "Xiaomi",
    "78:02:F8": "Xiaomi", "7C:1D:D9": "Xiaomi", "8C:BE:BE": "Xiaomi",
    "98:FA:E3": "Xiaomi", "9C:99:A0": "Xiaomi", "A4:C1:38": "Xiaomi",
    "B0:E2:35": "Xiaomi", "C4:0B:CB": "Xiaomi", "CC:2D:E0": "Xiaomi",
    "D4:97:0B": "Xiaomi", "F0:B4:29": "Xiaomi", "F8:A4:5F": "Xiaomi",
    "FC:64:BA": "Xiaomi", "FC:F8:AE": "Xiaomi",
    # ── Huawei ──────────────────────────────────
    "00:18:82": "Huawei", "00:1E:10": "Huawei", "00:25:9E": "Huawei",
    "04:02:1F": "Huawei", "04:75:03": "Huawei", "0C:37:DC": "Huawei",
    "14:B9:68": "Huawei", "18:C5:8A": "Huawei", "1C:8E:5C": "Huawei",
    "20:2B:C1": "Huawei", "20:F3:A3": "Huawei", "28:6E:D4": "Huawei",
    "2C:AB:00": "Huawei", "2C:F4:32": "Huawei", "30:D1:7E": "Huawei",
    "34:6B:D3": "Huawei", "38:BC:01": "Huawei", "3C:F8:08": "Huawei",
    "40:4D:8E": "Huawei", "44:55:B1": "Huawei", "48:00:31": "Huawei",
    "48:46:FB": "Huawei", "4C:1F:CC": "Huawei", "4C:54:99": "Huawei",
    "50:9F:27": "Huawei", "54:89:98": "Huawei", "58:2A:F7": "Huawei",
    "5C:C3:07": "Huawei", "60:DE:44": "Huawei", "64:3E:8C": "Huawei",
    "68:13:24": "Huawei", "6C:8D:C1": "Huawei", "70:72:3C": "Huawei",
    "74:A5:28": "Huawei", "78:1D:BA": "Huawei", "78:F5:57": "Huawei",
    "7C:A2:3E": "Huawei", "80:B6:86": "Huawei", "84:47:09": "Huawei",
    "88:E3:AB": "Huawei", "8C:0D:76": "Huawei", "8C:34:FD": "Huawei",
    "90:67:1C": "Huawei", "94:DB:DA": "Huawei", "9C:37:F4": "Huawei",
    "A0:86:C6": "Huawei", "A4:CA:DD": "Huawei", "AC:4E:91": "Huawei",
    "AC:E2:15": "Huawei", "B0:05:94": "Huawei", "B4:15:13": "Huawei",
    "B4:CD:27": "Huawei", "BC:76:70": "Huawei", "C0:70:09": "Huawei",
    "C4:07:2F": "Huawei", "C4:FF:1F": "Huawei", "C8:14:79": "Huawei",
    "CC:A2:23": "Huawei", "D0:7A:B5": "Huawei", "D4:6A:A8": "Huawei",
    "D8:49:0B": "Huawei", "DC:D9:16": "Huawei", "E0:19:1D": "Huawei",
    "E4:68:A3": "Huawei", "E8:CD:2D": "Huawei", "EC:CB:30": "Huawei",
    "F4:4C:7F": "Huawei", "F4:CB:52": "Huawei", "F8:3D:FF": "Huawei",
    "FC:3F:DB": "Huawei",
    # ── Intel (laptops WiFi) ─────────────────────
    "00:02:B3": "Intel", "00:03:47": "Intel", "00:04:23": "Intel",
    "00:0C:F1": "Intel", "00:0E:35": "Intel", "00:0E:D7": "Intel",
    "00:11:11": "Intel", "00:12:F0": "Intel", "00:13:02": "Intel",
    "00:13:20": "Intel", "00:13:CE": "Intel", "00:13:E8": "Intel",
    "00:15:00": "Intel", "00:16:76": "Intel", "00:16:EA": "Intel",
    "00:16:EB": "Intel", "00:18:DE": "Intel", "00:19:D1": "Intel",
    "00:19:D2": "Intel", "00:1B:21": "Intel", "00:1B:77": "Intel",
    "00:1C:BF": "Intel", "00:1D:E0": "Intel", "00:1D:E1": "Intel",
    "00:1E:64": "Intel", "00:1E:65": "Intel", "00:1F:3A": "Intel",
    "00:1F:3B": "Intel", "00:20:FC": "Intel", "00:21:5C": "Intel",
    "00:21:5D": "Intel", "00:21:6A": "Intel", "00:21:6B": "Intel",
    "00:22:FB": "Intel", "00:23:14": "Intel", "00:24:D6": "Intel",
    "00:24:D7": "Intel", "00:27:10": "Intel", "04:0E:3C": "Intel",
    "08:D4:0C": "Intel", "10:02:B5": "Intel", "10:F2:01": "Intel",
    "24:77:03": "Intel", "28:D2:44": "Intel", "2C:6E:85": "Intel",
    "34:02:86": "Intel", "34:13:E8": "Intel", "38:BA:F8": "Intel",
    "3C:A9:F4": "Intel", "40:25:C2": "Intel", "44:85:00": "Intel",
    "48:51:B7": "Intel", "4C:79:6E": "Intel", "50:7B:9D": "Intel",
    "54:27:1E": "Intel", "58:A8:39": "Intel", "5C:51:4F": "Intel",
    "60:67:20": "Intel", "68:5D:43": "Intel", "6C:88:14": "Intel",
    "70:5A:0F": "Intel", "78:92:9C": "Intel", "7C:7A:91": "Intel",
    "80:19:34": "Intel", "84:3A:4B": "Intel", "8C:70:5A": "Intel",
    "90:48:9A": "Intel", "94:65:9C": "Intel", "98:4F:EE": "Intel",
    "9C:DA:3E": "Intel", "A0:A8:CD": "Intel", "A4:34:D9": "Intel",
    "AC:37:43": "Intel", "B0:35:9F": "Intel", "B4:AE:2B": "Intel",
    "B8:08:CF": "Intel", "BC:0F:9A": "Intel", "C4:8E:8F": "Intel",
    "C8:FF:28": "Intel", "CC:3D:82": "Intel", "D0:50:99": "Intel",
    "D4:BE:D9": "Intel", "D8:FC:93": "Intel", "DC:85:DE": "Intel",
    "E0:06:E6": "Intel", "E4:A7:C5": "Intel", "F8:16:54": "Intel",
    "FC:F8:AE": "Intel",
    # ── Qualcomm / Atheros ───────────────────────
    "00:02:6F": "Qualcomm-Atheros", "00:03:7F": "Qualcomm-Atheros",
    "00:0B:6B": "Qualcomm-Atheros", "00:17:3F": "Qualcomm-Atheros",
    "00:1A:EF": "Qualcomm-Atheros", "00:1B:FC": "Qualcomm-Atheros",
    "00:90:4C": "Qualcomm-Atheros", "04:F0:21": "Qualcomm-Atheros",
    "20:C9:D0": "Qualcomm-Atheros", "6C:40:08": "Qualcomm-Atheros",
    "D4:85:64": "Qualcomm-Atheros", "E8:DE:27": "Qualcomm-Atheros",
    # ── Realtek ──────────────────────────────────
    "00:01:2E": "Realtek", "00:02:44": "Realtek", "00:11:2F": "Realtek",
    "00:14:78": "Realtek", "00:15:AF": "Realtek", "00:1B:2F": "Realtek",
    "00:20:FC": "Realtek", "00:21:91": "Realtek", "00:26:18": "Realtek",
    "00:E0:4C": "Realtek", "52:54:00": "Realtek",
    # ── MediaTek ─────────────────────────────────
    "00:0C:E7": "MediaTek", "00:0D:56": "MediaTek", "00:1A:11": "MediaTek",
    "00:1F:E1": "MediaTek", "00:28:F8": "MediaTek", "6C:5A:B0": "MediaTek",
    "A4:C3:F0": "MediaTek", "D4:DF:2E": "MediaTek",
    # ── Espressif (ESP32 / ESP8266) ──────────────
    "10:52:1C": "Espressif", "18:FE:34": "Espressif",
    "24:0A:C4": "Espressif", "24:6F:28": "Espressif",
    "2C:F4:32": "Espressif", "30:AE:A4": "Espressif",
    "3C:61:05": "Espressif", "48:3F:DA": "Espressif",
    "5C:CF:7F": "Espressif", "60:01:94": "Espressif",
    "68:C6:3A": "Espressif", "70:03:9F": "Espressif",
    "7C:87:CE": "Espressif", "80:7D:3A": "Espressif",
    "84:0D:8E": "Espressif", "84:CC:A8": "Espressif",
    "84:F3:EB": "Espressif", "8C:AA:B5": "Espressif",
    "90:97:D5": "Espressif", "94:B9:7E": "Espressif",
    "A0:20:A6": "Espressif", "A4:CF:12": "Espressif",
    "A8:03:2A": "Espressif", "AC:67:B2": "Espressif",
    "B4:E6:2D": "Espressif", "BC:DD:C2": "Espressif",
    "C4:DD:57": "Espressif", "C8:2B:96": "Espressif",
    "CC:50:E3": "Espressif", "D8:A0:1D": "Espressif",
    "DC:4F:22": "Espressif", "E0:98:06": "Espressif",
    "E8:68:E7": "Espressif", "EC:94:CB": "Espressif",
    "F4:CF:A2": "Espressif",
    # ── Motorola ─────────────────────────────────
    "00:04:56": "Motorola", "00:0D:FD": "Motorola", "00:15:E9": "Motorola",
    "00:17:76": "Motorola", "00:1A:1B": "Motorola", "00:1C:9A": "Motorola",
    "00:50:14": "Motorola", "08:00:60": "Motorola", "40:6C:8F": "Motorola",
    "50:A4:C8": "Motorola", "68:7F:74": "Motorola", "84:10:0D": "Motorola",
    "AC:37:43": "Motorola", "BC:77:37": "Motorola", "CC:32:E5": "Motorola",
    "E8:B6:A7": "Motorola",
    # ── OnePlus ──────────────────────────────────
    "00:00:00": "OnePlus", "AC:59:75": "OnePlus", "D4:73:9B": "OnePlus",
    "D8:31:CF": "OnePlus",
    # ── Google (Pixel) ───────────────────────────
    "00:1A:11": "Google", "08:9E:08": "Google", "20:DF:B9": "Google",
    "3C:5A:B4": "Google", "54:60:09": "Google", "60:F1:89": "Google",
    "C4:43:8F": "Google", "F4:F5:DB": "Google",
    # ── Lenovo ───────────────────────────────────
    "00:00:1D": "Lenovo", "00:1A:6B": "Lenovo", "00:1B:B1": "Lenovo",
    "10:C3:7B": "Lenovo", "28:D2:44": "Lenovo", "40:2C:F4": "Lenovo",
    "4C:1D:96": "Lenovo", "50:5B:C2": "Lenovo", "54:05:DB": "Lenovo",
    "68:F7:28": "Lenovo", "70:5A:AC": "Lenovo", "78:92:9C": "Lenovo",
    "80:FA:5B": "Lenovo", "90:2B:34": "Lenovo", "98:FA:9B": "Lenovo",
    "A4:4E:31": "Lenovo", "AC:B5:7D": "Lenovo", "C4:69:F0": "Lenovo",
    "D0:53:49": "Lenovo", "E4:A7:C5": "Lenovo", "F8:16:54": "Lenovo",
    # ── Dell ─────────────────────────────────────
    "00:06:5B": "Dell", "00:08:74": "Dell", "00:0B:DB": "Dell",
    "00:0D:56": "Dell", "00:11:43": "Dell", "00:12:3F": "Dell",
    "00:13:72": "Dell", "00:14:22": "Dell", "00:15:C5": "Dell",
    "00:16:F0": "Dell", "00:18:8B": "Dell", "00:19:B9": "Dell",
    "00:1A:A0": "Dell", "00:1C:23": "Dell", "00:1D:09": "Dell",
    "00:21:70": "Dell", "00:22:19": "Dell", "00:23:AE": "Dell",
    "00:24:E8": "Dell", "00:25:64": "Dell", "00:26:B9": "Dell",
    "18:03:73": "Dell", "18:FB:7B": "Dell", "1C:40:24": "Dell",
    "24:B6:FD": "Dell", "28:F1:0E": "Dell", "34:E6:D7": "Dell",
    "38:EA:A7": "Dell", "44:A8:42": "Dell", "54:9F:35": "Dell",
    "5C:F9:DD": "Dell", "6C:2B:59": "Dell", "74:E6:E2": "Dell",
    "78:45:C4": "Dell", "84:7B:EB": "Dell", "88:AE:1D": "Dell",
    "8C:EC:4B": "Dell", "90:B1:1C": "Dell", "9C:EB:E8": "Dell",
    "A4:1F:72": "Dell", "A4:C3:F0": "Dell", "BC:EE:7B": "Dell",
    "C8:1F:66": "Dell", "D4:AE:52": "Dell", "D8:9E:F3": "Dell",
    "E4:B9:7A": "Dell", "F0:1F:AF": "Dell", "F4:8E:38": "Dell",
    "FC:15:B4": "Dell",
    # ── HP ───────────────────────────────────────
    "00:01:E6": "HP", "00:02:A5": "HP", "00:04:EA": "HP",
    "00:08:02": "HP", "00:0B:CD": "HP", "00:0E:7F": "HP",
    "00:10:83": "HP", "00:11:0A": "HP", "00:12:79": "HP",
    "00:13:21": "HP", "00:14:38": "HP", "00:15:60": "HP",
    "00:16:35": "HP", "00:17:08": "HP", "00:18:FE": "HP",
    "00:19:BB": "HP", "00:1A:4B": "HP", "00:1B:78": "HP",
    "00:1C:C4": "HP", "00:1E:0B": "HP", "00:1F:29": "HP",
    "00:21:5A": "HP", "00:22:64": "HP", "00:23:7D": "HP",
    "00:24:81": "HP", "00:25:B3": "HP", "00:26:55": "HP",
    "00:30:6E": "HP", "18:A9:05": "HP", "1C:C1:DE": "HP",
    "28:92:4A": "HP", "3C:D9:2B": "HP", "40:B0:34": "HP",
    "48:0F:CF": "HP", "5C:B9:01": "HP", "6C:C2:17": "HP",
    "78:48:59": "HP", "80:CE:62": "HP", "9C:8E:99": "HP",
    "A0:D3:C1": "HP", "B8:AC:6F": "HP", "C8:CB:9E": "HP",
    "D8:9D:67": "HP", "EC:B1:D7": "HP", "F4:CE:46": "HP",
    # ── ASUS ─────────────────────────────────────
    "00:0C:6E": "ASUS", "00:0E:A6": "ASUS", "00:11:2F": "ASUS",
    "00:13:D4": "ASUS", "00:15:F2": "ASUS", "00:17:31": "ASUS",
    "00:18:F3": "ASUS", "00:1A:92": "ASUS", "00:1B:FC": "ASUS",
    "00:1D:60": "ASUS", "00:1E:8C": "ASUS", "00:1F:C6": "ASUS",
    "00:22:15": "ASUS", "00:23:54": "ASUS", "00:24:8C": "ASUS",
    "00:25:D3": "ASUS", "00:26:18": "ASUS", "04:92:26": "ASUS",
    "10:C3:7B": "ASUS", "14:DA:E9": "ASUS", "1C:B7:2C": "ASUS",
    "20:CF:30": "ASUS", "2C:FD:A1": "ASUS", "30:5A:3A": "ASUS",
    "38:2C:4A": "ASUS", "3C:97:0E": "ASUS", "40:16:7E": "ASUS",
    "48:5B:39": "ASUS", "50:46:5D": "ASUS", "54:04:A6": "ASUS",
    "60:45:CB": "ASUS", "74:D0:2B": "ASUS", "7C:10:C9": "ASUS",
    "90:E6:BA": "ASUS", "9C:5C:8E": "ASUS", "AC:22:0B": "ASUS",
    "BC:AE:C5": "ASUS", "C8:60:00": "ASUS", "D8:50:E6": "ASUS",
    "E0:3F:49": "ASUS", "F4:6D:04": "ASUS", "FC:AA:14": "ASUS",
    # ── Raspberry Pi Foundation ───────────────────
    "B8:27:EB": "Raspberry Pi", "DC:A6:32": "Raspberry Pi",
    "E4:5F:01": "Raspberry Pi", "28:CD:C1": "Raspberry Pi",
    # ── TP-Link ──────────────────────────────────
    "00:14:78": "TP-Link", "00:1D:0F": "TP-Link", "00:23:CD": "TP-Link",
    "00:27:19": "TP-Link", "14:CC:20": "TP-Link", "1C:61:B4": "TP-Link",
    "20:DC:E6": "TP-Link", "2C:4D:54": "TP-Link", "30:B5:C2": "TP-Link",
    "38:8B:59": "TP-Link", "40:16:9F": "TP-Link", "50:C7:BF": "TP-Link",
    "54:E6:FC": "TP-Link", "60:E3:27": "TP-Link", "64:70:02": "TP-Link",
    "68:FF:7B": "TP-Link", "74:EA:3A": "TP-Link", "78:A1:06": "TP-Link",
    "90:F6:52": "TP-Link", "94:0C:98": "TP-Link", "98:DA:C4": "TP-Link",
    "A0:F3:C1": "TP-Link", "AC:84:C6": "TP-Link", "B0:4E:26": "TP-Link",
    "C4:6E:1F": "TP-Link", "D8:07:B6": "TP-Link", "E4:D3:32": "TP-Link",
    "EC:17:2F": "TP-Link", "F4:F2:6D": "TP-Link", "18:D6:C7": "TP-Link Technologies",
    "D8:9A:0D": "Shenzhen Bilian Electronic",
    "6C:11:BA": "ASUSTek Computer Inc.",
    # Honor
    "90:4C:81":"Honor",
    "2C:AB:A4":"Honor",
    "A8:BA:25":"Honor",

    # Tecno
    "48:00:20":"Tecno",
    "60:6C:63":"Tecno",
    "54:F0:B1":"Tecno",
    "A8:BA:25":"Tecno",

    # Oppo
    "10:2B:41":"Oppo",
    "20:7D:74":"Oppo",
    "8C:0E:E3":"Oppo",
    "D4:61:2E":"Oppo",

    # Vivo
    "38:BC:1A":"Vivo",
    "50:8F:4C":"Vivo",
    "A0:56:F3":"Vivo",

    # Realme
    "68:47:B0":"Realme",
    "C0:E8:62":"Realme",
    "98:FD:B4":"Realme",

    # Infinix
    "B4:7C:29":"Infinix",
    "60:01:B3":"Infinix",

    # Razer
    "C8:E5:D8":"Razer",

    # JBL
    "00:1D:DF":"JBL",

    # Sony
    "F8:D0:27":"Sony",

    # TP-Link extra
    "68:FF:7B":"TP-Link",
    "50:C7:BF":"TP-Link",
    "60:E3:27":"TP-Link",

    # routers ISP frecuentes
    "54:F0:B1":"FiberHome",
    "48:00:20":"ZTE",
    "90:4C:81":"ZTE"
}

def lookup_manufacturer(mac: str):
    mac = mac.upper().replace("-", ":").strip()

    if len(mac) < 8:
        return "Desconocido", False

    try:
        first_byte = int(mac[0:2],16)
        is_random = bool(first_byte & 0x02)
    except:
        is_random=False

    oui=mac[:8]

    manufacturer=OUI_DB.get(oui)

    if manufacturer:
        return manufacturer,is_random

    if is_random:
        return "MAC Aleatoria (Privacidad)",True

    return "Desconocido",False

def infer_from_ssid(ssid, manufacturer):

    if manufacturer != "MAC Aleatoria (Privacidad)":
        return manufacturer

    s=ssid.lower()

    patterns={

        "honor":"Honor",
        "redmi":"Xiaomi",
        "xiaomi":"Xiaomi",
        "mi ":"Xiaomi",
        "tecno":"Tecno",
        "spark":"Tecno",
        "galaxy":"Samsung",
        "samsung":"Samsung",
        "moto":"Motorola",
        "oppo":"Oppo",
        "vivo":"Vivo",
        "iphone":"Apple",
        "ipad":"Apple",
        "pixel":"Google",
        "huawei":"Huawei",
        "infinix":"Infinix",
        "realme":"Realme"

    }

    for k,v in patterns.items():
        if k in s:
            return v

    return manufacturer


def get_device_risk_profile(manufacturer: str, mac_is_random: bool, sig_type: str) -> dict:
    """
    Devuelve un perfil de riesgo basado en el fabricante y tipo de señal.
    Útil para el contexto de detección en exámenes.
    """
    mobile_brands = {"Apple", "Samsung", "Xiaomi", "Huawei", "Motorola", "OnePlus", "Google"}
    laptop_brands = {"Intel", "Qualcomm-Atheros", "Realtek", "MediaTek", "Dell", "HP", "ASUS", "Lenovo"}
    iot_brands    = {"Espressif", "Raspberry Pi", "TP-Link"}

    if mac_is_random:
        return {
            "device_type": "Smartphone moderno",
            "risk": "HIGH",
            "note": "MAC aleatoria activa. iOS 14+/Android 10+/Win10 usan esto para privacidad. Indica celular o laptop reciente intentando ocultarse."
        }
    elif manufacturer in mobile_brands:
        return {
            "device_type": "Smartphone / Tablet",
            "risk": "HIGH",
            "note": f"Dispositivo {manufacturer}. Probablemente un teléfono celular o tablet."
        }
    elif manufacturer in laptop_brands:
        return {
            "device_type": "Laptop / PC",
            "risk": "MEDIUM",
            "note": f"Chip WiFi {manufacturer}. Típico de laptops o computadoras de escritorio."
        }
    elif manufacturer in iot_brands:
        return {
            "device_type": "Dispositivo IoT",
            "risk": "LOW",
            "note": f"Hardware {manufacturer}. Probablemente un router, sensor o dispositivo IoT."
        }
    else:
        return {
            "device_type": "Desconocido",
            "risk": "MEDIUM",
            "note": "OUI no reconocido. Puede ser dispositivo de nicho o MAC personalizada."
        }

