"""Desktop-local tool execution primitives."""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from ctypes import wintypes
from uuid import uuid4

TEST_FAILURE_APP_NAME = "__project_sena_missing_app__"
TEST_FAILURE_ENV_VAR = "PROJECT_SENA_ENABLE_FAILURE_INJECTION"
APP_PROCESS_NAMES = {
    "notepad": "notepad.exe",
    "notepad.exe": "notepad.exe",
}
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DEFAULT_CAPTURE_RETENTION_DAYS = 7
DEFAULT_CAPTURE_MAX_BYTES = 1024 * 1024 * 1024
DEFAULT_CAPTURE_MAX_FILES = 500


def _enable_process_dpi_awareness() -> None:
    """Keep Win32 window coordinates aligned with screenshot pixels."""
    try:
        user32 = ctypes.windll.user32
        set_dpi_awareness_context = getattr(
            user32,
            "SetProcessDpiAwarenessContext",
            None,
        )
        if set_dpi_awareness_context is not None:
            set_dpi_awareness_context.argtypes = [wintypes.HANDLE]
            set_dpi_awareness_context.restype = wintypes.BOOL
            per_monitor_aware_v2 = wintypes.HANDLE(-4)
            if set_dpi_awareness_context(per_monitor_aware_v2):
                return
    except Exception:
        pass

    try:
        shcore = ctypes.windll.shcore
        process_per_monitor_dpi_aware = 2
        shcore.SetProcessDpiAwareness(process_per_monitor_dpi_aware)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _configure_win32_api_types() -> None:
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL

    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.SendMessageW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.SendMessageW.restype = wintypes.LPARAM
    user32.GetWindowRect.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.RECT),
    ]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL

    dwmapi = ctypes.windll.dwmapi
    dwmapi.DwmGetWindowAttribute.argtypes = [
        wintypes.HWND,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long


_enable_process_dpi_awareness()
_configure_win32_api_types()


class ToolExecutionError(RuntimeError):
    """Raised when a tool cannot complete successfully."""

    def __init__(self, message: str, result: dict | None = None) -> None:
        super().__init__(message)
        self.result = result or {}


@dataclass(slots=True)
class ToolExecutionOutcome:
    result: dict


@dataclass(slots=True)
class WindowInfo:
    handle: int
    title: str
    process_id: int | None = None
    process_name: str | None = None
    executable_path: str | None = None


class DesktopToolExecutor:
    """Runs a narrow set of desktop-local tools."""

    def __init__(self, failure_injection_enabled: bool | None = None) -> None:
        self._failure_injection_enabled = (
            _is_truthy_env(TEST_FAILURE_ENV_VAR)
            if failure_injection_enabled is None
            else failure_injection_enabled
        )

    def execute(self, tool_name: str, arguments: dict) -> ToolExecutionOutcome:
        handlers = {
            "open_app": self._open_app,
            "get_active_window": self._get_active_window,
            "capture_screen": self._capture_screen,
            "type_text": self._type_text,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            raise ToolExecutionError(f"Unsupported tool: {tool_name}")
        return handler(arguments)

    def get_foreground_window(self) -> WindowInfo | None:
        return self._get_foreground_window_info()

    def resolve_window_target(self, target: dict) -> WindowInfo | None:
        expected_handle = _optional_int(target.get("expected_window_handle"))
        if expected_handle is not None and ctypes.windll.user32.IsWindow(
            wintypes.HWND(expected_handle)
        ):
            return self._get_window_info(expected_handle)

        expected_process_id = _optional_int(target.get("expected_process_id"))
        if expected_process_id is not None:
            window = self._find_window_for_pid(expected_process_id)
            if window is not None:
                return window

        process_name = str(target.get("expected_process_name") or "").strip().lower()
        if not process_name:
            app_name = str(
                target.get("target_app") or target.get("app_name") or ""
            ).strip().lower()
            process_name = APP_PROCESS_NAMES.get(app_name, "")

        if process_name:
            return self._find_window_for_process_name(process_name)

        return None

    def _open_app(self, arguments: dict) -> ToolExecutionOutcome:
        app_name = str(arguments.get("app_name", "")).strip().lower()
        if app_name == TEST_FAILURE_APP_NAME:
            if self._failure_injection_enabled:
                raise ToolExecutionError(
                    "Injected open_app failure for Project-SENA verification.",
                    result={
                        "launched": False,
                        "app_name": app_name,
                        "failure_injected": True,
                    },
                )

            raise ToolExecutionError(f"Unsupported application: {app_name}")

        executable = APP_PROCESS_NAMES.get(app_name)
        if executable is None:
            raise ToolExecutionError(f"Unsupported application: {app_name}")

        process = subprocess.Popen([executable])
        base_result = {
            "launched": True,
            "app_name": app_name,
            "pid": process.pid,
        }
        executable_path = self._get_process_executable_path(process.pid)
        if executable_path:
            base_result["process_id"] = process.pid
            base_result["process_name"] = Path(executable_path).name
            base_result["executable_path"] = executable_path

        process_alive = self._wait_for_process_start(process)
        base_result["process_alive"] = process_alive
        if not process_alive:
            raise ToolExecutionError(
                f"Launched {app_name}, but the process exited before it became ready.",
                result=base_result,
            )

        window = self._wait_for_window_for_pid(process.pid)
        if window is None:
            base_result["window_detected"] = False
        else:
            base_result["window_detected"] = True
            base_result["window_handle"] = window.handle
            base_result["window_title"] = window.title
            base_result["process_id"] = window.process_id
            base_result["process_name"] = window.process_name
            base_result["executable_path"] = window.executable_path

        return ToolExecutionOutcome(
            result=base_result
        )

    def _get_active_window(self, arguments: dict) -> ToolExecutionOutcome:
        _ = arguments
        window = self._get_foreground_window_info()
        if window is None:
            raise ToolExecutionError("No active foreground window was detected.")

        return ToolExecutionOutcome(
            result={
                "window_title": window.title,
                "window_handle": window.handle,
                "process_id": window.process_id,
                "process_name": window.process_name,
                "executable_path": window.executable_path,
            }
        )

    def _get_foreground_window_info(self) -> WindowInfo | None:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd == 0:
            return None

        return self._get_window_info(hwnd)

    def _get_window_info(self, hwnd: Any) -> WindowInfo:
        pid = self._get_window_process_id(hwnd)
        executable_path = self._get_process_executable_path(pid) if pid else None

        return WindowInfo(
            handle=int(hwnd),
            title=self._get_window_title(hwnd),
            process_id=pid,
            process_name=Path(executable_path).name if executable_path else None,
            executable_path=executable_path,
        )

    def _capture_screen(self, arguments: dict) -> ToolExecutionOutcome:
        capture_mode = _normalize_capture_mode(arguments.get("capture_mode"))
        output_format = str(arguments.get("output_format") or "png").strip().lower()
        if output_format != "png":
            raise ToolExecutionError(
                "capture_screen currently supports only png output.",
                result={
                    "saved": False,
                    "reason": "unsupported_capture_format",
                    "output_format": output_format,
                },
            )

        output_file = _resolve_capture_output_path(arguments, capture_mode)
        target_window: WindowInfo | None = None
        capture_rect: tuple[int, int, int, int] | None = None

        if capture_mode == "all_screens":
            image = self._grab_screen_image()
        else:
            if capture_mode == "active_window":
                if _has_expected_window(arguments):
                    target_window = self.resolve_window_target(arguments)
                else:
                    target_window = self._get_foreground_window_info()
                if target_window is None:
                    raise ToolExecutionError(
                        "No active foreground window was detected for capture.",
                        result={
                            "saved": False,
                            "reason": "missing_foreground_window",
                            "capture_mode": capture_mode,
                        },
                    )
            elif capture_mode == "target_window":
                target_window = self.resolve_window_target(arguments)
                if target_window is None:
                    target_app = str(arguments.get("target_app") or "").strip()
                    reason = (
                        "target_app_window_not_found"
                        if target_app
                        else "target_window_not_found"
                    )
                    raise ToolExecutionError(
                        "The requested window could not be found for capture.",
                        result={
                            "saved": False,
                            "reason": reason,
                            "capture_mode": capture_mode,
                            "target_app": target_app or None,
                        },
                    )
            else:  # pragma: no cover - guarded by _normalize_capture_mode
                raise ToolExecutionError(f"Unsupported capture mode: {capture_mode}")

            self._focus_expected_window(arguments)
            current_window = self._get_foreground_window_info()
            if _has_expected_window(arguments) and (
                current_window is None
                or not self._matches_expected_window(current_window, arguments)
            ):
                raise ToolExecutionError(
                    "Target window could not be focused for capture.",
                    result={
                        "saved": False,
                        "reason": "target_window_not_foreground",
                        "capture_mode": capture_mode,
                        "expected_window": self._expected_window_result(arguments),
                        "current_window": self._window_result(current_window)
                        if current_window
                        else None,
                    },
                )
            if current_window is not None and self._same_window(
                target_window,
                current_window,
            ):
                target_window = current_window
            capture_rect = self._get_capturable_window_rect(target_window)
            image = self._grab_screen_image(bbox=capture_rect)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_file)

        result = {
            "saved": True,
            "output_path": str(output_file),
            "width": image.width,
            "height": image.height,
            "capture_mode": capture_mode,
            "output_format": output_format,
        }
        if capture_rect is not None:
            result["capture_rect"] = {
                "left": capture_rect[0],
                "top": capture_rect[1],
                "right": capture_rect[2],
                "bottom": capture_rect[3],
            }
        if target_window is not None:
            result["target_window"] = self._window_result(target_window)
        result["cleanup"] = _cleanup_capture_directory(
            output_file.parent,
            protected_paths={output_file},
        )

        return ToolExecutionOutcome(
            result=result
        )

    def _type_text(self, arguments: dict) -> ToolExecutionOutcome:
        text = str(arguments.get("text", ""))
        if not text:
            raise ToolExecutionError("type_text requires a non-empty text argument.")

        self._focus_expected_window(arguments)
        target_window = self._get_foreground_window_info()
        if target_window is None:
            raise ToolExecutionError("No active foreground window was detected.")

        if not self._matches_expected_window(target_window, arguments):
            raise ToolExecutionError(
                "Active window changed before typing; refused to type text.",
                result={
                    "typed": False,
                    "reason": "active_window_changed_before_typing",
                    "expected_window": self._expected_window_result(arguments),
                    "current_window": self._window_result(target_window),
                },
            )

        input_method = self._paste_text_via_clipboard(text, target_window)
        current_window = self._get_foreground_window_info()
        if current_window is None or not self._same_window(target_window, current_window):
            raise ToolExecutionError(
                "Active window changed while typing; stopped text input.",
                result={
                    "typed": False,
                    "reason": "active_window_changed_while_typing",
                    "requested_length": len(text),
                    "target_window": self._window_result(target_window),
                    "current_window": self._window_result(current_window)
                    if current_window
                    else None,
                },
            )

        return ToolExecutionOutcome(
            result={
                "typed": True,
                "length": len(text),
                "input_method": input_method,
                "target_window": self._window_result(target_window),
            }
        )

    def _wait_for_process_start(
        self,
        process: subprocess.Popen,
        timeout_seconds: float = 2.0,
        poll_interval_seconds: float = 0.1,
    ) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if process.poll() is None:
                return True
            time.sleep(poll_interval_seconds)
        return process.poll() is None

    def _wait_for_window_for_pid(
        self,
        pid: int,
        timeout_seconds: float = 2.0,
        poll_interval_seconds: float = 0.1,
    ) -> WindowInfo | None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            window = self._find_window_for_pid(pid)
            if window is not None:
                return window
            time.sleep(poll_interval_seconds)
        return self._find_window_for_pid(pid)

    def _find_window_for_pid(self, pid: int) -> WindowInfo | None:
        user32 = ctypes.windll.user32
        matches: list[WindowInfo] = []

        enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def callback(hwnd: int, lparam: int) -> bool:
            del lparam
            if not user32.IsWindowVisible(hwnd):
                return True

            window_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value != pid:
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True

            executable_path = self._get_process_executable_path(window_pid.value)
            matches.append(
                WindowInfo(
                    handle=int(hwnd),
                    title=self._get_window_title(hwnd),
                    process_id=int(window_pid.value),
                    process_name=Path(executable_path).name
                    if executable_path
                    else None,
                    executable_path=executable_path,
                )
            )
            return False

        user32.EnumWindows(enum_windows_proc(callback), 0)
        return matches[0] if matches else None

    def _find_window_for_process_name(self, process_name: str) -> WindowInfo | None:
        user32 = ctypes.windll.user32
        normalized_process_name = process_name.lower()
        matches: list[WindowInfo] = []

        enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def callback(hwnd: int, lparam: int) -> bool:
            del lparam
            if not user32.IsWindowVisible(hwnd):
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True

            window = self._get_window_info(hwnd)
            if (window.process_name or "").lower() != normalized_process_name:
                return True

            matches.append(window)
            return False

        user32.EnumWindows(enum_windows_proc(callback), 0)
        return matches[0] if matches else None

    def _get_capturable_window_rect(
        self,
        window: WindowInfo,
    ) -> tuple[int, int, int, int]:
        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(window.handle)
        if user32.IsIconic(hwnd):
            raise ToolExecutionError(
                "The target window is minimized and cannot be captured.",
                result={
                    "saved": False,
                    "reason": "window_not_capturable",
                    "detail": "window_minimized",
                    "target_window": self._window_result(window),
                },
            )

        rect = self._get_visible_window_rect(hwnd)
        if rect is None:
            raise ToolExecutionError(
                "Could not read target window bounds.",
                result={
                    "saved": False,
                    "reason": "window_rect_failed",
                    "win32_error": _get_last_error(),
                    "target_window": self._window_result(window),
                },
            )

        left = int(rect.left)
        top = int(rect.top)
        right = int(rect.right)
        bottom = int(rect.bottom)
        if right <= left or bottom <= top:
            raise ToolExecutionError(
                "Target window bounds are empty.",
                result={
                    "saved": False,
                    "reason": "window_not_capturable",
                    "detail": "empty_window_rect",
                    "target_window": self._window_result(window),
                },
            )
        return (left, top, right, bottom)

    @staticmethod
    def _get_visible_window_rect(hwnd: wintypes.HWND) -> wintypes.RECT | None:
        rect = wintypes.RECT()
        dwm_result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(rect),
            ctypes.sizeof(rect),
        )
        if dwm_result == 0:
            return rect

        if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return rect
        return None

    @staticmethod
    def _grab_screen_image(bbox: tuple[int, int, int, int] | None = None):
        from PIL import ImageGrab

        kwargs: dict[str, Any] = {"all_screens": True}
        if bbox is not None:
            kwargs["bbox"] = bbox
            kwargs["include_layered_windows"] = True

        try:
            return ImageGrab.grab(**kwargs)
        except TypeError:
            kwargs.pop("include_layered_windows", None)
            return ImageGrab.grab(**kwargs)

    @staticmethod
    def _get_window_title(hwnd: Any) -> str:
        user32 = ctypes.windll.user32
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    @staticmethod
    def _get_window_process_id(hwnd: Any) -> int | None:
        window_pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        return int(window_pid.value) if window_pid.value else None

    @staticmethod
    def _get_process_executable_path(pid: int) -> str | None:
        kernel32 = ctypes.windll.kernel32
        process_query_limited_information = 0x1000
        process = kernel32.OpenProcess(
            process_query_limited_information,
            False,
            pid,
        )
        if not process:
            return None

        try:
            capacity = 32768
            buffer = ctypes.create_unicode_buffer(capacity)
            size = ctypes.c_ulong(capacity)
            if kernel32.QueryFullProcessImageNameW(
                process,
                0,
                buffer,
                ctypes.byref(size),
            ):
                return buffer.value
            return None
        finally:
            kernel32.CloseHandle(process)

    @staticmethod
    def _send_unicode_character(character: str) -> None:
        for unit in _utf16_code_units(character):
            key_down = _make_unicode_input(unit, key_up=False)
            key_up = _make_unicode_input(unit, key_up=True)
            events = (INPUT * 2)(key_down, key_up)
            sent = ctypes.windll.user32.SendInput(
                len(events),
                events,
                ctypes.sizeof(INPUT),
            )
            if sent != len(events):
                raise ToolExecutionError(
                    "SendInput failed while typing Unicode text.",
                    result={
                        "typed": False,
                        "reason": "send_input_failed",
                    },
                )

    def _paste_text_via_clipboard(self, text: str, target_window: WindowInfo) -> str:
        clipboard_text = _normalize_text_for_clipboard(text)
        previous_text = self._get_clipboard_unicode_text()
        had_previous_text = previous_text is not None
        input_method = "clipboard_paste"

        try:
            self._set_clipboard_unicode_text(clipboard_text)
            try:
                self._send_ctrl_v()
            except ToolExecutionError as exc:
                if exc.result.get("reason") != "send_input_failed":
                    raise
                self._send_wm_paste(target_window.handle)
                input_method = "wm_paste"
            time.sleep(0.1)
        except ToolExecutionError:
            raise
        except Exception as exc:
            raise ToolExecutionError(
                "Clipboard paste failed while typing text.",
                result={
                    "typed": False,
                    "reason": "clipboard_paste_failed",
                    "error_type": type(exc).__name__,
                },
            ) from exc
        finally:
            try:
                if had_previous_text:
                    self._set_clipboard_unicode_text(previous_text or "")
            except Exception:
                pass

        return input_method

    @staticmethod
    def _send_ctrl_v() -> None:
        events = (INPUT * 4)(
            _make_virtual_key_input(VK_CONTROL, key_up=False),
            _make_virtual_key_input(ord("V"), key_up=False),
            _make_virtual_key_input(ord("V"), key_up=True),
            _make_virtual_key_input(VK_CONTROL, key_up=True),
        )
        sent = ctypes.windll.user32.SendInput(
            len(events),
            events,
            ctypes.sizeof(INPUT),
        )
        if sent != len(events):
            raise ToolExecutionError(
                "SendInput failed while sending Ctrl+V.",
                result={
                    "typed": False,
                    "reason": "send_input_failed",
                    "sent_events": int(sent),
                    "expected_events": len(events),
                },
            )

    @staticmethod
    def _send_wm_paste(target_handle: int) -> None:
        paste_target = _get_focus_window_for_target(target_handle)
        hwnd = wintypes.HWND(paste_target or target_handle)
        wm_paste = 0x0302
        ctypes.windll.user32.SendMessageW(hwnd, wm_paste, 0, 0)

    @staticmethod
    def _get_clipboard_unicode_text() -> str | None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        cf_unicode_text = 13

        if not user32.IsClipboardFormatAvailable(cf_unicode_text):
            return None

        if not _open_clipboard_with_retry():
            return None

        try:
            handle = user32.GetClipboardData(cf_unicode_text)
            if not handle:
                return None

            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                return None

            try:
                return ctypes.wstring_at(pointer)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()

    @staticmethod
    def _set_clipboard_unicode_text(text: str) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        cf_unicode_text = 13
        gmem_moveable = 0x0002

        data = (text + "\0").encode("utf-16-le")
        handle = kernel32.GlobalAlloc(gmem_moveable, len(data))
        if not handle:
            raise ToolExecutionError(
                "Could not allocate clipboard memory.",
                result={
                    "typed": False,
                    "reason": "clipboard_alloc_failed",
                    "win32_error": _get_last_error(),
                },
            )

        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            kernel32.GlobalFree(handle)
            raise ToolExecutionError(
                "Could not lock clipboard memory.",
                result={
                    "typed": False,
                    "reason": "clipboard_lock_failed",
                    "win32_error": _get_last_error(),
                },
            )

        try:
            ctypes.memmove(pointer, data, len(data))
        finally:
            kernel32.GlobalUnlock(handle)

        if not _open_clipboard_with_retry():
            kernel32.GlobalFree(handle)
            raise ToolExecutionError(
                "Could not open clipboard for text input.",
                result={
                    "typed": False,
                    "reason": "clipboard_open_failed",
                    "win32_error": _get_last_error(),
                },
            )

        try:
            if not user32.EmptyClipboard():
                raise ToolExecutionError(
                    "Could not clear clipboard for text input.",
                    result={
                        "typed": False,
                        "reason": "clipboard_empty_failed",
                        "win32_error": _get_last_error(),
                    },
                )
            if not user32.SetClipboardData(cf_unicode_text, handle):
                raise ToolExecutionError(
                    "Could not set clipboard text for input.",
                    result={
                        "typed": False,
                        "reason": "clipboard_set_failed",
                        "win32_error": _get_last_error(),
                    },
                )
            handle = None
        finally:
            user32.CloseClipboard()
            if handle:
                kernel32.GlobalFree(handle)

    @staticmethod
    def _same_window(left: WindowInfo, right: WindowInfo) -> bool:
        if left.handle and right.handle:
            return left.handle == right.handle
        if left.process_id and right.process_id:
            return left.process_id == right.process_id
        return False

    @staticmethod
    def _matches_expected_window(window: WindowInfo, arguments: dict) -> bool:
        expected_handle = _optional_int(arguments.get("expected_window_handle"))
        expected_process_id = _optional_int(arguments.get("expected_process_id"))

        if expected_handle is not None:
            return window.handle == expected_handle
        if expected_process_id is not None:
            return window.process_id == expected_process_id
        return True

    @staticmethod
    def _focus_expected_window(arguments: dict) -> None:
        expected_handle = _optional_int(arguments.get("expected_window_handle"))
        if expected_handle is None:
            return

        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(expected_handle)
        if not user32.IsWindow(hwnd):
            return

        show_window_restore = 9
        user32.ShowWindow(hwnd, show_window_restore)

        foreground_hwnd = user32.GetForegroundWindow()
        current_thread_id = kernel32_get_current_thread_id()
        target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        foreground_thread_id = (
            user32.GetWindowThreadProcessId(foreground_hwnd, None)
            if foreground_hwnd
            else 0
        )

        attached_to_foreground = False
        attached_to_target = False
        try:
            if foreground_thread_id and foreground_thread_id != current_thread_id:
                attached_to_foreground = bool(
                    user32.AttachThreadInput(
                        current_thread_id,
                        foreground_thread_id,
                        True,
                    )
                )
            if target_thread_id and target_thread_id != current_thread_id:
                attached_to_target = bool(
                    user32.AttachThreadInput(
                        current_thread_id,
                        target_thread_id,
                        True,
                    )
                )

            user32.BringWindowToTop(hwnd)
            user32.SetActiveWindow(hwnd)
            user32.SetFocus(hwnd)
            user32.SetForegroundWindow(hwnd)
        finally:
            if attached_to_target:
                user32.AttachThreadInput(current_thread_id, target_thread_id, False)
            if attached_to_foreground:
                user32.AttachThreadInput(
                    current_thread_id,
                    foreground_thread_id,
                    False,
                )

        deadline = time.monotonic() + 0.8
        while time.monotonic() < deadline:
            if int(user32.GetForegroundWindow()) == expected_handle:
                return
            time.sleep(0.05)

    @staticmethod
    def _expected_window_result(arguments: dict) -> dict:
        return {
            "window_title": arguments.get("expected_window_title"),
            "window_handle": _optional_int(arguments.get("expected_window_handle")),
            "process_id": _optional_int(arguments.get("expected_process_id")),
            "process_name": arguments.get("expected_process_name"),
            "executable_path": arguments.get("expected_executable_path"),
        }

    @staticmethod
    def _window_result(window: WindowInfo) -> dict:
        return {
            "window_title": window.title,
            "window_handle": window.handle,
            "process_id": window.process_id,
            "process_name": window.process_name,
            "executable_path": window.executable_path,
        }


