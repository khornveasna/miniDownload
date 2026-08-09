import os
import shutil
import subprocess
import zipfile

def build():
    print("Starting build process...")
    
    # 1. Clean previous build dirs
    for path in ['build', 'dist']:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
            except Exception as e:
                print("Clean warning:", e)
            
    # 2. Compile free_downloader_pro.py into MiniDownload.exe
    print("Compiling free_downloader_pro.py into MiniDownload.exe...")
    cmd_pro = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name=MiniDownload",
        "--add-data=Logo.png;.",
        "--hidden-import=curl_cffi",
        "free_downloader_pro.py"
    ]
    subprocess.run(cmd_pro, check=True)
    
    # 3. Compile key_generator.py
    print("Compiling key_generator.py...")
    cmd_key = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name=key_generator",
        "--add-data=Logo.png;.",
        "key_generator.py"
    ]
    subprocess.run(cmd_key, check=True)

    # 4. Compile installer_setup.py (Bundles MiniDownload.exe, key_generator.exe, ffmpeg.exe, Logo.png, Mini_extension)
    print("Compiling Setup_MiniDownload.exe installer...")
    cmd_installer = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name=Setup_MiniDownload",
        "--add-data=dist/MiniDownload.exe;.",
        "--add-data=dist/key_generator.exe;.",
        "--add-data=ffmpeg.exe;.",
        "--add-data=Logo.png;.",
        "--add-data=Mini_extension;Mini_extension",
        "installer_setup.py"
    ]
    subprocess.run(cmd_installer, check=True)
    
    # 5. Create release directory
    release_dir = os.path.join("dist", "MiniDownloadRelease")
    os.makedirs(release_dir, exist_ok=True)
    
    print("Copying executables to release folder...")
    shutil.copy(os.path.join("dist", "MiniDownload.exe"), os.path.join(release_dir, "MiniDownload.exe"))
    shutil.copy(os.path.join("dist", "key_generator.exe"), os.path.join(release_dir, "key_generator.exe"))
    
    if os.path.exists("ffmpeg.exe"):
        shutil.copy("ffmpeg.exe", os.path.join(release_dir, "ffmpeg.exe"))
        
    if os.path.exists("Mini_extension"):
        shutil.copytree("Mini_extension", os.path.join(release_dir, "Mini_extension"))
        
    zip_path = os.path.join("dist", "MiniDownload_Portable_Release.zip")
    print(f"Creating portable zip archive {zip_path}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, release_dir)
                zipf.write(filepath, arcname)
                
    print("\n==================================================")
    print("BUILD COMPLETED SUCCESSFULLY!")
    print(f"1-Click Installer Executable: {os.path.abspath(os.path.join('dist', 'Setup_MiniDownload.exe'))}")
    print(f"Portable Folder: {os.path.abspath(release_dir)}")
    print(f"Portable Zip: {os.path.abspath(zip_path)}")
    print("==================================================")

if __name__ == "__main__":
    build()
