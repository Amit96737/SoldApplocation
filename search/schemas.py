from pydantic import BaseModel
from typing import Optional, List, Any
from enum import Enum


class SearchSuggestions(BaseModel):
    query: str


class SearchResult(SearchSuggestions):
    views: Optional[int] = 0
