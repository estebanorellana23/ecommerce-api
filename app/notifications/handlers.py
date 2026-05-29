"""Patrón Factory para canales de notificación.

Agregar un canal nuevo (SMS, Slack) no requiere modificar el código existente,
solo registrar un handler nuevo (Open/Closed Principle). Ver nota 07 — Factory.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger("notifications")


@dataclass
class NotificationConfig:
    purchasing_team_emails: list[str] = field(default_factory=list)
    # Canales a usar por tipo de evento, p.ej. {"low_stock": ["email", "push"]}
    event_channels: dict[str, list[str]] = field(default_factory=dict)

    def channels_for_event(self, event_type: str) -> list[str]:
        return self.event_channels.get(event_type, ["email"])


class INotificationHandler(ABC):
    @abstractmethod
    def send(self, subject: str, body: str, recipients: list[str]) -> None: ...


class EmailNotificationHandler(INotificationHandler):
    def __init__(self, config: NotificationConfig):
        self._config = config

    def send(self, subject: str, body: str, recipients: list[str]) -> None:
        # En producción: integración SMTP. Aquí se registra el envío.
        logger.info("[EMAIL] -> %s | %s | %s", recipients, subject, body)


class PushNotificationHandler(INotificationHandler):
    def __init__(self, config: NotificationConfig):
        self._config = config

    def send(self, subject: str, body: str, recipients: list[str]) -> None:
        logger.info("[PUSH] -> %s | %s | %s", recipients, subject, body)


class NotificationFactory:
    """Registro y creación de handlers de notificación por canal."""

    _handlers: dict[str, type[INotificationHandler]] = {}

    @classmethod
    def register(cls, channel: str, handler: type[INotificationHandler]) -> None:
        cls._handlers[channel] = handler

    @classmethod
    def create(cls, channel: str, config: NotificationConfig) -> INotificationHandler:
        if channel not in cls._handlers:
            raise ValueError(f"Canal de notificación no registrado: {channel}")
        return cls._handlers[channel](config)

    @classmethod
    def create_for_event(
        cls, event_type: str, config: NotificationConfig
    ) -> list[INotificationHandler]:
        return [cls.create(ch, config) for ch in config.channels_for_event(event_type)]


# Registro de implementaciones (bootstrap de la aplicación)
NotificationFactory.register("email", EmailNotificationHandler)
NotificationFactory.register("push", PushNotificationHandler)
