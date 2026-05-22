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
