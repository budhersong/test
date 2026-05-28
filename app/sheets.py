import os
import logging
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/google-service-account.json")
SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID", "")

SHEET_HEADERS = [
    "수집일시", "수집유형", "키워드/채널명", "제목", "URL",
    "작성자", "작성일", "본문내용"
]


def _get_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _ensure_sheet_headers(service, spreadsheet_id: str, sheet_name: str = "블로그수집"):
    """시트가 없으면 생성하고 헤더가 없으면 추가"""
    try:
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        existing_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]

        if sheet_name not in existing_titles:
            body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
            service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            logger.info("시트 생성: %s", sheet_name)

        # 첫 번째 행 확인
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:H1")
            .execute()
        )
        if not result.get("values"):
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": [SHEET_HEADERS]},
            ).execute()
            logger.info("헤더 행 추가 완료")

    except HttpError as e:
        logger.error("시트 초기화 오류: %s", e)
        raise


def append_posts_to_sheet(posts: list[dict], sheet_name: str = "블로그수집") -> int:
    """포스트 목록을 Google Sheets에 추가, 추가된 행 수 반환"""
    if not SPREADSHEET_ID:
        raise ValueError("GOOGLE_SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")
    if not posts:
        return 0

    service = _get_service()
    _ensure_sheet_headers(service, SPREADSHEET_ID, sheet_name)

    rows = []
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for p in posts:
        content = p.get("content", "")
        # 셀 최대 50,000자 제한
        if len(content) > 50000:
            content = content[:50000] + "... (이하 생략)"
        rows.append([
            now_str,
            p.get("source_type", ""),
            p.get("source_value", ""),
            p.get("title", ""),
            p.get("post_url", ""),
            p.get("author", ""),
            p.get("post_date", ""),
            content,
        ])

    try:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()
        logger.info("Google Sheets 업로드 완료: %d행", len(rows))
        return len(rows)
    except HttpError as e:
        logger.error("Google Sheets 업로드 오류: %s", e)
        raise


def get_spreadsheet_url() -> Optional[str]:
    if SPREADSHEET_ID:
        return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
    return None