def _is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_capture_mode(value: Any) -> str:
    capture_mode = str(value or "all_screens").strip().lower()
    aliases = {
        "full_screen": "all_screens",
        "fullscreen": "all_screens",
        "all": "all_screens",
        "all_screen": "all_screens",
        "all_screens": "all_screens",
        "screen": "all_screens",
        "active": "active_window",
        "active_window": "active_window",
        "foreground": "active_window",
        "foreground_window": "active_window",
        "target": "target_window",
        "target_window": "target_window",
        "window": "target_window",
    }
    normalized = aliases.get(capture_mode)
    if normalized is None:
        raise ToolExecutionError(
            "Unsupported capture mode.",
            result={
                "saved": False,
                "reason": "unsupported_capture_mode",
                "capture_mode": capture_mode,
            },
        )
    return normalized


def _resolve_capture_output_path(arguments: dict, capture_mode: str) -> Path:
    output_path = str(arguments.get("output_path") or "").strip()
    if output_path:
        return Path(output_path)

    capture_dir = str(os.getenv("PROJECT_SENA_CAPTURE_DIR") or "").strip()
    if capture_dir:
        base_dir = Path(capture_dir)
    else:
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            base_dir = Path(local_app_data) / "ProjectSENA" / "captures"
        else:
            base_dir = Path.home() / ".project-sena" / "captures"

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return base_dir / f"capture_{timestamp}_{capture_mode}_{uuid4().hex[:8]}.png"


