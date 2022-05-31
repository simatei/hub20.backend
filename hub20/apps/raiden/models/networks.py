from __future__ import annotations

from django.db import models

from hub20.apps.core.models.networks import PaymentNetwork
from hub20.apps.ethereum.models import Chain


class RaidenPaymentNetwork(PaymentNetwork):
    chain = models.OneToOneField(Chain, on_delete=models.CASCADE)


__all__ = ["RaidenPaymentNetwork"]
