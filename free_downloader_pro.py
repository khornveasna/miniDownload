import sys
import os
import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                             QProgressBar, QFileDialog, QComboBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPlainTextEdit,
                             QGroupBox, QCheckBox, QSpinBox, QMessageBox, QAbstractItemView,
                             QSystemTrayIcon, QMenu, QAction, QStyle, QDialog, QFormLayout,
                             QFrame, QGridLayout)
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QRunnable, QThreadPool
from PyQt5.QtGui import QFont, QColor, QPalette, QBrush, QIcon
import yt_dlp

import os
import hashlib
import subprocess
import sys

SECRET_SALT = "MiniDownloadSecretSalt2026!"

def sanitize_filename(filename):
    base, ext = os.path.splitext(filename)
    invalid_chars = '<>:"/\\|?*'
    clean_base = "".join(c if c not in invalid_chars else " " for c in base)
    clean_base = " ".join(clean_base.split()).strip()
    return clean_base + ext

def get_hwid():
    try:
        output = subprocess.check_output('wmic csproduct get uuid', shell=True).decode().strip()
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        if len(lines) > 1:
            hwid = lines[1]
            if hwid and hwid != "00000000-0000-0000-0000-000000000000":
                return hwid
    except Exception as e:
        print("Failed to get Motherboard UUID:", e)
        
    try:
        output = subprocess.check_output('wmic cpu get processorid', shell=True).decode().strip()
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        if len(lines) > 1:
            return "CPU-" + lines[1]
    except Exception as e:
        print("Failed to get CPU ID:", e)

    import uuid
    return "MAC-" + str(uuid.getnode())

def validate_key(hwid, key):
    raw = hwid.strip() + SECRET_SALT
    h = hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()
    expected_key = f"{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"
    return key.strip().upper() == expected_key

class ActivationDialog(QDialog):
    def __init__(self, hwid, parent=None):
        super().__init__(parent)
        self.hwid = hwid
        self.setWindowTitle("Activation Required")
        self.resize(500, 240)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #070F1B;
                color: #FFFFFF;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QLabel {
                font-size: 12px;
                color: #E2E8F0;
            }
            QLabel#titleLabel {
                color: #3B82F6;
                font-size: 18px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #0B1625;
                color: #E2E8F0;
                border: 1px solid #1E3A8A;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
            }
            QPushButton {
                background-color: #1E293B;
                color: #FFFFFF;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton#activateBtn {
                background-color: #0D6EFD;
                border: 1px solid #0B5ED7;
            }
            QPushButton#activateBtn:hover {
                background-color: #0B5ED7;
            }
            QPushButton#copyBtn {
                background-color: #1E293B;
                color: #5D9CEC;
                border: 1px solid #1E3A8A;
                padding: 4px 8px;
            }
            QPushButton#copyBtn:hover {
                background-color: #1E3A8A;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Mini Download Activation")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        desc = QLabel("Please enter a valid activation key to use this software. Send your Machine ID below to the owner to get your activation key.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        hwid_layout = QHBoxLayout()
        hwid_label = QLabel("Machine ID:")
        hwid_label.setFixedWidth(80)
        self.hwid_edit = QLineEdit(self.hwid)
        self.hwid_edit.setReadOnly(True)
        
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("copyBtn")
        copy_btn.clicked.connect(self.copy_hwid)
        
        hwid_layout.addWidget(hwid_label)
        hwid_layout.addWidget(self.hwid_edit)
        hwid_layout.addWidget(copy_btn)
        layout.addLayout(hwid_layout)

        key_layout = QHBoxLayout()
        key_label = QLabel("Activation Key:")
        key_label.setFixedWidth(80)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_edit)
        layout.addLayout(key_layout)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #F87171; font-weight: bold;")
        layout.addWidget(self.error_label)

        layout.addSpacing(10)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.exit_btn = QPushButton("✖ Exit")
        self.activate_btn = QPushButton("✔ Activate")
        self.activate_btn.setObjectName("activateBtn")
        
        self.exit_btn.clicked.connect(self.reject)
        self.activate_btn.clicked.connect(self.check_activation)
        
        btn_layout.addWidget(self.exit_btn)
        btn_layout.addWidget(self.activate_btn)
        layout.addLayout(btn_layout)

    def copy_hwid(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hwid)
        QMessageBox.information(self, "Success", "Machine ID copied to clipboard!")

    def check_activation(self):
        key = self.key_edit.text().strip()
        if not key:
            self.error_label.setText("Key cannot be empty.")
            return
            
        if validate_key(self.hwid, key):
            try:
                local_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                license_path = os.path.join(local_dir, "license.key")
                with open(license_path, "w") as f:
                    f.write(key)
                QMessageBox.information(self, "Success", "Activation successful!")
                self.accept()
            except Exception as e:
                self.error_label.setText(f"Failed to save license key: {e}")
        else:
            self.error_label.setText("Invalid activation key.")

class ExtensionSignalEmitter(QObject):
    add_url_signal = pyqtSignal(dict)

class ExtensionRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet logging

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/ping':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"pong")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/add':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                # Emit to PyQt main thread safely
                self.server.main_window.extension_emitter.add_url_signal.emit(data)
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

class ExtensionServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, main_window):
        super().__init__(server_address, RequestHandlerClass)
        self.main_window = main_window

class WorkerSignals(QObject):
    progress = pyqtSignal(int, int, str, str) # row_idx, percent, speed, size
    progress_detailed = pyqtSignal(int, dict)
    status = pyqtSignal(int, str, str) # row_idx, filename, status
    finished = pyqtSignal(int, bool, str) # row_idx, success, message

