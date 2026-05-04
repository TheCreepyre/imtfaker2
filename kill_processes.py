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
    """Try to kill a process and its children without admin rights"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        try:
            parent.terminate()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    except Exception:
        return False

def force_kill(pid):
    """Most aggressive kill method available to non-admin users"""
    try:
        proc = psutil.Process(pid)
        proc.kill()
        return True
    except Exception:
        return False

def stop_imt_services():
    """Try to stop services without admin rights"""
    try:
        if platform.system() == 'Windows':
            import win32serviceutil
            import win32service
            try:
                scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
                services = win32service.EnumServicesStatus(scm)

                for service in services:
                    service_name = service[0]
                    if 'IMT' in service_name.upper():
                        try:
                            # Try to stop the service
                            win32serviceutil.StopService(service_name)
                            log_message(f"Attempted to stop service: {service_name}")
                        except Exception:
                            # If stopping fails, try to mark it for deletion
                            try:
                                win32serviceutil.ChangeServiceConfig(
                                    service_name,
                                    win32service.SERVICE_NO_CHANGE,
                                    win32service.SERVICE_NO_CHANGE,
                                    win32service.SERVICE_NO_CHANGE,
                                    None,
                                    None,
                                    None,
                                    None,
                                    None,
                                    None,
                                    "IMTMalwareMarkedForDeletion"
                                )
                                log_message(f"Marked service for deletion: {service_name}")
                            except Exception:
                                pass
                win32service.CloseServiceHandle(scm)
            except Exception as e:
                log_message(f"Service access error: {str(e)}")
    except ImportError:
        log_message("pywin32 not installed. Service functionality disabled.")
    except Exception as e:
        log_message(f"Error accessing services: {str(e)}")

def log_message(message):
    """Add a message to the GUI log"""
    if hasattr(log_message, 'text_widget'):
        log_message.text_widget.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        log_message.text_widget.see(tk.END)
        log_message.text_widget.update()

def start_monitoring():
    """Start the monitoring process in a separate thread"""
    stop_event = threading.Event()
    threads = []
    for i in range(10):
        t = threading.Thread(target=cpu_stress_worker, args=(i, stop_event), daemon=True)
        t.start()
        threads.append(t)

    def monitoring_loop():
        while not stop_event.is_set():
            if check_for_stop_key():
                log_message("Script stopped by Ctrl+P")
                stop_event.set()
                break

            killed = False

            # First try to stop IMT services
            stop_imt_services()

            # Then try to kill processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name']
                    if proc_name in ['IMTWin.exe', 'IMTWin32.exe']:
                        pid = proc.info['pid']

                        if pid == os.getpid():
                            continue

                        log_message(f"Attempting to kill: {proc_name} (PID: {pid})")

                        if kill_process_tree(pid) or force_kill(pid):
                            log_message(f"SUCCESS: Killed {proc_name} (PID: {pid})")
                            killed = True
                        else:
                            log_message(f"FAILED: Could not kill {proc_name} (PID: {pid})")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    log_message(f"Error processing {proc.info.get('name', 'unknown')}: {str(e)}")

            if not killed:
                log_message("No malware processes detected - monitoring...")

            time.sleep(0.1)

        log_message("Cleaning up threads...")
        stop_event.set()
        for t in threads:
            t.join(timeout=1)
        log_message("All threads terminated")
        stop_button.config(state=tk.NORMAL)
        start_button.config(state=tk.NORMAL)

    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()

def cpu_stress_worker(worker_id, stop_event):
    """Thread worker that attempts to maintain ~10% CPU usage."""
    while not stop_event.is_set():
        start = time.perf_counter()
        while (time.perf_counter() - start) < 0.01:
            _ = random.random() * random.random()
        time.sleep(0.09)

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
    root.title("Malware Process & Service Killer")
    root.geometry("600x400")
    root.resizable(True, True)
    root.configure(bg='#f0f0f0')

    font = ('Consolas', 10)

    # Header frame
    header_frame = tk.Frame(root, bg='#f0f0f0')
    header_frame.pack(fill=tk.X, padx=10, pady=10)

    tk.Label(
        header_frame,
        text="MALWARE KILLER - IMTWin.exe, IMTWin32.exe",
        font=('Consolas', 12, 'bold'),
        bg='#f0f0f0'
    ).pack(anchor=tk.W)

    tk.Label(
        header_frame,
        text="Non-admin version - limited functionality\nPress Ctrl+P to stop the script",
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

    log_message.text_widget = log_text
    log_message("Ready to start monitoring. Click 'Start Monitoring' to begin.")

    root.mainloop()

if __name__ == "__main__":
    try:
        create_gui()
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
        sys.exit(1)
