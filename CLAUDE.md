# CLAUDE.md

## Repository Overview

**네이버 플레이스 리뷰 분석기** — 네이버 플레이스 URL을 입력하면 고객 리뷰를 크롤링하여 감성 분석, 카테고리별 평가, 월별 추이, 경영 인사이트를 도출하는 웹서비스입니다.

- Repository: `budhersong/test`
- Language: Python 3.10+
- Framework: FastAPI + vanilla HTML/CSS/JS (Chart.js)

## Project Structure

```
.
├── CLAUDE.md              # AI assistant guide (this file)
├── README.md              # Project readme
├── requirements.txt       # Python 의존성
└── app/
    ├── __init__.py
    ├── main.py            # FastAPI 앱 진입점, 라우트 정의
    ├── crawler.py         # 네이버 플레이스 GraphQL 크롤러
    ├── analyzer.py        # 한국어 감성 분석 + 경영지표 도출
    ├── models.py          # Pydantic 요청/응답 모델
    └── static/
        ├── index.html     # SPA 대시보드 UI
        ├── style.css      # 전체 스타일시트
        └── app.js         # 프론트엔드 로직, 차트 렌더링
```

## Development Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

외부 API 키나 환경 변수는 필요하지 않습니다.

## Common Commands

```bash
# 개발 서버 실행 (핫 리로드)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

실행 후 `http://localhost:8000` 에서 접속할 수 있습니다.

## Key Modules

### `app/crawler.py`
- 네이버 플레이스 GraphQL API (`pcmap-api.place.naver.com/place/graphql`)를 통해 리뷰 크롤링
- 다양한 URL 형식 지원: `m.place.naver.com`, `map.naver.com`, `naver.me` 단축 URL, 숫자 ID 직접 입력
- 페이지네이션 처리 (기본 50건씩, 최대 10페이지)

### `app/analyzer.py`
- 키워드 기반 한국어 감성 분석 (긍정/부정/중립)
- 6개 경영 카테고리 분류: 맛/음식 품질, 양/가성비, 서비스, 청결/위생, 분위기/인테리어, 재방문 의향
- 월별 추이 분석, 별점 분포, 사장님 답글 비율 산출
- 경영 개선사항 자동 도출 (우선순위: high/medium/low)

### `app/main.py`
- `POST /api/analyze` — URL 기반 분석 엔드포인트
- `GET /` — 대시보드 HTML 서빙
- `GET /health` — 헬스체크

### `app/static/`
- 순수 HTML/CSS/JS로 구성된 SPA 대시보드
- Chart.js (CDN)로 도넛/바/라인 차트 렌더링
- 반응형 디자인 (모바일 지원)

## Code Style and Conventions

- Python: 표준 PEP 8, 한국어 docstring 사용
- JS: ES6+, 전역 함수 기반 (번들러 미사용)
- CSS: CSS 커스텀 프로퍼티(변수) 사용, BEM 미사용

## Git Workflow

- **Default branch**: `master`
- Write clear, descriptive commit messages
- Keep commits focused on a single change

## Architecture Notes

**데이터 흐름:**
1. 사용자가 프론트엔드에서 네이버 플레이스 URL 입력
2. `POST /api/analyze` → `crawler.py`가 네이버 GraphQL API에서 리뷰 크롤링
3. `analyzer.py`가 수집된 리뷰에 대해 감성 분석 + 카테고리 분류 + 경영지표 산출
4. 결과 JSON을 프론트엔드로 반환 → Chart.js 기반 대시보드 렌더링

**설계 결정:**
- DB 미사용: 실시간 크롤링 + 분석 방식 (상태 없음)
- ML 모델 미사용: 키워드 사전 기반 감성 분석으로 의존성 최소화
- CDN 기반 Chart.js: 빌드 도구 없이 즉시 사용 가능
