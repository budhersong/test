"""한국어 리뷰 감성 분석 및 경영지표 도출 모듈."""

import re
from collections import Counter, defaultdict

# ──────────────────────────────────────────────
# 1. 감성 사전 (Sentiment Lexicons)
# ──────────────────────────────────────────────

POSITIVE_WORDS: set[str] = {
    # 맛/음식
    "맛있", "맛남", "존맛", "꿀맛", "감칠맛", "신선", "바삭", "촉촉", "부드러",
    "담백", "고소", "풍미", "정갈", "깔끔", "든든", "푸짐", "넉넉", "알찬",
    "다양", "풍성", "특별", "별미", "일품",
    # 서비스
    "친절", "상냥", "배려", "세심", "빠른", "신속", "응대", "미소", "정성",
    "프로", "전문", "능숙", "센스",
    # 분위기
    "깨끗", "청결", "인테리어", "분위기", "아늑", "편안", "쾌적", "조용",
    "예쁜", "예뻐", "고급", "감성", "트렌디", "세련",
    # 가격
    "가성비", "합리적", "저렴", "착한가격", "혜자",
    # 일반 긍정
    "추천", "재방문", "또올", "단골", "최고", "대박", "만족", "좋아", "좋은",
    "좋았", "훌륭", "완벽", "감동", "행복", "즐거", "기분좋", "사랑",
    "강추", "인생", "굿", "베스트", "짱",
}

NEGATIVE_WORDS: set[str] = {
    # 맛/음식
    "맛없", "별로", "느끼", "짜다", "짠", "싱거", "식은", "딱딱", "질긴",
    "눅눅", "비린", "텁텁", "기름", "느끼하", "과하", "부족",
    # 서비스
    "불친절", "무뚝뚝", "느린", "늦은", "오래걸", "무시", "무관심",
    "불쾌", "짜증", "실망", "어이없", "황당", "불만",
    # 분위기/위생
    "더러", "지저분", "비위생", "냄새", "시끄러", "좁은", "답답",
    "불편", "낡은", "어두", "춥", "더운",
    # 가격
    "비싼", "비싸", "가격대비", "아깝", "바가지",
    # 일반 부정
    "후회", "다시안", "안갈", "최악", "별로", "실패", "아쉬",
    "그냥그냥", "그저그래", "거기서거기", "평범",
}

# ──────────────────────────────────────────────
# 2. 경영 카테고리 키워드 매핑
# ──────────────────────────────────────────────

CATEGORY_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "맛/음식 품질": {
        "positive": [
            "맛있", "맛남", "존맛", "꿀맛", "신선", "바삭", "촉촉", "부드러",
            "담백", "고소", "풍미", "정갈", "깔끔", "별미", "일품", "감칠맛",
            "인생맛집", "인생",
        ],
        "negative": [
            "맛없", "느끼", "짜다", "짠", "싱거", "식은", "딱딱", "질긴",
            "눅눅", "비린", "텁텁", "기름", "느끼하",
        ],
    },
    "양/가성비": {
        "positive": [
            "푸짐", "넉넉", "알찬", "다양", "풍성", "가성비", "합리적",
            "저렴", "착한가격", "혜자", "든든",
        ],
        "negative": [
            "부족", "적은", "비싼", "비싸", "아깝", "바가지", "가격대비",
        ],
    },
    "서비스": {
        "positive": [
            "친절", "상냥", "배려", "세심", "빠른", "신속", "응대", "미소",
            "정성", "프로", "전문", "능숙", "센스",
        ],
        "negative": [
            "불친절", "무뚝뚝", "느린", "늦은", "오래걸", "무시", "무관심",
            "불쾌", "짜증",
        ],
    },
    "청결/위생": {
        "positive": ["깨끗", "청결", "위생적", "깔끔", "쾌적"],
        "negative": ["더러", "지저분", "비위생", "냄새", "벌레"],
    },
    "분위기/인테리어": {
        "positive": [
            "분위기", "아늑", "편안", "조용", "예쁜", "예뻐", "고급", "감성",
            "트렌디", "세련", "인테리어",
        ],
        "negative": [
            "시끄러", "좁은", "답답", "불편", "낡은", "어두", "춥", "더운",
        ],
    },
    "재방문 의향": {
        "positive": ["재방문", "또올", "또가", "단골", "추천", "강추"],
        "negative": ["다시안", "안갈", "후회", "최악"],
    },
}


