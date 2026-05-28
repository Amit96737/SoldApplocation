

from sqlalchemy import Column, String, Text

from database import Base


class Cms(Base):
    __tablename__ = "cms"

    id = Column(String(length=36), unique=True, primary_key=True)
    slug = Column(String(length=200), default="")
    content = Column(Text)
