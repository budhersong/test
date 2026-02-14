# 네이버 플레이스 리뷰 분석기

고객 리뷰 기반 경영 인사이트 도출 웹서비스

네이버 플레이스 URL을 입력하면 리뷰 데이터를 크롤링하여 긍/부정 감성 분석, 카테고리별 평가, 월별 추이, 경영 개선사항을 자동으로 도출합니다.

## 주요 기능

- **리뷰 크롤링** — 네이버 플레이스 GraphQL API를 통해 방문자 리뷰 수집
- **감성 분석** — 한국어 키워드 기반 긍정/부정/중립 분류
- **카테고리별 분석** — 맛/음식, 가성비, 서비스, 청결, 분위기, 재방문 의향
- **경영 인사이트** — 우선순위별 개선사항 자동 도출
- **시각화 대시보드** — Chart.js 기반 인터랙티브 차트
- **월별 추이** — 시간에 따른 고객 감성 변화 추적

## 빠른 시작

```bash
# 의존성 설치
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

브라우저에서 `http://localhost:8000` 접속 후, 네이버 플레이스 URL을 입력하세요.

## 지원 URL 형식

| 형식 | 예시 |
|------|------|
| 모바일 플레이스 | `https://m.place.naver.com/restaurant/1234567890` |
| 네이버 지도 | `https://map.naver.com/v5/entry/place/1234567890` |
| PC 플레이스 | `https://pcmap.place.naver.com/restaurant/1234567890` |
| 단축 URL | `https://naver.me/xxxxx` |
| 장소 ID 직접 입력 | `1234567890` |

## 기술 스택

- **Backend**: Python 3.10+, FastAPI, httpx
- **Frontend**: HTML/CSS/JS, Chart.js (CDN)
- **분석**: 키워드 사전 기반 한국어 감성 분석

## 프로젝트 구조

```
app/
├── main.py        # FastAPI 앱 & 라우트
├── crawler.py     # 네이버 플레이스 리뷰 크롤러
├── analyzer.py    # 감성 분석 & 경영지표 도출
├── models.py      # Pydantic 데이터 모델
└── static/
    ├── index.html # 대시보드 UI
    ├── style.css  # 스타일시트
    └── app.js     # 프론트엔드 로직
```
