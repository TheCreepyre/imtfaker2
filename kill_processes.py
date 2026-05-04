import os
import time
import psutil
import sys
import platform
import random
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

def check_for_stop_key():
    """Check if Ctrl+P is pressed (Windows only)"""
    if platform.system() == 'Windows':
        import msvcrt
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
                ctypes.windll.kernel32.OpenProcess(1, False, pid), -1
            )
        return True
    except:
        return False

def cpu_stress_worker(worker_id, stop_event):
    """Thread worker that attempts to maintain ~10% CPU usage."""
    while not stop_event.is_set():
        # Work for ~10ms, sleep for ~90ms => ~10% duty cycle
        start = time.perf_counter()
        while (time.perf_counter() - start) < 0.01:
            _ = random.random() * random.random()
        time.sleep(0.09)

def stop_imt_services():
    """Stop services that contain 'IMT' in their name"""
    try:
        if platform.system() == 'Windows':
            import win32serviceutil
            import win32service
            scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
            services = win32service.EnumServicesStatus(scm)

            for service in services:
                service_name = service[0]
                if 'IMT' in service_name.upper():
                    try:
                        win32serviceutil.StopService(service_name)
                        log_message(f"Stopped service: {service_name}")
                    except Exception as e:
                        log_message(f"Failed to stop service {service_name}: {str(e)}")
            win32service.CloseServiceHandle(scm)
    except ImportError:
        log_message("pywin32 not installed. Cannot stop services on this system.")
    except Exception as e:
        log_message(f"Error stopping services: {str(e)}")

def log_message(message):
    """Add a message to the GUI log"""
    if hasattr(log_message, 'text_widget'):
        log_message.text_widget.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        log_message.text_widget.see(tk.END)
        log_message.text_widget.update()

def start_monitoring():
    """Start the monitoring process in a separate thread"""
    # Start CPU stress threads
    stop_event = threading.Event()
    threads = []
    for i in range(10):
        t = threading.Thread(target=cpu_stress_worker, args=(i, stop_event), daemon=True)
        t.start()
        threads.append(t)

    # Start monitoring loop
    def monitoring_loop():
        while not stop_event.is_set():
            if check_for_stop_key():
                log_message("Script stopped by Ctrl+P")
                stop_event.set()
                break

            killed = False

            # First stop IMT services
            stop_imt_services()

            # Then kill processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] in ['IMTWin.exe', 'IMTWin32.exe', 'explorer.exe']:
                        pid = proc.info['pid']

                        # Skip killing explorer.exe if it's the current process
                        if pid == os.getpid():
                            continue

                        methods = [
                            ("Process Tree", kill_process_tree(pid)),
                            ("Terminate()", kill_with_terminate(pid)),
                            ("Kill()", kill_with_kill(pid)),
                            ("SIGKILL", kill_with_sigkill(pid)),
                        ]

                        success = [m[0] for m in methods if m[1]]
                        log_message(f"KILLED: {proc.info['name']} (PID: {pid})")
                        log_message(f"Methods used: {', '.join(success)}")
                        killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            if not killed:
                log_message("No malware processes detected - monitoring...")

            time.sleep(0.1)

        # Cleanup
        log_message("Cleaning up threads...")
        stop_event.set()
        for t in threads:
            t.join(timeout=1)
        log_message("All threads terminated")
        stop_button.config(state=tk.NORMAL)
        start_button.config(state=tk.NORMAL)

    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()

def on_start():
    """Handle start button click"""
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    start_monitoring()

def on_stop():
    """Handle stop button click"""
    stop_button.config(state=tk.DISABLED)
    log_message("Stopping script...")
    # The monitoring loop will handle the actual stopping

def create_gui():
    """Create the main application window"""
    root = tk.Tk()
    root.title("Malware Process Killer")
    root.geometry("600x400")
    root.resizable(True, True)

    # Configure styles
    root.configure(bg='#f0f0f0')
    font = ('Consolas', 10)

    # Header frame
    header_frame = tk.Frame(root, bg='#f0f0f0')
    header_frame.pack(fill=tk.X, padx=10, pady=10)

    tk.Label(
        header_frame,
        text="MALWARE PROCESS KILLER - IMTWin.exe, IMTWin32.exe & explorer.exe",
        font=('Consolas', 12, 'bold'),
        bg='#f0f0f0'
    ).pack(anchor=tk.W)

    tk.Label(
        header_frame,
        text="Using 4 different termination methods\nPress Ctrl+P to stop the script",
        font=('Consolas', 10),
        bg='#f0f0f0'
    ).pack(anchor=tk.W, pady=(5, 0))

    # Button frame
    button_frame = tk.Frame(root, bg='#f0f0f0')
    button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

    global start_button, stop_button
    start_button = tk.Button(
        button_frame,
        text="Start Monitoring",
        command=on_start,
        bg='#4CAF50',
        fg='white',
        font=('Consolas', 10, 'bold'),
        padx=10,
        pady=5
    )
    start_button.pack(side=tk.LEFT, padx=(0, 10))

    stop_button = tk.Button(
        button_frame,
        text="Stop Monitoring",
        command=on_stop,
        bg='#f00000',
        fg='white',
        font=('Consolas', 10, 'bold'),
        padx=10,
        pady=5,
        state=tk.DISABLED
    )
    stop_button.pack(side=tk.LEFT)

    # Log display
    log_frame = tk.Frame(root, bg='#f0f0f0')
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    global log_text
    log_text = scrolledtext.ScrolledText(
        log_frame,
        wrap=tk.WORD,
        font=font,
        bg='black',
        fg='white',
        padx=5,
        pady=5
    )
    log_text.pack(fill=tk.BOTH, expand=True)

    # Store reference for logging function
    log_message.text_widget = log_text

    # Initial message
    log_message("Ready to start monitoring. Click 'Start Monitoring' to begin.")

    root.mainloop()

if __name__ == "__main__":
    try:
        create_gui()
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
        sys.exit(1)
