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
        lambda pid: WindowInfo(
            handle=1001,
            title="Untitled - Notepad",
            process_id=4321,
            process_name="notepad.exe",
            executable_path="C:\\Windows\\System32\\notepad.exe",
        ),
    )

    outcome = executor.execute("open_app", {"app_name": "notepad"})

    assert outcome.result["process_alive"] is True
    assert outcome.result["window_detected"] is True
    assert outcome.result["window_handle"] == 1001
    assert outcome.result["window_title"] == "Untitled - Notepad"
    assert outcome.result["process_name"] == "notepad.exe"


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


def test_type_text_sends_unicode_text_to_expected_foreground_window(monkeypatch) -> None:
    executor = DesktopToolExecutor()
    window = WindowInfo(
        handle=1001,
        title="Untitled - Notepad",
        process_id=4321,
        process_name="notepad.exe",
        executable_path="C:\\Windows\\System32\\notepad.exe",
    )
    pasted_texts: list[str] = []

    monkeypatch.setattr(executor, "_get_foreground_window_info", lambda: window)
    monkeypatch.setattr(executor, "_focus_expected_window", lambda arguments: None)
    monkeypatch.setattr(
        executor,
        "_paste_text_via_clipboard",
        lambda text, target_window: pasted_texts.append(text) or "clipboard_paste",
    )

    outcome = executor.execute(
        "type_text",
        {
            "text": "안녕\nSENA",
            "expected_window_handle": 1001,
            "expected_process_id": 4321,
        },
    )

    assert pasted_texts == ["안녕\nSENA"]
    assert outcome.result["typed"] is True
    assert outcome.result["length"] == 7
    assert outcome.result["input_method"] == "clipboard_paste"
    assert outcome.result["target_window"]["process_name"] == "notepad.exe"


def test_type_text_falls_back_to_wm_paste_when_send_input_fails(monkeypatch) -> None:
    executor = DesktopToolExecutor()
    window = WindowInfo(
        handle=1001,
        title="Untitled - Notepad",
        process_id=4321,
        process_name="notepad.exe",
        executable_path="C:\\Windows\\System32\\notepad.exe",
    )
    pasted_targets: list[int] = []

    monkeypatch.setattr(executor, "_get_foreground_window_info", lambda: window)
    monkeypatch.setattr(executor, "_focus_expected_window", lambda arguments: None)
    monkeypatch.setattr(executor, "_get_clipboard_unicode_text", lambda: None)
    monkeypatch.setattr(executor, "_set_clipboard_unicode_text", lambda text: None)

    def fail_ctrl_v() -> None:
        raise ToolExecutionError(
            "SendInput failed while sending Ctrl+V.",
            result={"typed": False, "reason": "send_input_failed"},
        )

    monkeypatch.setattr(executor, "_send_ctrl_v", fail_ctrl_v)
    monkeypatch.setattr(
        executor,
        "_send_wm_paste",
        lambda target_handle: pasted_targets.append(target_handle),
    )

    outcome = executor.execute(
        "type_text",
        {
            "text": "안녕",
            "expected_window_handle": 1001,
            "expected_process_id": 4321,
        },
    )

    assert pasted_targets == [1001]
    assert outcome.result["typed"] is True
    assert outcome.result["input_method"] == "wm_paste"


def test_type_text_refuses_when_foreground_window_changed(monkeypatch) -> None:
    executor = DesktopToolExecutor()
    current_window = WindowInfo(
        handle=2002,
        title="Browser",
        process_id=9876,
        process_name="chrome.exe",
    )

    monkeypatch.setattr(executor, "_get_foreground_window_info", lambda: current_window)
    monkeypatch.setattr(executor, "_focus_expected_window", lambda arguments: None)

    try:
        executor.execute(
            "type_text",
            {
                "text": "안녕",
                "expected_window_handle": 1001,
                "expected_process_id": 4321,
            },
        )
    except ToolExecutionError as exc:
        assert "Active window changed before typing" in str(exc)
        assert exc.result["typed"] is False
        assert exc.result["reason"] == "active_window_changed_before_typing"
        assert exc.result["current_window"]["process_name"] == "chrome.exe"
    else:
        raise AssertionError("Expected changed foreground window to fail.")
