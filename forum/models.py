from datetime import datetime

from sqlalchemy import Column, Enum, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from auth.models import user_favorite_topics
from database import Base
from forum.schemas import ForumTopicCategory
import uuid


class ForumTopic(Base):
    __tablename__ = "forum_topics"

    id = Column(String(length=36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(length=36), ForeignKey("users.id"), nullable=True)
    admin_id = Column(String(length=36), ForeignKey("administrator.id"), nullable=True)
    category = Column(Enum(ForumTopicCategory), default=ForumTopicCategory.Clothes)
    title = Column(String(), default="")
    description = Column(String(), default="")
    images = Column(String(), default="[]")
    date_created = Column(DateTime, default=datetime.utcnow)

    item_id = Column(String(length=36), ForeignKey("shop_items.id"), nullable=True)

    favorited_by = relationship('User', secondary=user_favorite_topics, back_populates='favorited_topics')

    user = relationship("User", back_populates='forum_topics', uselist=False)
    admin = relationship("Administrator", back_populates='forum_topics', uselist=False)
    answers = relationship("TopicAnswer", back_populates="topic", cascade="all,delete")
    item = relationship("ShopItem", uselist=False)


class TopicAnswer(Base):
    __tablename__ = "topic_answers"

    id = Column(String(), primary_key=True)
    topic_id = Column(String(), ForeignKey("forum_topics.id"))
    answer = Column(String(), default="")
    user_id = Column(String(), ForeignKey("users.id"))
    attachment = Column(String(), default="[]")
    date_answered = Column(DateTime, default=datetime.utcnow)

    topic = relationship("ForumTopic", back_populates="answers")
    user = relationship("User")
