import logging
from contextlib import contextmanager
from hashlib import md5

import celery_pubsub
from celery import shared_task
from django.core.cache import cache
from django.db.transaction import atomic
from requests.exceptions import ConnectionError
from web3 import Web3
from web3.exceptions import ExtraDataLengthError

from .analytics import MAX_PRIORITY_FEE_TRACKER, get_historical_block_data
from .app_settings import BLOCK_SCAN_RANGE
from .client import inspect_web3, make_web3
from .models import BaseEthereumAccount, Block, Transaction, Web3Provider
from .signals import block_sealed

logger = logging.getLogger(__name__)


@contextmanager
def stream_processor_lock(provider, oid, timeout):
    logger.info(f"Getting lock for {provider.url}")
    lock_id = md5(provider.url.encode()).hexdigest()

    # cache.add fails if the key already exists
    status = cache.add(lock_id, oid, timeout)
    try:
        yield status
    finally:
        # release lock if we are the ones that acquired it
        if status:
            cache.delete(lock_id)


# Tasks that are processing event logs from the blockchain (should
# have only one at a time)
@shared_task(bind=True)
def process_mined_blocks(self):
    # Conservatively, we can process 10 blocks per second, so let's give
    # double the time for the lock

    # TODO: make the timeout specific to the chain average block time
    lock_ttl = (2 * BLOCK_SCAN_RANGE) / 10

    for provider in Web3Provider.available.select_related("chain"):
        try:
            with stream_processor_lock(provider, self.app.oid, lock_ttl) as acquired:
                if acquired:
                    chain = provider.chain
                    w3: Web3 = make_web3(provider=provider)
                    logger.info(f"Getting blocks for {chain.name}")
                    current_block = w3.eth.block_number
                    start = chain.highest_block
                    stop = min(current_block, chain.highest_block + BLOCK_SCAN_RANGE)
                    for block_number in range(start, stop):
                        logger.debug(f"Getting block #{block_number} from {chain}")
                        block_data = w3.eth.get_block(block_number, full_transactions=True)
                        block_number = block_data.number
                        logger.info(f"Processing block #{block_number} on {provider}")
                        celery_pubsub.publish(
                            "blockchain.mined.block",
                            chain_id=w3.eth.chain_id,
                            block_data=block_data,
                            provider_url=provider.url,
                        )
                        chain.highest_block = block_number
                        logger.debug(f"Updating chain height to {block_number}")
                    chain.save()
        except ExtraDataLengthError:
            logger.error(f"Failed to get block info from {provider.hostname}")


# Tasks that are meant to be run periodically
@shared_task
def reset_inactive_providers():
    Web3Provider.objects.filter(is_active=False).update(synced=False, connected=False)


@shared_task
def refresh_max_priority_fee():
    for provider in Web3Provider.available.filter(supports_eip1559=True):
        try:
            w3 = make_web3(provider=provider)
            MAX_PRIORITY_FEE_TRACKER.set(w3.eth.chain_id, w3.eth.max_priority_fee)
        except Exception as exc:
            logger.info(f"Failed to get max priority fee from {provider.hostname}: {exc}")


@shared_task
def check_providers_configuration():
    for provider in Web3Provider.active.all():
        w3 = make_web3(provider=provider)
        configuration = inspect_web3(w3=w3)
        Web3Provider.objects.filter(id=provider.id).update(**configuration.dict())


@shared_task
def check_providers_are_connected():
    for provider in Web3Provider.active.all():
        logger.info(f"Checking status from {provider.hostname}")
        try:
            w3 = make_web3(provider=provider)
            is_online = w3.isConnected() and (w3.net.peer_count > 0)
        except ConnectionError:
            is_online = False
        except ValueError:
            # The node does not support the peer count method. Assume healthy.
            is_online = w3.isConnected()

        if provider.connected and not is_online:
            logger.info(f"Node {provider.hostname} went offline")
            celery_pubsub.publish(
                "node.connection.nok", chain_id=provider.chain_id, provider_url=provider.url
            )

        elif is_online and not provider.connected:
            logger.info(f"Node {provider.hostname} is back online")
            celery_pubsub.publish(
                "node.connection.ok", chain_id=provider.chain_id, provider_url=provider.url
            )


