import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from hub20.apps.core.models.blockchain import Block, Chain, Transaction, TransactionDataRecord
from hub20.apps.core.models.payments import Deposit, PaymentConfirmation
from hub20.apps.core.models.stores import Checkout
from hub20.apps.core.settings import app_settings
from hub20.apps.core.signals import payment_received
from hub20.apps.core.tasks import (
    call_checkout_webhook,
    notify_block_created,
    publish_checkout_event,
    send_session_event,
)

from . import signals
from .constants import Events
from .models import (
    BlockchainPayment,
    BlockchainPaymentRoute,
    BlockchainWithdrawal,
    BlockchainWithdrawalConfirmation,
)

logger = logging.getLogger(__name__)


def _check_for_blockchain_payment_confirmations(block_number):
    confirmed_block = block_number - app_settings.Payment.minimum_confirmations

    unconfirmed_payments = BlockchainPayment.objects.filter(
        confirmation__isnull=True, transaction__block__number__lte=confirmed_block
    )

    for payment in unconfirmed_payments:
        PaymentConfirmation.objects.create(payment=payment)


def _publish_block_created_event(chain_id, block_data):
    block_number = block_data.get("number")
    routes = BlockchainPaymentRoute.objects.in_chain(chain_id).open(block_number=block_number)

    notify_block_created.delay(chain_id, block_data)

    for checkout in Checkout.objects.filter(order__routes__in=routes):
        logger.debug(
            f"Scheduling publish event for checkout {checkout.id}: block #{block_number} created"
        )
        publish_checkout_event.delay(
            checkout.id,
            event=Events.BLOCK_CREATED.value,
            block=block_number,
            chain_id=chain_id,
        )


@receiver(post_save, sender=Chain)
def on_chain_updated_check_payment_confirmations(sender, **kw):
    chain = kw["instance"]
    _check_for_blockchain_payment_confirmations(chain.highest_block)


@receiver(payment_received, sender=BlockchainPayment)
def on_blockchain_payment_received_send_notification(sender, **kw):
    payment = kw["payment"]

    deposit = Deposit.objects.filter(routes__payments=payment).first()

    checkout = Checkout.objects.filter(order__routes__payments=payment).first()

    payment_data = dict(
        amount=str(payment.amount),
        token=payment.currency.address,
        transaction=payment.transaction.hash.hex(),
        block_number=payment.transaction.block.number,
    )

    if deposit and deposit.session_key:
        send_session_event.delay(
            session_key=deposit.session_key,
            event=Events.DEPOSIT_RECEIVED.value,
            deposit_id=str(payment.route.deposit.id),
            **payment_data,
        )

    if checkout:
        publish_checkout_event.delay(
            checkout.id, event=Events.DEPOSIT_RECEIVED.value, **payment_data
        )


@receiver(payment_received, sender=BlockchainPayment)
def on_blockchain_payment_received_call_checkout_webhooks(sender, **kw):
    payment = kw["payment"]

    checkouts = Checkout.objects.filter(order__routes__payments=payment)
    for checkout_id in checkouts.values_list("id", flat=True):
        call_checkout_webhook.delay(checkout_id)


@receiver(signals.incoming_transfer_mined, sender=Transaction)
def on_incoming_transfer_mined_check_blockchain_payments(sender, **kw):
    account = kw["account"]
    amount = kw["amount"]
    transaction = kw["transaction"]

    if BlockchainPayment.objects.filter(transaction=transaction).exists():
        logger.info(f"Transaction {transaction} is already recorded for payment")
        return

    route = BlockchainPaymentRoute.objects.filter(
        deposit__currency=amount.currency,
        account=account,
        payment_window__contains=transaction.block.number,
    ).first()

    if not route:
        return

    payment = BlockchainPayment.objects.create(
        route=route,
        amount=amount.amount,
        currency=amount.currency,
        transaction=transaction,
    )
    payment_received.send(sender=BlockchainPayment, payment=payment)


