import json
from sqlite3 import IntegrityError
from uuid import uuid4

from sqlalchemy.orm import Session
from starlette import status
from starlette.requests import Request

from I18n.load_language import get_lang_content
from auth.models import User
from exception import UnicornException
from forum import schemas, models
from auth import models as auth_models


def add_topic(request: Request, topic_data: schemas.AddTopic, current_user: User, db: Session):
    unique_id = str(uuid4())
    topicDict = topic_data.model_dump()

    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    topicDict['id'] = unique_id
    topicDict['user_id'] = current_user.id
    topicDict['images'] = json.dumps(topic_data.images)

    forumTopicModel = models.ForumTopic(**topicDict)

    try:
        db.add(forumTopicModel)
        db.commit()
        db.refresh(forumTopicModel)

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message=language_content.get('forum topic created', "forum topic created"))

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message=language_content.get('forum topic already exists'))


def get_user_topics(current_user: User, db: Session):
    allTopicsInDb = []
    topicInDb = db.query(models.ForumTopic).filter_by(user_id=current_user.id).all()

    for topic in topicInDb:
        topicSchema = schemas.TopicInDb.model_validate(topic)
        topicSchema.user_username = topic.user.profile.username
        topicSchema.user_fullname = topic.user.profile.fullname
        topicSchema.user_profile_pic = topic.user.profile.profile_pic
        topicSchema.user_profile_pic = topicSchema.profile_picture
        topicSchema.comment_count = len(topic.answers)

        allTopicsInDb.append(topicSchema)

    allTopicsInDb.reverse()

    return allTopicsInDb


def delete_topic(request: Request, topic_id: str, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)
    topicInDb = db.query(models.ForumTopic).filter_by(id=topic_id).first()

    if not topicInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('forum topic not found'))
    db.delete(topicInDb)
    db.commit()
    request.session["flash_message"] = {"type": "success",
                                        "message": "Topic deleted successfully"}

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message=language_content.get('forum topic deleted successfully'))


def get_topics_by_category(category_name: str, current_user: User, db: Session):
    allTopicsInDb = []
    topicInDb = db.query(models.ForumTopic).all()

    for topic in topicInDb:
        if topic.user and topic.category.value.lower() == category_name.lower():
            topicSchema = schemas.TopicInDb.model_validate(topic)
            topicSchema.user_username = topic.user.profile.username
            topicSchema.user_fullname = topic.user.profile.fullname
            topicSchema.user_fullname = topic.user.profile.fullname
            topicSchema.user_profile_pic = topic.user.profile.profile_pic
            topicSchema.user_profile_pic = topicSchema.profile_picture
            topicSchema.comment_count = len(topic.answers)

            allTopicsInDb.append(topicSchema)

    allTopicsInDb.reverse()

    return allTopicsInDb


def get_topic_answers(request: Request, topic_id: str, current_user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    topicInDb = db.query(models.ForumTopic).filter_by(id=topic_id).first()

    if not topicInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('forum topic not found'))

    allTopicAnswers = []

    for topic_answer in topicInDb.answers:
        topicAnswerSchema = schemas.TopicAnswerInDb.model_validate(topic_answer)
        topicAnswerSchema.user_username = topic_answer.user.profile.username
        topicAnswerSchema.user_fullname = topic_answer.user.profile.fullname
        topicAnswerSchema.user_fullname = topic_answer.user.profile.fullname
        topicAnswerSchema.user_profile_pic = topic_answer.user.profile.profile_pic
        topicAnswerSchema.user_profile_pic = topicAnswerSchema.profile_picture

        allTopicAnswers.append(topicAnswerSchema)

    allTopicAnswers.reverse()

    return allTopicAnswers


def post_topic_answer(request: Request, answer_data: schemas.AddTopicAnswer, current_user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    topicInDb = db.query(models.ForumTopic).filter_by(id=answer_data.topic_id).first()

    if not topicInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('forum topic not found'))

    unique_id = str(uuid4())

    topicAnswerDict = answer_data.model_dump()
    topicAnswerDict['id'] = unique_id
    topicAnswerDict['user_id'] = current_user.id
    topicAnswerDict['attachment'] = json.dumps(answer_data.attachment)
    topicAnswerModel = models.TopicAnswer(**topicAnswerDict)

    try:
        db.add(topicAnswerModel)
        db.commit()
        db.refresh(topicAnswerModel)

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message=language_content.get('answer submitted successfully'))

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message=language_content.get('forum topic answer with this id already exists'))


def fav_topic(request: Request, topic_id: str, current_user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    userInDb = db.query(auth_models.User).filter_by(id=current_user.id).first()
    topicInDb = db.query(models.ForumTopic).filter_by(id=topic_id).first()
    if not topicInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('forum topic not found'))

    if topicInDb in userInDb.favorited_topics:
        userInDb.favorited_topics.remove(topicInDb)
        db.commit()
        raise UnicornException(status_code=status.HTTP_200_OK,
                               message=language_content.get('topic removed from favorite topics'))
    else:
        userInDb.favorited_topics.append(topicInDb)
        db.commit()

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message=language_content.get('topic added to favorite topics'))


def get_favorite_topics(current_user: User, db: Session):
    userInDb = db.query(auth_models.User).filter_by(id=current_user.id).first()

    fav_topic_list = []
    for topic in userInDb.favorited_topics:
        topicSchema = schemas.TopicInDb.model_validate(topic)
        topicSchema.user_username = topic.user.profile.username
        topicSchema.user_fullname = topic.user.profile.fullname
        topicSchema.user_profile_pic = topic.user.profile.profile_pic
        topicSchema.user_profile_pic = topicSchema.profile_picture

        fav_topic_list.append(topicSchema)

    return fav_topic_list
