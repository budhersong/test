"""Pydantic 모델 정의."""

from pydantic import BaseModel, HttpUrl


class AnalyzeRequest(BaseModel):
    url: str


class PlaceInfo(BaseModel):
    id: str
    name: str
    category: str
    address: str
    phone: str = ""
    image_url: str = ""
    rating_avg: float
    rating_total: int


class Summary(BaseModel):
    total_reviews: int
    avg_rating: float
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    reply_rate: float


class CategoryDetail(BaseModel):
    positive_mentions: int
    negative_mentions: int
    total_reviews_mentioning: int
    score: str


class MonthlyTrend(BaseModel):
    month: str
    positive: int
    negative: int
    neutral: int
    total: int


class Insight(BaseModel):
    type: str
    title: str
    description: str
    priority: str


class ReviewItem(BaseModel):
    id: str
    nickname: str
    body: str
    rating: int
    sentiment: str
    categories: list[str]
    created: str


class AnalyzeResponse(BaseModel):
    place: PlaceInfo
    summary: Summary
    sentiment_distribution: dict[str, int]
    rating_distribution: dict[str, int]
    category_analysis: dict[str, CategoryDetail]
    monthly_trend: list[MonthlyTrend]
    top_positive_keywords: list[list]
    top_negative_keywords: list[list]
    insights: list[Insight]
    reviews: list[ReviewItem]
