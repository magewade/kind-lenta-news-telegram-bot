# db/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    date = Column(DateTime)
    topics = Column(String)  # Можно хранить как JSON или строку с разделителями
    keywords = Column(String)

    def __repr__(self):
        return f"<News(title={self.title})>"