# ──────────────────────────────────────────────
# 3. 분석 함수
# ──────────────────────────────────────────────


def _contains(text: str, keywords: list[str] | set[str]) -> list[str]:
    """텍스트에 포함된 키워드 목록을 반환."""
    return [kw for kw in keywords if kw in text]


def analyze_sentiment(text: str) -> dict:
    """단일 리뷰 텍스트의 감성을 분석합니다."""
    if not text:
        return {"score": 0, "label": "중립", "positive": [], "negative": []}

    pos_found = _contains(text, POSITIVE_WORDS)
    neg_found = _contains(text, NEGATIVE_WORDS)

    score = len(pos_found) - len(neg_found)
    if score > 0:
        label = "긍정"
    elif score < 0:
        label = "부정"
    else:
        label = "중립"

    return {
        "score": score,
        "label": label,
        "positive": pos_found,
        "negative": neg_found,
    }


def classify_categories(text: str) -> dict[str, dict]:
    """리뷰 텍스트를 경영 카테고리별로 분류합니다."""
    result = {}
    for cat_name, kw_map in CATEGORY_KEYWORDS.items():
        pos = _contains(text, kw_map["positive"])
        neg = _contains(text, kw_map["negative"])
        if pos or neg:
            result[cat_name] = {"positive": pos, "negative": neg}
    return result


