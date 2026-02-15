"""네이버 플레이스 리뷰 크롤러 모듈.

다양한 URL 형식(단축 URL 포함)을 처리하고,
네이버 플레이스 GraphQL API를 통해 리뷰를 크롤링합니다.
"""

import asyncio
import re
import httpx

GRAPHQL_URL = "https://pcmap-api.place.naver.com/place/graphql"

VISITOR_REVIEWS_QUERY = """
query getVisitorReviews($input: VisitorReviewsInput) {
  visitorReviews(input: $input) {
    items {
      id
      rating
      author {
        nickname
      }
      body
      visited
      created
      tags
      reply {
        body
        created
      }
    }
    total
  }
}
"""

PLACE_INFO_QUERY = """
query getPlaceInfo($input: PlaceInput) {
  place(input: $input) {
    id
    name
    category
    roadAddress
    address
    businessHours
    phone
    imageUrl
    rating {
      avg
      total
    }
  }
}
"""

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

GRAPHQL_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": BROWSER_HEADERS["User-Agent"],
    "Referer": "https://pcmap.place.naver.com/",
    "Origin": "https://pcmap.place.naver.com",
}

# 네이버 플레이스 URL에 등장하는 업종 경로 → GraphQL businessType 매핑
BUSINESS_TYPE_MAP = {
    "restaurant": "restaurant",
    "cafe": "cafe",
    "hairshop": "hairshop",
    "beauty": "beauty",
    "hospital": "hospital",
    "pharmacy": "pharmacy",
    "accommodation": "accommodation",
    "shopping": "shopping",
    "place": "place",
    "food": "restaurant",
}


# ──────────────────────────────────────────────
# URL 파싱
# ──────────────────────────────────────────────


def extract_place_info_from_url(url: str) -> dict:
    """URL에서 place ID와 business type을 추출합니다.

    Returns:
        {"place_id": str, "business_type": str | None}
    """
    url = url.strip()

    # 숫자만 입력 (place ID 직접 입력)
    if re.fullmatch(r"\d+", url):
        return {"place_id": url, "business_type": None}

    # place.naver.com 계열: /restaurant/12345, /cafe/12345 등
    m = re.search(r"place\.naver\.com/(\w+)/(\d+)", url)
    if m:
        btype = BUSINESS_TYPE_MAP.get(m.group(1))
        return {"place_id": m.group(2), "business_type": btype}

    # map.naver.com 신형: /p/entry/place/12345
    m = re.search(r"map\.naver\.com/p/entry/place/(\d+)", url)
    if m:
        return {"place_id": m.group(1), "business_type": None}

    # map.naver.com 구형: /v5/entry/place/12345
    m = re.search(r"map\.naver\.com/v5/entry/place/(\d+)", url)
    if m:
        return {"place_id": m.group(1), "business_type": None}

    # map.naver.com 검색 결과에 포함된 경우: ?placePath=place%2F12345
    m = re.search(r"placePath=(?:place%2F|place/)(\d+)", url)
    if m:
        return {"place_id": m.group(1), "business_type": None}

    # map.naver.com 기타: /place/12345
    m = re.search(r"/place/(\d+)", url)
    if m:
        return {"place_id": m.group(1), "business_type": None}

    # 범용 패턴: URL 경로 어딘가에 있는 긴 숫자 ID (8자리 이상)
    m = re.search(r"/(\d{8,})", url)
    if m:
        return {"place_id": m.group(1), "business_type": None}

    raise ValueError(
        f"네이버 플레이스 URL에서 장소 ID를 추출할 수 없습니다: {url}"
    )


# ──────────────────────────────────────────────
# 단축 URL 처리
# ──────────────────────────────────────────────


async def resolve_short_url(url: str) -> str:
    """naver.me / me2.do 등 단축 URL을 실제 URL로 변환합니다.

    1차: HTTP redirect 추적 (follow_redirects)
    2차: HTML 내 meta refresh / JS location 파싱 (fallback)
    """
    short_domains = ("naver.me", "me2.do")
    if not any(d in url for d in short_domains):
        return url

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=15,
        headers=BROWSER_HEADERS,
    ) as client:
        resp = await client.get(url)
        final_url = str(resp.url)

        # redirect로 place URL에 도달했으면 바로 반환
        if "place.naver.com" in final_url or "map.naver.com" in final_url:
            return final_url

        # JS/meta redirect fallback: HTML 본문에서 URL 추출
        body = resp.text
        extracted = _extract_redirect_url(body)
        if extracted:
            return extracted

        # 그래도 안 되면 최종 URL 그대로 반환 (extract_place_info_from_url이 재시도)
        return final_url


def _extract_redirect_url(html: str) -> str | None:
    """HTML 내 meta refresh 또는 JS location redirect URL을 추출합니다."""
    # <meta http-equiv="refresh" content="0;url=...">
    m = re.search(
        r'<meta[^>]*http-equiv=["\']?refresh["\']?[^>]*'
        r'content=["\']?\d+;\s*url=([^"\'\s>]+)',
        html,
        re.IGNORECASE,
    )
    if m:
        return m.group(1)

    # location.href = '...' 또는 location.replace('...')
    m = re.search(
        r"location(?:\.href\s*=\s*|\.replace\s*\(\s*)['\"]"
        r"(https?://[^'\"]+)['\"]",
        html,
    )
    if m:
        return m.group(1)

    # window.location = '...'
    m = re.search(
        r"window\.location\s*=\s*['\"]"
        r"(https?://[^'\"]+)['\"]",
        html,
    )
    if m:
        return m.group(1)

    # HTML 본문 내에 place.naver.com URL이 포함된 경우
    m = re.search(
        r"(https?://[a-z]*\.?place\.naver\.com/\w+/\d+[^\s'\"<>]*)",
        html,
    )
    if m:
        return m.group(1)

    return None


