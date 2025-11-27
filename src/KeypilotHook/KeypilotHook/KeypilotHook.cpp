#include "pch.h"
#include <windows.h>
#include <stdio.h>

HHOOK hKeyHook = NULL;
HINSTANCE hInst = NULL;

LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        if (wParam == WM_KEYDOWN) {
            KBDLLHOOKSTRUCT* pKeyInfo = (KBDLLHOOKSTRUCT*)lParam;

            char buffer[64];
            sprintf_s(buffer, "[Native C++] Key Pressed: %d\n", pKeyInfo->vkCode);
            OutputDebugStringA(buffer);
        }
    }
    return CallNextHookEx(hKeyHook, nCode, wParam, lParam);
}


extern "C" __declspec(dllexport) void StartHook() {
    if (hKeyHook == NULL) {
        hKeyHook = SetWindowsHookEx(WH_KEYBOARD_LL, LowLevelKeyboardProc, hInst, 0);
        if (hKeyHook != NULL) OutputDebugStringA("[Native C++] Hook Started!\n");
    }
}

extern "C" __declspec(dllexport) void StopHook() {
    if (hKeyHook != NULL) {
        UnhookWindowsHookEx(hKeyHook);
        hKeyHook = NULL;
        OutputDebugStringA("[Native C++] Hook Stopped.\n");
    }
}

BOOL APIENTRY DllMain(HMODULE hModule,
    DWORD  ul_reason_for_call,
    LPVOID lpReserved
)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        hInst = hModule;
        break;
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        if (hKeyHook != NULL) UnhookWindowsHookEx(hKeyHook);
        break;
    }
    return TRUE;
}