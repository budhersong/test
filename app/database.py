from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

engine = create_engine("sqlite:///./naver_crawler.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(String(200), unique=True, nullable=False)
    type = Column(String(20), default="keyword")  # "keyword" or "channel"
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class CrawledPost(Base):
    __tablename__ = "crawled_posts"

    id = Column(Integer, primary_key=True, index=True)
    post_url = Column(String(500), unique=True, nullable=False, index=True)
    title = Column(String(500))
    author = Column(String(200))
    post_date = Column(String(50))
    content = Column(Text)
    source_type = Column(String(20))  # "keyword" or "channel"
    source_value = Column(String(200))
    crawled_at = Column(DateTime, default=datetime.now)
    synced_to_sheets = Column(Boolean, default=False)


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="running")  # running / success / error
    new_posts = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
