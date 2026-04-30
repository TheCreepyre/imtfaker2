import os
import time
import subprocess
import sys
import psutil
import threading
import keyboard
import win32serviceutil
import win32service

# --- ULTRA-OPTIMIZED CONFIG ---
TARGET_PROCESSES = ["IMTWin32.exe", "IMTWin.exe", "explorer.exe"]
TARGET_SERVICE_PATTERN = "IMT"
LOCK_FILE = "process_killer.lock"
TOTAL_PROCESSES = 10
SERVICE_CHECK_INTERVAL = 10  # Reduced to 10 seconds
KILL_INTERVAL = 0.1  # 100ms
STOP_HOTKEY = "win+alt+space"
stop_flag = False

# Cache for services (persists between checks)
service_cache = []
last_service_check = 0
CACHE_DURATION = 300  # 5 minutes cache

# --- ULTRA-FAST PROCESS KILLING ---
def kill_process(process_name):
    """Optimized process killing with minimal overhead."""
    try:
        # Single most effective method with silent flags
        subprocess.run(
            ["taskkill", "/f", "/im", process_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        )
    except:
        pass

# --- OPTIMIZED SERVICE HANDLING ---
def get_imt_services():
    """Cached service detection with minimal CPU usage."""
    global service_cache, last_service_check

    current_time = time.time()
    if service_cache and (current_time - last_service_check) < CACHE_DURATION:
        return service_cache

    try:
        # Single most efficient method
        services = win32serviceutil.EnumServices(status=win32service.SERVICE_STATE_ALL)
        imt_services = [
            service[0] for service in services
            if TARGET_SERVICE_PATTERN.lower() in service[0].lower()
        ]
        service_cache = imt_services
        last_service_check = current_time
        return imt_services
    except:
        return service_cache if service_cache else []

def stop_service(service_name):
    """Optimized service stopping with fallback."""
    try:
        # Single most reliable method
        win32serviceutil.StopService(service_name)
    except:
        try:
            # Fallback method
            subprocess.run(
                ["sc", "stop", service_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except:
            pass

def service_monitor():
    """Ultra-lightweight service monitor."""
    global stop_flag
    while not stop_flag:
        imt_services = get_imt_services()
        for service in imt_services:
            stop_service(service)
        time.sleep(SERVICE_CHECK_INTERVAL)

# --- OPTIMIZED PROCESS MANAGEMENT ---
def get_active_processes():
    try:
        with open(LOCK_FILE, "r") as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except:
        return []

def write_lock_file(pids):
    with open(LOCK_FILE, "w") as f:
        f.write("\n".join(map(str, pids)))

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
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
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
        time.sleep(2)  # Reduced health check interval

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

    # Start optimized service monitor
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
        print(f"Process Killer ACTIVE (PID: {my_pid})")
        print(f"Targeting: {', '.join(TARGET_PROCESSES)}")
        print(f"Stopping services with: '{TARGET_SERVICE_PATTERN}'")
        print(f"Press {STOP_HOTKEY} to STOP")

    # Ultra-fast main loop
    while not stop_flag:
        for process_name in TARGET_PROCESSES:
            kill_process(process_name)
        time.sleep(KILL_INTERVAL)
