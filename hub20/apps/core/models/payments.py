import datetime
import logging
import random
import uuid
from typing import Optional

from django.conf import settings
from django.db import models
from django.db.models import F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from model_utils.managers import InheritanceManager
from model_utils.models import TimeStampedModel

from ..choices import DEPOSIT_STATUS
from .networks import PaymentNetwork
from .tokens import BaseToken, TokenAmountField, TokenValueModel

logger = logging.getLogger(__name__)


def generate_payment_route_id():
    # Default payment identifier generated by Raiden's web UI is based on unix
    # time. We would like to make the distinction between payment ids
    # generated by default and those generated by us.

    LOWER_BOUND = 2**48  # Enough to take us to the year 10889.
    UPPER_BOUND = 2**53 - 1  # Javascript can not handle numbers bigger than 2^53 - 1

    return random.randint(LOWER_BOUND, UPPER_BOUND)


class PaymentOrderQuerySet(models.QuerySet):
    def unpaid(self):
        q_no_payment = Q(total_paid__isnull=True)
        q_low_payment = Q(total_paid__lt=F("amount"))

        return self.annotate(total_paid=Sum("routes__payments__amount")).filter(
            q_no_payment | q_low_payment
        )

    def paid(self):
        return self.annotate(total_paid=Sum("routes__payments__amount")).filter(
            total_paid__gte=F("amount")
        )


class PaymentRouteQuerySet(models.QuerySet):
    def with_payment_amounts(self) -> models.QuerySet:
        return self.annotate(
            currency=F("payments__currency"),
            total_paid=Coalesce(
                Sum("payments__amount"), Value(0), output_field=TokenAmountField()
            ),
            total_confirmed=Coalesce(
                Sum("payments__amount", filter=Q(payments__confirmation__isnull=False)),
                Value(0),
                output_field=TokenAmountField(),
            ),
        )

    def used(self) -> models.QuerySet:
        return self.with_payment_amounts().filter(
            total_paid__gte=F("deposit__amount"), currency=F("deposit__currency")
        )


class InternalPaymentRouteQuerySet(PaymentRouteQuerySet):
    def available(self, at: Optional[datetime.datetime] = None) -> models.QuerySet:
        date_value = at or timezone.now()
        return self.filter(created__lte=date_value)


class Deposit(TimeStampedModel):
    STATUS = DEPOSIT_STATUS

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    network = models.ForeignKey(PaymentNetwork, on_delete=models.PROTECT)
    session_key = models.SlugField(null=True)
    currency = models.ForeignKey(BaseToken, on_delete=models.PROTECT)

    @property
    def payments(self):
        return Payment.objects.filter(route__deposit=self).select_subclasses()

    @property
    def confirmed_payments(self):
        return self.payments.filter(confirmation__isnull=False)

    @property
    def total_transferred(self):
        return self.payments.aggregate(total=Sum("amount")).get("total") or 0

    @property
    def total_confirmed(self):
        return self.confirmed_payments.aggregate(total=Sum("amount")).get("total") or 0

    @property
    def is_expired(self):
        return all([route.is_expired for route in self.routes.select_subclasses()])

    @property
    def status(self):
        return self.STATUS.expired if self.is_expired else self.STATUS.open


class PaymentOrder(Deposit, TokenValueModel):
    reference = models.CharField(max_length=200, null=True, blank=True)
    objects = PaymentOrderQuerySet.as_manager()

    @property
    def due_amount(self):
        return max(0, self.amount - self.total_transferred)

    @property
    def is_paid(self):
        return self.due_amount <= 0

    @property
    def is_confirmed(self):
        return self.is_paid and self.total_confirmed >= self.amount

    @property
    def status(self):
        if self.is_confirmed:
            return self.STATUS.confirmed
        elif self.is_paid:
            return self.STATUS.paid
        else:
            return self.STATUS.open


class PaymentRoute(TimeStampedModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    deposit = models.ForeignKey(Deposit, on_delete=models.CASCADE, related_name="routes")
    identifier = models.BigIntegerField(default=generate_payment_route_id, unique=True)
    objects = InheritanceManager()

    @property
    def network(self):
        return self._get_route_network_name()

    @property
    def is_expired(self):
        return False

    @property
    def is_used(self):
        return self.payments.exists()

    @property
    def is_open(self):
        return not self.is_expired

    def _get_route_network_name(self):
        if not self.NETWORK:
            route = PaymentRoute.objects.get_subclass(id=self.id)
            return route.NETWORK
        return self.NETWORK

    @classmethod
    def is_usable_for_token(cls, token: BaseToken):
        return False

    @classmethod
    def make(cls, deposit):
        raise NotImplementedError


class InternalPaymentRoute(PaymentRoute):
    NETWORK = "internal"

    objects = InternalPaymentRouteQuerySet.as_manager()


class Payment(TimeStampedModel, TokenValueModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    route = models.ForeignKey(PaymentRoute, on_delete=models.PROTECT, related_name="payments")
    objects = InheritanceManager()

    @property
    def is_confirmed(self):
        return hasattr(self, "confirmation")


class InternalPayment(Payment):
    memo = models.TextField(null=True, blank=True)

    @property
    def identifier(self):
        return str(self.id)


class PaymentConfirmation(TimeStampedModel):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="confirmation")


__all__ = [
    "Deposit",
    "PaymentOrder",
    "PaymentRoute",
    "PaymentRouteQuerySet",
    "InternalPaymentRoute",
    "Payment",
    "InternalPayment",
    "PaymentConfirmation",
]
