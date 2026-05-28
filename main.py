import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Depends, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import init_db, get_db, Keyword, CrawledPost, CrawlLog
from app.crawl_service import run_full_crawl
from app.scheduler import start_scheduler, stop_scheduler
from app.sheets import get_spreadsheet_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    day = os.getenv("SCHEDULE_DAY_OF_WEEK", "mon")
    hour = int(os.getenv("SCHEDULE_HOUR", "9"))
    minute = int(os.getenv("SCHEDULE_MINUTE", "0"))
    start_scheduler(day, hour, minute)
    yield
    stop_scheduler()


app = FastAPI(title="네이버 블로그 리뷰 크롤러", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── 대시보드 ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    keyword_count = db.query(Keyword).filter(Keyword.active == True).count()
    post_count = db.query(CrawledPost).count()
    logs = db.query(CrawlLog).order_by(CrawlLog.started_at.desc()).limit(10).all()
    recent_posts = db.query(CrawledPost).order_by(CrawledPost.crawled_at.desc()).limit(20).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "keyword_count": keyword_count,
        "post_count": post_count,
        "logs": logs,
        "recent_posts": recent_posts,
        "spreadsheet_url": get_spreadsheet_url(),
    })


# ── 키워드/채널 관리 ──────────────────────────────────────────────────────────

@app.get("/keywords", response_class=HTMLResponse)
def keywords_page(request: Request, db: Session = Depends(get_db)):
    items = db.query(Keyword).order_by(Keyword.created_at.desc()).all()
    return templates.TemplateResponse("keywords.html", {"request": request, "keywords": items})


@app.post("/keywords/add")
def add_keyword(
    value: str = Form(...),
    type: str = Form("keyword"),
    db: Session = Depends(get_db),
):
    value = value.strip()
    if not value:
        return RedirectResponse("/keywords", status_code=303)
    existing = db.query(Keyword).filter(Keyword.value == value).first()
    if not existing:
        db.add(Keyword(value=value, type=type))
        db.commit()
    return RedirectResponse("/keywords", status_code=303)


@app.post("/keywords/{kw_id}/toggle")
def toggle_keyword(kw_id: int, db: Session = Depends(get_db)):
    kw = db.query(Keyword).filter(Keyword.id == kw_id).first()
    if kw:
        kw.active = not kw.active
        db.commit()
    return RedirectResponse("/keywords", status_code=303)


@app.post("/keywords/{kw_id}/delete")
def delete_keyword(kw_id: int, db: Session = Depends(get_db)):
    kw = db.query(Keyword).filter(Keyword.id == kw_id).first()
    if kw:
        db.delete(kw)
        db.commit()
    return RedirectResponse("/keywords", status_code=303)


# ── 크롤링 실행 ───────────────────────────────────────────────────────────────

@app.post("/crawl/run")
def run_crawl_now(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    def _task():
        from app.database import SessionLocal
        _db = SessionLocal()
        try:
            run_full_crawl(_db)
        finally:
            _db.close()

    background_tasks.add_task(_task)
    return RedirectResponse("/?msg=크롤링이 백그라운드에서 시작됐습니다", status_code=303)


@app.get("/crawl/status")
def crawl_status(db: Session = Depends(get_db)):
    log = db.query(CrawlLog).order_by(CrawlLog.started_at.desc()).first()
    if not log:
        return JSONResponse({"status": "never"})
    return JSONResponse({
        "status": log.status,
        "new_posts": log.new_posts,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
    })


# ── 수집 데이터 조회 ──────────────────────────────────────────────────────────

@app.get("/posts", response_class=HTMLResponse)
def posts_page(
    request: Request,
    page: int = 1,
    q: str = "",
    db: Session = Depends(get_db),
):
    page_size = 30
    query = db.query(CrawledPost)
    if q:
        query = query.filter(
            CrawledPost.title.contains(q) | CrawledPost.content.contains(q)
        )
    total = query.count()
    posts = query.order_by(CrawledPost.crawled_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return templates.TemplateResponse("posts.html", {
        "request": request,
        "posts": posts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "q": q,
        "total_pages": (total + page_size - 1) // page_size,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("APP_PORT", "8000")), reload=True)
