from project_sena_desktop_agent.executor import (
    DesktopToolExecutor,
    ToolExecutionError,
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
