"""TaniClaw Memory — database operations."""

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from taniclaw.models.plant import Plant
from taniclaw.models.action import Action
from taniclaw.models.history import History, WeatherCache

logger = logging.getLogger("taniclaw.memory")


class Memory:
    """Database operations for TaniClaw.

    All persistence goes through this class.
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def _session(self) -> Session:
        return self.session_factory()

    # ── Plant operations ──────────────────────────────────────────────────────

    def create_plant(self, data: dict) -> Plant:
        with self._session() as session:
            plant = Plant(**data)
            session.add(plant)
            session.commit()
            session.refresh(plant)
            logger.info(f"Created plant: {plant.id} ({plant.name})")
            return self._detach(plant)

    def get_plant(self, plant_id: uuid.UUID) -> Plant | None:
        with self._session() as session:
            plant = session.get(Plant, plant_id)
            if plant:
                session.expunge(plant)
            return plant

    def get_active_plants(self) -> list[Plant]:
        with self._session() as session:
            plants = session.query(Plant).filter(Plant.is_active == True).all()
            for p in plants:
                session.expunge(p)
            return plants

    def get_all_plants(self) -> list[Plant]:
        with self._session() as session:
            plants = session.query(Plant).order_by(Plant.created_at.desc()).all()
            for p in plants:
                session.expunge(p)
            return plants

    def update_plant(self, plant_id: uuid.UUID, data: dict) -> Plant | None:
        with self._session() as session:
            plant = session.get(Plant, plant_id)
            if not plant:
                return None
            for key, value in data.items():
                if hasattr(plant, key):
                    setattr(plant, key, value)
            plant.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(plant)
            session.expunge(plant)
            return plant

    def update_plant_state(self, plant_id: uuid.UUID, new_state: str) -> Plant | None:
        return self.update_plant(plant_id, {
            "current_state": new_state,
            "state_changed_at": datetime.now(timezone.utc),
        })

    def deactivate_plant(self, plant_id: uuid.UUID) -> bool:
        plant = self.update_plant(plant_id, {"is_active": False})
        return plant is not None

    # ── Action operations ─────────────────────────────────────────────────────

    def create_action(self, data: dict) -> Action:
        with self._session() as session:
            action = Action(**data)
            session.add(action)
            session.commit()
            session.refresh(action)
            session.expunge(action)
            return action

    def get_actions(self, plant_id: uuid.UUID, limit: int = 100) -> list[Action]:
        with self._session() as session:
            actions = (
                session.query(Action)
                .filter(Action.plant_id == plant_id)
                .order_by(Action.created_at.desc())
                .limit(limit)
                .all()
            )
            for a in actions:
                session.expunge(a)
            return actions

    def get_pending_actions(self, plant_id: uuid.UUID) -> list[Action]:
        with self._session() as session:
            actions = (
                session.query(Action)
                .filter(Action.plant_id == plant_id, Action.status == "pending")
                .order_by(Action.created_at.desc())
                .all()
            )
            for a in actions:
                session.expunge(a)
            return actions

    def get_today_actions(self, plant_id: uuid.UUID) -> list[Action]:
        today = date.today()
        with self._session() as session:
            actions = (
                session.query(Action)
                .filter(
                    Action.plant_id == plant_id,
                    Action.created_at >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc),
                )
                .order_by(Action.created_at.asc())
                .all()
            )
            for a in actions:
                session.expunge(a)
            return actions

    def get_today_actions_count(self, plant_id: uuid.UUID) -> int:
        return len(self.get_today_actions(plant_id))

    def mark_action_executed(self, action_id: uuid.UUID) -> Action | None:
        with self._session() as session:
            action = session.get(Action, action_id)
            if not action:
                return None
            action.status = "executed"
            action.executed_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(action)
            session.expunge(action)
            return action

    def get_last_action_of_type(self, plant_id: uuid.UUID, action_type: str) -> Action | None:
        with self._session() as session:
            action = (
                session.query(Action)
                .filter(
                    Action.plant_id == plant_id,
                    Action.action_type == action_type,
                    Action.status == "executed",
                )
                .order_by(Action.executed_at.desc())
                .first()
            )
            if action:
                session.expunge(action)
            return action

    def get_days_since_last_action(self, plant_id: uuid.UUID, action_type: str) -> int:
        action = self.get_last_action_of_type(plant_id, action_type)
        if not action or not action.executed_at:
            return 9999  # Never done → treat as "long ago"
        now = datetime.now(timezone.utc)
        executed = action.executed_at
        if executed.tzinfo is None:
            executed = executed.replace(tzinfo=timezone.utc)
        return max(0, (now - executed).days)

    # ── History operations ────────────────────────────────────────────────────

    def add_history(self, plant_id: uuid.UUID, event_type: str, event_data: dict) -> History:
        with self._session() as session:
            history = History(plant_id=plant_id, event_type=event_type, event_data=event_data)
            session.add(history)
            session.commit()
            session.refresh(history)
            session.expunge(history)
            return history

    def get_plant_history(self, plant_id: uuid.UUID, limit: int = 50) -> list[History]:
        with self._session() as session:
            items = (
                session.query(History)
                .filter(History.plant_id == plant_id)
                .order_by(History.created_at.desc())
                .limit(limit)
                .all()
            )
            for h in items:
                session.expunge(h)
            return items

    def get_all_history(self, limit: int = 100) -> list[History]:
        with self._session() as session:
            items = (
                session.query(History)
                .order_by(History.created_at.desc())
                .limit(limit)
                .all()
            )
            for h in items:
                session.expunge(h)
            return items

    # ── Weather cache operations ──────────────────────────────────────────────

    def cache_weather(self, data: dict) -> WeatherCache:
        with self._session() as session:
            # Upsert: delete old entry if exists
            existing = (
                session.query(WeatherCache)
                .filter(
                    WeatherCache.latitude == data["latitude"],
                    WeatherCache.longitude == data["longitude"],
                    WeatherCache.date == data["date"],
                )
                .first()
            )
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
                session.commit()
                session.refresh(existing)
                session.expunge(existing)
                return existing
            else:
                cache = WeatherCache(**data)
                session.add(cache)
                session.commit()
                session.refresh(cache)
                session.expunge(cache)
                return cache

    def get_cached_weather(self, lat: float, lon: float, for_date: date) -> WeatherCache | None:
        with self._session() as session:
            cache = (
                session.query(WeatherCache)
                .filter(
                    WeatherCache.latitude == round(lat, 2),
                    WeatherCache.longitude == round(lon, 2),
                    WeatherCache.date == for_date,
                )
                .first()
            )
            if cache:
                session.expunge(cache)
            return cache

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _detach(obj):
        """Return object after expunge (for use outside session)."""
        return obj
