from sqlalchemy import Column, String, Integer

from database import Base
from sqlalchemy import Column, String, Integer

from database import Base


class SearchSuggestions(Base):
    __tablename__ = "search_suggestions"

    query = Column(String(), unique=True, primary_key=True)
    views = Column(Integer(), default=1)

