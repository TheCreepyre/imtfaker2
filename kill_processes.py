import os
import time
import psutil
import subprocess
import sys

# List of processes to kill
processes_to_kill = ["IMTWin32.exe", "IMTWin.exe", "edge.exe", "explorer.exe"]

# Function to log events
def log_event(message):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}")

# Function to kill a process by name
def kill_process(process_name):
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                proc.kill()
                log_event(f"Terminated process: {process_name}")
    except Exception as e:
        log_event(f"Error killing {process_name}: {e}")

# Function to spawn a child process of this script
def spawn_child():
    try:
        # Get the current script's path
        script_path = os.path.abspath(__file__)
        # Spawn a new child process
        subprocess.Popen(
            [sys.executable, script_path],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        log_event("Spawned child process")
    except Exception as e:
        log_event(f"Error spawning child: {e}")

# Main execution
if __name__ == "__main__":
    # Spawn a child process
    spawn_child()

    # Main loop
    while True:
        for process_name in processes_to_kill:
            kill_process(process_name)
        time.sleep(0.5)  # Wait 500ms (0.5 seconds) before repeating