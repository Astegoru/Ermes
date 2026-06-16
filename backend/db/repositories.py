from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client


class RepositoryError(Exception):
    pass


class Repositories:
    def __init__(self, client: Client):
        self.client = client

    @staticmethod
    def _single(response: Any) -> dict[str, Any]:
        data = getattr(response, "data", None)
        if not data:
            raise RepositoryError("Record not found")
        if isinstance(data, list):
            return data[0]
        return data

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def upsert_user(self, external_username: str, display_name: Optional[str] = None) -> dict[str, Any]:
        payload = {
            "external_username": external_username,
            "display_name": display_name,
            "is_active": True,
            "last_login_at": self._now_iso(),
        }
        response = (
            self.client.table("users")
            .upsert(payload, on_conflict="external_username")
            .execute()
        )
        return self._single(response)

    def get_user_by_id(self, user_id: str) -> dict[str, Any]:
        response = self.client.table("users").select("*").eq("id", user_id).limit(1).execute()
        return self._single(response)

    def get_users_by_ids(self, user_ids: list[str]) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        response = (
            self.client.table("users")
            .select("id, external_username")
            .in_("id", user_ids)
            .execute()
        )
        return getattr(response, "data", []) or []

    def get_users_by_external_usernames(self, usernames: list[str]) -> list[dict[str, Any]]:
        if not usernames:
            return []
        response = (
            self.client.table("users")
            .select("id, external_username")
            .in_("external_username", usernames)
            .execute()
        )
        return getattr(response, "data", []) or []

    def list_users(self) -> list[dict[str, Any]]:
        response = (
            self.client.table("users")
            .select("id, external_username, display_name, created_at, last_login_at, is_active")
            .order("created_at", desc=True)
            .execute()
        )
        return getattr(response, "data", []) or []

    def list_user_profiles(self, user_ids: list[str]) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        response = (
            self.client.table("user_profiles")
            .select("user_id, role, profiled_by, updated_at")
            .in_("user_id", user_ids)
            .execute()
        )
        return getattr(response, "data", []) or []

    def get_user_role(self, user_id: str) -> str:
        response = (
            self.client.table("user_profiles")
            .select("role")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        data = getattr(response, "data", []) or []
        if not data:
            return "outsider"
        return (data[0].get("role") or "outsider").lower()

    def upsert_user_profile(self, user_id: str, role: str, profiled_by: str) -> dict[str, Any]:
        payload = {
            "user_id": user_id,
            "role": role.lower(),
            "profiled_by": profiled_by,
            "updated_at": self._now_iso(),
        }
        response = self.client.table("user_profiles").upsert(payload, on_conflict="user_id").execute()
        return self._single(response)

    def get_user_by_external_username(self, username: str) -> dict[str, Any]:
        response = (
            self.client.table("users")
            .select("*")
            .eq("external_username", username)
            .limit(1)
            .execute()
        )
        return self._single(response)

    def create_category(self, data: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table("categories").insert(data).execute()
        return self._single(response)

    def list_active_categories(self) -> list[dict[str, Any]]:
        response = (
            self.client.table("categories")
            .select("*")
            .eq("is_active", True)
            .order("name")
            .execute()
        )
        return getattr(response, "data", []) or []

    def get_category(self, category_id: str) -> dict[str, Any]:
        response = self.client.table("categories").select("*").eq("id", category_id).limit(1).execute()
        return self._single(response)

    def update_category(self, category_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        updates["updated_at"] = self._now_iso()
        response = self.client.table("categories").update(updates).eq("id", category_id).execute()
        return self._single(response)

    def merge_categories(self, source_ids: list[str], target_id: str, actor_user_id: str) -> dict[str, Any]:
        if target_id in source_ids:
            raise RepositoryError("Target category cannot be merged into itself")

        self.client.table("tickets").update({"category_id": target_id}).in_("category_id", source_ids).execute()

        self.client.table("categories").update(
            {
                "is_active": False,
                "merged_into_category_id": target_id,
                "updated_at": self._now_iso(),
            }
        ).in_("id", source_ids).execute()

        self.create_event(
            ticket_id=None,
            actor_user_id=actor_user_id,
            event_type="category_merged",
            metadata={"source_ids": source_ids, "target_id": target_id},
        )
        return {"source_ids": source_ids, "target_id": target_id}

    def create_ticket(self, data: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table("tickets").insert(data).execute()
        created = self._single(response)
        self.create_event(
            ticket_id=created["id"],
            actor_user_id=created["owner_user_id"],
            event_type="created",
            metadata={},
        )
        return created

    def list_tickets(
        self,
        sort_field: str = "urgency",
        sort_desc: bool = True,
        status: Optional[str] = None,
        statuses: Optional[list[str]] = None,
        category_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query = self.client.table("tickets").select("*").is_("deleted_at", "null")
        if statuses:
            query = query.in_("status", statuses)
        elif status:
            query = query.eq("status", status)
        if category_id:
            query = query.eq("category_id", category_id)

        query = query.order(sort_field, desc=sort_desc)
        if sort_field != "created_at":
            query = query.order("created_at", desc=True)

        response = query.execute()
        return getattr(response, "data", []) or []

    def list_deleted_tickets(
        self,
        sort_desc: bool = True,
        category_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query = self.client.table("tickets").select("*").not_.is_("deleted_at", "null")
        if category_id:
            query = query.eq("category_id", category_id)
        if owner_user_id:
            query = query.eq("owner_user_id", owner_user_id)

        query = query.order("deleted_at", desc=sort_desc).order("created_at", desc=True)
        response = query.execute()
        return getattr(response, "data", []) or []

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        response = self.client.table("tickets").select("*").eq("id", ticket_id).limit(1).execute()
        return self._single(response)

    def update_ticket(self, ticket_id: str, updates: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        updates["updated_at"] = self._now_iso()
        response = self.client.table("tickets").update(updates).eq("id", ticket_id).execute()
        ticket = self._single(response)
        self.create_event(ticket_id=ticket_id, actor_user_id=actor_user_id, event_type="edited", metadata=updates)
        return ticket

    def mark_in_progress(self, ticket_id: str, actor_user_id: str) -> dict[str, Any]:
        updates = {
            "status": "in_progress",
            "updated_at": self._now_iso(),
        }
        response = self.client.table("tickets").update(updates).eq("id", ticket_id).execute()
        ticket = self._single(response)
        self.create_event(ticket_id=ticket_id, actor_user_id=actor_user_id, event_type="in_progress", metadata={})
        return ticket

    def solve_ticket(self, ticket_id: str, actor_user_id: str) -> dict[str, Any]:
        updates = {
            "status": "solved",
            "solved_at": self._now_iso(),
            "solved_by_user_id": actor_user_id,
            "updated_at": self._now_iso(),
        }
        response = self.client.table("tickets").update(updates).eq("id", ticket_id).execute()
        ticket = self._single(response)
        self.create_event(ticket_id=ticket_id, actor_user_id=actor_user_id, event_type="solved", metadata={})
        return ticket

    def soft_delete_ticket(self, ticket_id: str, actor_user_id: str) -> dict[str, Any]:
        updates = {
            "deleted_at": self._now_iso(),
            "status": "deleted_soft",
            "updated_at": self._now_iso(),
        }
        response = self.client.table("tickets").update(updates).eq("id", ticket_id).execute()
        ticket = self._single(response)
        self.create_event(ticket_id=ticket_id, actor_user_id=actor_user_id, event_type="deleted_soft", metadata={})
        return ticket

    def restore_ticket(self, ticket_id: str, actor_user_id: str) -> dict[str, Any]:
        updates = {
            "deleted_at": None,
            "status": "open",
            "updated_at": self._now_iso(),
        }
        response = self.client.table("tickets").update(updates).eq("id", ticket_id).execute()
        ticket = self._single(response)
        self.create_event(ticket_id=ticket_id, actor_user_id=actor_user_id, event_type="restored", metadata={})
        return ticket

    def purge_ticket(self, ticket_id: str, actor_user_id: str) -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        self.client.table("ticket_events").delete().eq("ticket_id", ticket_id).execute()
        self.client.table("tickets").delete().eq("id", ticket_id).execute()
        self.create_event(
            ticket_id=None,
            actor_user_id=actor_user_id,
            event_type="deleted_hard",
            metadata={"ticket_id": ticket_id, "title": ticket.get("title")},
        )
        return ticket

    def create_event(
        self,
        ticket_id: Optional[str],
        actor_user_id: str,
        event_type: str,
        metadata: dict[str, Any],
    ) -> None:
        payload = {
            "ticket_id": ticket_id,
            "actor_user_id": actor_user_id,
            "event_type": event_type,
            "metadata": metadata,
            "created_at": self._now_iso(),
        }
        self.client.table("ticket_events").insert(payload).execute()

    def list_ticket_comments(self, ticket_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("ticket_comments")
            .select("*")
            .eq("ticket_id", ticket_id)
            .order("created_at", desc=False)
            .execute()
        )
        return getattr(response, "data", []) or []

    def get_ticket_comment(self, comment_id: str) -> dict[str, Any]:
        response = self.client.table("ticket_comments").select("*").eq("id", comment_id).limit(1).execute()
        return self._single(response)

    def create_ticket_comment(self, data: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table("ticket_comments").insert(data).execute()
        return self._single(response)

    def update_ticket_comment(self, comment_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table("ticket_comments").update(updates).eq("id", comment_id).execute()
        return self._single(response)

    def delete_ticket_comment(self, comment_id: str) -> None:
        self.client.table("ticket_comments").delete().eq("id", comment_id).execute()

    def delete_comment_mentions(self, comment_id: str) -> None:
        self.client.table("comment_mentions").delete().eq("comment_id", comment_id).execute()

    def create_comment_mentions(self, comment_id: str, mentioned_user_ids: list[str]) -> list[dict[str, Any]]:
        if not mentioned_user_ids:
            return []
        payload = [
            {
                "comment_id": comment_id,
                "mentioned_user_id": user_id,
                "created_at": self._now_iso(),
            }
            for user_id in sorted(set(mentioned_user_ids))
        ]
        response = self.client.table("comment_mentions").insert(payload).execute()
        return getattr(response, "data", []) or []

    def list_comment_mentions(self, comment_ids: list[str]) -> list[dict[str, Any]]:
        if not comment_ids:
            return []
        response = (
            self.client.table("comment_mentions")
            .select("comment_id, mentioned_user_id")
            .in_("comment_id", comment_ids)
            .execute()
        )
        return getattr(response, "data", []) or []

    def create_notifications(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self.client.table("notifications").insert(rows).execute()
        return getattr(response, "data", []) or []

    def list_notifications(self, user_id: str, unread_only: bool = False) -> list[dict[str, Any]]:
        query = (
            self.client.table("notifications")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        if unread_only:
            query = query.eq("is_read", False)
        response = query.limit(100).execute()
        return getattr(response, "data", []) or []

    def mark_notification_read(self, notification_id: int, user_id: str) -> dict[str, Any]:
        response = (
            self.client.table("notifications")
            .update({"is_read": True, "read_at": self._now_iso()})
            .eq("id", notification_id)
            .eq("user_id", user_id)
            .execute()
        )
        return self._single(response)

    def get_superuser(self) -> Optional[dict[str, Any]]:
        response = self.client.table("app_meta").select("*").eq("key", "superuser_id").limit(1).execute()
        data = getattr(response, "data", []) or []
        return data[0] if data else None

    def assign_superuser(self, user_id: str, actor: str) -> dict[str, Any]:
        payload = {
            "key": "superuser_id",
            "value": user_id,
            "updated_by": actor,
            "updated_at": self._now_iso(),
        }
        response = self.client.table("app_meta").upsert(payload, on_conflict="key").execute()
        return self._single(response)
