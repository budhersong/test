"""네이버 플레이스 리뷰 분석 웹서비스 - FastAPI 백엔드."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.crawler import crawl_place
from app.analyzer import analyze_reviews
from app.models import AnalyzeRequest

app = FastAPI(
    title="네이버 플레이스 리뷰 분석기",
    description="고객 리뷰 기반 경영 인사이트 도출 서비스",
    version="1.0.0",
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    """네이버 플레이스 URL을 받아 리뷰를 분석합니다."""
    try:
        crawled = await crawl_place(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"네이버 플레이스에서 데이터를 가져오는 중 오류가 발생했습니다: {e}",
        )

    result = analyze_reviews(crawled["reviews"])
    return {"place": crawled["place"], **result}


@app.get("/health")
async def health():
    return {"status": "ok"}
