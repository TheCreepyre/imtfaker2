import os
import time
import subprocess
import sys
import psutil
import signal
import ctypes
import threading
import win32com.client

# --- CONFIG ---
TARGET_PROCESSES = ["IMTWin32.exe", "IMTWin.exe", "edge.exe", "explorer.exe"]
LOCK_FILE = "process_killer.lock"
TOTAL_PROCESSES = 10  # 1 main + 9 children
CHECK_INTERVAL = 2    # Seconds between health checks
KILL_INTERVAL = 0.5   # Seconds between kill attempts

# --- CORE FUNCTIONS ---
def kill_process(process_name):
    """Kill a process using 4 different methods."""
    try:
        # Method 1: taskkill
        subprocess.run(
            ["taskkill", "/f", "/im", process_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Method 2: psutil
        for proc in psutil.process_iter(['name', 'pid']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                try:
                    proc.kill()
                except:
                    pass

        # Method 3: WMI
        try:
            wmi = win32com.client.GetObject("winmgmts:\\\\.\\root\\cimv2")
            for p in wmi.ExecQuery(f"SELECT * FROM Win32_Process WHERE Name LIKE '%{process_name}%'"):
                p.Terminate()
        except:
            pass

        # Method 4: os.kill
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                try:
                    os.kill(proc.pid, signal.SIGTERM)
                except:
                    pass
    except:
        pass

def get_active_processes():
    """Get list of active PIDs from lock file."""
    try:
        with open(LOCK_FILE, "r") as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except:
        return []

def write_lock_file(pids):
    """Write list of PIDs to lock file."""
    with open(LOCK_FILE, "w") as f:
        for pid in pids:
            f.write(f"{pid}\n")

def is_process_alive(pid):
    """Check if a process is still running."""
    try:
        return psutil.pid_exists(pid)
    except:
        return False

def count_live_processes(pids):
    """Count how many processes from the list are still alive."""
    return sum(1 for pid in pids if is_process_alive(pid))

def spawn_process(is_child=False):
    """Spawn a new process (main or child)."""
    try:
        if is_child:
            proc = subprocess.Popen(
                [sys.executable, __file__, "child"],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            proc = subprocess.Popen(
                [sys.executable, __file__],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        return proc.pid
    except:
        return None

def regulate_processes(my_pid, is_main):
    """Maintain exactly TOTAL_PROCESSES running."""
    while True:
        try:
            active_pids = get_active_processes()
            live_count = count_live_processes(active_pids)

            if live_count < TOTAL_PROCESSES:
                needed = TOTAL_PROCESSES - live_count
                new_pids = []
                for _ in range(needed):
                    if is_main:
                        new_pid = spawn_process(is_child=True)
                    else:
                        new_pid = spawn_process(is_child=True)
                    if new_pid:
                        new_pids.append(new_pid)

                if new_pids:
                    updated_pids = [pid for pid in active_pids if is_process_alive(pid)] + new_pids
                    write_lock_file(updated_pids)

            elif live_count > TOTAL_PROCESSES:
                pass

            if not is_main and my_pid not in active_pids:
                main_pid = spawn_process(is_child=False)
                if main_pid:
                    updated_pids = [main_pid] + [pid for pid in active_pids if is_process_alive(pid)]
                    write_lock_file(updated_pids)

        except:
            pass
        time.sleep(CHECK_INTERVAL)

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    if sys.platform == "win32":
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    is_main = len(sys.argv) == 1 or sys.argv[1] != "child"
    my_pid = os.getpid()

    if not os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "w") as f:
            f.write(f"{my_pid}\n")
        is_main = True
    else:
        active_pids = get_active_processes()
        if my_pid not in active_pids:
            active_pids.append(my_pid)
            write_lock_file(active_pids)

    regulate_thread = threading.Thread(
        target=regulate_processes,
        args=(my_pid, is_main),
        daemon=True
    )
    regulate_thread.start()

    while True:
        for process_name in TARGET_PROCESSES:
            kill_process(process_name)
        time.sleep(KILL_INTERVAL)
