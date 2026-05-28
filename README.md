# 네이버 블로그 리뷰 크롤러

네이버 블로그 리뷰를 키워드/채널 단위로 매주 자동 수집해 Google Sheets에 누적 저장하는 웹 서비스입니다.

## 기능

- 키워드 검색 크롤링: 네이버 검색 API + 본문 전체 스크래핑
- 특정 블로그 채널 크롤링: RSS 피드 파싱 + 본문 스크래핑
- 중복 방지: URL 기준 중복 체크, 신규 포스트만 누적
- 매주 자동 실행: APScheduler (기본: 매주 월요일 오전 9시)
- Google Sheets 자동 업로드
- 웹 대시보드: 키워드 관리, 수집 이력, 데이터 검색

## 사전 준비

### 1. 네이버 개발자 API 키 발급

1. https://developers.naver.com → 애플리케이션 등록
2. 사용 API: **검색** 선택
3. Client ID, Client Secret 복사

### 2. Google Sheets 서비스 계정 설정

1. https://console.cloud.google.com → 새 프로젝트 생성
2. **Google Sheets API** 활성화
3. IAM 및 관리자 → 서비스 계정 생성 → JSON 키 다운로드
4. `credentials/` 폴더 생성 후 JSON 파일 저장
5. Google Sheets 스프레드시트 생성 → 서비스 계정 이메일을 **편집자**로 공유
6. 스프레드시트 ID 복사 (URL의 `/d/` 다음 부분)

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 값 입력
```

## 실행

```bash
pip install -r requirements.txt
python main.py
```

브라우저에서 http://localhost:8000 접속

## 구조

```
main.py              # FastAPI 앱 진입점 + 라우터
app/
  crawler.py         # 네이버 블로그 크롤링 로직
  sheets.py          # Google Sheets 연동
  scheduler.py       # 주간 스케줄러 (APScheduler)
  crawl_service.py   # 크롤링 오케스트레이션 + 중복 제거
  database.py        # SQLite 모델 (SQLAlchemy)
templates/           # Jinja2 HTML 템플릿
static/              # CSS, JS
credentials/         # Google 서비스 계정 JSON (gitignore)
```

## Google Sheets 컬럼 구조

| 수집일시 | 수집유형 | 키워드/채널명 | 제목 | URL | 작성자 | 작성일 | 본문내용 |
|---------|---------|-------------|------|-----|-------|-------|---------|

## 스케줄 변경

`.env`에서 조정:

```env
SCHEDULE_DAY_OF_WEEK=mon   # mon/tue/wed/thu/fri/sat/sun
SCHEDULE_HOUR=9
SCHEDULE_MINUTE=0
```
