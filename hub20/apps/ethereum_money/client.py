import logging
from typing import Optional

from django.contrib.auth import get_user_model
from eth_utils import to_checksum_address
from ethereum.abi import ContractTranslator
from web3 import Web3
from web3._utils.events import get_event_data
from web3.exceptions import LogTopicError, MismatchedABI

from hub20.apps.blockchain.client import make_web3
from hub20.apps.blockchain.models import Chain
from hub20.apps.blockchain.typing import Address, EthereumAccount_T
from hub20.apps.ethereum_money import get_ethereum_account_model

from .abi import EIP20_ABI
from .app_settings import TRANSFER_GAS_LIMIT
from .models import EthereumToken, EthereumTokenAmount
from .typing import EthereumClient_T

logger = logging.getLogger(__name__)
EthereumAccount = get_ethereum_account_model()
User = get_user_model()


def get_transaction_events(transaction_receipt, event_abi):
    w3 = Web3()
    events = []
    for log in transaction_receipt.logs:
        try:
            event = get_event_data(w3.codec, event_abi, log)
            events.append(event)
        except (MismatchedABI, LogTopicError) as exc:
            tx_hash = transaction_receipt.transactionHash.hex()
            logger.info(f"{exc} when getting events from tx {tx_hash}")
    return events


def encode_transfer_data(recipient_address, amount: EthereumTokenAmount):
    translator = ContractTranslator(EIP20_ABI)
    encoded_data = translator.encode_function_call("transfer", (recipient_address, amount.as_wei))
    return f"0x{encoded_data.hex()}"


def get_max_fee(w3: Web3) -> EthereumTokenAmount:
    chain = Chain.objects.get(id=w3.eth.chain_id, enabled=True)
    ETH = EthereumToken.ETH(chain=chain)

    gas_price = chain.gas_price_estimate or w3.eth.generateGasPrice()
    return ETH.from_wei(TRANSFER_GAS_LIMIT * gas_price)


def get_account_balance(w3: Web3, token: EthereumToken, address: Address) -> EthereumTokenAmount:
    if token.is_ERC20:
        contract = w3.eth.contract(abi=EIP20_ABI, address=token.address)
        return token.from_wei(contract.functions.balanceOf(address).call())
    else:
        return token.from_wei(w3.eth.getBalance(address))


def get_token_information(w3: Web3, address):
    contract = w3.eth.contract(abi=EIP20_ABI, address=to_checksum_address(address))
    return {
        "name": contract.functions.name().call(),
        "code": contract.functions.symbol().call(),
        "decimals": contract.functions.decimals().call(),
    }


def make_token(w3: Web3, address) -> EthereumToken:
    token_data = get_token_information(w3=w3, address=address)
    chain = Chain.objects.get(enabled=True, id=w3.eth.chain_id)
    return EthereumToken.make(chain=chain, address=address, **token_data)


class EthereumClient:
    def __init__(self, account: EthereumAccount_T, w3: Optional[Web3] = None) -> None:
        self.account = account

    def build_transfer_transaction(self, recipient, amount: EthereumTokenAmount):
        token = amount.currency

        w3 = make_web3(provider_url=token.chain.provider_url)
        chain_id = w3.eth.chain_id
        message = f"Connected to network {chain_id}, token {token.code} is on {token.chain_id}"
        assert token.chain_id == chain_id, message

        transaction_params = {
            "chainId": chain_id,
            "nonce": w3.eth.getTransactionCount(self.account.address),
            "gasPrice": w3.eth.generateGasPrice(),
            "gas": TRANSFER_GAS_LIMIT,
            "from": self.account.address,
        }

        if token.is_ERC20:
            transaction_params.update(
                {"to": token.address, "value": 0, "data": encode_transfer_data(recipient, amount)}
            )
        else:
            transaction_params.update({"to": recipient, "value": amount.as_wei})
        return transaction_params

    def transfer(self, amount: EthereumTokenAmount, address, *args, **kw):
        w3 = make_web3(provider_url=amount.currency.chain.provider_url)
        transaction_data = self.build_transfer_transaction(recipient=address, amount=amount)
        signed_tx = self.sign_transaction(transaction_data=transaction_data, w3=w3)
        return w3.eth.sendRawTransaction(signed_tx.rawTransaction)

    def sign_transaction(self, transaction_data, w3: Web3, *args, **kw):
        if not hasattr(self.account, "private_key"):
            raise NotImplementedError("Can not sign transaction without the private key")
        return w3.eth.account.signTransaction(transaction_data, self.account.private_key)

    def get_balance(self, token: EthereumToken):
        w3 = make_web3(provider_url=token.chain.provider_url)
        return get_account_balance(w3=w3, token=token, address=self.account.address)

    @classmethod
    def select_for_transfer(
        cls,
        amount: EthereumTokenAmount,
        receiver: Optional[User] = None,
        address: Optional[Address] = None,
    ) -> Optional[EthereumClient_T]:

        chain = amount.currency.chain
        w3 = make_web3(provider_url=chain.provider_url)

        transfer_fee: EthereumTokenAmount = cls.estimate_transfer_fees(w3=w3)
        assert transfer_fee.is_ETH

        ETH = transfer_fee.currency

        accounts = EthereumAccount.objects.all().order_by("?")

        if amount.is_ETH:
            amount += transfer_fee

        for account in accounts:
            get_balance = lambda t: get_account_balance(w3=w3, token=t, address=account.address)

            eth_balance = get_balance(ETH)
            token_balance = eth_balance if amount.is_ETH else get_balance(amount.currency)

            if eth_balance >= transfer_fee and token_balance >= amount:
                return cls(account=account, w3=w3)
        return None

    @classmethod
    def estimate_transfer_fees(cls, *args, **kw) -> EthereumTokenAmount:
        w3 = kw["w3"]
        return get_max_fee(w3=w3)