class ScanWorker(QRunnable):
    def __init__(self, row_idx, url, signals):
        super().__init__()
        self.row_idx = row_idx
        self.url = url
        self.signals = signals

    def run(self):
        self.signals.status.emit(self.row_idx, "Scanning...", "Scanning")
        ydl_opts = {
            'extract_flat': True,
            'skip_download': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if info:
                    title = info.get('title', 'Unknown Video')
                    duration = info.get('duration', None)
                    duration_str = f" ({duration}s)" if duration else ""
                    self.signals.status.emit(self.row_idx, title + duration_str, "Ready")
                else:
                    self.signals.status.emit(self.row_idx, "Could not extract title", "Ready")
        except Exception as e:
            self.signals.status.emit(self.row_idx, "Scan failed", "Scan Error")

class DownloadWorker(QRunnable):
    def __init__(self, row_idx, url, save_dir, format_type, quality, naming_opts, extras_opts, signals, custom_filename=None):
        super().__init__()
        self.row_idx = row_idx
        self.url = url
        self.save_dir = save_dir
        self.format_type = format_type
        self.quality = quality
        self.naming_opts = naming_opts
        self.extras_opts = extras_opts
        self.signals = signals
        self._is_cancelled = False
        self.custom_filename = custom_filename

    def progress_hook(self, d):
        if self._is_cancelled:
            raise Exception("Cancelled")
            
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            
            percent_val = 0
            if total > 0:
                percent_val = int((downloaded / total) * 100)
                
            speed = d.get('_speed_str', '0.00MiB/s')
            eta = d.get('_eta_str', 'N/A')
            
            total_mb = total / (1024 * 1024) if total > 0 else 0
            size_str = f"{total_mb:.2f} MiB" if total_mb > 0 else "N/A"
            
            downloaded_mb = downloaded / (1024 * 1024)
            downloaded_str = f"{downloaded_mb:.2f} MiB"
            
            self.signals.progress_detailed.emit(self.row_idx, {
                'percent': percent_val,
                'speed': speed,
                'size': size_str,
                'downloaded_str': downloaded_str,
                'eta': eta
            })
            
            self.signals.progress.emit(self.row_idx, percent_val, speed, size_str)
            
        elif d['status'] == 'finished':
            self.signals.status.emit(self.row_idx, "", "Processing")

    def run(self):
        self.signals.status.emit(self.row_idx, "", "Downloading")
        
        # Determine ffmpeg.exe path robustly
        local_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        local_ffmpeg = os.path.join(local_dir, "ffmpeg.exe")
        extracted_ffmpeg_54 = r"c:\Users\K-VeaSna\Desktop\Mini Download 5.4.1 full\Mini Download 5.4.1 full.exe_extracted\ffmpeg.exe"
        extracted_ffmpeg_55 = r"c:\Users\K-VeaSna\Desktop\Mini Download 5.4.1 full\Mini Download 5.5 full.exe_extracted\ffmpeg.exe"
        
        if os.path.exists(local_ffmpeg):
            ffmpeg_path = local_ffmpeg
        elif os.path.exists(extracted_ffmpeg_55):
            ffmpeg_path = extracted_ffmpeg_55
        else:
            ffmpeg_path = extracted_ffmpeg_54
        
        # Configure output template
        if self.custom_filename:
            base_name, _ = os.path.splitext(self.custom_filename)
            out_name = f"{base_name}.%(ext)s"
        elif self.naming_opts.get('title_id', False):
            out_name = "%(title)s - %(id)s.%(ext)s"
        elif self.naming_opts.get('id_only', False):
            out_name = "%(id)s.%(ext)s"
        elif self.naming_opts.get('number_only', False):
            out_name = f"{self.row_idx + 1}.%(ext)s"
        elif self.naming_opts.get('num_title', False):
            out_name = f"{self.row_idx + 1} - %(title)s.%(ext)s"
        else: # title_only (default)
            out_name = "%(title)s.%(ext)s"
            
        ydl_opts = {
            'outtmpl': os.path.join(self.save_dir, out_name),
            'progress_hooks': [self.progress_hook],
            'noprogress': True,
        }

        # Embed thumbnail/description
        if self.extras_opts.get('thumbnail', False):
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'] = [{
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            }]
            
        if self.extras_opts.get('description', False):
            ydl_opts['writedesc'] = True

        if os.path.exists(ffmpeg_path):
            ydl_opts['ffmpeg_location'] = ffmpeg_path

        # Configure formats
        if self.format_type == "MP3 (Audio Only)":
            ydl_opts['format'] = 'bestaudio/best'
            if 'postprocessors' not in ydl_opts:
                ydl_opts['postprocessors'] = []
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })
        else: # MP4
            import re
            match = re.search(r'\d+', self.quality)
            if match:
                height = match.group()
                ydl_opts['format'] = f'bestvideo[height<={height}]+bestaudio/best'
            else: # best
                ydl_opts['format'] = 'bestvideo+bestaudio/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                filepath = ydl.prepare_filename(info)
                if not os.path.exists(filepath):
                    base, ext = os.path.splitext(filepath)
                    for possible_ext in ['.mp4', '.mkv', '.webm', '.mp3', '.m4a']:
                        if os.path.exists(base + possible_ext):
                            filepath = base + possible_ext
                            break
                title = info.get('title', '') if info else ''
                if title:
                    self.signals.status.emit(self.row_idx, title, "done")
                else:
                    self.signals.status.emit(self.row_idx, "", "done")
            self.signals.finished.emit(self.row_idx, True, filepath)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.signals.finished.emit(self.row_idx, False, str(e))

