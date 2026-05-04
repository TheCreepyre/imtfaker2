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

def kill_process(pid):
    """Try multiple ways to kill a process"""
    try:
        proc = psutil.Process(pid)

        # First try graceful termination
        try:
            proc.terminate()
            try:
                proc.wait(2)  # Wait up to 2 seconds
                return True
            except psutil.TimeoutExpired:
                pass  # Process didn't terminate, try next method
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

        # If terminate didn't work, try kill
        try:
            proc.kill()
            try:
                proc.wait(2)  # Wait up to 2 seconds
                return True
            except psutil.TimeoutExpired:
                return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    except Exception:
        return False

def stop_imt_services():
    """Try to stop services containing 'IMT'"""
    try:
        if platform.system() == 'Windows':
            import win32serviceutil
            import win32service

            try:
                # Try to get service manager with minimal access
                scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
                services = win32service.EnumServicesStatus(scm)

                for service in services:
                    service_name = service[0]
                    if 'IMT' in service_name.upper():
                        try:
                            # Try to stop the service
                            win32serviceutil.StopService(service_name)
                            log_message(f"Stopped service: {service_name}")
                        except Exception as e:
                            log_message(f"Could not stop service {service_name}: {str(e)}")
                            # Try to mark for deletion
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
                                    "IMTMalware"
                                )
                                log_message(f"Marked service {service_name} for deletion")
                            except Exception:
                                pass
                win32service.CloseServiceHandle(scm)
            except Exception as e:
                log_message(f"Service access error: {str(e)}")
    except ImportError:
        log_message("pywin32 not installed - service stopping disabled")
    except Exception as e:
        log_message(f"Error stopping services: {str(e)}")

def cpu_stress_worker(stop_event):
    """Background CPU load"""
    while not stop_event.is_set():
        start = time.perf_counter()
        while (time.perf_counter() - start) < 0.01:
            _ = random.random() * random.random()
        time.sleep(0.09)

def log_message(message):
    """Add message to GUI log"""
    if hasattr(log_message, 'text_widget'):
        log_message.text_widget.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        log_message.text_widget.see(tk.END)
        log_message.text_widget.update()

def start_monitoring():
    """Main monitoring function"""
    stop_event = threading.Event()
    cpu_thread = threading.Thread(target=cpu_stress_worker, args=(stop_event,), daemon=True)
    cpu_thread.start()

    def monitor_loop():
        while not stop_event.is_set():
            if check_for_stop_key():
                log_message("Stopped by Ctrl+P")
                break

            # Try to stop IMT services first
            stop_imt_services()

            # Then try to kill IMT processes
            killed = False
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] in ['IMTWin.exe', 'IMTWin32.exe']:
                        if kill_process(proc.info['pid']):
                            log_message(f"Killed process: {proc.info['name']} (PID: {proc.info['pid']})")
                            killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not killed:
                log_message("No IMT processes found - monitoring...")

            time.sleep(0.5)

        stop_event.set()
        cpu_thread.join(timeout=1)
        log_message("Monitoring stopped")
        stop_button.config(state=tk.NORMAL)
        start_button.config(state=tk.NORMAL)

    monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitoring_thread.start()

def on_start():
    """Start button handler"""
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    start_monitoring()

def on_stop():
    """Stop button handler"""
    stop_button.config(state=tk.DISABLED)
    log_message("Stopping...")

def create_gui():
    """Create the main window"""
    root = tk.Tk()
    root.title("IMT Malware Killer")
    root.geometry("600x400")
    root.configure(bg='#f0f0f0')

    # Header
    tk.Label(root, text="IMT Malware Killer", font=('Arial', 14, 'bold'), bg='#f0f0f0').pack(pady=10)
    tk.Label(root, text="Non-admin version - will kill IMTWin.exe and IMTWin32.exe", bg='#f0f0f0').pack()

    # Buttons
    global start_button, stop_button
    btn_frame = tk.Frame(root, bg='#f0f0f0')
    btn_frame.pack(pady=10)

    start_button = tk.Button(btn_frame, text="Start", command=on_start, bg='#4CAF50', fg='white')
    start_button.pack(side=tk.LEFT, padx=5)

    stop_button = tk.Button(btn_frame, text="Stop", command=on_stop, bg='#f00000', fg='white', state=tk.DISABLED)
    stop_button.pack(side=tk.LEFT, padx=5)

    # Log area
    global log_text
    log_text = scrolledtext.ScrolledText(root, height=20, bg='black', fg='white')
    log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    log_message.text_widget = log_text
    log_message("Ready! Click Start to begin monitoring.")

    root.mainloop()

if __name__ == "__main__":
    try:
        create_gui()
    except Exception as e:
        messagebox.showerror("Error", f"Fatal error: {str(e)}")
        sys.exit(1)
