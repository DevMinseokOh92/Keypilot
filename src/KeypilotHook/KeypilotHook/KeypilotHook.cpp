#include "pch.h"
#include <windows.h>
#include <stdio.h>

// [전역 변수]
HHOOK hKeyHook = NULL;
HINSTANCE hInst = NULL;

// ---------------------------------------------------------
// [Core] 키보드 훅 프로시저
// ---------------------------------------------------------
LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        // 키를 눌렀을 때 (WM_KEYDOWN)
        if (wParam == WM_KEYDOWN) {
            KBDLLHOOKSTRUCT* pKeyInfo = (KBDLLHOOKSTRUCT*)lParam;

            // [수정됨] 파일 저장(느림) 대신 디버그 출력(빠름)만 남김
            // 나중에 여기에 'Named Pipe 전송 코드'가 들어갑니다.
            char buffer[64];
            sprintf_s(buffer, "[Native C++] Key Pressed: %d\n", pKeyInfo->vkCode);
            OutputDebugStringA(buffer);
        }
    }
    // 다음 훅으로 넘김 (필수)
    return CallNextHookEx(hKeyHook, nCode, wParam, lParam);
}

// ---------------------------------------------------------
// [Export] 외부 공개 함수
// ---------------------------------------------------------

extern "C" __declspec(dllexport) void StartHook() {
    if (hKeyHook == NULL) {
        hKeyHook = SetWindowsHookEx(WH_KEYBOARD_LL, LowLevelKeyboardProc, hInst, 0);

        if (hKeyHook != NULL) {
            OutputDebugStringA("[Native C++] Hook Started Successfully!\n");
        }
        else {
            OutputDebugStringA("[Native C++] Failed to Start Hook.\n");
        }
    }
}

extern "C" __declspec(dllexport) void StopHook() {
    if (hKeyHook != NULL) {
        UnhookWindowsHookEx(hKeyHook);
        hKeyHook = NULL;
        OutputDebugStringA("[Native C++] Hook Stopped.\n");
    }
}

// ---------------------------------------------------------
// [System] DLL 진입점
// ---------------------------------------------------------
BOOL APIENTRY DllMain(HMODULE hModule, DWORD  ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
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