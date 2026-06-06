import os
import shutil
import subprocess
import zipfile

def build():
    print("Starting build process...")
    
    # 1. Clean previous build dirs
    for path in ['build', 'dist']:
        if os.path.exists(path):
            shutil.rmtree(path)
            
    # 2. Compile free_downloader_pro.py
    print("Compiling free_downloader_pro.py...")
    cmd_pro = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--add-data", "Logo.png;.",
        "--hidden-import", "curl_cffi",
        "free_downloader_pro.py"
    ]
    subprocess.run(cmd_pro, check=True)
    
    # 3. Compile key_generator.py
    print("Compiling key_generator.py...")
    cmd_key = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--add-data", "Logo.png;.",
        "key_generator.py"
    ]
    subprocess.run(cmd_key, check=True)
    
    # 4. Create release directory
    release_dir = os.path.join("dist", "MiniDownloadRelease")
    os.makedirs(release_dir, exist_ok=True)
    
    # 5. Copy built executables
    print("Copying executables to release folder...")
    shutil.copy(os.path.join("dist", "free_downloader_pro.exe"), os.path.join(release_dir, "free_downloader_pro.exe"))
    shutil.copy(os.path.join("dist", "key_generator.exe"), os.path.join(release_dir, "key_generator.exe"))
    
    # 6. Copy ffmpeg.exe
    if os.path.exists("ffmpeg.exe"):
        print("Copying ffmpeg.exe...")
        shutil.copy("ffmpeg.exe", os.path.join(release_dir, "ffmpeg.exe"))
    else:
        print("Warning: ffmpeg.exe not found in root!")
        
    # 7. Copy Mini_extension folder
    if os.path.exists("Mini_extension"):
        print("Copying Mini_extension...")
        shutil.copytree("Mini_extension", os.path.join(release_dir, "Mini_extension"))
    else:
        print("Warning: Mini_extension folder not found!")
        
    # 8. Create Zip Archive
    zip_path = os.path.join("dist", "MiniDownload_Release.zip")
    print(f"Creating zip archive {zip_path}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, release_dir)
                zipf.write(filepath, arcname)
                
    print("Build completed successfully!")
    print(f"Release files are in: {os.path.abspath(release_dir)}")
    print(f"Distribution ZIP is at: {os.path.abspath(zip_path)}")

if __name__ == "__main__":
    build()