@shared_task
def check_providers_are_synced():
    for provider in Web3Provider.active.all():
        try:
            w3 = make_web3(provider=provider)
            is_synced = bool(not w3.eth.syncing)
        except (ValueError, AttributeError):
            # The node does not support the eth_syncing method. Assume healthy.
            is_synced = True
        except ConnectionError:
            continue

        if provider.synced and not is_synced:
            celery_pubsub.publish(
                "node.sync.nok", chain_id=provider.chain_id, provider_url=provider.url
            )
        elif is_synced and not provider.synced:
            logger.info(f"Node {provider.hostname} is back in sync")
            celery_pubsub.publish(
                "node.sync.ok", chain_id=provider.chain_id, provider_url=provider.url
            )


@shared_task
def check_chains_were_reorganized():
    for provider in Web3Provider.active.all():
        with atomic():
            chain = provider.chain
            w3 = make_web3(provider=provider)
            block_number = w3.eth.block_number

            if chain.highest_block > block_number:
                chain.blocks.filter(number__gt=block_number).delete()

            chain.highest_block = block_number
            chain.save()


# Tasks that are setup to subscribe and handle events generated by the event streams
@shared_task
def save_historical_data(chain_id, block_data, provider_url):
    logger.debug(f"Adding {block_data} to {chain_id} historical data")
    block_history = get_historical_block_data(chain_id)
    block_history.push(block_data)


@shared_task
def notify_new_block(chain_id, block_data, provider_url):
    block_sealed.send(sender=Block, chain_id=chain_id, block_data=block_data)


@shared_task
def record_account_transactions(chain_id, block_data, provider_url):

    addresses = BaseEthereumAccount.objects.values_list("address", flat=True)

    txs = [
        t for t in block_data["transactions"] if (t["from"] in addresses or t["to"] in addresses)
    ]

    if len(txs) > 0:
        provider = Web3Provider.objects.get(url=provider_url)
        w3 = make_web3(provider=provider)
        assert chain_id == w3.eth.chain_id, f"{provider.hostname} not on chain #{chain_id}"

        for tx_data in txs:
            transaction_receipt = w3.eth.get_transaction_receipt(tx_data.hash)
            tx = Transaction.make(
                chain_id=chain_id,
                tx_receipt=transaction_receipt,
                block_data=block_data,
            )
            for account in BaseEthereumAccount.objects.filter(
                address__in=[tx.from_address, tx.to_address]
            ):
                account.transactions.add(tx)


@shared_task
def set_node_connection_ok(chain_id, provider_url):
    logger.info(f"Setting node {provider_url} to online")
    Web3Provider.objects.filter(chain_id=chain_id, url=provider_url).update(connected=True)


@shared_task
def set_node_connection_nok(chain_id, provider_url):
    logger.info(f"Setting node {provider_url} to offline")
    Web3Provider.objects.filter(chain_id=chain_id, url=provider_url).update(connected=False)


@shared_task
def set_node_sync_ok(chain_id, provider_url):
    logger.info(f"Setting node {provider_url} to sync")
    Web3Provider.objects.filter(chain_id=chain_id, url=provider_url).update(synced=True)


@shared_task
def set_node_sync_nok(chain_id, provider_url):
    logger.info(f"Setting node {provider_url} to out-of-sync")
    Web3Provider.objects.filter(chain_id=chain_id, url=provider_url).update(synced=False)


celery_pubsub.subscribe("blockchain.mined.block", save_historical_data)
celery_pubsub.subscribe("blockchain.mined.block", notify_new_block)
celery_pubsub.subscribe("blockchain.mined.block", record_account_transactions)
celery_pubsub.subscribe("node.connection.ok", set_node_connection_ok)
celery_pubsub.subscribe("node.connection.nok", set_node_connection_nok)
celery_pubsub.subscribe("node.sync.ok", set_node_sync_ok)
celery_pubsub.subscribe("node.sync.nok", set_node_sync_nok)
