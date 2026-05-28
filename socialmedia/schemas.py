from pydantic import BaseModel


class PostStatus(BaseModel):
    status_url: str


class StatusInDb(PostStatus):
    full_name: str
    user_profile_pic: str
