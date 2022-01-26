from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Case, ProtectedError, Value, When
from django.db.models.query import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from hub20.apps.blockchain.client import make_web3
from hub20.apps.ethereum_money.client import get_estimate_fee
from hub20.apps.ethereum_money.models import EthereumToken
from hub20.apps.ethereum_money.views import BaseTokenViewSet, TokenViewSet

from . import models, serializers
from .filters import DepositFilter, UserFilter
from .permissions import IsStoreOwner

User = get_user_model()


class ReadWriteSerializerMixin(generics.GenericAPIView):
    """
    Overrides get_serializer_class to choose the read serializer
    for GET requests and the write serializer for POST requests.

    Set read_serializer_class and write_serializer_class attributes on a
    generic APIView
    """

    read_serializer_class: Optional[Serializer] = None
    write_serializer_class: Optional[Serializer] = None

    def get_serializer_class(self) -> Serializer:
        if self.request and self.request.method in ["POST", "PUT", "PATCH"]:
            return self.get_write_serializer_class()
        return self.get_read_serializer_class()

    def get_read_serializer_class(self) -> Serializer:
        assert self.read_serializer_class is not None, (
            "'%s' should either include a `read_serializer_class` attribute,"
            "or override the `get_read_serializer_class()` method." % self.__class__.__name__
        )
        return self.read_serializer_class

    def get_write_serializer_class(self) -> Serializer:
        assert self.write_serializer_class is not None, (
            "'%s' should either include a `write_serializer_class` attribute,"
            "or override the `get_write_serializer_class()` method." % self.__class__.__name__
        )
        return self.write_serializer_class


