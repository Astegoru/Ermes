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
