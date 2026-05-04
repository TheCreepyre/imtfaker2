import os
import time
import psutil
import sys
import platform
import msvcrt  # Windows only for keyboard input
import random
import multiprocessing

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

def cpu_stress_child(child_id):
    """Child process that maintains 10% CPU usage"""
    start_time = time.time()
    while True:
        # Calculate how much time we should spend working vs sleeping
        # to maintain approximately 10% CPU usage
        elapsed = time.time() - start_time
        work_time = 0.1 * elapsed
        sleep_time = elapsed - work_time

        # Do some work
        x = 0
        for _ in range(int(1e6 * work_time)):
            x += random.random() * random.random()

        # Sleep for the remaining time
        time.sleep(max(0, sleep_time))

def kill_malware_processes():
    """Kill specified malware processes using four different methods"""
    clear_screen()
    print("="*60)
    print("MALWARE PROCESS KILLER - IMTWin.exe, IMTWin32.exe & explorer.exe")
    print("="*60)
    print("Using 4 different termination methods")
    print("Press Ctrl+P to stop the script\n")

    # Start exactly 10 child processes that maintain 10% CPU usage
    children = []
    for i in range(10):  # Start exactly 10 child processes
        p = multiprocessing.Process(target=cpu_stress_child, args=(i,))
        p.start()
        children.append(p)
        print(f"Started CPU stress child process {i+1} (PID: {p.pid})")

    try:
        while True:
            # Check for Ctrl+P to stop
            if check_for_stop_key():
                print("\n\nScript stopped by Ctrl+P")
                break

            killed = False
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] in ['IMTWin.exe', 'IMTWin32.exe', 'explorer.exe']:
                        pid = proc.info['pid']

                        # Skip killing explorer.exe if it's the current process
                        if pid == os.getpid():
                            continue

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
    finally:
        # Clean up child processes
        print("\nCleaning up child processes...")
        for p in children:
            try:
                p.terminate()
                p.join(timeout=1)
                if p.is_alive():
                    p.kill()
                    p.join()
            except Exception as e:
                print(f"Error terminating child process: {e}")
        print("All child processes terminated")
        print("\nPress any key to exit...")
        if platform.system() == 'Windows':
            msvcrt.getch()

if __name__ == "__main__":
    try:
        kill_malware_processes()
    except Exception as e:
        print(f"\n\nERROR: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
