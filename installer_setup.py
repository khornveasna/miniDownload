import os
import sys
import shutil
import subprocess
import winreg
import hashlib
import json

from PyQt5.QtWidgets import (QApplication, QDialog, QLabel, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QCheckBox, QProgressBar,
                             QFileDialog, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QFont

APP_NAME = "MiniDownload"
VERSION = "5.5.1"

def get_ext_id():
    h = hashlib.md5(b"MiniDownloadExtension2026").hexdigest()[:32]
    chars = "abcdefghijklmnop"
    return "".join(chars[int(c, 16)] for c in h)

def register_browser_extension(ext_folder):
    ext_id = get_ext_id()
    manifest_path = os.path.join(ext_folder, "manifest.json")
    if not os.path.exists(manifest_path):
        return False

    abs_ext_path = os.path.abspath(ext_folder)
    success = False

    # 1. Register HKCU Keys for Chrome & Edge
    for reg_path in [rf"Software\Google\Chrome\Extensions\{ext_id}", rf"Software\Microsoft\Edge\Extensions\{ext_id}"]:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as k:
                winreg.SetValueEx(k, "path", 0, winreg.REG_SZ, abs_ext_path)
                winreg.SetValueEx(k, "version", 0, winreg.REG_SZ, "1.0.0")
                success = True
        except Exception as e:
            print("REG HKCU error:", e)

    # 2. Register HKLM Keys for Chrome & Edge
    for reg_path in [rf"Software\Google\Chrome\Extensions\{ext_id}", rf"Software\Microsoft\Edge\Extensions\{ext_id}"]:
        try:
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as k:
                winreg.SetValueEx(k, "path", 0, winreg.REG_SZ, abs_ext_path)
                winreg.SetValueEx(k, "version", 0, winreg.REG_SZ, "1.0.0")
        except Exception:
            pass

    # 3. Register Policy Allowlist Keys
    for policy_path in [r"Software\Policies\Google\Chrome\ExtensionInstallAllowlist", r"Software\Policies\Microsoft\Edge\ExtensionInstallAllowlist"]:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, policy_path) as k:
                winreg.SetValueEx(k, "1", 0, winreg.REG_SZ, ext_id)
        except Exception:
            pass

    # 4. Drop JSON Descriptors into External Extensions folders for Chrome, Edge, Brave
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    target_dirs = [
        os.path.join(local_appdata, r"Google\Chrome\User Data\External Extensions"),
        os.path.join(local_appdata, r"Microsoft\Edge\User Data\External Extensions"),
        os.path.join(local_appdata, r"BraveSoftware\Brave-Browser\User Data\External Extensions"),
    ]

    json_data = json.dumps({
        "external_directory": abs_ext_path,
        "external_version": "1.0.0"
    }, indent=2)

    for target_dir in target_dirs:
        try:
            os.makedirs(target_dir, exist_ok=True)
            json_file = os.path.join(target_dir, f"{ext_id}.json")
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(json_data)
            success = True
        except Exception as e:
            print("JSON descriptor error:", e)

    return success

def register_startup(exe_path):
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            winreg.SetValueEx(k, "MiniDownload", 0, winreg.REG_SZ, f'"{exe_path}"')
    except Exception as e:
        print("Startup reg error:", e)

def create_desktop_shortcut(target_exe, shortcut_name="Mini Download"):
    try:
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")
        ps_cmd = f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{shortcut_path}"); $s.TargetPath="{target_exe}"; $s.WorkingDirectory="{os.path.dirname(target_exe)}"; $s.Save()'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    except Exception as e:
        print("Shortcut error:", e)

