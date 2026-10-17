"""Native Windows UIA: confirm only the user-authorized Power BI source warning."""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import time

INVOKE_STARTED = False

def validate_warning(names, buttons):
    """Fail closed on another warning, inaccessible content, or ambiguous controls."""
    if not any((name or "").startswith("This file uses multiple data sources.") for name in names):
        raise RuntimeError("Warning body mismatch or unavailable; manual handling required")
    if "Do you want to open this file?" not in names:
        raise RuntimeError("Warning question mismatch; manual handling required")
    ok = [button for button in buttons if button[0] == "OK"]
    cancel = [button for button in buttons if button[0] == "Cancel"]
    if len(ok) != 1 or len(cancel) != 1 or not ok[0][1]:
        raise RuntimeError("Ambiguous or disabled warning controls")


def main():
    global INVOKE_STARTED
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int)
    parser.add_argument("--handle", type=int)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--confirm", action="store_true", help="Only with the user's explicit authorization")
    parser.add_argument("--check-dependencies", action="store_true")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise RuntimeError("Native Desktop UI Automation requires Windows")
    if args.check_dependencies:
        import comtypes.client
        uia = comtypes.client.GetModule("UIAutomationCore.dll")
        comtypes.client.CreateObject(uia.CUIAutomation8, interface=uia.IUIAutomation)
        return {"dependencies": "ok", "provider": "CUIAutomation8"}
    if not args.pid or not args.handle:
        parser.error("--pid and --handle are required unless checking dependencies")
    # Locate the target process dialog without traversing a report being rebuilt.
    # Power BI uses an unowned top-level window for this warning.
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    process = kernel32.OpenProcess(0x1000, False, args.pid)
    if not process:
        raise RuntimeError("Cannot inspect target process")
    try:
        image = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(image))
        if not kernel32.QueryFullProcessImageNameW(process, 0, image, ctypes.byref(length)) or Path(image.value).name.lower() != "pbidesktop.exe":
            raise RuntimeError("Target process must be PBIDesktop.exe")
    finally:
        kernel32.CloseHandle(process)
    def title(hwnd):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, len(buf))
        return buf.value
    handles = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    @callback_type
    def visit(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == args.pid and title(hwnd) == "Potential security risk" and user32.IsWindowVisible(hwnd):
            handles.append(hwnd)
        return True
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows(visit, 0)
    if not handles:
        return {"confirmed": False, "reason": "matching_dialog_not_present"}
    if len(handles) != 1:
        raise RuntimeError("Ambiguous warning windows")
    import comtypes.client
    uia = comtypes.client.GetModule("UIAutomationCore.dll")
    client = comtypes.client.CreateObject(uia.CUIAutomation8, interface=uia.IUIAutomation)
    options = client.QueryInterface(uia.IUIAutomation2)
    options.ConnectionTimeout = 5000
    options.TransactionTimeout = 5000
    root = client.ElementFromHandle(args.handle)
    if root.CurrentProcessId != args.pid:
        raise RuntimeError("Target window process does not match")
    def bounds():
        # UIA can return an empty rectangle while Desktop rebuilds its UI.
        rectangle = wintypes.RECT()
        if not user32.GetWindowRect(args.handle, ctypes.byref(rectangle)):
            raise RuntimeError("Cannot read target window bounds")
        if rectangle.right <= rectangle.left or rectangle.bottom <= rectangle.top:
            raise RuntimeError("Target window bounds are empty")
        return [rectangle.left, rectangle.top, rectangle.right, rectangle.bottom]
    dialog_handle = handles[0]
    dialog = client.ElementFromHandle(dialog_handle)
    if dialog.CurrentProcessId != args.pid or dialog.CurrentAutomationId != "MessageDetailsDialog":
        raise RuntimeError("Warning identity mismatch")
    found = dialog.FindAll(4, client.CreateTrueCondition())
    nodes = [found.GetElement(i) for i in range(found.Length)]
    names = [e.CurrentName for e in nodes]
    validate_warning(names, [(e.CurrentName, bool(e.CurrentIsEnabled)) for e in nodes if e.CurrentControlType == 50000])
    buttons = lambda name: [e for e in nodes if e.CurrentControlType == 50000 and e.CurrentName == name]
    ok, cancel = buttons("OK"), buttons("Cancel")
    if len(ok) != 1 or len(cancel) != 1 or not ok[0].CurrentIsEnabled:
        raise RuntimeError("Ambiguous or disabled warning controls")
    invoke = ok[0].GetCurrentPattern(10000).QueryInterface(uia.IUIAutomationInvokePattern)
    if args.inspect or not args.confirm:
        return {"confirmed": False, "matched": True, "invokePatternAvailable": True}
    before = bounds()
    INVOKE_STARTED = True
    invoke.Invoke()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not user32.IsWindow(dialog_handle) or not user32.IsWindowVisible(dialog_handle):
            after = bounds()
            return {"confirmed": True, "method": "native_UIA_InvokePattern", "before": before,
                    "after": after, "boundsUnchanged": before == after}
        time.sleep(0.2)
    raise RuntimeError("Invoke returned but warning did not close")

if __name__ == "__main__":
    try:
        print(json.dumps(main()))
    except Exception as error:
        # UIA elements can disappear while Desktop replaces the report during reload.
        # Retry discovery only; never retry an invocation whose outcome is unknown.
        if not INVOKE_STARTED and getattr(error, "hresult", None) in (-2147220991, -2147418111, -2146233083):
            print(json.dumps({"confirmed": False, "reason": "provider_refreshing"}))
        else:
            print(json.dumps({"error": str(error)}))
            sys.exit(1)