def _cleanup_capture_directory(
    capture_dir: Path,
    protected_paths: set[Path] | None = None,
) -> dict:
    summary = {
        "enabled": True,
        "deleted_files": 0,
        "deleted_bytes": 0,
        "error_message": None,
    }
    try:
        retention_days = _read_int_env(
            "PROJECT_SENA_CAPTURE_RETENTION_DAYS",
            DEFAULT_CAPTURE_RETENTION_DAYS,
            minimum=0,
        )
        max_bytes = _read_int_env(
            "PROJECT_SENA_CAPTURE_MAX_BYTES",
            DEFAULT_CAPTURE_MAX_BYTES,
            minimum=0,
        )
        max_files = _read_int_env(
            "PROJECT_SENA_CAPTURE_MAX_FILES",
            DEFAULT_CAPTURE_MAX_FILES,
            minimum=0,
        )
        now = time.time()
        candidates = _list_cleanup_candidates(capture_dir, protected_paths or set())

        if retention_days > 0:
            cutoff = now - (retention_days * 24 * 60 * 60)
            expired = [item for item in candidates if item["mtime"] < cutoff]
            _delete_capture_candidates(expired, summary)
            expired_paths = {item["path"] for item in expired}
            candidates = [
                item for item in candidates if item["path"] not in expired_paths
            ]

        candidates = [item for item in candidates if Path(item["path"]).exists()]
        total_bytes = sum(int(item["size"]) for item in candidates)
        candidates.sort(key=lambda item: float(item["mtime"]))

        while candidates and (
            (max_files > 0 and len(candidates) > max_files)
            or (max_bytes > 0 and total_bytes > max_bytes)
        ):
            item = candidates.pop(0)
            deleted_bytes = _delete_capture_candidate(item, summary)
            total_bytes -= deleted_bytes
    except Exception as exc:  # pragma: no cover - defensive cleanup boundary
        summary["error_message"] = f"{type(exc).__name__}: {exc}"

    return summary