class ExtensionHelperDialog(QDialog):
    def __init__(self, ext_folder, parent=None):
        super().__init__(parent)
        self.ext_folder = os.path.abspath(ext_folder)
        self.setWindowTitle("Mini Download Browser Extension Helper")
        self.resize(560, 360)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #E2E8F0;
                font-size: 13px;
            }
            QLabel#titleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #38BDF8;
            }
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton#secondaryBtn {
                background-color: #334155;
                color: #F8FAFC;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #475569;
            }
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #38BDF8;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("🌐 Browser Extension Enable Helper")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        info = QLabel(
            "Mini Download has registered the extension into Chrome and Edge registry & external directories.\n\n"
            "📌 Step 1: Restart your Chrome or Edge browser.\n"
            "📌 Step 2: Click 'Enable extension' when prompted by the browser.\n"
            "📌 Step 3: If not prompted, click the buttons below to open Chrome/Edge extension page or copy path:"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(self.ext_folder)
        self.path_edit.setReadOnly(True)
        copy_btn = QPushButton("Copy Path")
        copy_btn.setObjectName("secondaryBtn")
        copy_btn.clicked.connect(self.copy_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(copy_btn)
        layout.addLayout(path_layout)

        btn_layout = QHBoxLayout()
        open_chrome_btn = QPushButton("🌐 Open Chrome Extensions")
        open_edge_btn = QPushButton("🌐 Open Edge Extensions")
        close_btn = QPushButton("OK / Close")
        close_btn.setObjectName("secondaryBtn")

        open_chrome_btn.clicked.connect(self.open_chrome)
        open_edge_btn.clicked.connect(self.open_edge)
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(open_chrome_btn)
        btn_layout.addWidget(open_edge_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def copy_path(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.ext_folder)
        QMessageBox.information(self, "Copied", "Extension folder path copied to clipboard!")

    def open_chrome(self):
        try:
            cmd = f'start chrome --load-extension="{self.ext_folder}" chrome://extensions'
            subprocess.run(cmd, shell=True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not launch Chrome: {e}")

    def open_edge(self):
        try:
            cmd = f'start msedge --load-extension="{self.ext_folder}" edge://extensions'
            subprocess.run(cmd, shell=True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not launch Edge: {e}")

class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str, str, str)

    def __init__(self, install_dir, add_ext, add_shortcut, auto_start):
        super().__init__()
        self.install_dir = install_dir
        self.add_ext = add_ext
        self.add_shortcut = add_shortcut
        self.auto_start = auto_start

    def run(self):
        try:
            self.progress.emit(10, "Creating installation directory...")
            os.makedirs(self.install_dir, exist_ok=True)

            bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            items = [i for i in os.listdir(bundle_dir) if not i.startswith('_') and not i.endswith('.pyc') and i not in ['installer_setup.py', 'build_dist.py']]

            total_items = max(1, len(items))
            for idx, item in enumerate(items):
                percent = int(10 + (idx / total_items) * 60)
                self.progress.emit(percent, f"Copying {item}...")
                src = os.path.join(bundle_dir, item)
                dst = os.path.join(self.install_dir, item)
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

            ext_folder = os.path.join(self.install_dir, "Mini_extension")
            if self.add_ext and os.path.exists(ext_folder):
                self.progress.emit(75, "Registering browser extension into Chrome & Edge...")
                register_browser_extension(ext_folder)

            main_exe = os.path.join(self.install_dir, "free_downloader_pro.exe")
            if not os.path.exists(main_exe):
                main_exe = os.path.join(self.install_dir, "MiniDownload.exe")

            if self.add_shortcut and os.path.exists(main_exe):
                self.progress.emit(85, "Creating desktop shortcut...")
                create_desktop_shortcut(main_exe)

            if self.auto_start and os.path.exists(main_exe):
                self.progress.emit(95, "Setting up Windows startup...")
                register_startup(main_exe)

            self.progress.emit(100, "Installation Complete!")
            self.finished.emit(True, "Installation completed successfully!", main_exe, ext_folder)

        except Exception as e:
            self.finished.emit(False, str(e), "", "")

class SetupWizard(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Mini Download {VERSION} Setup")
        self.resize(580, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #E2E8F0;
                font-size: 13px;
            }
            QLabel#titleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #38BDF8;
            }
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
                color: #F8FAFC;
                font-size: 13px;
            }
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton#cancelBtn {
                background-color: #334155;
                color: #94A3B8;
            }
            QPushButton#cancelBtn:hover {
                background-color: #475569;
            }
            QCheckBox {
                color: #E2E8F0;
                font-size: 13px;
                spacing: 8px;
            }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                background-color: #1E293B;
                text-align: center;
                color: white;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #0EA5E9;
                border-radius: 5px;
            }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title_lbl = QLabel(f"Mini Download {VERSION} Setup")
        title_lbl.setObjectName("titleLabel")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

        desc_lbl = QLabel("Welcome to the Mini Download Installation Wizard. This setup will install Mini Download, core components, and browser integration on your computer.")
        desc_lbl.setWordWrap(True)
        self.main_layout.addWidget(desc_lbl)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #334155;")
        self.main_layout.addWidget(line)

        dir_lbl = QLabel("Installation Directory:")
        self.main_layout.addWidget(dir_lbl)

        dir_layout = QHBoxLayout()
        default_path = os.path.join(os.environ.get("LOCALAPPDATA", "."), APP_NAME)
        self.dir_input = QLineEdit(default_path)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_dir)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(browse_btn)
        self.main_layout.addLayout(dir_layout)

        self.chk_ext = QCheckBox("🌐 Automatically install Browser Extension (Google Chrome & Microsoft Edge)")
        self.chk_ext.setChecked(True)

        self.chk_shortcut = QCheckBox("🖥️ Create Desktop Shortcut")
        self.chk_shortcut.setChecked(True)

        self.chk_startup = QCheckBox("🚀 Start Mini Download automatically when Windows boots")
        self.chk_startup.setChecked(True)

        self.main_layout.addWidget(self.chk_ext)
        self.main_layout.addWidget(self.chk_shortcut)
        self.main_layout.addWidget(self.chk_startup)

        self.status_lbl = QLabel("Ready to install.")
        self.main_layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.main_layout.addWidget(self.progress_bar)

        self.main_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)

        self.install_btn = QPushButton("Install Now")
        self.install_btn.clicked.connect(self.start_install)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.install_btn)
        self.main_layout.addLayout(btn_layout)

        self.installed_exe = ""

    def browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Folder", self.dir_input.text())
        if folder:
            self.dir_input.setText(folder)

    def start_install(self):
        install_dir = self.dir_input.text().strip()
        if not install_dir:
            QMessageBox.warning(self, "Invalid Path", "Please select a valid installation directory.")
            return

        self.install_btn.setEnabled(False)
        self.dir_input.setEnabled(False)
        self.chk_ext.setEnabled(False)
        self.chk_shortcut.setEnabled(False)
        self.chk_startup.setEnabled(False)

        self.worker = InstallWorker(
            install_dir=install_dir,
            add_ext=self.chk_ext.isChecked(),
            add_shortcut=self.chk_shortcut.isChecked(),
            auto_start=self.chk_startup.isChecked()
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, percent, msg):
        self.progress_bar.setValue(percent)
        self.status_lbl.setText(msg)

    def on_finished(self, success, message, exe_path, ext_folder):
        if success:
            self.installed_exe = exe_path

            if self.chk_ext.isChecked() and ext_folder and os.path.exists(ext_folder):
                helper_dialog = ExtensionHelperDialog(ext_folder, self)
                helper_dialog.exec_()

            if exe_path and os.path.exists(exe_path):
                try:
                    os.startfile(exe_path)
                except Exception:
                    subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
            self.accept()
        else:
            QMessageBox.critical(self, "Installation Error", f"Failed to install Mini Download:\n{message}")
            self.install_btn.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.exec_()

if __name__ == "__main__":
    main()
