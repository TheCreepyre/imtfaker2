import os
import time
import psutil
import sys
import platform
import msvcrt  # Windows only for keyboard input

def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def check_for_stop_key():
    """Check if Ctrl+P is pressed (Windows only)"""
    if platform.system() == 'Windows':
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\x10':  # Ctrl+P
                return True
    return False

def kill_process_tree(pid):
    """Kill a process and all its child processes"""
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.terminate()
            except:
                pass
        parent.terminate()
        return True
    except:
        return False

def kill_with_terminate(pid):
    """Kill process using terminate() method"""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        return True
    except:
        return False

def kill_with_kill(pid):
    """Kill process using kill() method"""
    try:
        proc = psutil.Process(pid)
        proc.kill()
        return True
    except:
        return False

def kill_with_sigkill(pid):
    """Kill process using SIGKILL signal (Unix-like systems)"""
    try:
        if platform.system() != 'Windows':
            import signal
            os.kill(pid, signal.SIGKILL)
        else:
            # Windows equivalent of SIGKILL
            import ctypes
            ctypes.windll.kernel32.TerminateProcess(
                ctypes.windll.kernel32.OpenProcess(1, False, pid), -1)
        return True
    except:
        return False

def kill_malware_processes():
    """Kill specified malware processes using four different methods"""
    clear_screen()
    print("="*60)
    print("MALWARE PROCESS KILLER - IMTWin.exe & IMTWin32.exe")
    print("="*60)
    print("Using 4 different termination methods")
    print("Press Ctrl+P to stop the script\n")

    while True:
        # Check for Ctrl+P to stop
        if check_for_stop_key():
            print("\n\nScript stopped by Ctrl+P")
            sys.exit(0)

        killed = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] in ['IMTWin.exe', 'IMTWin32.exe']:
                    pid = proc.info['pid']

                    # Try all four termination methods
                    methods = [
                        ("Process Tree", kill_process_tree(pid)),
                        ("Terminate()", kill_with_terminate(pid)),
                        ("Kill()", kill_with_kill(pid)),
                        ("SIGKILL", kill_with_sigkill(pid))
                    ]

                    # Check which methods succeeded
                    success = [m[0] for m in methods if m[1]]
                    print(f"[{time.strftime('%H:%M:%S')}] KILLED: {proc.info['name']} (PID: {pid})")
                    print(f"           Methods used: {', '.join(success)}")
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if not killed:
            print(f"[{time.strftime('%H:%M:%S')}] No malware processes detected - monitoring...")

        time.sleep(0.1)  # 100ms delay

if __name__ == "__main__":
    try:
        kill_malware_processes()
    except Exception as e:
        print(f"\n\nERROR: {e}")
        sys.exit(1)
