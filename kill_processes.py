import os
import time
import subprocess
import sys
import psutil
import signal
import threading
import keyboard

# --- CONFIG ---
TARGET_PROCESSES = ["IMTWin32.exe", "IMTWin.exe", "explorer.exe"]
TARGET_SERVICE_PATTERN = "IMT"  # Stops all services with "IMT" in name
LOCK_FILE = "process_killer.lock"
TOTAL_PROCESSES = 10
CHECK_INTERVAL = 2
KILL_INTERVAL = 0.1  # 100ms
STOP_HOTKEY = "win+alt+space"
stop_flag = False

# --- PROCESS KILLING ---
def kill_process(process_name):
    """Kill a process using multiple methods."""
    try:
        # Method 1: taskkill
        subprocess.run(["taskkill", "/f", "/im", process_name],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Method 2: psutil
        for proc in psutil.process_iter(['name', 'pid']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                try:
                    proc.kill()
                except:
                    pass
    except:
        pass

# --- SERVICE STOPPING (5 METHODS) ---
def get_imt_services():
    """Get list of IMT services using multiple methods."""
    services = set()

    # Method 1: sc query
    try:
        result = subprocess.run(["sc", "query", "type=", "service", "state=", "all"],
                               capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "SERVICE_NAME:" in line:
                service_name = line.split(":")[1].strip()
                if TARGET_SERVICE_PATTERN.lower() in service_name.lower():
                    services.add(service_name)
    except:
        pass

    # Method 2: wmic
    try:
        result = subprocess.run(["wmic", "service", "get", "name,displayname"],
                               capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "IMT" in line.upper():
                service_name = line.split()[0].strip()
                if service_name:
                    services.add(service_name)
    except:
        pass

    # Method 3: powershell
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-Service | Where-Object {$_.DisplayName -like '*IMT*'} | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if line.strip():
                services.add(line.strip())
    except:
        pass

    return list(services)

def stop_service(service_name):
    """Stop a service using 5 different methods."""
    # Method 1: sc stop
    try:
        subprocess.run(["sc", "stop", service_name],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    # Method 2: net stop
    try:
        subprocess.run(["net", "stop", service_name],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    # Method 3: wmic
    try:
        subprocess.run(["wmic", "service", service_name, "call", "stopservice"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    # Method 4: powershell
    try:
        subprocess.run(
            ["powershell", "-Command", f"Stop-Service -Name '{service_name}' -Force"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    # Method 5: taskkill (if service has associated processes)
    try:
        subprocess.run(["taskkill", "/f", "/fi", f"SERVICES eq {service_name}"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

def service_monitor():
    """Monitor and stop IMT services using all methods."""
    global stop_flag
    while not stop_flag:
        imt_services = get_imt_services()
        for service in imt_services:
            stop_service(service)
        time.sleep(2)  # Check every 2 seconds

# --- PROCESS MANAGEMENT ---
def get_active_processes():
    try:
        with open(LOCK_FILE, "r") as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except:
        return []

def write_lock_file(pids):
    with open(LOCK_FILE, "w") as f:
        for pid in pids:
            f.write(f"{pid}\n")

def is_process_alive(pid):
    try:
        return psutil.pid_exists(pid)
    except:
        return False

def spawn_process(is_child=False):
    try:
        if is_child:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            proc = subprocess.Popen(
                [sys.executable, __file__, "child"],
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            proc = subprocess.Popen(
                [sys.executable, __file__],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        return proc.pid
    except:
        return None

def regulate_processes(my_pid, is_main):
    global stop_flag
    while not stop_flag:
        try:
            active_pids = get_active_processes()
            live_count = sum(1 for pid in active_pids if is_process_alive(pid))

            if live_count < TOTAL_PROCESSES:
                needed = TOTAL_PROCESSES - live_count
                new_pids = []
                for _ in range(needed):
                    new_pid = spawn_process(is_child=True)
                    if new_pid:
                        new_pids.append(new_pid)

                if new_pids:
                    updated_pids = [pid for pid in active_pids if is_process_alive(pid)] + new_pids
                    write_lock_file(updated_pids)

            if not is_main and not any(pid != my_pid and is_process_alive(pid) for pid in active_pids):
                main_pid = spawn_process(is_child=False)
                if main_pid:
                    updated_pids = [main_pid] + [pid for pid in active_pids if is_process_alive(pid)]
                    write_lock_file(updated_pids)
        except:
            pass
        time.sleep(CHECK_INTERVAL)

def stop_all_processes():
    global stop_flag
    stop_flag = True
    try:
        os.remove(LOCK_FILE)
    except:
        pass
    for proc in psutil.process_iter(['name', 'cmdline']):
        if proc.info['name'] == 'python.exe':
            try:
                if any(__file__ in cmd for cmd in proc.info['cmdline']):
                    proc.kill()
            except:
                pass

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    keyboard.add_hotkey(STOP_HOTKEY, stop_all_processes)

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

    # Start service monitor thread (non-blocking)
    service_thread = threading.Thread(target=service_monitor, daemon=True)
    service_thread.start()

    # Start regulation thread
    regulate_thread = threading.Thread(
        target=regulate_processes,
        args=(my_pid, is_main),
        daemon=True
    )
    regulate_thread.start()

    if is_main:
        print(f"Process Killer ACTIVE (Main PID: {my_pid})")
        print(f"Targeting processes: {', '.join(TARGET_PROCESSES)}")
        print(f"Stopping services with: '{TARGET_SERVICE_PATTERN}'")
        print(f"Maintaining {TOTAL_PROCESSES} processes...")
        print(f"Press {STOP_HOTKEY} to STOP")
        print("--- Running ---")

    # Main killing loop (100ms interval, completely independent)
    while not stop_flag:
        for process_name in TARGET_PROCESSES:
            kill_process(process_name)
        time.sleep(KILL_INTERVAL)

    if is_main:
        print("Process Killer STOPPED")
