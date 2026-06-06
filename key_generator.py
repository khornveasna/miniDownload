import hashlib
import sys

SECRET_SALT = "MiniDownloadSecretSalt2026!"

def generate_key(hwid):
    raw = hwid.strip() + SECRET_SALT
    h = hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()
    return f"{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        hwid = " ".join(sys.argv[1:])
    else:
        hwid = input("Enter Client Machine ID (HWID): ").strip()
        
    if not hwid:
        print("Error: Machine ID cannot be empty.")
        sys.exit(1)
        
    key = generate_key(hwid)
    print("\n" + "="*40)
    print(f"Machine ID: {hwid}")
    print(f"Activation Key: {key}")
    print("="*40 + "\n")
