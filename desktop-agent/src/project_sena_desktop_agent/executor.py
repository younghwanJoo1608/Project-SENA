"""Desktop-local tool execution primitives."""

from __future__ import annotations

import ctypes
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


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


class DesktopToolExecutor:
    """Runs a narrow set of desktop-local tools."""

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

    def _open_app(self, arguments: dict) -> ToolExecutionOutcome:
        app_name = str(arguments.get("app_name", "")).strip().lower()
        app_map = {
            "notepad": "notepad.exe",
            "notepad.exe": "notepad.exe",
        }
        executable = app_map.get(app_name)
        if executable is None:
            raise ToolExecutionError(f"Unsupported application: {app_name}")

        process = subprocess.Popen([executable])
        base_result = {
            "launched": True,
            "app_name": app_name,
            "pid": process.pid,
        }

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

        return ToolExecutionOutcome(
            result=base_result
        )

    def _get_active_window(self, arguments: dict) -> ToolExecutionOutcome:
        _ = arguments
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd == 0:
            raise ToolExecutionError("No active foreground window was detected.")

        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)

        return ToolExecutionOutcome(
            result={
                "window_title": buffer.value,
                "window_handle": int(hwnd),
            }
        )

    def _capture_screen(self, arguments: dict) -> ToolExecutionOutcome:
        output_path = str(arguments.get("output_path", "")).strip()
        if not output_path:
            raise ToolExecutionError("capture_screen requires an output_path.")

        from PIL import ImageGrab

        image = ImageGrab.grab(all_screens=True)
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_file)

        return ToolExecutionOutcome(
            result={
                "saved": True,
                "output_path": str(output_file),
                "width": image.width,
                "height": image.height,
            }
        )

    def _type_text(self, arguments: dict) -> ToolExecutionOutcome:
        text = str(arguments.get("text", ""))
        if not text:
            raise ToolExecutionError("type_text requires a non-empty text argument.")

        try:
            import pyautogui
        except ImportError as exc:
            raise ToolExecutionError(
                "type_text requires pyautogui to be installed."
            ) from exc

        pyautogui.write(text)
        return ToolExecutionOutcome(result={"typed": True, "length": len(text)})

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

            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            matches.append(WindowInfo(handle=int(hwnd), title=buffer.value))
            return False

        user32.EnumWindows(enum_windows_proc(callback), 0)
        return matches[0] if matches else None
