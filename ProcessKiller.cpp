#include <windows.h>
#include <tlhelp32.h>
#include <chrono>
#include <thread>
#include <iostream>
#include <string>
#include <vector>
#include <mutex>
#include <atomic>

// Configuration
constexpr int CHECK_INTERVAL_MS = 10;
constexpr int GUARDIAN_INSTANCES = 3;
const std::vector<std::wstring> TARGET_PROCESSES = {
    L"IMTWin.exe",
    L"IMTWin32.exe",
    L"explorer.exe"
};

// Global mutex for single instance
std::mutex g_mutex;
std::atomic<bool> g_running{true};

// Process termination function with error handling
bool TerminateProcessByName(const std::wstring& processName) {
    bool killed = false;
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);

    if (hSnapshot == INVALID_HANDLE_VALUE) {
        std::wcerr << L"Failed to create process snapshot: " << GetLastError() << std::endl;
        return false;
    }

    PROCESSENTRY32W pe32;
    pe32.dwSize = sizeof(PROCESSENTRY32W);

    if (!Process32FirstW(hSnapshot, &pe32)) {
        std::wcerr << L"Failed to get first process: " << GetLastError() << std::endl;
        CloseHandle(hSnapshot);
        return false;
    }

    do {
        if (_wcsicmp(pe32.szExeFile, processName.c_str()) == 0) {
            HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pe32.th32ProcessID);
            if (hProcess) {
                if (TerminateProcess(hProcess, 0)) {
                    killed = true;
                    std::wcout << L"Successfully terminated: " << processName << std::endl;
                } else {
                    std::wcerr << L"Failed to terminate " << processName
                              << ": " << GetLastError() << std::endl;
                }
                CloseHandle(hProcess);
            }
        }
    } while (Process32NextW(hSnapshot, &pe32));

    CloseHandle(hSnapshot);
    return killed;
}

// Main process killer function
void ProcessKiller() {
    // Hide console window
    ShowWindow(GetConsoleWindow(), SW_HIDE);

    while (g_running) {
        for (const auto& process : TARGET_PROCESSES) {
            if (TerminateProcessByName(process)) {
                // Small delay between process terminations
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(CHECK_INTERVAL_MS));
    }
}

// Guardian spawner function
void SpawnGuardian() {
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi;

    si.dwFlags = CREATE_NO_WINDOW;
    si.wShowWindow = SW_HIDE;

    if (!CreateProcessW(
        nullptr,
        const_cast<wchar_t*>(L"ProcessKiller.exe"),
        nullptr,
        nullptr,
        FALSE,
        CREATE_NO_WINDOW,
        nullptr,
        nullptr,
        &si,
        &pi
    )) {
        std::wcerr << L"Failed to spawn guardian: " << GetLastError() << std::endl;
        return;
    }

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
}

// Single instance check
bool IsSingleInstance() {
    HANDLE hMutex = CreateMutexW(nullptr, TRUE, L"Global\\ProcessKillerMutex");
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        CloseHandle(hMutex);
        return false;
    }
    return true;
}

// Cleanup handler
BOOL WINAPI ConsoleHandler(DWORD signal) {
    if (signal == CTRL_C_EVENT || signal == CTRL_CLOSE_EVENT) {
        g_running = false;
        return TRUE;
    }
    return FALSE;
}

int main() {
    // Set up console control handler
    SetConsoleCtrlHandler(ConsoleHandler, TRUE);

    // Check for single instance
    if (!IsSingleInstance()) {
        std::wcerr << L"Another instance is already running" << std::endl;
        return 1;
    }

    // Spawn guardian instances
    for (int i = 0; i < GUARDIAN_INSTANCES; ++i) {
        SpawnGuardian();
    }

    // Main process killer loop
    ProcessKiller();

    // Cleanup
    ReleaseMutex(CreateMutexW(nullptr, FALSE, L"Global\\ProcessKillerMutex"));
    return 0;
}
