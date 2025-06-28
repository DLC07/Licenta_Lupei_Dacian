import sys
import qtawesome as qta
import zenoh
from cryptography.fernet import Fernet
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QSpacerItem, QSizePolicy, QTextEdit, QFrame
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer

SHARED_KEY = b'91uKPT7BqEWdPpOA1pAY-leCrrG9bhk9PEVNeIQi7BM='
cipher = Fernet(SHARED_KEY)

class CraneControlApp(QWidget):
    def __init__(self):
        super().__init__()
        self.zenoh_session = None
        self.zenoh_pub = None
        self.init_zenoh()
        self.init_ui()
        self.zenoh_connected = False
        self.init_zenoh_subscriber()

    def init_zenoh(self):
        try:
            cfg = zenoh.Config()
            cfg.insert_json5("connect/endpoints", '["tcp/10.13.13.104:7447"]')
            self.zenoh_session = zenoh.open(cfg)
            self.zenoh_pub = self.zenoh_session.declare_publisher("hex/send")
            self.zenoh_connected = True
        except Exception as e:
            print(f"❌ Inițializare Zenoh nereușită: {e}")
            self.zenoh_session = None
            self.zenoh_connected = False

    def init_zenoh_subscriber(self):
        try:
            def on_telemetry(sample):
                try:
                    data = cipher.decrypt(bytes(sample.payload)).decode()
                    parts = dict(item.split(":") for item in data.split(","))
                    pwm_val = parts.get("PWM", "N/A")
                    weight_val = parts.get("WEIGHT", "N/A")

                    self.current_pwm_label.setText(f"<b>PWM:</b> {pwm_val} %")
                    self.current_weight_label.setText(f"<b>Greutate:</b> {weight_val} g")
                    self.log_command(f"📡 Primit telemetrie - PWM: {pwm_val} %, Greutate: {weight_val} g")
                except Exception as e:
                    self.log_command(f"❌ Eroare primire telemetrie: {e}")

            telemetry_key = "telemetry/status"
            self.zenoh_session.declare_subscriber(telemetry_key, on_telemetry)
        except Exception as e:
            self.log_command(f"❌ Telemetry subscriber eroare: {e}")

        # Status log subscriber
        try:
            def on_status_log(sample):
                try:
                    message = cipher.decrypt(bytes(sample.payload)).decode()
                    self.log_command(f"📢 Status: {message}")
                except Exception as e:
                    self.log_command(f"❌ Error parsing status log: {e}")

            statuslog_key = "telemetry/statuslog"
            self.zenoh_session.declare_subscriber(statuslog_key, on_status_log)
        except Exception as e:
            self.log_command(f"❌ Status log subscriber error: {e}")

    def init_ui(self):
        self.setWindowTitle("Aplicatie mini macara")
        self.setFixedSize(500, 1000)
        self.setStyleSheet(self.dark_theme())

        layout = QVBoxLayout()
        layout.setSpacing(12)

        title = QLabel("🛠 Sistem de comandă mini macara")
        title.setFont(QFont("Arial", 16))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.status_label = QLabel()
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        self.update_connection_status()

        layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        button_layout = QVBoxLayout()
        buttons = [
            ("Viteza Mica", self.set_pwm_low),
            ("Viteza Mare", self.set_pwm_max),
            ("Viteza Variabila (Calcul greutate)", self.calculate_pwm),
            ("Spre Stanga", self.move_left),
            ("Spre Dreapta", self.move_right),
            ("Stop Motoare", self.stop_motors),
            ("Calcul distanță", self.measure_distance),
            ("Ieșire", self.exit_app),
        ]

        for label, method in buttons:
            btn = QPushButton(label)
            btn.setFixedHeight(45)
            btn.setFont(QFont("Arial", 12))
            btn.clicked.connect(method)
            layout.addWidget(btn)

        layout.addLayout(button_layout)

        # Telemetry display under buttons
        telemetry_layout = QVBoxLayout()
        telemetry_label = QLabel("📊 Telemetrie")
        telemetry_label.setFont(QFont("Arial", 14))
        telemetry_label.setAlignment(Qt.AlignCenter)
        big_font = QFont("Arial", 11, QFont.Bold)
        self.current_pwm_label = QLabel("<b>PWM:</b> N/A")
        self.current_pwm_label.setFont(big_font)
        self.current_weight_label = QLabel("<b>Greutate:</b> N/A")
        self.current_weight_label.setFont(big_font)
        self.current_pwm_label.setAlignment(Qt.AlignCenter)
        self.current_weight_label.setAlignment(Qt.AlignCenter)
        #self.current_pwm_label.setStyleSheet("color: #0af;")
        #self.current_weight_label.setStyleSheet("color: #0af;")

        telemetry_layout.addWidget(telemetry_label)
        telemetry_layout.addWidget(self.current_pwm_label)
        telemetry_layout.addWidget(self.current_weight_label)

        layout.addLayout(telemetry_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #555;")
        layout.addWidget(line)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background-color: #222; color: #0f0; border-radius: 5px;")
        self.log.setFont(QFont("Courier", 10))
        layout.addWidget(self.log)

        self.setLayout(layout)

    def update_connection_status(self):
        if self.zenoh_connected:
            self.status_label.setText("🟢 Conectat la Zenoh")
            self.status_label.setStyleSheet("color: #0f0;")
        else:
            self.status_label.setText("🔴 Conexiune nereușită la Zenoh")
            self.status_label.setStyleSheet("color: #f44;")

    def log_command(self, command):
        color = "#0f0"
        if "❌" in command:
            color = "#f44"  # Red
        elif "📡" in command or "PWM:" in command:
            color = "#0af"  # Cyan
        elif "📢" in command:
            color = "#ff0"  # Yellow
        html = f'<span style="color: {color};">{command}</span>'
        self.log.append(html)

    def send_hex_command(self, hex_code, label):
        try:
            raw_bytes = f"{hex_code}".encode()
            #raw_bytes = bytes.fromhex(hex_code)
            print("Trimitere prin Zenoh comanda:")
            print(f"{raw_bytes}")
            encrypted_data = cipher.encrypt(raw_bytes)
            print(f"Mesaj encriptat: {encrypted_data}")
            if self.zenoh_pub:
                self.zenoh_pub.put(encrypted_data)
                self.log_command(f"Trimis [{label}]")
            else:
                self.log_command(f"⚠ Zenoh nu e conectat. Am încercat să trimit: {label}")
        except Exception as e:
            self.log_command(f"❌ Eroare criptare/trimitere {label}: {e}")

    # Button actions
    def set_pwm_low(self):
        self.send_hex_command("01", "Viteza mica")

    def set_pwm_max(self):
        self.send_hex_command("02", "Viteza mare")

    def calculate_pwm(self):
        self.send_hex_command("03", "Viteza Variabila (Calcul greutate)")

    def move_left(self):
        self.send_hex_command("04", "Spre A")

    def move_right(self):
        self.send_hex_command("05", "Spre B")

    def stop_motors(self):
        self.send_hex_command("06", "Stop Motoare")

    def exit_app(self):
        self.send_hex_command("07", "Iesire")
        self.log_command("Aplicația se va închide în 5 secunde...")
        QTimer.singleShot(5000, self.close)

    def measure_distance(self):
        self.send_hex_command("08", "Calcul distanță")


    def dark_theme(self):
        return """
        QWidget {
            background-color: #1e1e1e;
            color: #f0f0f0;
        }
        QPushButton {
            background-color: #2e2e2e;
            border: 1px solid #444;
            border-radius: 8px;
            padding: 8px;
        }
        QPushButton:hover {
            background-color: #3a3a3a;
        }
        QPushButton:pressed {
            background-color: #4a4a4a;
        }
        """

    def closeEvent(self, event):
        if self.zenoh_session:
            self.zenoh_session.close()
        event.accept()

# Entry point
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CraneControlApp()
    window.show()
    sys.exit(app.exec_())
