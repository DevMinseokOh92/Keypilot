#include "pch.h"
#include <windows.h>
#include <stdio.h>

typedef void(__stdcall* DebugCallback)(int code); // 키보드/마우스 공용 콜백

HHOOK hKeyHook = NULL;
HHOOK hMouseHook = NULL; // ★ 마우스 훅 추가
HINSTANCE hInst = NULL;
DebugCallback g_Callback = NULL;

// 1. 키보드 훅
LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        if (wParam == WM_KEYDOWN) {
            KBDLLHOOKSTRUCT* pKeyInfo = (KBDLLHOOKSTRUCT*)lParam;
            if (g_Callback != NULL) g_Callback(pKeyInfo->vkCode); // 키 코드 전송
        }
    }
    return CallNextHookEx(hKeyHook, nCode, wParam, lParam);
}

// 2. ★ [추가] 마우스 훅
LRESULT CALLBACK LowLevelMouseProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        // 좌클릭(LBUTTON) 또는 우클릭(RBUTTON) 발생 시
        if (wParam == WM_LBUTTONDOWN || wParam == WM_RBUTTONDOWN) {
            if (g_Callback != NULL) {
                // 약속: 마우스 클릭은 '-1'이라는 코드로 C#에 알림
                g_Callback(-1);
            }
        }
    }
    return CallNextHookEx(hMouseHook, nCode, wParam, lParam);
}

extern "C" __declspec(dllexport) void SetKeyCallback(DebugCallback callback) {
    g_Callback = callback;
}

extern "C" __declspec(dllexport) int StartHook() {
    if (hKeyHook != NULL) return 0;

    HMODULE hModule = NULL;
    GetModuleHandleEx(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, (LPCTSTR)StartHook, &hModule);

    // 키보드 훅 설치
    hKeyHook = SetWindowsHookEx(WH_KEYBOARD_LL, LowLevelKeyboardProc, hModule, 0);

    // ★ [추가] 마우스 훅 설치
    hMouseHook = SetWindowsHookEx(WH_MOUSE_LL, LowLevelMouseProc, hModule, 0);

    if (hKeyHook == NULL || hMouseHook == NULL) return GetLastError();
    return 0;
}

extern "C" __declspec(dllexport) void StopHook() {
    if (hKeyHook != NULL) {
        UnhookWindowsHookEx(hKeyHook);
        hKeyHook = NULL;
    }
    // ★ [추가] 마우스 훅 해제
    if (hMouseHook != NULL) {
        UnhookWindowsHookEx(hMouseHook);
        hMouseHook = NULL;
    }
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    return TRUE;
}