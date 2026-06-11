import os

from project_sena_desktop_agent.executor import (
    DesktopToolExecutor,
    TEST_FAILURE_APP_NAME,
    ToolExecutionError,
    WindowInfo,
    _cleanup_capture_directory,
)


class FakeProcess:
    def __init__(self, pid: int = 4321, returncode: int | None = None) -> None:
        self.pid = pid
        self._returncode = returncode

    def poll(self) -> int | None:
        return self._returncode


class FakeImage:
    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        bbox: tuple[int, int, int, int] | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.bbox = bbox
        self.saved_path: str | None = None

    def save(self, output_file) -> None:
        self.saved_path = str(output_file)


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


def test_capture_screen_saves_all_screens_to_default_path(monkeypatch, tmp_path) -> None:
    executor = DesktopToolExecutor()
    image = FakeImage(width=3840, height=2160)
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_DIR", str(tmp_path))
    monkeypatch.setattr(executor, "_grab_screen_image", lambda bbox=None: image)

    outcome = executor.execute("capture_screen", {"capture_mode": "all_screens"})

    assert outcome.result["saved"] is True
    assert outcome.result["capture_mode"] == "all_screens"
    assert outcome.result["width"] == 3840
    assert outcome.result["height"] == 2160
    assert outcome.result["output_path"].startswith(str(tmp_path))
    assert outcome.result["output_path"].endswith(".png")
    assert image.saved_path == outcome.result["output_path"]
    assert outcome.result["cleanup"]["enabled"] is True
    assert outcome.result["cleanup"]["deleted_files"] == 0


def test_capture_screen_crops_active_window(monkeypatch, tmp_path) -> None:
    executor = DesktopToolExecutor()
    window = WindowInfo(
        handle=1001,
        title="Project-SENA - Unity",
        process_id=4321,
        process_name="Unity.exe",
    )
    captured_bboxes: list[tuple[int, int, int, int] | None] = []

    monkeypatch.setenv("PROJECT_SENA_CAPTURE_DIR", str(tmp_path))
    monkeypatch.setattr(executor, "_get_foreground_window_info", lambda: window)
    monkeypatch.setattr(
        executor,
        "_get_capturable_window_rect",
        lambda target_window: (10, 20, 810, 620),
    )

    def fake_grab(bbox=None):
        captured_bboxes.append(bbox)
        return FakeImage(width=800, height=600, bbox=bbox)

    monkeypatch.setattr(executor, "_grab_screen_image", fake_grab)

    outcome = executor.execute("capture_screen", {"capture_mode": "active_window"})

    assert captured_bboxes == [(10, 20, 810, 620)]
    assert outcome.result["capture_mode"] == "active_window"
    assert outcome.result["capture_rect"] == {
        "left": 10,
        "top": 20,
        "right": 810,
        "bottom": 620,
    }
    assert outcome.result["target_window"]["process_name"] == "Unity.exe"


def test_capture_screen_crops_target_app_window(monkeypatch, tmp_path) -> None:
    executor = DesktopToolExecutor()
    window = WindowInfo(
        handle=2002,
        title="Untitled - Notepad",
        process_id=8765,
        process_name="notepad.exe",
    )
    captured_bboxes: list[tuple[int, int, int, int] | None] = []

    monkeypatch.setenv("PROJECT_SENA_CAPTURE_DIR", str(tmp_path))
    monkeypatch.setattr(executor, "resolve_window_target", lambda arguments: window)
    monkeypatch.setattr(
        executor,
        "_get_capturable_window_rect",
        lambda target_window: (100, 150, 700, 550),
    )

    def fake_grab(bbox=None):
        captured_bboxes.append(bbox)
        return FakeImage(width=600, height=400, bbox=bbox)

    monkeypatch.setattr(executor, "_grab_screen_image", fake_grab)

    outcome = executor.execute(
        "capture_screen",
        {"capture_mode": "target_window", "target_app": "notepad"},
    )

    assert captured_bboxes == [(100, 150, 700, 550)]
    assert outcome.result["capture_mode"] == "target_window"
    assert outcome.result["width"] == 600
    assert outcome.result["target_window"]["window_handle"] == 2002


