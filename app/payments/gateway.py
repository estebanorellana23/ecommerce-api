"""Pasarelas de pago — Patrón Factory + Open/Closed Principle.

``CheckoutService`` depende de la abstracción ``IPaymentGateway`` (DIP). Agregar
una pasarela nueva (Stripe, PagoFácil) no obliga a tocar el proceso de checkout.
Ver nota 07 — secciones O (Open/Closed) y Factory.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.domain.value_objects import PaymentResult, RefundResult


class IPaymentGateway(ABC):
    @abstractmethod
    def charge(self, amount: Decimal, token: str) -> PaymentResult: ...

    @abstractmethod
    def refund(self, transaction_id: str, amount: Decimal) -> RefundResult: ...


@dataclass
class PaymentConfig:
    api_key: str = "test"
    endpoint: str = "https://sandbox.local"


class VisaNetGateway(IPaymentGateway):
    """Integración con VisaNet Guatemala (pagos nacionales Visa/Mastercard)."""

    def __init__(self, config: PaymentConfig):
        self._config = config

    def charge(self, amount: Decimal, token: str) -> PaymentResult:
        if not token:
            return PaymentResult(False, "", "Token de pago ausente")
        return PaymentResult(True, f"visanet_{uuid.uuid4().hex[:12]}", "Aprobado")

    def refund(self, transaction_id: str, amount: Decimal) -> RefundResult:
        return RefundResult(True, f"rf_{uuid.uuid4().hex[:12]}", "Reembolso aprobado")


class PayPalGateway(IPaymentGateway):
    """Integración con PayPal API v2 (clientes internacionales — versión futura)."""

    def __init__(self, config: PaymentConfig):
        self._config = config

    def charge(self, amount: Decimal, token: str) -> PaymentResult:
        if not token:
            return PaymentResult(False, "", "Token de pago ausente")
        return PaymentResult(True, f"paypal_{uuid.uuid4().hex[:12]}", "COMPLETED")

    def refund(self, transaction_id: str, amount: Decimal) -> RefundResult:
        return RefundResult(True, f"rf_{uuid.uuid4().hex[:12]}", "Reembolso aprobado")


class PaymentGatewayFactory:
    """Registro y creación de pasarelas en tiempo de ejecución."""

    _registry: dict[str, type[IPaymentGateway]] = {}

    @classmethod
    def register(cls, name: str, gateway: type[IPaymentGateway]) -> None:
        cls._registry[name] = gateway

    @classmethod
    def create(cls, name: str, config: PaymentConfig) -> IPaymentGateway:
        if name not in cls._registry:
            raise ValueError(f"Pasarela de pago no registrada: {name}")
        return cls._registry[name](config)


PaymentGatewayFactory.register("visanet", VisaNetGateway)
PaymentGatewayFactory.register("paypal", PayPalGateway)
