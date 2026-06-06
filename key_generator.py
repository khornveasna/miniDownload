import hashlib
import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtCore import Qt

SECRET_SALT = "MiniDownloadSecretSalt2026!"

def generate_key(hwid):
    raw = hwid.strip() + SECRET_SALT
    h = hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()
    return f"{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

class KeyGeneratorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Mini Download - Key Generator")
        self.resize(500, 250)
        
        # Dark Theme Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #070F1B;
                color: #FFFFFF;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QLabel {
                color: #5D9CEC;
                font-weight: bold;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #0B1625;
                color: #E2E8F0;
                border: 1px solid #1E3A8A;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
            }
            QPushButton {
                background-color: #0D6EFD;
                color: #FFFFFF;
                border: 1px solid #0B5ED7;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0B5ED7;
            }
            QPushButton#secondaryBtn {
                background-color: #1E293B;
                border: 1px solid #334155;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #334155;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("🔑 Mini Download License Generator")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(header)
        
        # HWID input row
        hwid_label = QLabel("Client Machine ID (HWID):")
        self.hwid_input = QLineEdit()
        self.hwid_input.setPlaceholderText("Paste client HWID here...")
        layout.addWidget(hwid_label)
        layout.addWidget(self.hwid_input)
        
        # Key output row
        key_label = QLabel("Generated Activation Key:")
        key_layout = QHBoxLayout()
        self.key_output = QLineEdit()
        self.key_output.setReadOnly(True)
        self.key_output.setPlaceholderText("Activation key will appear here...")
        
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setObjectName("secondaryBtn")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        
        key_layout.addWidget(self.key_output)
        key_layout.addWidget(self.copy_btn)
        layout.addWidget(key_label)
        layout.addLayout(key_layout)
        
        # Buttons row
        btn_layout = QHBoxLayout()
        self.gen_btn = QPushButton("Generate Key")
        self.gen_btn.clicked.connect(self.on_generate)
        
        self.save_btn = QPushButton("Save local license.key")
        self.save_btn.setObjectName("secondaryBtn")
        self.save_btn.clicked.connect(self.save_license_file)
        
        btn_layout.addWidget(self.gen_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)
        
        # Load app icon if exists
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
    def on_generate(self):
        hwid = self.hwid_input.text().strip()
        if not hwid:
            QMessageBox.warning(self, "Warning", "Please enter a Machine ID (HWID) first!")
            return
        key = generate_key(hwid)
        self.key_output.setText(key)
        
    def copy_to_clipboard(self):
        key = self.key_output.text().strip()
        if not key:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(key)
        QMessageBox.information(self, "Success", "Key copied to clipboard!")
        
    def save_license_file(self):
        key = self.key_output.text().strip()
        if not key:
            QMessageBox.warning(self, "Warning", "Please generate a key first!")
            return
        try:
            with open("license.key", "w", encoding="utf-8") as f:
                f.write(key)
            QMessageBox.information(self, "Success", "license.key saved successfully in application directory!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Optional dark palette override
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(7, 15, 27))
    palette.setColor(QPalette.WindowText, Qt.white)
    app.setPalette(palette)
    
    window = KeyGeneratorApp()
    window.show()
    sys.exit(app.exec_())