def test_capture_cleanup_deletes_expired_files(monkeypatch, tmp_path) -> None:
    old_file = tmp_path / "capture_20260101T000000Z_all_screens_old.png"
    keep_file = tmp_path / "capture_20260101T000000Z_all_screens_keep.keep.png"
    old_file.write_bytes(b"old")
    keep_file.write_bytes(b"keep")
    old_mtime = 1_700_000_000
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_RETENTION_DAYS", "7")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_BYTES", "0")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_FILES", "0")
    monkeypatch.setattr(
        "project_sena_desktop_agent.executor.time.time",
        lambda: old_mtime + 10 * 24 * 60 * 60,
    )
    for path in (old_file, keep_file):
        path.touch()
        os.utime(path, (old_mtime, old_mtime))

    summary = _cleanup_capture_directory(tmp_path)

    assert summary["deleted_files"] == 1
    assert summary["deleted_bytes"] == 3
    assert not old_file.exists()
    assert keep_file.exists()


def test_capture_cleanup_enforces_file_limit(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_RETENTION_DAYS", "0")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_BYTES", "0")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_FILES", "2")

    files = []
    for index in range(3):
        path = tmp_path / f"capture_20260101T00000{index}Z_all_screens_{index}.png"
        path.write_bytes(bytes([index]))
        os.utime(path, (1_700_000_000 + index, 1_700_000_000 + index))
        files.append(path)

    summary = _cleanup_capture_directory(tmp_path)

    assert summary["deleted_files"] == 1
    assert not files[0].exists()
    assert files[1].exists()
    assert files[2].exists()


def test_capture_cleanup_enforces_size_limit(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_RETENTION_DAYS", "0")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_BYTES", "5")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_FILES", "0")

    first = tmp_path / "capture_20260101T000000Z_all_screens_first.png"
    second = tmp_path / "capture_20260101T000001Z_all_screens_second.png"
    first.write_bytes(b"1234")
    second.write_bytes(b"5678")
    os.utime(first, (1_700_000_000, 1_700_000_000))
    os.utime(second, (1_700_000_001, 1_700_000_001))

    summary = _cleanup_capture_directory(tmp_path)

    assert summary["deleted_files"] == 1
    assert summary["deleted_bytes"] == 4
    assert not first.exists()
    assert second.exists()


def test_capture_cleanup_keeps_protected_current_capture(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_RETENTION_DAYS", "0")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_BYTES", "1")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_FILES", "1")

    old_file = tmp_path / "capture_20260101T000000Z_all_screens_old.png"
    current_file = tmp_path / "capture_20260101T000001Z_all_screens_current.png"
    old_file.write_bytes(b"old")
    current_file.write_bytes(b"current")
    os.utime(old_file, (1_700_000_000, 1_700_000_000))
    os.utime(current_file, (1_700_000_001, 1_700_000_001))

    summary = _cleanup_capture_directory(
        tmp_path,
        protected_paths={current_file},
    )

    assert summary["deleted_files"] == 1
    assert not old_file.exists()
    assert current_file.exists()


def test_capture_cleanup_skips_keep_directory(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_RETENTION_DAYS", "1")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_BYTES", "1")
    monkeypatch.setenv("PROJECT_SENA_CAPTURE_MAX_FILES", "1")
    keep_dir = tmp_path / "keep"
    keep_dir.mkdir()
    keep_file = keep_dir / "capture_20260101T000000Z_all_screens_keep.png"
    keep_file.write_bytes(b"keep")
    os.utime(keep_file, (1_700_000_000, 1_700_000_000))
    monkeypatch.setattr(
        "project_sena_desktop_agent.executor.time.time",
        lambda: 1_700_000_000 + 10 * 24 * 60 * 60,
    )

    summary = _cleanup_capture_directory(tmp_path)

    assert summary["deleted_files"] == 0
    assert keep_file.exists()


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
