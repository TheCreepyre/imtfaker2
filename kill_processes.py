import os
import time
import subprocess
import sys
import psutil
import signal
import ctypes

# List of processes to kill
processes_to_kill = ["IMTWin32.exe", "IMTWin.exe", "edge.exe", "explorer.exe"]

# Function to kill a process using multiple methods
def kill_process(process_name):
    try:
        # Method 1: Use taskkill (Windows-specific)
        subprocess.run(
            ["taskkill", "/f", "/im", process_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Method 2: Use psutil
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                try:
                    proc.kill()
                except:
                    pass

        # Method 3: Use os.kill (fallback)
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                try:
                    os.kill(proc.pid, signal.SIGTERM)
                except:
                    pass
    except:
        pass

# Hide console window (Windows only)
if sys.platform == "win32":
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Main loop
while True:
    for process_name in processes_to_kill:
        kill_process(process_name)
    time.sleep(0.5)  # 500ms delay
