from project_sena_desktop_agent.executor import (
    DesktopToolExecutor,
    TEST_FAILURE_APP_NAME,
    ToolExecutionError,
    WindowInfo,
)


class FakeProcess:
    def __init__(self, pid: int = 4321, returncode: int | None = None) -> None:
        self.pid = pid
        self._returncode = returncode

    def poll(self) -> int | None:
        return self._returncode


def test_open_app_reports_window_metadata_when_process_and_window_exist(monkeypatch) -> None:
    executor = DesktopToolExecutor()

    monkeypatch.setattr(
        "project_sena_desktop_agent.executor.subprocess.Popen",
        lambda args: FakeProcess(pid=4321),
    )
    monkeypatch.setattr(executor, "_wait_for_process_start", lambda process: True)
    monkeypatch.setattr(
        executor,
        "_wait_for_window_for_pid",
        lambda pid: type("Window", (), {"handle": 1001, "title": "Untitled - Notepad"})(),
    )

    outcome = executor.execute("open_app", {"app_name": "notepad"})

    assert outcome.result["process_alive"] is True
    assert outcome.result["window_detected"] is True
    assert outcome.result["window_handle"] == 1001
    assert outcome.result["window_title"] == "Untitled - Notepad"


def test_open_app_raises_error_when_window_is_not_detected(monkeypatch) -> None:
    executor = DesktopToolExecutor()

    monkeypatch.setattr(
        "project_sena_desktop_agent.executor.subprocess.Popen",
        lambda args: FakeProcess(pid=4321),
    )
    monkeypatch.setattr(executor, "_wait_for_process_start", lambda process: True)
    monkeypatch.setattr(executor, "_wait_for_window_for_pid", lambda pid: None)

    outcome = executor.execute("open_app", {"app_name": "notepad"})

    assert outcome.result["process_alive"] is True
    assert outcome.result["window_detected"] is False


def test_open_app_failure_injection_is_disabled_by_default() -> None:
    executor = DesktopToolExecutor(failure_injection_enabled=False)

    try:
        executor.execute("open_app", {"app_name": TEST_FAILURE_APP_NAME})
    except ToolExecutionError as exc:
        assert "Unsupported application" in str(exc)
        assert exc.result == {}
    else:
        raise AssertionError("Expected test failure app to be rejected.")


def test_open_app_failure_injection_returns_structured_error() -> None:
    executor = DesktopToolExecutor(failure_injection_enabled=True)

    try:
        executor.execute("open_app", {"app_name": TEST_FAILURE_APP_NAME})
    except ToolExecutionError as exc:
        assert "Injected open_app failure" in str(exc)
        assert exc.result == {
            "launched": False,
            "app_name": TEST_FAILURE_APP_NAME,
            "failure_injected": True,
        }
    else:
        raise AssertionError("Expected injected failure.")


def test_get_active_window_returns_window_and_process_metadata(monkeypatch) -> None:
    executor = DesktopToolExecutor()

    monkeypatch.setattr(
        executor,
        "_get_foreground_window_info",
        lambda: WindowInfo(
            handle=1001,
            title="Project-SENA - Unity",
            process_id=4321,
            process_name="Unity.exe",
            executable_path="C:\\Program Files\\Unity\\Unity.exe",
        ),
    )

    outcome = executor.execute("get_active_window", {})

    assert outcome.result == {
        "window_title": "Project-SENA - Unity",
        "window_handle": 1001,
        "process_id": 4321,
        "process_name": "Unity.exe",
        "executable_path": "C:\\Program Files\\Unity\\Unity.exe",
    }


def test_get_active_window_raises_error_when_no_foreground_window(monkeypatch) -> None:
    executor = DesktopToolExecutor()

    monkeypatch.setattr(executor, "_get_foreground_window_info", lambda: None)

    try:
        executor.execute("get_active_window", {})
    except ToolExecutionError as exc:
        assert "No active foreground window" in str(exc)
    else:
        raise AssertionError("Expected missing foreground window to fail.")