def _list_cleanup_candidates(
    capture_dir: Path,
    protected_paths: set[Path],
) -> list[dict]:
    if not capture_dir.exists():
        return []

    normalized_protected_paths = {
        _normalize_path_for_compare(path) for path in protected_paths
    }
    candidates: list[dict] = []
    for path in capture_dir.rglob("capture_*.png"):
        if _normalize_path_for_compare(path) in normalized_protected_paths:
            continue
        if not path.is_file() or _is_preserved_capture(path, capture_dir):
            continue

        try:
            stat = path.stat()
        except OSError:
            continue

        candidates.append(
            {
                "path": path,
                "mtime": stat.st_mtime,
                "size": stat.st_size,
            }
        )
    return candidates


def _normalize_path_for_compare(path: Path) -> str:
    try:
        return str(path.resolve()).lower()
    except OSError:
        return str(path.absolute()).lower()


def _is_preserved_capture(path: Path, capture_dir: Path) -> bool:
    try:
        relative = path.relative_to(capture_dir)
    except ValueError:
        return True

    if relative.parts and relative.parts[0].lower() == "keep":
        return True
    return ".keep" in path.name


def _delete_capture_candidates(candidates: list[dict], summary: dict) -> None:
    for item in sorted(candidates, key=lambda candidate: float(candidate["mtime"])):
        _delete_capture_candidate(item, summary)


