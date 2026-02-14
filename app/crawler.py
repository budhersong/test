"""네이버 플레이스 리뷰 크롤러 모듈."""

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

COMMON_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://pcmap.place.naver.com/",
    "Origin": "https://pcmap.place.naver.com",
}


def extract_place_id(url: str) -> str:
    """네이버 플레이스 URL에서 place ID를 추출합니다.

    지원 URL 형식:
      - https://m.place.naver.com/restaurant/1234567890/...
      - https://map.naver.com/v5/entry/place/1234567890
      - https://pcmap.place.naver.com/restaurant/1234567890/...
      - https://naver.me/xxxxx (단축 URL)
      - 숫자만 입력 (place ID 직접 입력)
    """
    url = url.strip()

    if re.fullmatch(r"\d+", url):
        return url

    patterns = [
        r"place\.naver\.com/\w+/(\d+)",
        r"map\.naver\.com/v5/entry/place/(\d+)",
        r"map\.naver\.com/\w*/entry/place/(\d+)",
        r"/place/(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(
        f"네이버 플레이스 URL에서 장소 ID를 추출할 수 없습니다: {url}"
    )


async def resolve_short_url(url: str) -> str:
    """naver.me 단축 URL을 실제 URL로 변환합니다."""
    if "naver.me" not in url:
        return url
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        resp = await client.get(url)
        return str(resp.url)


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
        resp = await client.post(
            GRAPHQL_URL, json=payload, headers=COMMON_HEADERS
        )
        resp.raise_for_status()
        data = resp.json()

    place = data[0].get("data", {}).get("place")
    if not place:
        return {
            "id": place_id,
            "name": "알 수 없음",
            "category": "",
            "address": "",
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
    place_id: str, page_size: int = 50, max_pages: int = 10
) -> list[dict]:
    """장소의 방문자 리뷰를 페이지별로 조회합니다."""
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
                            "businessType": "restaurant",
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
            resp = await client.post(
                GRAPHQL_URL, json=payload, headers=COMMON_HEADERS
            )
            resp.raise_for_status()
            data = resp.json()

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


async def crawl_place(url: str) -> dict:
    """네이버 플레이스 URL로부터 장소 정보와 리뷰를 크롤링합니다."""
    resolved_url = await resolve_short_url(url)
    place_id = extract_place_id(resolved_url)
    place_info = await fetch_place_info(place_id)
    reviews = await fetch_reviews(place_id)
    return {"place": place_info, "reviews": reviews}
