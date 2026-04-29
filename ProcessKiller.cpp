#include <windows.h>
#include <tlhelp32.h>
#include <thread>
#include <string>
#include <vector>

// Configuration
const std::vector<std::wstring> TARGET_PROCESSES = {
    L"IMTWin.exe",
    L"IMTWin32.exe",
    L"explorer.exe"
};

// Process termination with error handling
void KillProcess(const std::wstring& processName) {
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnapshot == INVALID_HANDLE_VALUE) return;

    PROCESSENTRY32W pe32 = { sizeof(PROCESSENTRY32W) };
    if (!Process32FirstW(hSnapshot, &pe32)) {
        CloseHandle(hSnapshot);
        return;
    }

    do {
        if (_wcsicmp(pe32.szExeFile, processName.c_str()) == 0) {
            HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pe32.th32ProcessID);
            if (hProcess) {
                TerminateProcess(hProcess, 0);
                CloseHandle(hProcess);
            }
        }
    } while (Process32NextW(hSnapshot, &pe32));

    CloseHandle(hSnapshot);
}

// Main entry point (hidden window)
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    // Ensure only one instance runs
    HANDLE hMutex = CreateMutexW(NULL, TRUE, L"MyUniqueProgramMutex");
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        // Another instance is already running
        return 0;
    }

    // Hide console completely (only works if console exists)
    HWND hConsole = GetConsoleWindow();
    if (hConsole) {
        ShowWindow(hConsole, SW_HIDE);
    }

    // Main loop - runs forever
    for (;;) {
        for (const auto& process : TARGET_PROCESSES) {
            KillProcess(process);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(500)); // 500ms delay
    }

    // Release mutex (though we never reach here)
    ReleaseMutex(hMutex);
    CloseHandle(hMutex);

    return 0;
}