class AccountCreditEntryList(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.CreditSerializer

    def get_queryset(self) -> QuerySet:
        return models.Credit.objects.filter(book__account__user=self.request.user)


class AccountDebitEntryList(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.DebitSerializer

    def get_queryset(self) -> QuerySet:
        return self.request.user.account.debits.all()


class BaseDepositView:
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.DepositSerializer


class DepositListView(BaseDepositView, generics.ListCreateAPIView):
    filterset_class = DepositFilter
    filter_backends = (
        OrderingFilter,
        DjangoFilterBackend,
    )
    ordering = "-created"

    def get_queryset(self) -> QuerySet:
        return self.request.user.deposit_set.all()


class DepositView(BaseDepositView, generics.RetrieveAPIView):
    def get_object(self) -> models.Deposit:
        return get_object_or_404(models.Deposit, pk=self.kwargs.get("pk"), user=self.request.user)


class BasePaymentOrderView(ReadWriteSerializerMixin):
    read_serializer_class = serializers.PaymentOrderReadSerializer
    write_serializer_class = serializers.PaymentOrderSerializer


class PaymentOrderListView(BasePaymentOrderView, generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self) -> QuerySet:
        return models.PaymentOrder.objects.filter(user=self.request.user)


class PaymentOrderView(BasePaymentOrderView, generics.RetrieveDestroyAPIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self) -> models.PaymentOrder:
        return get_object_or_404(
            models.PaymentOrder, pk=self.kwargs.get("pk"), user=self.request.user
        )

    def destroy(self, request, pk=None):
        try:
            return super().destroy(request, pk=pk)
        except ProtectedError:
            return Response(
                "Order has either been paid or has open routes and can not be canceled",
                status=status.HTTP_400_BAD_REQUEST,
            )


class TokenBrowserViewSet(TokenViewSet):
    @action(detail=True)
    def transfer_cost(self, request, **kwargs):
        """
        Returns estimated cost in Wei (estimated gas * gas price) to execute a transfer

        Returns 404 if not connected to the blockchain or if token not in database
        """
        token = self.get_object()
        try:
            w3 = make_web3(provider=token.chain.provider)
            transfer_cost = get_estimate_fee(w3=w3, token=token)
            return Response(transfer_cost.as_wei)
        except AttributeError:
            raise Http404


class TransferListView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.TransferSerializer

    def get_queryset(self) -> QuerySet:
        return self.request.user.transfers_sent.all()


class TransferView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.TransferSerializer

    def get_object(self):
        try:
            return models.Transfer.objects.get(pk=self.kwargs.get("pk"), sender=self.request.user)
        except models.Transfer.DoesNotExist:
            raise Http404


class TokenBalanceListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.HyperlinkedTokenBalanceSerializer
    filter_backends = (OrderingFilter,)
    ordering = ("chain_id", "-is_native", "symbol")

    def get_queryset(self) -> QuerySet:
        return self.request.user.account.get_balances().annotate(
            is_native=Case(
                When(address=EthereumToken.NULL_ADDRESS, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )


class TokenBalanceView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.HyperlinkedTokenBalanceSerializer

    def get_object(self) -> EthereumToken:
        token = get_object_or_404(
            EthereumToken, chain_id=self.kwargs["chain_id"], address=self.kwargs["address"]
        )
        return self.request.user.account.get_balance(token)


class CheckoutViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin):
    permission_classes = (AllowAny,)
    serializer_class = serializers.HttpCheckoutSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return models.Checkout.objects.all()

    def get_object(self):
        return get_object_or_404(models.Checkout, id=self.kwargs["pk"])


class PaymentViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return models.Payment.objects.all()

    def get_permissions(self):
        permission_class = IsAdminUser if self.action == "list" else AllowAny
        return (permission_class(),)

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.PaymentSerializer

        payment = self.get_object()

        return {
            models.InternalPayment: serializers.InternalPaymentSerializer,
            models.BlockchainPayment: serializers.BlockchainPaymentSerializer,
            models.RaidenPayment: serializers.RaidenPaymentSerializer,
        }.get(type(payment), serializers.PaymentSerializer)

    def get_object(self):
        try:
            return models.Payment.objects.get_subclass(id=self.kwargs["pk"])
        except (models.Payment.DoesNotExist, KeyError):
            return None


class StoreViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    permission_classes = (AllowAny,)
    serializer_class = serializers.StoreViewerSerializer
    queryset = models.Store.objects.all()

    def get_object(self, *args, **kw):
        return get_object_or_404(models.Store, id=self.kwargs["pk"])


class UserStoreViewSet(ModelViewSet):
    permission_classes = (IsStoreOwner,)
    serializer_class = serializers.StoreEditorSerializer

    def get_queryset(self) -> QuerySet:
        try:
            return self.request.user.store_set.all()
        except AttributeError:
            return models.Store.objects.none()

    def get_object(self, *args, **kw):
        store = get_object_or_404(models.Store, id=self.kwargs["pk"])
        self.check_object_permissions(self.request, store)
        return store


class UserTokenViewSet(BaseTokenViewSet, DestroyModelMixin):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserTokenSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return serializers.UserTokenCreatorSerializer

        return self.serializer_class

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        return qs.filter(userpreferences__user=self.request.user)

    def destroy(self, *args, **kw):
        token = self.get_object()
        self.request.user.preferences.tokens.remove(token)
        return Response(status.HTTP_204_NO_CONTENT)


class UserPreferencesView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserPreferencesSerializer

    def get_object(self) -> QuerySet:
        return self.request.user.preferences


class UserViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserSerializer
    filterset_class = UserFilter
    filter_backends = (
        OrderingFilter,
        DjangoFilterBackend,
    )
    lookup_field = "username"
    ordering = "username"

    def get_queryset(self) -> QuerySet:
        return User.objects.filter(is_active=True, is_superuser=False, is_staff=False)

    def get_object(self, *args, **kw):
        return get_object_or_404(
            User,
            is_active=True,
            is_superuser=False,
            is_staff=False,
            username=self.kwargs["username"],
        )


class StatusView(APIView):
    permission_classes = (IsAuthenticated,)


class AccountingReportView(StatusView):
    permission_classes = (IsAdminUser,)

    def _get_serialized_book(self, accounting_model_class):
        books = accounting_model_class.balance_sheet().exclude(total_credit=0, total_debit=0)
        return serializers.AccountingBookSerializer(
            books, many=True, context={"request": self.request}
        ).data

    def get(self, request, **kw):
        return Response(
            dict(
                treasury=self._get_serialized_book(models.Treasury),
                wallets=self._get_serialized_book(models.WalletAccount),
                raiden=self._get_serialized_book(models.RaidenClientAccount),
                user_accounts=self._get_serialized_book(models.UserAccount),
                external_addresses=self._get_serialized_book(models.ExternalAddressAccount),
            )
        )


class BalanceSheetWalletViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    permission_classes = (IsAdminUser,)
    serializer_class = serializers.WalletBalanceSheetSerializer
    lookup_url_kwarg = "address"
    lookup_field = "account__address"

    def get_queryset(self) -> QuerySet:
        return models.WalletAccount.objects.all()

    def get_object(self) -> models.WalletAccount:
        return get_object_or_404(models.WalletAccount, account__address=self.kwargs.get("address"))