class DownloadInfoDialog(QDialog):
    def __init__(self, url, format_label, default_filepath, description, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download info")
        self.resize(600, 260)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #070F1B;
                color: #FFFFFF;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QLabel {
                color: #5D9CEC;
                font-weight: bold;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #0B1625;
                color: #E2E8F0;
                border: 1px solid #1E3A8A;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
            }
            QPushButton {
                background-color: #1E293B;
                color: #FFFFFF;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton#startBtn {
                background-color: #0D6EFD;
                border: 1px solid #0B5ED7;
            }
            QPushButton#startBtn:hover {
                background-color: #0B5ED7;
            }
            QPushButton#cancelBtn {
                background-color: #1E293B;
                color: #F87171;
                border: 1px solid #450A0A;
            }
            QPushButton#cancelBtn:hover {
                background-color: #450A0A;
            }
            QCheckBox {
                color: #94A3B8;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setSpacing(8)

        self.address_edit = QLineEdit(url)
        self.address_edit.setReadOnly(True)
        form.addRow("Address", self.address_edit)

        self.format_edit = QLineEdit(format_label)
        self.format_edit.setReadOnly(True)
        form.addRow("Format", self.format_edit)

        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit(default_filepath)
        self.file_edit.setReadOnly(True)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(40)
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(browse_btn)
        form.addRow("Saved file", file_layout)

        self.desc_edit = QLineEdit(description)
        form.addRow("Description", self.desc_edit)

        layout.addLayout(form)

        self.show_msg_chk = QCheckBox("Show message when download completed")
        self.show_msg_chk.setChecked(True)
        layout.addWidget(self.show_msg_chk)

        layout.addSpacing(10)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.later_btn = QPushButton("↻ Download Later")
        self.start_btn = QPushButton("➡ Start Download")
        self.start_btn.setObjectName("startBtn")
        self.cancel_btn = QPushButton("✖ Cancel")
        self.cancel_btn.setObjectName("cancelBtn")

        self.later_btn.clicked.connect(lambda: self.done(2))
        self.start_btn.clicked.connect(lambda: self.done(1))
        self.cancel_btn.clicked.connect(lambda: self.done(0))

        btn_layout.addWidget(self.later_btn)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def browse_file(self):
        current_path = self.file_edit.text()
        directory, filename = os.path.split(current_path)
        
        name_part, ext = os.path.splitext(filename)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", current_path, f"Files (*{ext or '.*'})"
        )
        if file_path:
            self.file_edit.setText(file_path)

    def get_result(self):
        return {
            'filepath': self.file_edit.text(),
            'description': self.desc_edit.text(),
            'show_completed_msg': self.show_msg_chk.isChecked()
        }

class DownloadProgressDialog(QDialog):
    def __init__(self, filename, url, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.url = url
        self.setWindowTitle(f"0% {filename}")
        self.resize(550, 250)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #070F1B;
                color: #FFFFFF;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QLabel {
                font-size: 12px;
            }
            QLabel#titleLabel {
                color: #5D9CEC;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #1E3A8A;
                border-radius: 4px;
                background-color: #0B1625;
                text-align: center;
                color: white;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
            }
            QPushButton {
                background-color: #1E293B;
                color: #F87171;
                border: 1px solid #450A0A;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #450A0A;
            }
            QFrame#statsFrame {
                border: 1px solid #1E3A8A;
                border-radius: 6px;
                background-color: #091220;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        url_lbl = QLabel(url)
        url_lbl.setObjectName("titleLabel")
        url_lbl.setWordWrap(True)
        layout.addWidget(url_lbl)

        stats_frame = QFrame()
        stats_frame.setObjectName("statsFrame")
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setSpacing(8)

        def add_stat_row(grid, row, label_text):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #5D9CEC; font-weight: bold;")
            val = QLabel("-")
            val.setStyleSheet("color: #FFFFFF;")
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            return val

        self.val_status = add_stat_row(stats_layout, 0, "Status")
        self.val_size = add_stat_row(stats_layout, 1, "File size")
        self.val_downloaded = add_stat_row(stats_layout, 2, "Downloaded")
        self.val_rate = add_stat_row(stats_layout, 3, "Transfer rate")
        self.val_time = add_stat_row(stats_layout, 4, "Time left")
        self.val_resume = add_stat_row(stats_layout, 5, "Resume capability")
        self.val_resume.setText("Yes")

        layout.addWidget(stats_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = QPushButton("✖ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def update_progress(self, percent, speed, size, downloaded_str, eta):
        self.setWindowTitle(f"{percent}% {self.filename}")
        self.progress_bar.setValue(percent)
        self.val_status.setText("Downloading...")
        self.val_size.setText(size)
        self.val_downloaded.setText(f"{downloaded_str} ({percent}%)")
        self.val_rate.setText(speed)
        self.val_time.setText(eta)

class DownloadCompleteDialog(QDialog):
    def __init__(self, filename, url, filepath, total_bytes, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.setWindowTitle("Download complete")
        self.resize(550, 240)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #070F1B;
                color: #FFFFFF;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QLabel {
                font-size: 12px;
            }
            QFrame#headerFrame {
                border: 1px solid #10B981;
                border-radius: 6px;
                background-color: #064E3B;
                padding: 12px;
            }
            QFrame#detailsFrame {
                border: 1px solid #1E3A8A;
                border-radius: 6px;
                background-color: #091220;
                padding: 10px;
            }
            QPushButton {
                background-color: #1E293B;
                color: #FFFFFF;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton#openBtn {
                background-color: #0D6EFD;
                border: 1px solid #0B5ED7;
            }
            QPushButton#openBtn:hover {
                background-color: #0B5ED7;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 5, 10, 5)
        header_layout.setSpacing(15)

        check_lbl = QLabel("✔")
        check_lbl.setStyleSheet("color: #10B981; font-size: 32px; font-weight: bold;")
        
        text_layout = QVBoxLayout()
        title_lbl = QLabel("Download complete")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #10B981;")
        
        size_mb = total_bytes / (1024 * 1024) if total_bytes > 0 else 0
        desc_lbl = QLabel(f"{filename}\nDownloaded {size_mb:.2f} MB ({total_bytes} Bytes)")
        desc_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(desc_lbl)
        
        header_layout.addWidget(check_lbl)
        header_layout.addLayout(text_layout)
        layout.addWidget(header_frame)

        details_frame = QFrame()
        details_frame.setObjectName("detailsFrame")
        details_layout = QFormLayout(details_frame)
        details_layout.setSpacing(8)

        lbl_addr = QLabel("Address")
        lbl_addr.setStyleSheet("color: #5D9CEC; font-weight: bold;")
        val_addr = QLabel(url)
        val_addr.setStyleSheet("color: #FFFFFF;")
        val_addr.setWordWrap(True)
        details_layout.addRow(lbl_addr, val_addr)

        lbl_saved = QLabel("Saved file")
        lbl_saved.setStyleSheet("color: #5D9CEC; font-weight: bold;")
        val_saved = QLabel(filepath)
        val_saved.setStyleSheet("color: #FFFFFF;")
        val_saved.setWordWrap(True)
        details_layout.addRow(lbl_saved, val_saved)

        layout.addWidget(details_frame)

        btn_layout = QHBoxLayout()
        
        self.open_btn = QPushButton("▶ Open")
        self.open_btn.setObjectName("openBtn")
        self.open_folder_btn = QPushButton("📁 Open folder")
        self.close_btn = QPushButton("✖ Close")

        self.open_btn.clicked.connect(self.open_file)
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def open_file(self):
        try:
            if os.path.exists(self.filepath):
                os.startfile(self.filepath)
        except Exception as e:
            print("Failed to open file:", e)

    def open_folder(self):
        try:
            if os.path.exists(self.filepath):
                os.system(f'explorer /select,"{os.path.abspath(self.filepath)}"')
            else:
                dir_path = os.path.dirname(self.filepath)
                if os.path.exists(dir_path):
                    os.startfile(dir_path)
        except Exception as e:
            print("Failed to open folder:", e)

class MiniDownloadPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_dark_mode = True
        self.thread_pool = QThreadPool()
        self.active_workers = {}
        self.url_metadata = {}
        self.progress_dialogs = {}
        self.allow_quit = False
        
        self.initUI()
        self.setup_tray_icon()
        
        self.extension_emitter = ExtensionSignalEmitter()
        self.extension_emitter.add_url_signal.connect(self.add_extension_url)
        self.start_extension_server()
        
    def initUI(self):
        self.setWindowTitle("Mini Download 5.5 (Pro Free MT)")
        self.resize(1000, 750)
        
        self.dark_stylesheet = """
            QMainWindow {
                background-color: #1A1A1A;
            }
            QWidget {
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#titleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #42A85F;
            }
            QGroupBox {
                border: 1px solid #333333;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                color: #42A85F;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QPlainTextEdit {
                background-color: #242424;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                padding: 8px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #42A85F;
            }
            QPushButton {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #353535;
                border: 1px solid #42A85F;
            }
            QPushButton#downloadBtn {
                background-color: #2D8B4E;
                color: white;
                border: none;
                font-size: 14px;
            }
            QPushButton#downloadBtn:hover {
                background-color: #38A05D;
            }
            QPushButton#stopBtn {
                background-color: #A83232;
                color: white;
                border: none;
                font-size: 14px;
            }
            QPushButton#stopBtn:hover {
                background-color: #C04040;
            }
            QPushButton#settingsBtn, QPushButton#helpBtn {
                background-color: transparent;
                border: none;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 4px 8px;
            }
            QPushButton#settingsBtn:hover, QPushButton#helpBtn:hover {
                color: #42A85F;
            }
            QPushButton#themeBtn {
                background-color: transparent;
                border: 1px solid #444444;
                border-radius: 13px;
                min-width: 26px;
                max-width: 26px;
                min-height: 26px;
                max-height: 26px;
                font-size: 13px;
                color: #FFB300;
                padding: 0px;
            }
            QPushButton#themeBtn:hover {
                background-color: #2D2D2D;
                border-color: #FFB300;
            }
            QPushButton#minBtn {
                background-color: #FFB020;
                color: #1A1A1A;
                border: none;
                border-radius: 9px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                font-weight: bold;
                font-size: 12px;
                padding: 0px;
            }
            QPushButton#minBtn:hover {
                background-color: #FFC040;
            }
            QPushButton#maxBtn {
                background-color: #2DCA73;
                color: #1A1A1A;
                border: none;
                border-radius: 9px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                font-weight: bold;
                font-size: 10px;
                padding: 0px;
                margin-bottom: 1px;
            }
            QPushButton#maxBtn:hover {
                background-color: #3DDA83;
            }
            QPushButton#closeBtn {
                background-color: #FF5F56;
                color: #1A1A1A;
                border: none;
                border-radius: 9px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                font-weight: bold;
                font-size: 12px;
                padding: 0px;
                margin-bottom: 1px;
            }
            QPushButton#closeBtn:hover {
                background-color: #FF7F76;
            }
            QComboBox, QSpinBox {
                background-color: #242424;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                padding: 6px;
                color: #FFFFFF;
            }
            QCheckBox {
                spacing: 5px;
                font-weight: normal;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #555555;
                background-color: #242424;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #42A85F;
                background-color: #42A85F;
                border-radius: 3px;
            }
            QTableWidget {
                background-color: #202020;
                border: 1px solid #333333;
                gridline-color: #2A2A2A;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #2A2A2A;
                padding: 6px;
                border: 1px solid #202020;
                color: #888888;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #333333;
                border-radius: 6px;
                text-align: center;
                background-color: #242424;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2D8B4E;
                border-radius: 5px;
            }
        """
        
        self.light_stylesheet = """
            QMainWindow {
                background-color: #F3F3F3;
            }
            QWidget {
                color: #1A1A1A;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#titleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2D8B4E;
            }
            QGroupBox {
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                color: #2D8B4E;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QPlainTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 8px;
                color: #1A1A1A;
                font-size: 13px;
            }
            QLineEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #2D8B4E;
            }
            QPushButton {
                background-color: #EAEAEA;
                color: #1A1A1A;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #DFDFDF;
                border: 1px solid #2D8B4E;
            }
            QPushButton#downloadBtn {
                background-color: #2D8B4E;
                color: white;
                border: none;
                font-size: 14px;
            }
            QPushButton#downloadBtn:hover {
                background-color: #38A05D;
            }
            QPushButton#stopBtn {
                background-color: #A83232;
                color: white;
                border: none;
                font-size: 14px;
            }
            QPushButton#stopBtn:hover {
                background-color: #C04040;
            }
            QPushButton#settingsBtn, QPushButton#helpBtn {
                background-color: transparent;
                border: none;
                color: #1A1A1A;
                font-weight: bold;
                font-size: 13px;
                padding: 4px 8px;
            }
            QPushButton#settingsBtn:hover, QPushButton#helpBtn:hover {
                color: #2D8B4E;
            }
            QPushButton#themeBtn {
                background-color: transparent;
                border: 1px solid #CCCCCC;
                border-radius: 13px;
                min-width: 26px;
                max-width: 26px;
                min-height: 26px;
                max-height: 26px;
                font-size: 13px;
                color: #FF8F00;
                padding: 0px;
            }
            QPushButton#themeBtn:hover {
                background-color: #EAEAEA;
                border-color: #FF8F00;
            }
            QPushButton#minBtn {
                background-color: #FFB020;
                color: #1A1A1A;
                border: none;
                border-radius: 9px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                font-weight: bold;
                font-size: 12px;
                padding: 0px;
            }
            QPushButton#minBtn:hover {
                background-color: #FFC040;
            }
            QPushButton#maxBtn {
                background-color: #2DCA73;
                color: #1A1A1A;
                border: none;
                border-radius: 9px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                font-weight: bold;
                font-size: 10px;
                padding: 0px;
                margin-bottom: 1px;
            }
            QPushButton#maxBtn:hover {
                background-color: #3DDA83;
            }
            QPushButton#closeBtn {
                background-color: #FF5F56;
                color: #1A1A1A;
                border: none;
                border-radius: 9px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                font-weight: bold;
                font-size: 12px;
                padding: 0px;
                margin-bottom: 1px;
            }
            QPushButton#closeBtn:hover {
                background-color: #FF7F76;
            }
            QComboBox, QSpinBox {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 6px;
                color: #1A1A1A;
            }
            QCheckBox {
                spacing: 5px;
                font-weight: normal;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #AAAAAA;
                background-color: #FFFFFF;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #2D8B4E;
                background-color: #2D8B4E;
                border-radius: 3px;
            }
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                gridline-color: #E5E5E5;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #F0F0F0;
                padding: 6px;
                border: 1px solid #E5E5E5;
                color: #555555;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                text-align: center;
                background-color: #EAEAEA;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2D8B4E;
                border-radius: 5px;
            }
        """

        self.setStyleSheet(self.dark_stylesheet)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Header Row
        header_layout = QHBoxLayout()
        title_label = QLabel("Mini Download 5.5")
        title_label.setObjectName("titleLabel")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Settings button with icon
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.setObjectName("settingsBtn")
        
        # Help button with icon and dropdown indicator
        help_btn = QPushButton("❓ Help  ▾")
        help_btn.setObjectName("helpBtn")
        
        # Theme/Sun circular button
        self.theme_btn = QPushButton("☀️")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.clicked.connect(self.toggle_theme)
        
        # Minimize circular button
        min_btn = QPushButton("-")
        min_btn.setObjectName("minBtn")
        min_btn.clicked.connect(self.showMinimized)
        
        # Maximize circular button
        max_btn = QPushButton("□")
        max_btn.setObjectName("maxBtn")
        max_btn.clicked.connect(self.toggle_maximize)
        
        # Close circular button
        close_btn = QPushButton("x")
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.close)
        
        header_layout.addWidget(settings_btn)
        header_layout.addWidget(help_btn)
        header_layout.addWidget(self.theme_btn)
        header_layout.addWidget(min_btn)
        header_layout.addWidget(max_btn)
        header_layout.addWidget(close_btn)
        main_layout.addLayout(header_layout)

        # Add Video Links Box
        links_box = QGroupBox("Add Video Links")
        links_layout = QVBoxLayout(links_box)
        
        self.links_input = QPlainTextEdit()
        self.links_input.setPlaceholderText("Paste video/playlist URLs here (one per line)...")
        self.links_input.setFixedHeight(100)
        links_layout.addWidget(self.links_input)
        
        buttons_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Video Links")
        self.scan_btn.clicked.connect(self.scan_links)
        
        self.no_scan_btn = QPushButton("No Scan Video Link")
        self.no_scan_btn.clicked.connect(self.add_links_no_scan)
        
        buttons_layout.addWidget(self.scan_btn)
        buttons_layout.addWidget(self.no_scan_btn)
        buttons_layout.addStretch()
        
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.clicked.connect(self.paste_clipboard)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_links)
        buttons_layout.addWidget(self.paste_btn)
        buttons_layout.addWidget(self.clear_btn)
        
        links_layout.addLayout(buttons_layout)
        main_layout.addWidget(links_box)

        # Settings and Location Row
        settings_row_layout = QHBoxLayout()
        
        # Output Settings
        out_box = QGroupBox("Output Settings")
        out_layout = QVBoxLayout(out_box)
        
        # Save Naming
        naming_layout = QHBoxLayout()
        save_name_label = QLabel("Save name:")
        save_name_label.setFixedWidth(80)
        naming_layout.addWidget(save_name_label)
        
        self.name_title_chk = QCheckBox("Title")
        self.name_title_chk.setChecked(True)
        self.name_title_chk.clicked.connect(lambda: self.uncheck_others('title'))
        
        self.name_title_id_chk = QCheckBox("Title + ID")
        self.name_title_id_chk.clicked.connect(lambda: self.uncheck_others('title_id'))
        
        self.name_id_chk = QCheckBox("ID Video")
        self.name_id_chk.clicked.connect(lambda: self.uncheck_others('id'))
        
        self.name_num_chk = QCheckBox("Number")
        self.name_num_chk.clicked.connect(lambda: self.uncheck_others('number'))
        
        self.name_num_title_chk = QCheckBox("Number+Title")
        self.name_num_title_chk.clicked.connect(lambda: self.uncheck_others('num_title'))
        
        naming_layout.addWidget(self.name_title_chk)
        naming_layout.addWidget(self.name_title_id_chk)
        naming_layout.addWidget(self.name_id_chk)
        naming_layout.addWidget(self.name_num_chk)
        naming_layout.addWidget(self.name_num_title_chk)
        naming_layout.addStretch()
        out_layout.addLayout(naming_layout)
        
        # Extras
        extras_layout = QHBoxLayout()
        extras_label = QLabel("Extras :")
        extras_label.setFixedWidth(80)
        extras_layout.addWidget(extras_label)
        
        self.extra_thumb_chk = QCheckBox("🖼️ Thumbnail")
        self.extra_desc_chk = QCheckBox("📝 Description")
        
        extras_layout.addWidget(self.extra_thumb_chk)
        extras_layout.addWidget(self.extra_desc_chk)
        extras_layout.addStretch()
        out_layout.addLayout(extras_layout)
        
        # Format & Quality
        fmt_q_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4 (Video)", "MP3 (Audio Only)"])
        self.format_combo.currentIndexChanged.connect(self.format_changed)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "Quality: 2160",
            "Quality: 1440",
            "Quality: 1080",
            "Quality: 720",
            "Quality: 480",
            "Quality: 360",
            "Quality: 240",
            "Best Quality"
        ])
        # Set default selection to Quality: 1080
        self.quality_combo.setCurrentIndex(2)
        
        fmt_q_layout.addWidget(QLabel("Format:"))
        fmt_q_layout.addWidget(self.format_combo)
        fmt_q_layout.addWidget(QLabel("Quality:"))
        fmt_q_layout.addWidget(self.quality_combo)
        out_layout.addLayout(fmt_q_layout)
        
        settings_row_layout.addWidget(out_box, 6)
        
        # Save Location
        save_box = QGroupBox("Save Location")
        save_layout = QVBoxLayout(save_box)
        
        self.save_dir_input = QLineEdit()
        default_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.save_dir_input.setText(default_dir)
        save_layout.addWidget(self.save_dir_input)
        
        save_btns_layout = QHBoxLayout()
        self.change_dir_btn = QPushButton("Change Folder")
        self.change_dir_btn.clicked.connect(self.change_folder)
        self.open_dir_btn = QPushButton("Open Folder")
        self.open_dir_btn.clicked.connect(self.open_folder)
        save_btns_layout.addWidget(self.change_dir_btn)
        save_btns_layout.addWidget(self.open_dir_btn)
        save_layout.addLayout(save_btns_layout)
        
        settings_row_layout.addWidget(save_box, 4)
        main_layout.addLayout(settings_row_layout)

        # Queue Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["File Name", "Speed", "Size", "Status", "URL"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        main_layout.addWidget(self.table)

        # Bottom Controls
        controls_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        
        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all)
        
        controls_layout.addWidget(self.delete_btn)
        controls_layout.addWidget(self.clear_all_btn)
        controls_layout.addStretch()
        
        controls_layout.addWidget(QLabel("Threads:"))
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 16)
        self.threads_spin.setValue(4)
        controls_layout.addWidget(self.threads_spin)
        
        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("downloadBtn")
        self.download_btn.clicked.connect(self.start_downloads)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self.stop_downloads)
        
        controls_layout.addWidget(self.download_btn)
        controls_layout.addWidget(self.stop_btn)
        main_layout.addLayout(controls_layout)

        # Status and Progress Bar
        status_bar_layout = QHBoxLayout()
        self.status_label = QLabel("Added 0 link(s) to queue")
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        status_bar_layout.addWidget(self.status_label)
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setValue(0)
        status_bar_layout.addWidget(self.overall_progress)
        main_layout.addLayout(status_bar_layout)

    def uncheck_others(self, active):
        self.name_title_chk.setChecked(active == 'title')
        self.name_title_id_chk.setChecked(active == 'title_id')
        self.name_id_chk.setChecked(active == 'id')
        self.name_num_chk.setChecked(active == 'number')
        self.name_num_title_chk.setChecked(active == 'num_title')

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.theme_btn.setText("☀️")
            self.setStyleSheet(self.dark_stylesheet)
        else:
            self.theme_btn.setText("🌙")
            self.setStyleSheet(self.light_stylesheet)
            
        self.update_palette()
        
        # Update existing items in the table to use the new default text color
        default_text_color = '#FFFFFF' if self.is_dark_mode else '#1A1A1A'
        for r in range(self.table.rowCount()):
            status_item = self.table.item(r, 3)
            if status_item:
                status_text = status_item.text().lower()
                if status_text not in ['done', 'failed', 'scanning'] and not status_text.startswith('downloading'):
                    status_item.setForeground(QBrush(QColor(default_text_color)))

    def update_palette(self):
        palette = QPalette()
        if self.is_dark_mode:
            palette.setColor(QPalette.Window, QColor(26, 26, 26))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(36, 36, 36))
            palette.setColor(QPalette.AlternateBase, QColor(26, 26, 26))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(42, 42, 42))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(66, 168, 95))
            palette.setColor(QPalette.Highlight, QColor(66, 168, 95))
            palette.setColor(QPalette.HighlightedText, Qt.black)
        else:
            palette.setColor(QPalette.Window, QColor(243, 243, 243))
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.AlternateBase, QColor(243, 243, 243))
            palette.setColor(QPalette.ToolTipBase, Qt.black)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(230, 230, 230))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(45, 139, 78))
            palette.setColor(QPalette.Highlight, QColor(45, 139, 78))
            palette.setColor(QPalette.HighlightedText, Qt.white)
        QApplication.instance().setPalette(palette)

    def format_changed(self, index):
        self.quality_combo.setEnabled(index == 0)

    def paste_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.links_input.appendPlainText(text)

    def clear_links(self):
        self.links_input.clear()

    def change_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.save_dir_input.text())
        if directory:
            self.save_dir_input.setText(directory)

    def open_folder(self):
        path = self.save_dir_input.text()
        if os.path.exists(path):
            os.startfile(path)
        else:
            QMessageBox.warning(self, "Warning", "Directory does not exist yet!")

    def add_row_to_table(self, filename, speed, size, status, url):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Disable direct cell editing
        for col, text in enumerate([filename, speed, size, status, url]):
            item = QTableWidgetItem(text)
            if col == 3: # Status column
                status_color = '#aaaaaa' if self.is_dark_mode else '#555555'
                item.setForeground(QBrush(QColor(status_color)))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, col, item)
            
        self.update_status_label()

    def update_status_label(self):
        total = self.table.rowCount()
        done = 0
        for r in range(total):
            status = self.table.item(r, 3).text()
            if status.lower() == 'done':
                done += 1
        self.status_label.setText(f"Download Queue (Total: {total}) - Done: {done}")
        
        if total > 0:
            percent = int((done / total) * 100)
            self.overall_progress.setValue(percent)
        else:
            self.overall_progress.setValue(0)

    def get_links(self):
        text = self.links_input.toPlainText().strip()
        if not text:
            return []
        # Support split by newline, comma, or semicolon
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return lines

    def add_links_no_scan(self):
        links = self.get_links()
        if not links:
            return
        for url in links:
            # Check if url already in table to prevent duplicates
            exists = False
            for r in range(self.table.rowCount()):
                if self.table.item(r, 4).text() == url:
                    exists = True
                    break
            if not exists:
                self.add_row_to_table("Waiting for download...", "0.00MiB/s", "N/A", "Pending", url)
        self.links_input.clear()

    def scan_links(self):
        links = self.get_links()
        if not links:
            return
        
        self.scan_signals = WorkerSignals()
        self.scan_signals.status.connect(self.update_row_status)
        
        for url in links:
            exists = False
            for r in range(self.table.rowCount()):
                if self.table.item(r, 4).text() == url:
                    exists = True
                    break
            if not exists:
                row_idx = self.table.rowCount()
                self.add_row_to_table("Fetching info...", "0.00MiB/s", "N/A", "Scanning", url)
                worker = ScanWorker(row_idx, url, self.scan_signals)
                self.thread_pool.start(worker)
        self.links_input.clear()

    def delete_selected(self):
        selected_ranges = self.table.selectedRanges()
        rows_to_delete = set()
        for r in selected_ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                rows_to_delete.add(row)
                
        for row in sorted(list(rows_to_delete), reverse=True):
            self.table.removeRow(row)
        self.update_status_label()

    def clear_all(self):
        self.table.setRowCount(0)
        self.update_status_label()

    def update_row_progress(self, row_idx, percent, speed, size):
        if row_idx < self.table.rowCount():
            self.table.item(row_idx, 1).setText(speed)
            self.table.item(row_idx, 2).setText(size)
            self.table.item(row_idx, 3).setText(f"Downloading ({percent}%)")
            self.table.item(row_idx, 3).setForeground(QBrush(QColor('#42A85F')))

    def update_row_status(self, row_idx, filename, status):
        if row_idx < self.table.rowCount():
            if filename:
                self.table.item(row_idx, 0).setText(filename)
            self.table.item(row_idx, 3).setText(status)
            
            # Colors for statuses
            if status.lower() == 'done':
                self.table.item(row_idx, 3).setForeground(QBrush(QColor('#2D8B4E')))
                self.table.item(row_idx, 1).setText("0.00MiB/s")
            elif status.lower() == 'failed':
                self.table.item(row_idx, 3).setForeground(QBrush(QColor('#A83232')))
            elif status.lower() == 'scanning':
                self.table.item(row_idx, 3).setForeground(QBrush(QColor('#E09025')))
            else:
                default_text_color = '#FFFFFF' if self.is_dark_mode else '#1A1A1A'
                self.table.item(row_idx, 3).setForeground(QBrush(QColor(default_text_color)))
                
            self.update_status_label()

    def start_downloads(self):
        # Configure thread pool
        num_threads = self.threads_spin.value()
        self.thread_pool.setMaxThreadCount(num_threads)
        
        save_dir = self.save_dir_input.text()
        format_type = self.format_combo.currentText()
        quality = self.quality_combo.currentText()
        
        # Naming Options
        naming_opts = {
            'title_id': self.name_title_id_chk.isChecked(),
            'id_only': self.name_id_chk.isChecked(),
            'number_only': self.name_num_chk.isChecked(),
            'num_title': self.name_num_title_chk.isChecked(),
        }
        
        # Extras Options
        extras_opts = {
            'thumbnail': self.extra_thumb_chk.isChecked(),
            'description': self.extra_desc_chk.isChecked(),
        }

        self.download_signals = WorkerSignals()
        self.download_signals.progress.connect(self.update_row_progress)
        self.download_signals.progress_detailed.connect(self.update_dialog_progress)
        self.download_signals.status.connect(self.update_row_status)
        self.download_signals.finished.connect(self.on_worker_finished)

        # Add all pending rows to download queue
        for r in range(self.table.rowCount()):
            status = self.table.item(r, 3).text()
            if status.lower() in ['pending', 'ready', 'failed', 'scan error']:
                url = self.table.item(r, 4).text()
                meta = self.url_metadata.get(url, {})
                
                # Manual download fallback setup
                if 'title' not in meta:
                    default_name = "Download_from_Link"
                    try:
                        from urllib.parse import urlparse
                        path = urlparse(url).path
                        parsed_filename = os.path.basename(path)
                        if parsed_filename:
                            default_name = parsed_filename
                    except:
                        pass
                    
                    base, ext = os.path.splitext(default_name)
                    if format_type == "MP3 (Audio Only)" and ext.lower() != ".mp3":
                        default_name = base + ".mp3"
                    elif format_type == "MP4 (Video)" and not ext:
                        default_name = base + ".mp4"
                        
                    default_name = sanitize_filename(default_name)
                        
                    default_filepath = os.path.join(save_dir, default_name)
                    description = f"{default_name} | Cookie: browser"
                    
                    dialog = DownloadInfoDialog(url, f"{format_type} ({quality})", default_filepath, description, self)
                    result = dialog.exec_()
                    if result == 0: # Cancel
                        continue
                        
                    dialog_data = dialog.get_result()
                    custom_filepath = dialog_data['filepath']
                    custom_save_dir, custom_filename = os.path.split(custom_filepath)
                    show_completed_msg = dialog_data['show_completed_msg']
                    
                    meta = {
                        'format_type': format_type,
                        'quality': quality,
                        'save_dir': custom_save_dir,
                        'title': custom_filename,
                        'show_completed_msg': show_completed_msg
                    }
                    self.url_metadata[url] = meta
                    self.table.item(r, 0).setText(custom_filename)
                
                row_format = meta.get('format_type', format_type)
                row_quality = meta.get('quality', quality)
                row_save_dir = meta.get('save_dir', save_dir)
                custom_filename = meta.get('title', None)
                
                # Show non-modal Progress dialog
                dialog = DownloadProgressDialog(custom_filename or "Download", url, self)
                self.progress_dialogs[r] = dialog
                dialog.rejected.connect(lambda row=r: self.cancel_row_download(row))
                dialog.show()

                worker = DownloadWorker(r, url, row_save_dir, row_format, row_quality, naming_opts, extras_opts, self.download_signals, custom_filename=custom_filename)
                self.active_workers[r] = worker
                self.thread_pool.start(worker)

    def cancel_row_download(self, row_idx):
        if row_idx in self.active_workers:
            self.active_workers[row_idx]._is_cancelled = True
            self.update_row_status(row_idx, "", "Failed")
            if row_idx in self.progress_dialogs:
                self.progress_dialogs[row_idx].close()
                del self.progress_dialogs[row_idx]

    def update_dialog_progress(self, row_idx, data):
        if row_idx in self.progress_dialogs:
            self.progress_dialogs[row_idx].update_progress(
                data['percent'],
                data['speed'],
                data['size'],
                data['downloaded_str'],
                data['eta']
            )

    def on_worker_finished(self, row_idx, success, message):
        if row_idx in self.active_workers:
            del self.active_workers[row_idx]
            
        status = "done" if success else "failed"
        self.update_row_status(row_idx, "", status)
        
        # Close progress dialog and show completion dialog
        if row_idx in self.progress_dialogs:
            self.progress_dialogs[row_idx].close()
            
            if success:
                url = self.table.item(row_idx, 4).text()
                meta = self.url_metadata.get(url, {})
                show_msg = meta.get('show_completed_msg', True)
                
                if show_msg:
                    filepath = message
                    filename = os.path.basename(filepath)
                    total_bytes = 0
                    if os.path.exists(filepath):
                        total_bytes = os.path.getsize(filepath)
                        
                    comp_dialog = DownloadCompleteDialog(filename, url, filepath, total_bytes, self)
                    comp_dialog.exec_()
            
            del self.progress_dialogs[row_idx]
            
        if not success and message != "Cancelled":
            # Append error trace to cells
            self.table.item(row_idx, 0).setToolTip(message)
            self.table.item(row_idx, 0).setText(f"Failed: {message}")
            print(f"Row {row_idx} failed: {message}")

    def stop_downloads(self):
        # Cancel active workers
        for row_idx, worker in list(self.active_workers.items()):
            worker._is_cancelled = True
            self.update_row_status(row_idx, "", "Failed")
            if row_idx in self.progress_dialogs:
                self.progress_dialogs[row_idx].close()
                del self.progress_dialogs[row_idx]
        self.active_workers.clear()
        self.update_status_label()

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Load app icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logo.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logo.png")
            
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            
        # Create tray menu
        tray_menu = QMenu()
        open_action = QAction("Open Mini Download", self)
        open_action.triggered.connect(self.show_normal_and_active)
        tray_menu.addAction(open_action)
        
        tray_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def show_normal_and_active(self):
        self.show()
        self.showNormal()
        self.activateWindow()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal_and_active()
        elif reason == QSystemTrayIcon.DoubleClick:
            self.show_normal_and_active()

    def quit_application(self):
        self.allow_quit = True
        self.close()

    def closeEvent(self, event):
        if hasattr(self, 'allow_quit') and self.allow_quit:
            self.tray_icon.hide()
            event.accept()
        else:
            self.hide()
            event.ignore()

    def start_extension_server(self):
        try:
            self.extension_server = ExtensionServer(('127.0.0.1', 8765), ExtensionRequestHandler, self)
            t = threading.Thread(target=self.extension_server.serve_forever, daemon=True)
            t.start()
        except Exception as e:
            print("Failed to start extension HTTP server:", e)

    def add_extension_url(self, data):
        url = data.get('url')
        title = data.get('title', 'Video from Browser')
        if not url:
            return
            
        filename = data.get('filename', title)
        if not filename or filename == "Mini Download":
            filename = title

        # Determine format and quality
        ext_type = data.get('type', 'mp4') # 'mp4' or 'mp3' or 'original'
        ext_quality = data.get('quality', '1080')
        
        if ext_type == 'mp3':
            format_type = "MP3 (Audio Only)"
            quality = "Best Quality"
            base, ext = os.path.splitext(filename)
            if ext.lower() != ".mp3":
                filename = base + ".mp3"
        elif ext_type == 'original':
            format_type = "MP4 (Video)"
            quality = "Best Quality"
            base, ext = os.path.splitext(filename)
            if not ext:
                filename = base + ".mp4"
        else:
            format_type = "MP4 (Video)"
            if ext_quality == 'original':
                quality = "Best Quality"
            else:
                quality = f"Quality: {ext_quality}"
            base, ext = os.path.splitext(filename)
            if not ext:
                filename = base + ".mp4"

        filename = sanitize_filename(filename)

        # Bring window to front
        self.show()
        self.showNormal()
        self.activateWindow()
        
        # Build default filepath
        default_filepath = os.path.join(self.save_dir_input.text(), filename)
        description = f"{filename} | Cookie: browser"
        
        dialog = DownloadInfoDialog(url, f"{format_type} ({quality})", default_filepath, description, self)
        result = dialog.exec_()
        
        if result == 0: # Cancel
            return
            
        dialog_data = dialog.get_result()
        custom_filepath = dialog_data['filepath']
        custom_save_dir, custom_filename = os.path.split(custom_filepath)
        show_completed_msg = dialog_data['show_completed_msg']
        
        exists = False
        for r in range(self.table.rowCount()):
            if self.table.item(r, 4).text() == url:
                exists = True
                break
                
        if not exists:
            self.url_metadata[url] = {
                'format_type': format_type,
                'quality': quality,
                'save_dir': custom_save_dir,
                'title': custom_filename,
                'show_completed_msg': show_completed_msg
            }
            
            self.add_row_to_table(custom_filename, "0.00MiB/s", "N/A", "Pending", url)
            
            # Show a system tray message
            if self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    "Mini Download",
                    f"Added video to queue:\n{custom_filename[:50]}...",
                    QSystemTrayIcon.Information,
                    2000
                )
            
            if result == 1: # Download Now
                self.start_downloads()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Force a modern dark theme color palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(26, 26, 26))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(36, 36, 36))
    palette.setColor(QPalette.AlternateBase, QColor(26, 26, 26))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(42, 42, 42))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(66, 168, 95))
    palette.setColor(QPalette.Highlight, QColor(66, 168, 95))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    hwid = get_hwid()
    local_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    license_path = os.path.join(local_dir, "license.key")
    
    activated = False
    if os.path.exists(license_path):
        with open(license_path, "r") as f:
            key = f.read().strip()
        if validate_key(hwid, key):
            activated = True
            
    if not activated:
        dialog = ActivationDialog(hwid)
        if dialog.exec_() != QDialog.Accepted:
            sys.exit(0)
            
    ex = MiniDownloadPro()
    ex.show()
    sys.exit(app.exec_())
