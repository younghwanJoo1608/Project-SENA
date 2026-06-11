# 캡처 파일 관리 정책

Project-SENA의 `capture_screen`은 사용자의 실제 데스크톱 화면을 PNG 파일로 저장한다. 캡처 파일은 Vision 분석, 디버깅, 회귀 테스트에는 유용하지만 개인정보와 민감 정보가 포함될 수 있으므로 짧게 보관하고 쉽게 삭제할 수 있어야 한다.

## 기본 원칙

- 캡처는 기본적으로 클립보드가 아니라 파일로 저장한다.
- 캡처 파일은 사용자의 로컬 PC에만 저장한다.
- 사용자가 명시적으로 보존하지 않은 캡처는 임시 데이터로 취급한다.
- 캡처 파일 경로는 tool result에 반환하되, 원격 저장소에 커밋하지 않는다.
- 캡처 파일은 Vision 분석에 필요한 기간만 보관하고 자동 정리할 수 있어야 한다.

## 저장 위치

기본 저장 위치:

```text
%LOCALAPPDATA%\ProjectSENA\captures
```

환경변수로 저장 위치를 바꿀 수 있다.

```powershell
$env:PROJECT_SENA_CAPTURE_DIR = "D:\ProjectSENA\captures"
```

저장 파일명 형식:

```text
capture_YYYYMMDDTHHMMSSZ_{capture_mode}_{random}.png
```

예:

```text
capture_20260610T125400Z_active_window_82d14f39.png
```

## 보관 정책

Phase 1.5 기본 정책:

- 최대 보관 기간: 7일
- 최대 총 용량: 1GB
- 최대 파일 개수: 500개
- 정리 기준: 오래된 파일부터 삭제

위 세 조건 중 하나라도 초과하면 오래된 캡처부터 삭제한다.

## 수동 보존 정책

사용자가 장기 보존하고 싶은 캡처는 자동 정리 대상에서 제외할 수 있어야 한다.

권장 방식:

- `captures/keep/` 하위 폴더로 이동한 파일은 자동 삭제하지 않는다.
- 또는 파일명에 `.keep` marker를 붙인 파일은 자동 삭제하지 않는다.

Phase 1.5에서는 UI 보존 기능을 만들지 않고, 필요할 때 사용자가 파일을 직접 이동하는 방식을 허용한다.

## 개인정보 취급

캡처에는 다음 정보가 포함될 수 있다.

- 브라우저 탭, 문서, 메신저, 파일 탐색기 내용
- 계정 이름, 파일 경로, 알림 내용
- 비밀번호 입력창, 토큰, API key, 개인 문서

따라서 `capture_screen`은 항상 사용자 승인을 요구한다. `approval_policy: "auto_allowed"`가 들어오더라도 desktop-agent 정책은 승인을 요구해야 한다.

## 로그 정책

로그와 tool result에는 아래 정보까지만 남긴다.

- `output_path`
- `width`
- `height`
- `capture_mode`
- `target_window` metadata
- `capture_rect`

로그에 이미지 base64, OCR 결과, 전체 이미지 내용을 직접 남기지 않는다.

## 자동 정리 동작

Phase 1.5에서는 desktop-agent가 `capture_screen` 저장 직후 같은 capture directory를 자동 정리한다.

정리 순서:

1. `keep/` 하위 폴더와 `.keep` marker 파일은 제외한다.
2. 7일 초과 파일을 오래된 순서로 삭제한다.
3. 총 용량 또는 파일 개수 제한을 초과하면 오래된 파일부터 추가 삭제한다.
4. 삭제 결과는 tool result의 `cleanup` 요약으로만 남긴다.

정리 실패는 캡처 실패로 처리하지 않는다. 캡처 파일 저장이 성공했다면 tool result는 성공으로 반환하고, 정리 실패 정보는 `cleanup.error_message`에만 남긴다.

`cleanup` 요약 예:

```json
{
  "enabled": true,
  "deleted_files": 3,
  "deleted_bytes": 1820342,
  "error_message": null
}
```

## 설정 후보

환경변수:

```text
PROJECT_SENA_CAPTURE_DIR
PROJECT_SENA_CAPTURE_RETENTION_DAYS
PROJECT_SENA_CAPTURE_MAX_BYTES
PROJECT_SENA_CAPTURE_MAX_FILES
```

기본값:

```text
PROJECT_SENA_CAPTURE_RETENTION_DAYS=7
PROJECT_SENA_CAPTURE_MAX_BYTES=1073741824
PROJECT_SENA_CAPTURE_MAX_FILES=500
```

## Phase 2 연결

Vision 분석이 붙으면 캡처 파일은 다음 흐름으로 사용된다.

```text
capture_screen -> PNG file -> vision adapter -> summarized screen context -> conversation state
```

Vision adapter는 원본 이미지를 장기 보관하지 않고, 필요한 경우 요약된 screen context만 session memory에 남긴다. 원본 이미지를 memory/RAG에 자동 저장하는 기능은 별도 승인 정책을 만든 뒤 추가한다.
