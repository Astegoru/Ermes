from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: str
    external_username: str
    display_name: Optional[str]
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]


@dataclass
class Category:
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    merged_into_category_id: Optional[str]
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


@dataclass
class Ticket:
    id: str
    title: str
    urgency: int
    category_id: str
    link: Optional[str]
    file_url: Optional[str]
    file_type: Optional[str]
    description: Optional[str]
    owner_user_id: str
    status: str
    solved_at: Optional[datetime]
    deleted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass
class UserProfile:
    user_id: str
    role: str
    profiled_by: Optional[str]
    updated_at: datetime


@dataclass
class TicketComment:
    id: str
    ticket_id: str
    author_user_id: str
    parent_comment_id: Optional[str]
    body: str
    mark_type: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class CommentMention:
    id: int
    comment_id: str
    mentioned_user_id: str
    created_at: datetime


@dataclass
class Notification:
    id: int
    user_id: str
    ticket_id: str
    comment_id: Optional[str]
    kind: str
    payload: dict
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