# ──────────────────────────────────────────────
# GraphQL API 호출
# ──────────────────────────────────────────────


async def _graphql_request(client: httpx.AsyncClient, payload: list) -> list:
    """GraphQL 요청을 보내고, 429 응답 시 재시도합니다."""
    for attempt in range(4):
        resp = await client.post(
            GRAPHQL_URL, json=payload, headers=GRAPHQL_HEADERS
        )
        if resp.status_code == 429:
            wait = 2 ** attempt  # 1, 2, 4, 8초
            await asyncio.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise httpx.HTTPStatusError(
        "429 Too Many Requests (재시도 초과)",
        request=resp.request,
        response=resp,
    )


async def fetch_place_info(place_id: str) -> dict:
    """장소 기본 정보를 조회합니다."""
    payload = [
        {
            "operationName": "getPlaceInfo",
            "query": PLACE_INFO_QUERY,
            "variables": {"input": {"id": place_id}},
        }
    ]
    async with httpx.AsyncClient(timeout=15) as client:
        data = await _graphql_request(client, payload)

    place = data[0].get("data", {}).get("place")
    if not place:
        return {
            "id": place_id,
            "name": "알 수 없음",
            "category": "",
            "address": "",
            "phone": "",
            "image_url": "",
            "rating_avg": 0,
            "rating_total": 0,
        }

    rating = place.get("rating") or {}
    return {
        "id": place_id,
        "name": place.get("name", "알 수 없음"),
        "category": place.get("category", ""),
        "address": place.get("roadAddress") or place.get("address", ""),
        "phone": place.get("phone", ""),
        "image_url": place.get("imageUrl", ""),
        "rating_avg": rating.get("avg", 0),
        "rating_total": rating.get("total", 0),
    }


async def fetch_reviews(
    place_id: str,
    business_type: str | None = None,
    page_size: int = 50,
    max_pages: int = 10,
) -> list[dict]:
    """장소의 방문자 리뷰를 페이지별로 조회합니다.

    business_type이 None이면 여러 타입을 순차 시도합니다.
    """
    if business_type:
        return await _fetch_reviews_with_type(
            place_id, business_type, page_size, max_pages
        )

    # 업종 타입을 모를 때: 주요 타입 순서대로 시도 (딜레이 포함)
    for btype in ("restaurant", "cafe", "place"):
        reviews = await _fetch_reviews_with_type(
            place_id, btype, page_size, max_pages
        )
        if reviews:
            return reviews
        await asyncio.sleep(1)

    # 어떤 타입으로도 결과가 없으면 빈 리스트
    return []


async def _fetch_reviews_with_type(
    place_id: str,
    business_type: str,
    page_size: int,
    max_pages: int,
) -> list[dict]:
    """특정 businessType으로 리뷰를 조회합니다."""
    reviews: list[dict] = []
    page = 1

    async with httpx.AsyncClient(timeout=15) as client:
        while page <= max_pages:
            payload = [
                {
                    "operationName": "getVisitorReviews",
                    "query": VISITOR_REVIEWS_QUERY,
                    "variables": {
                        "input": {
                            "businessId": place_id,
                            "businessType": business_type,
                            "item": "0",
                            "bookingBusinessId": None,
                            "page": page,
                            "size": page_size,
                            "isPhotoUsed": False,
                            "includeContent": True,
                            "getUserStats": True,
                            "includeReceiptPhotos": True,
                            "cidList": [],
                        }
                    },
                }
            ]

            try:
                data = await _graphql_request(client, payload)
            except (httpx.HTTPStatusError, httpx.RequestError):
                break

            # 페이지 간 딜레이
            if page > 1:
                await asyncio.sleep(0.5)

            visitor_reviews = (
                data[0].get("data", {}).get("visitorReviews") or {}
            )
            items = visitor_reviews.get("items") or []
            total = visitor_reviews.get("total", 0)

            for item in items:
                author = item.get("author") or {}
                reply = item.get("reply")
                reviews.append(
                    {
                        "id": item.get("id", ""),
                        "rating": item.get("rating", 0),
                        "nickname": author.get("nickname", "익명"),
                        "body": item.get("body", ""),
                        "visited": item.get("visited", ""),
                        "created": item.get("created", ""),
                        "tags": item.get("tags") or [],
                        "has_reply": reply is not None,
                        "reply_body": reply.get("body", "") if reply else "",
                    }
                )

            if not items or len(reviews) >= total:
                break
            page += 1

    return reviews


# ──────────────────────────────────────────────
# 메인 크롤링 함수
# ──────────────────────────────────────────────


async def crawl_place(url: str) -> dict:
    """네이버 플레이스 URL로부터 장소 정보와 리뷰를 크롤링합니다.

    지원 URL 형식:
      - https://m.place.naver.com/{type}/{id}
      - https://pcmap.place.naver.com/{type}/{id}
      - https://map.naver.com/v5/entry/place/{id}
      - https://map.naver.com/p/entry/place/{id}
      - https://naver.me/xxxxx  (단축 URL)
      - https://me2.do/xxxxx    (단축 URL)
      - 숫자 ID 직접 입력
    """
    resolved_url = await resolve_short_url(url)
    info = extract_place_info_from_url(resolved_url)
    place_id = info["place_id"]
    business_type = info["business_type"]

    place_info = await fetch_place_info(place_id)
    await asyncio.sleep(1)
    reviews = await fetch_reviews(place_id, business_type)
    return {"place": place_info, "reviews": reviews}
