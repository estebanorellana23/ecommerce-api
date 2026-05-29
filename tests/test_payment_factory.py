"""Pruebas del patrón Factory de pasarelas de pago (OCP)."""
from decimal import Decimal

import pytest

from app.payments.gateway import (
    IPaymentGateway,
    PaymentConfig,
    PaymentGatewayFactory,
    PayPalGateway,
    VisaNetGateway,
)


def test_factory_crea_visanet():
    gw = PaymentGatewayFactory.create("visanet", PaymentConfig())
    assert isinstance(gw, VisaNetGateway)
    assert isinstance(gw, IPaymentGateway)


def test_factory_crea_paypal():
    gw = PaymentGatewayFactory.create("paypal", PaymentConfig())
    assert isinstance(gw, PayPalGateway)


def test_factory_pasarela_desconocida_falla():
    with pytest.raises(ValueError):
        PaymentGatewayFactory.create("stripe", PaymentConfig())


def test_charge_sin_token_es_rechazado():
    gw = PaymentGatewayFactory.create("visanet", PaymentConfig())
    result = gw.charge(Decimal("100.00"), "")
    assert result.success is False


def test_ocp_registrar_nueva_pasarela_sin_modificar_codigo():
    """Open/Closed: se agrega una pasarela nueva solo registrándola."""

    class FakeGateway(VisaNetGateway):
        pass

    PaymentGatewayFactory.register("fake", FakeGateway)
    gw = PaymentGatewayFactory.create("fake", PaymentConfig())
    assert isinstance(gw, FakeGateway)
