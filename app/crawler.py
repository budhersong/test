import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urljoin

logger = logging.getLogger(__name__)

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def _naver_search_api(query: str, display: int = 100, start: int = 1) -> list[dict]:
    """네이버 검색 API로 블로그 포스트 목록 가져오기"""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise ValueError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 설정되지 않았습니다.")

    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "start": start, "sort": "date"}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("items", [])


def _resolve_naver_blog_url(link: str) -> str:
    """단축 URL → 실제 blog.naver.com URL로 변환"""
    if "blog.naver.com" in link:
        return link
    try:
        resp = requests.get(link, headers=HEADERS, timeout=10, allow_redirects=True)
        return resp.url
    except Exception:
        return link


def _extract_blog_id_log_no(url: str) -> tuple[Optional[str], Optional[str]]:
    """URL에서 blogId, logNo 추출"""
    # https://blog.naver.com/blogId/logNo
    m = re.match(r"https?://blog\.naver\.com/([^/?#]+)/(\d+)", url)
    if m:
        return m.group(1), m.group(2)
    # PostView.naver?blogId=...&logNo=...
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    blog_id = qs.get("blogId", [None])[0]
    log_no = qs.get("logNo", [None])[0]
    return blog_id, log_no


def fetch_post_content(url: str) -> str:
    """네이버 블로그 포스트 본문 전체 텍스트 가져오기 (모바일 버전 사용)"""
    resolved = _resolve_naver_blog_url(url)
    blog_id, log_no = _extract_blog_id_log_no(resolved)

    if blog_id and log_no:
        mobile_url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
    else:
        mobile_url = resolved

    try:
        resp = requests.get(mobile_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # 모바일 블로그 본문 선택자
        content_area = (
            soup.find("div", class_="se-main-container")
            or soup.find("div", {"id": "viewTypeSelector"})
            or soup.find("div", class_="post-view")
            or soup.find("div", class_="se_component_wrap")
        )

        if content_area:
            text = content_area.get_text(separator="\n", strip=True)
        else:
            # fallback: body 전체에서 스크립트/스타일 제거
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)

        # 연속 빈 줄 정리
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    except Exception as e:
        logger.warning("본문 수집 실패 (%s): %s", mobile_url, e)
        return ""


def crawl_by_keyword(keyword: str, max_posts: int = 100) -> list[dict]:
    """키워드 검색으로 블로그 포스트 수집"""
    results = []
    try:
        items = _naver_search_api(keyword, display=min(max_posts, 100))
    except Exception as e:
        logger.error("네이버 API 오류 (keyword=%s): %s", keyword, e)
        return []

    for item in items:
        raw_link = item.get("link", "")
        title = re.sub(r"<[^>]+>", "", item.get("title", ""))
        author = item.get("bloggername", "")
        post_date = item.get("postdate", "")

        time.sleep(0.5)  # 요청 간격
        content = fetch_post_content(raw_link)

        results.append({
            "title": title,
            "post_url": raw_link,
            "author": author,
            "post_date": post_date,
            "content": content,
            "source_type": "keyword",
            "source_value": keyword,
        })

    logger.info("키워드 '%s' 수집 완료: %d건", keyword, len(results))
    return results


def _get_blog_post_list(blog_id: str, page: int = 1) -> list[dict]:
    """특정 블로그 채널의 포스트 목록 가져오기 (RSS 우선, 실패 시 웹 파싱)"""
    posts = []

    # RSS 피드 시도
    rss_url = f"https://rss.blog.naver.com/{blog_id}.xml"
    try:
        resp = requests.get(rss_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "xml")
            for item in soup.find_all("item"):
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                creator = item.find("dc:creator") or item.find("author")
                posts.append({
                    "title": title.get_text(strip=True) if title else "",
                    "post_url": link.get_text(strip=True) if link else "",
                    "author": creator.get_text(strip=True) if creator else blog_id,
                    "post_date": pub_date.get_text(strip=True) if pub_date else "",
                })
            return posts
    except Exception as e:
        logger.warning("RSS 수집 실패 (%s): %s", blog_id, e)

    # 웹 파싱 fallback
    list_url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}&currentPage={page}"
    try:
        resp = requests.get(list_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.select("a[href*='logNo']"):
            href = a.get("href", "")
            if "logNo=" in href:
                full_url = urljoin("https://blog.naver.com", href)
                posts.append({
                    "title": a.get_text(strip=True),
                    "post_url": full_url,
                    "author": blog_id,
                    "post_date": "",
                })
    except Exception as e:
        logger.warning("블로그 목록 파싱 실패 (%s): %s", blog_id, e)

    return posts


def crawl_by_channel(blog_id: str, max_posts: int = 50) -> list[dict]:
    """특정 블로그 채널 포스트 수집"""
    results = []
    post_list = _get_blog_post_list(blog_id)[:max_posts]

    for post in post_list:
        if not post.get("post_url"):
            continue
        time.sleep(0.5)
        content = fetch_post_content(post["post_url"])
        results.append({
            **post,
            "content": content,
            "source_type": "channel",
            "source_value": blog_id,
        })

    logger.info("채널 '%s' 수집 완료: %d건", blog_id, len(results))
    return results
