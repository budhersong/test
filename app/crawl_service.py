import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import Keyword, CrawledPost, CrawlLog
from app.crawler import crawl_by_keyword, crawl_by_channel
from app.sheets import append_posts_to_sheet

logger = logging.getLogger(__name__)


def run_full_crawl(db: Session) -> dict:
    """모든 활성 키워드/채널에 대해 크롤링 실행"""
    log = CrawlLog(started_at=datetime.now(), status="running")
    db.add(log)
    db.commit()
    db.refresh(log)

    new_count = 0
    try:
        keywords = db.query(Keyword).filter(Keyword.active == True).all()
        all_new_posts = []

        for kw in keywords:
            if kw.type == "keyword":
                posts = crawl_by_keyword(kw.value)
            else:
                posts = crawl_by_channel(kw.value)

            for post in posts:
                url = post.get("post_url", "")
                if not url:
                    continue
                existing = db.query(CrawledPost).filter(CrawledPost.post_url == url).first()
                if existing:
                    continue

                db_post = CrawledPost(
                    post_url=url,
                    title=post.get("title", ""),
                    author=post.get("author", ""),
                    post_date=post.get("post_date", ""),
                    content=post.get("content", ""),
                    source_type=post.get("source_type", ""),
                    source_value=post.get("source_value", ""),
                    crawled_at=datetime.now(),
                    synced_to_sheets=False,
                )
                db.add(db_post)
                all_new_posts.append(post)

        db.commit()

        if all_new_posts:
            try:
                append_posts_to_sheet(all_new_posts)
                db.query(CrawledPost).filter(
                    CrawledPost.synced_to_sheets == False
                ).update({"synced_to_sheets": True})
                db.commit()
            except Exception as e:
                logger.error("Google Sheets 업로드 실패: %s", e)

        new_count = len(all_new_posts)
        log.status = "success"
        log.new_posts = new_count

    except Exception as e:
        logger.error("크롤링 오류: %s", e)
        log.status = "error"
        log.error_message = str(e)

    log.finished_at = datetime.now()
    db.commit()

    return {"status": log.status, "new_posts": new_count}
