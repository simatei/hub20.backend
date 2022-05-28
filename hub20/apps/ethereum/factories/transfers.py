import factory

from hub20.apps.core.factories import EthereumProvider, TransferFactory

from ..models import BlockchainTransfer
from .networks import BlockchainPaymentNetworkFactory

factory.Faker.add_provider(EthereumProvider)


class BlockchainTransferFactory(TransferFactory):
    address = factory.Faker("ethereum_address")
    network = factory.SubFactory(BlockchainPaymentNetworkFactory)

    class Meta:
        model = BlockchainTransfer


__all__ = ["BlockchainTransferFactory"]