import sys
import os
import threading
import yt_dlp
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                             QProgressBar, QFileDialog, QComboBox, QTextEdit)
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtGui import QFont, QIcon

class DownloadSignals(QObject):
    progress = pyqtSignal(float, str, str) # percent, speed, eta
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

class DownloaderThread(threading.Thread):
    def __init__(self, url, save_dir, format_type, quality, signals):
        super().__init__()
        self.url = url
        self.save_dir = save_dir
        self.format_type = format_type
        self.quality = quality
        self.signals = signals
        self._is_cancelled = False

    def progress_hook(self, d):
        if self._is_cancelled:
            raise Exception("Download cancelled by user")
            
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            
            percent = 0.0
            if total > 0:
                percent = (downloaded / total) * 100
                
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            
            filename = os.path.basename(d.get('filename', ''))
            self.signals.status.emit(f"Downloading: {filename}")
            self.signals.progress.emit(percent, speed, eta)
            
        elif d['status'] == 'finished':
            self.signals.status.emit("Download complete, processing...")

    def run(self):
        # Locate ffmpeg.exe if available in the extracted directory to merge high-quality video/audio
        extracted_ffmpeg = r"c:\Users\K-VeaSna\Desktop\Mini Download 5.4.1 full\Mini Download 5.4.1 full.exe_extracted\ffmpeg.exe"
        
        ydl_opts = {
            'outtmpl': os.path.join(self.save_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
        }

        if os.path.exists(extracted_ffmpeg):
            ydl_opts['ffmpeg_location'] = extracted_ffmpeg
            self.signals.status.emit("Using FFmpeg helper for high quality merges...")

        if self.format_type == "Audio Only (MP3)":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else: # Video
            if self.quality == "1080p (High Quality)":
                ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
            elif self.quality == "720p (Medium Quality)":
                ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
            elif self.quality == "480p (Low Quality)":
                ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best'
            else:
                ydl_opts['format'] = 'bestvideo+bestaudio/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.signals.finished.emit(True, "Download completed successfully!")
        except Exception as e:
            self.signals.finished.emit(False, str(e))

class ModernDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.signals = DownloadSignals()
        self.initUI()
        
        # Connect signals
        self.signals.progress.connect(self.update_progress)
        self.signals.status.connect(self.update_status)
        self.signals.finished.connect(self.download_finished)

    def initUI(self):
        self.setWindowTitle("Free Video Downloader (yt-dlp GUI)")
        self.resize(700, 500)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 14px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #00ADB5;
            }
            QPushButton {
                background-color: #00ADB5;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #008F95;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
            QComboBox {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #333333;
                border-radius: 6px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #00ADB5;
                border-radius: 5px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 6px;
                font-family: Consolas, monospace;
                color: #888888;
                font-size: 12px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_label = QLabel("Video Downloader")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00ADB5;")
        main_layout.addWidget(title_label)

        # Subtitle
        sub_label = QLabel("Paste a URL from YouTube, Facebook, TikTok, or other sites to download.")
        sub_label.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        main_layout.addWidget(sub_label)

        # URL Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste video link here...")
        main_layout.addWidget(self.url_input)

        # Save Directory Row
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        # Default to user's downloads folder
        default_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.dir_input.setText(default_dir)
        self.dir_input.setReadOnly(True)
        self.dir_btn = QPushButton("Browse...")
        self.dir_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.dir_input, 4)
        dir_layout.addWidget(self.dir_btn, 1)
        main_layout.addLayout(dir_layout)

        # Options Row
        options_layout = QHBoxLayout()
        
        # Format Selector
        format_label_layout = QVBoxLayout()
        format_label_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Video + Audio (MP4)", "Audio Only (MP3)"])
        self.format_combo.currentIndexChanged.connect(self.format_changed)
        format_label_layout.addWidget(self.format_combo)
        
        # Quality Selector
        quality_label_layout = QVBoxLayout()
        quality_label_layout.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best Available", "1080p (High Quality)", "720p (Medium Quality)", "480p (Low Quality)"])
        quality_label_layout.addWidget(self.quality_combo)

        options_layout.addLayout(format_label_layout, 1)
        options_layout.addLayout(quality_label_layout, 1)
        main_layout.addLayout(options_layout)

        # Download Button
        self.download_btn = QPushButton("Start Download")
        self.download_btn.clicked.connect(self.start_download)
        main_layout.addWidget(self.download_btn)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        main_layout.addWidget(self.status_label)

        # Logs/Details Box
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Detailed download information will appear here...")
        main_layout.addWidget(self.log_box)

    def format_changed(self, index):
        if index == 1: # Audio Only
            self.quality_combo.setEnabled(False)
        else:
            self.quality_combo.setEnabled(True)

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.dir_input.text())
        if directory:
            self.dir_input.setText(directory)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.status_label.setText("Error: Please paste a valid URL first!")
            return
            
        save_dir = self.dir_input.text()
        format_type = self.format_combo.currentText()
        quality = self.quality_combo.currentText()

        self.download_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        self.dir_btn.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.quality_combo.setEnabled(False)
        
        self.progress_bar.setValue(0)
        self.log_box.clear()
        self.log_box.append(f"Starting download for: {url}")
        
        self.downloader_thread = DownloaderThread(url, save_dir, format_type, quality, self.signals)
        self.downloader_thread.start()

    def update_progress(self, percent, speed, eta):
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(f"Speed: {speed} | ETA: {eta}")

    def update_status(self, text):
        self.log_box.append(text)
        # Scroll to bottom
        self.log_box.ensureCursorVisible()

    def download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.dir_btn.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.format_changed(self.format_combo.currentIndex())
        
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Download completed successfully!")
            self.log_box.append("\n>>> SUCCESS: " + message)
        else:
            self.status_label.setText("Download failed!")
            self.log_box.append("\n>>> ERROR: " + message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ModernDownloader()
    ex.show()
    sys.exit(app.exec_())
