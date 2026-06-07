"""Desktop-local tool execution primitives."""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TEST_FAILURE_APP_NAME = "__project_sena_missing_app__"
TEST_FAILURE_ENV_VAR = "PROJECT_SENA_ENABLE_FAILURE_INJECTION"


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


def _is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
