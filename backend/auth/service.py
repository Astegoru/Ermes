from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import requests
from flask import current_app

from backend.db.repositories import Repositories


class AuthenticationError(Exception):
    pass


def verify_facts_credentials(username: str, password: str) -> dict[str, Any]:
    response = requests.post(
        current_app.config["FACTS_TOKEN_URL"],
        json={"username": username, "password": password},
        timeout=10,
    )

    if response.status_code >= 400:
        payload = response.json() if response.content else {}
        detail = payload.get("detail", "Authentication failed")
        if detail == "No active account found with the given credentials":
            raise AuthenticationError("Invalid FACTS credentials")
        raise AuthenticationError(detail)

    return response.json()


def issue_tokens(user: dict[str, Any]) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    access_exp = now + timedelta(minutes=current_app.config["JWT_ACCESS_MINUTES"])
    refresh_exp = now + timedelta(days=current_app.config["JWT_REFRESH_DAYS"])

    access_payload = {
        "sub": user["id"],
        "username": user["external_username"],
        "type": "access",
        "exp": int(access_exp.timestamp()),
        "iat": int(now.timestamp()),
    }
    refresh_payload = {
        "sub": user["id"],
        "username": user["external_username"],
        "type": "refresh",
        "exp": int(refresh_exp.timestamp()),
        "iat": int(now.timestamp()),
    }

    secret = current_app.config["JWT_SECRET"]
    return {
        "access_token": jwt.encode(access_payload, secret, algorithm="HS256"),
        "refresh_token": jwt.encode(refresh_payload, secret, algorithm="HS256"),
    }


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    payload = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise AuthenticationError("Invalid token type")
    return payload


def login_with_facts(repo: Repositories, username: str, password: str) -> dict[str, Any]:
    verify_facts_credentials(username=username, password=password)
    user = repo.upsert_user(external_username=username)
    tokens = issue_tokens(user)
    return {
        "user": {
            "id": user["id"],
            "external_username": user["external_username"],
            "display_name": user.get("display_name"),
        },
        **tokens,
    }
