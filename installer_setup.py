import os
import sys
import shutil
import subprocess
import winreg
import hashlib

APP_NAME = "MiniDownload"
VERSION = "5.5.1"

def get_ext_id():
    h = hashlib.md5(b"MiniDownloadExtension2026").hexdigest()[:32]
    chars = "abcdefghijklmnop"
    return "".join(chars[int(c, 16)] for c in h)

def register_registry_extension(ext_folder):
    ext_id = get_ext_id()
    manifest_path = os.path.join(ext_folder, "manifest.json")
    if not os.path.exists(manifest_path):
        return False

    success = False
    # Register for Google Chrome
    try:
        key_path = rf"Software\Google\Chrome\Extensions\{ext_id}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            winreg.SetValueEx(k, "path", 0, winreg.REG_SZ, os.path.abspath(ext_folder))
            winreg.SetValueEx(k, "version", 0, winreg.REG_SZ, "1.0.0")
            success = True
    except Exception as e:
        print("Chrome reg failed:", e)

    # Register for Microsoft Edge
    try:
        key_path = rf"Software\Microsoft\Edge\Extensions\{ext_id}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            winreg.SetValueEx(k, "path", 0, winreg.REG_SZ, os.path.abspath(ext_folder))
            winreg.SetValueEx(k, "version", 0, winreg.REG_SZ, "1.0.0")
            success = True
    except Exception as e:
        print("Edge reg failed:", e)

    return success

def create_desktop_shortcut(target_exe, shortcut_name="Mini Download"):
    try:
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")
        ps_cmd = f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{shortcut_path}"); $s.TargetPath="{target_exe}"; $s.WorkingDirectory="{os.path.dirname(target_exe)}"; $s.Save()'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    except Exception as e:
        print("Shortcut error:", e)

def install():
    print(f"Installing {APP_NAME} {VERSION}...")
    install_dir = os.path.join(os.environ.get("LOCALAPPDATA", "."), APP_NAME)
    os.makedirs(install_dir, exist_ok=True)

    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

    # Copy all bundled application files
    for item in os.listdir(bundle_dir):
        if item.startswith('_') or item.endswith('.pyc') or item in ['installer_setup.py', 'build_dist.py']:
            continue
        src = os.path.join(bundle_dir, item)
        dst = os.path.join(install_dir, item)
        try:
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            print(f"Error copying {item}:", e)

    # Auto-register Browser Extension into Chrome and Edge
    ext_folder = os.path.join(install_dir, "Mini_extension")
    if os.path.exists(ext_folder):
        register_registry_extension(ext_folder)

    # Create Desktop Shortcut & launch
    main_exe = os.path.join(install_dir, "free_downloader_pro.exe")
    if not os.path.exists(main_exe):
        main_exe = os.path.join(install_dir, "MiniDownload.exe")

    if os.path.exists(main_exe):
        create_desktop_shortcut(main_exe)
        try:
            os.startfile(main_exe)
        except Exception:
            subprocess.Popen([main_exe], cwd=install_dir)

if __name__ == "__main__":
    install()