def _delete_capture_candidate(item: dict, summary: dict) -> int:
    path = Path(item["path"])
    size = int(item["size"])
    try:
        path.unlink()
    except FileNotFoundError:
        return 0
    except OSError as exc:
        previous = summary.get("error_message")
        message = f"{type(exc).__name__}: {exc}"
        summary["error_message"] = (
            message if not previous else f"{previous}; {message}"
        )
        return 0

    summary["deleted_files"] = int(summary["deleted_files"]) + 1
    summary["deleted_bytes"] = int(summary["deleted_bytes"]) + size
    return size


def _read_int_env(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default

    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


def kernel32_get_current_thread_id() -> int:
    return int(ctypes.windll.kernel32.GetCurrentThreadId())


def _open_clipboard_with_retry(
    timeout_seconds: float = 1.0,
    poll_interval_seconds: float = 0.05,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if ctypes.windll.user32.OpenClipboard(None):
            return True
        time.sleep(poll_interval_seconds)
    return bool(ctypes.windll.user32.OpenClipboard(None))


def _get_last_error() -> int:
    return int(ctypes.windll.kernel32.GetLastError())


def _get_focus_window_for_target(target_handle: int) -> int | None:
    user32 = ctypes.windll.user32
    target_hwnd = wintypes.HWND(target_handle)
    current_thread_id = kernel32_get_current_thread_id()
    target_thread_id = user32.GetWindowThreadProcessId(target_hwnd, None)
    attached = False

    try:
        if target_thread_id and target_thread_id != current_thread_id:
            attached = bool(
                user32.AttachThreadInput(
                    current_thread_id,
                    target_thread_id,
                    True,
                )
            )

        focus_hwnd = user32.GetFocus()
        if focus_hwnd and (
            int(focus_hwnd) == target_handle
            or user32.IsChild(target_hwnd, wintypes.HWND(focus_hwnd))
        ):
            return int(focus_hwnd)
        return target_handle
    finally:
        if attached:
            user32.AttachThreadInput(current_thread_id, target_thread_id, False)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _has_expected_window(arguments: dict) -> bool:
    return (
        _optional_int(arguments.get("expected_window_handle")) is not None
        or _optional_int(arguments.get("expected_process_id")) is not None
    )


def _normalize_text_for_clipboard(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")


def _utf16_code_units(character: str) -> list[int]:
    data = character.encode("utf-16-le")
    return [
        int.from_bytes(data[index : index + 2], byteorder="little")
        for index in range(0, len(data), 2)
    ]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_CONTROL = 0x11


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


def _make_unicode_input(unit: int, key_up: bool) -> INPUT:
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if key_up else 0)
    return INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(
            wVk=0,
            wScan=unit,
            dwFlags=flags,
            time=0,
            dwExtraInfo=0,
        ),
    )


def _make_virtual_key_input(virtual_key: int, key_up: bool) -> INPUT:
    return INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(
            wVk=virtual_key,
            wScan=0,
            dwFlags=KEYEVENTF_KEYUP if key_up else 0,
            time=0,
            dwExtraInfo=0,
        ),
    )