def extract_month(date_str: str) -> str:
    """날짜 문자열에서 YYYY-MM 형식을 추출합니다."""
    m = re.search(r"(\d{4})[.\-/](\d{1,2})", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return "unknown"


# ──────────────────────────────────────────────
# 4. 전체 분석 파이프라인
# ──────────────────────────────────────────────


def analyze_reviews(reviews: list[dict]) -> dict:
    """전체 리뷰 데이터를 분석하여 경영 인사이트를 도출합니다."""
    if not reviews:
        return _empty_result()

    total = len(reviews)
    sentiments = {"긍정": 0, "부정": 0, "중립": 0}
    category_scores: dict[str, dict[str, int]] = {
        cat: {"positive": 0, "negative": 0, "total": 0}
        for cat in CATEGORY_KEYWORDS
    }
    monthly_sentiment: dict[str, dict[str, int]] = defaultdict(
        lambda: {"긍정": 0, "부정": 0, "중립": 0, "count": 0}
    )
    positive_keywords: Counter = Counter()
    negative_keywords: Counter = Counter()
    rating_dist = Counter()
    reply_count = 0
    review_details = []

    for review in reviews:
        body = review.get("body", "")
        rating = review.get("rating", 0)
        created = review.get("created", "")
        tags = review.get("tags") or []

        # 감성 분석
        sent = analyze_sentiment(body + " " + " ".join(tags))
        sentiments[sent["label"]] += 1

        # 키워드 집계
        for kw in sent["positive"]:
            positive_keywords[kw] += 1
        for kw in sent["negative"]:
            negative_keywords[kw] += 1

        # 카테고리 분류
        cats = classify_categories(body + " " + " ".join(tags))
        for cat_name, hits in cats.items():
            category_scores[cat_name]["positive"] += len(hits["positive"])
            category_scores[cat_name]["negative"] += len(hits["negative"])
            category_scores[cat_name]["total"] += 1

        # 월별 추이
        month = extract_month(created)
        monthly_sentiment[month][sent["label"]] += 1
        monthly_sentiment[month]["count"] += 1

        # 별점 분포
        if rating:
            rating_dist[rating] += 1

        # 사장님 답글 비율
        if review.get("has_reply"):
            reply_count += 1

        review_details.append(
            {
                "id": review.get("id", ""),
                "nickname": review.get("nickname", ""),
                "body": body[:200],
                "rating": rating,
                "sentiment": sent["label"],
                "categories": list(cats.keys()),
                "created": created,
            }
        )

    # ── 경영지표 산출 ──
    avg_rating = (
        sum(r * c for r, c in rating_dist.items()) / sum(rating_dist.values())
        if rating_dist
        else 0
    )
    pos_ratio = sentiments["긍정"] / total * 100 if total else 0
    neg_ratio = sentiments["부정"] / total * 100 if total else 0
    reply_rate = reply_count / total * 100 if total else 0

    # ── 경영 개선사항 도출 ──
    insights = _generate_insights(
        sentiments, category_scores, avg_rating, reply_rate, total,
        negative_keywords, positive_keywords,
    )

    # 월별 추이 정렬
    sorted_months = sorted(
        (k, v)
        for k, v in monthly_sentiment.items()
        if k != "unknown"
    )

    return {
        "summary": {
            "total_reviews": total,
            "avg_rating": round(avg_rating, 2),
            "positive_ratio": round(pos_ratio, 1),
            "negative_ratio": round(neg_ratio, 1),
            "neutral_ratio": round(100 - pos_ratio - neg_ratio, 1),
            "reply_rate": round(reply_rate, 1),
        },
        "sentiment_distribution": sentiments,
        "rating_distribution": {
            str(k): v for k, v in sorted(rating_dist.items())
        },
        "category_analysis": {
            cat: {
                "positive_mentions": scores["positive"],
                "negative_mentions": scores["negative"],
                "total_reviews_mentioning": scores["total"],
                "score": _cat_score(scores),
            }
            for cat, scores in category_scores.items()
        },
        "monthly_trend": [
            {
                "month": month,
                "positive": data["긍정"],
                "negative": data["부정"],
                "neutral": data["중립"],
                "total": data["count"],
            }
            for month, data in sorted_months
        ],
        "top_positive_keywords": positive_keywords.most_common(15),
        "top_negative_keywords": negative_keywords.most_common(15),
        "insights": insights,
        "reviews": review_details[:100],
    }


def _cat_score(scores: dict) -> str:
    total = scores["positive"] + scores["negative"]
    if total == 0:
        return "데이터 부족"
    ratio = scores["positive"] / total * 100
    if ratio >= 80:
        return "매우 우수"
    if ratio >= 60:
        return "양호"
    if ratio >= 40:
        return "보통"
    if ratio >= 20:
        return "개선 필요"
    return "시급한 개선 필요"


def _generate_insights(
    sentiments: dict,
    category_scores: dict,
    avg_rating: float,
    reply_rate: float,
    total: int,
    neg_kw: Counter,
    pos_kw: Counter,
) -> list[dict]:
    """분석 결과를 바탕으로 경영 인사이트를 생성합니다."""
    insights: list[dict] = []

    # 1) 전반적 평판
    pos_ratio = sentiments["긍정"] / total * 100 if total else 0
    neg_ratio = sentiments["부정"] / total * 100 if total else 0

    if pos_ratio >= 70:
        insights.append({
            "type": "strength",
            "title": "높은 고객 만족도",
            "description": (
                f"긍정 리뷰 비율이 {pos_ratio:.0f}%로 매우 높습니다. "
                "현재의 강점을 유지하면서 마케팅에 활용하세요."
            ),
            "priority": "low",
        })
    elif neg_ratio >= 40:
        insights.append({
            "type": "critical",
            "title": "고객 불만 비율 높음",
            "description": (
                f"부정 리뷰 비율이 {neg_ratio:.0f}%입니다. "
                "아래 카테고리별 분석을 참고하여 시급한 개선이 필요합니다."
            ),
            "priority": "high",
        })

    # 2) 카테고리별 경고
    for cat, scores in category_scores.items():
        total_mentions = scores["positive"] + scores["negative"]
        if total_mentions < 3:
            continue
        neg_pct = scores["negative"] / total_mentions * 100
        if neg_pct >= 50:
            insights.append({
                "type": "warning",
                "title": f"[{cat}] 개선 필요",
                "description": (
                    f"'{cat}' 관련 언급 중 부정 비율이 {neg_pct:.0f}%입니다. "
                    "해당 영역의 품질 점검이 필요합니다."
                ),
                "priority": "high",
            })
        elif neg_pct <= 20 and total_mentions >= 5:
            insights.append({
                "type": "strength",
                "title": f"[{cat}] 고객 호평",
                "description": (
                    f"'{cat}'이(가) 핵심 강점입니다 "
                    f"(긍정 비율 {100 - neg_pct:.0f}%). "
                    "마케팅 포인트로 활용하세요."
                ),
                "priority": "low",
            })

    # 3) 답글 비율
    if reply_rate < 30:
        insights.append({
            "type": "recommendation",
            "title": "사장님 답글 비율 개선 필요",
            "description": (
                f"답글 비율이 {reply_rate:.0f}%로 낮습니다. "
                "리뷰 답글은 고객 재방문율과 신뢰도에 큰 영향을 줍니다. "
                "특히 부정 리뷰에 대한 정중한 답글을 우선 달아보세요."
            ),
            "priority": "medium",
        })
    elif reply_rate >= 70:
        insights.append({
            "type": "strength",
            "title": "적극적인 고객 소통",
            "description": (
                f"답글 비율이 {reply_rate:.0f}%로 높습니다. "
                "고객과의 소통이 잘 이루어지고 있습니다."
            ),
            "priority": "low",
        })

    # 4) 평균 별점
    if avg_rating < 3.5:
        insights.append({
            "type": "critical",
            "title": "평균 별점 하락 주의",
            "description": (
                f"평균 별점이 {avg_rating:.1f}점으로 낮습니다. "
                "부정 키워드를 확인하고 집중 개선하세요."
            ),
            "priority": "high",
        })

    # 5) 부정 키워드 핫이슈
    top_neg = neg_kw.most_common(3)
    if top_neg and top_neg[0][1] >= 3:
        kw_list = ", ".join(f"'{kw}'({cnt}회)" for kw, cnt in top_neg)
        insights.append({
            "type": "recommendation",
            "title": "주요 불만 키워드",
            "description": (
                f"가장 빈번한 부정 키워드: {kw_list}. "
                "해당 이슈를 우선적으로 해결하세요."
            ),
            "priority": "medium",
        })

    # 6) 긍정 키워드 강점
    top_pos = pos_kw.most_common(3)
    if top_pos and top_pos[0][1] >= 3:
        kw_list = ", ".join(f"'{kw}'({cnt}회)" for kw, cnt in top_pos)
        insights.append({
            "type": "strength",
            "title": "고객이 가장 좋아하는 포인트",
            "description": (
                f"가장 빈번한 긍정 키워드: {kw_list}. "
                "이 강점을 SNS/홍보에 적극 활용하세요."
            ),
            "priority": "low",
        })

    # 우선순위 정렬
    priority_order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda x: priority_order.get(x["priority"], 99))

    return insights


def _empty_result() -> dict:
    return {
        "summary": {
            "total_reviews": 0,
            "avg_rating": 0,
            "positive_ratio": 0,
            "negative_ratio": 0,
            "neutral_ratio": 0,
            "reply_rate": 0,
        },
        "sentiment_distribution": {"긍정": 0, "부정": 0, "중립": 0},
        "rating_distribution": {},
        "category_analysis": {},
        "monthly_trend": [],
        "top_positive_keywords": [],
        "top_negative_keywords": [],
        "insights": [
            {
                "type": "info",
                "title": "리뷰 데이터 없음",
                "description": "분석할 리뷰가 없습니다.",
                "priority": "high",
            }
        ],
        "reviews": [],
    }