@receiver(signals.incoming_transfer_broadcast, sender=TransactionDataRecord)
def on_incoming_transfer_broadcast_send_notification_to_active_sessions(sender, **kw):
    recipient = kw["account"]
    payment_amount = kw["amount"]
    tx_data = kw["transaction_data"]

    route = BlockchainPaymentRoute.objects.open().filter(account=recipient).first()

    if not route:
        return

    deposit = Deposit.objects.with_blockchain_route().filter(routes=route).first()

    if deposit and deposit.session_key:
        send_session_event.delay(
            deposit.session_key,
            event=Events.DEPOSIT_BROADCAST.value,
            deposit_id=str(deposit.id),
            amount=str(payment_amount.amount),
            token=payment_amount.currency.address,
            transaction=tx_data.hash.hex(),
        )


@receiver(signals.incoming_transfer_broadcast, sender=TransactionDataRecord)
def on_incoming_transfer_broadcast_send_notification_to_open_checkouts(sender, **kw):
    recipient = kw["account"]
    payment_amount = kw["amount"]
    tx_data = kw["transaction_data"]

    route = BlockchainPaymentRoute.objects.open().filter(account=recipient).first()

    if not route:
        return

    checkout = Checkout.objects.filter(order__routes=route).first()

    if checkout:
        publish_checkout_event.delay(
            checkout.id,
            event=Events.DEPOSIT_BROADCAST.value,
            amount=str(payment_amount.amount),
            token=payment_amount.currency.address,
            transaction=tx_data.hash.hex(),
        )


@receiver(signals.block_sealed, sender=Block)
def on_block_sealed_publish_block_created_event(sender, **kw):
    block_data = kw["block_data"]
    chain_id = kw["chain_id"]
    logger.debug(f"Handling block sealed notification of new block on chain #{chain_id}")
    _publish_block_created_event(chain_id=chain_id, block_data=block_data)


@receiver(signals.block_sealed, sender=Block)
def on_block_sealed_check_confirmed_payments(sender, **kw):
    block_data = kw["block_data"]
    _check_for_blockchain_payment_confirmations(block_data.get("number"))


@receiver(post_save, sender=Block)
def on_block_created_check_confirmed_payments(sender, **kw):
    if kw["created"]:
        block = kw["instance"]
        _check_for_blockchain_payment_confirmations(block.number)


@receiver(signals.block_sealed, sender=Block)
def on_block_added_publish_expired_blockchain_routes(sender, **kw):
    block_data = kw["block_data"]
    block_number = block_data["number"]

    expiring_routes = BlockchainPaymentRoute.objects.filter(
        payment_window__endswith=block_number - 1
    )

    for route in expiring_routes:
        publish_checkout_event.delay(
            route.deposit_id,
            event=Events.ROUTE_EXPIRED.value,
            route=route.account.address,
        )


@receiver(signals.outgoing_transfer_mined, sender=Transaction)
def on_blockchain_transfer_mined_record_confirmation(sender, **kw):
    amount = kw["amount"]
    transaction = kw["transaction"]
    address = kw["address"]

    transfer = BlockchainWithdrawal.processed.filter(
        amount=amount.amount,
        currency=amount.currency,
        address=address,
        receipt__blockchainwithdrawalreceipt__transaction_data__hash=transaction.hash,
    ).first()

    if transfer:
        BlockchainWithdrawalConfirmation.objects.create(transfer=transfer, transaction=transaction)


__all__ = [
    "on_chain_updated_check_payment_confirmations",
    "on_blockchain_payment_received_send_notification",
    "on_incoming_transfer_mined_check_blockchain_payments",
    "on_incoming_transfer_broadcast_send_notification_to_active_sessions",
    "on_incoming_transfer_broadcast_send_notification_to_open_checkouts",
    "on_block_sealed_publish_block_created_event",
    "on_block_sealed_check_confirmed_payments",
    "on_block_created_check_confirmed_payments",
    "on_block_added_publish_expired_blockchain_routes",
    "on_blockchain_transfer_mined_record_confirmation",
]