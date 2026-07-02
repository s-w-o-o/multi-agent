import subprocess
import re
import json
import os
import sys
import time
import threading

def run_tunnel():
    print("[Tunnel] Starting SSH tunnel to localhost.run...")
    os.makedirs("data", exist_ok=True)
    config_file = "data/tunnel_config.json"
    
    # Generate SSH key if it doesn't exist (required for localhost.run)
    ssh_dir = os.path.expanduser("~/.ssh")
    ssh_key_path = os.path.join(ssh_dir, "id_rsa")
    if not os.path.exists(ssh_key_path):
        try:
            print("[Tunnel] Generating SSH key...")
            os.makedirs(ssh_dir, exist_ok=True)
            subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", ssh_key_path, "-N", ""], check=True)
            print("[Tunnel] SSH key generated successfully.")
        except Exception as e:
            print(f"[Tunnel] Failed to generate SSH key: {e}")
            
    # Run the SSH command
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:8503", "nokey@localhost.run"]
    
    # We run in a loop to restart if it drops
    while True:
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Read stdout line by line
            for line in iter(process.stdout.readline, ''):
                sys.stdout.write(line)
                sys.stdout.flush()
                
                # Check for the lhr.life HTTPS link
                # Example output line: ed317f87d0b696.lhr.life tunneled with tls termination, https://ed317f87d0b696.lhr.life
                match = re.search(r"https://[a-zA-Z0-9-]+\.lhr\.life", line)
                if match:
                    url = match.group(0)
                    print(f"\n[Tunnel] Detected public URL: {url}")
                    
                    # Write to config file
                    with open(config_file, "w", encoding="utf-8") as f:
                        json.dump({"url": url, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False, indent=4)
                    print(f"[Tunnel] Config updated at {config_file}\n")
            
            process.wait()
        except Exception as e:
            print(f"[Tunnel] Error in subprocess: {e}")
        
        print("[Tunnel] Connection lost. Reconnecting in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    run_tunnel()
