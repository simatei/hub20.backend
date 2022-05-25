# Generated by Django 4.0 on 2022-05-25 14:00

import django.contrib.postgres.fields.hstore
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.contrib.postgres.operations import HStoreExtension
from django.db import migrations, models

import hub20.apps.core.fields
import hub20.apps.raiden.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("web3", "0001_initial"),
        ("core", "0001_initial"),
    ]

    operations = [
        HStoreExtension(),
        migrations.CreateModel(
            name="Channel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "status",
                    model_utils.fields.StatusField(
                        choices=[
                            ("opened", "opened"),
                            ("waiting_for_settle", "waiting_for_settle"),
                            ("settling", "settling"),
                            ("settled", "settled"),
                            ("unusable", "unusable"),
                            ("closed", "closed"),
                            ("closing", "closing"),
                        ],
                        default="opened",
                        max_length=100,
                        no_check_for_status=True,
                        verbose_name="status",
                    ),
                ),
                (
                    "status_changed",
                    model_utils.fields.MonitorField(
                        default=django.utils.timezone.now,
                        monitor="status",
                        verbose_name="status changed",
                    ),
                ),
                ("identifier", models.PositiveIntegerField()),
                ("partner_address", hub20.apps.core.fields.EthereumAddressField(db_index=True)),
                (
                    "balance",
                    hub20.apps.core.fields.TokenAmountField(decimal_places=18, max_digits=32),
                ),
                (
                    "total_deposit",
                    hub20.apps.core.fields.TokenAmountField(decimal_places=18, max_digits=32),
                ),
                (
                    "total_withdraw",
                    hub20.apps.core.fields.TokenAmountField(decimal_places=18, max_digits=32),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "amount",
                    hub20.apps.core.fields.TokenAmountField(decimal_places=18, max_digits=32),
                ),
                ("timestamp", models.DateTimeField()),
                ("identifier", hub20.apps.core.fields.Uint256Field()),
                ("sender_address", hub20.apps.core.fields.EthereumAddressField()),
                ("receiver_address", hub20.apps.core.fields.EthereumAddressField()),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="raiden.channel",
                    ),
                ),
            ],
            options={
                "unique_together": {
                    ("channel", "identifier", "sender_address", "receiver_address")
                },
            },
        ),
        migrations.CreateModel(
            name="Raiden",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("url", hub20.apps.raiden.models.RaidenURLField(unique=True)),
                ("address", hub20.apps.core.fields.EthereumAddressField()),
                (
                    "chain",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="raiden_node",
                        to="web3.chain",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RaidenWithdrawal",
            fields=[
                (
                    "withdrawal_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="core.withdrawal",
                    ),
                ),
                ("address", hub20.apps.core.fields.EthereumAddressField(db_index=True)),
            ],
            options={
                "abstract": False,
            },
            bases=("core.withdrawal",),
        ),
        migrations.CreateModel(
            name="RaidenWithdrawalReceipt",
            fields=[
                (
                    "transferreceipt_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="core.transferreceipt",
                    ),
                ),
                ("payment_data", django.contrib.postgres.fields.hstore.HStoreField()),
            ],
            options={
                "abstract": False,
            },
            bases=("core.transferreceipt",),
        ),
        migrations.CreateModel(
            name="TokenNetwork",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("address", hub20.apps.core.fields.EthereumAddressField()),
                (
                    "token",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="web3.erc20token"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RaidenWithdrawalConfirmation",
            fields=[
                (
                    "transferconfirmation_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="core.transferconfirmation",
                    ),
                ),
                (
                    "payment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="raiden.payment"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("core.transferconfirmation",),
        ),
        migrations.CreateModel(
            name="RaidenPaymentRoute",
            fields=[
                (
                    "paymentroute_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="core.paymentroute",
                    ),
                ),
                (
                    "payment_window",
                    models.DurationField(
                        default=hub20.apps.raiden.models.calculate_raiden_payment_window
                    ),
                ),
                (
                    "raiden",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_routes",
                        to="raiden.raiden",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("core.paymentroute",),
        ),
        migrations.CreateModel(
            name="RaidenPayment",
            fields=[
                (
                    "payment_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="core.payment",
                    ),
                ),
                (
                    "payment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="raiden.payment"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("core.payment",),
        ),
        migrations.AddField(
            model_name="channel",
            name="raiden",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="channels",
                to="raiden.raiden",
            ),
        ),
        migrations.AddField(
            model_name="channel",
            name="token_network",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="raiden.tokennetwork"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="channel",
            unique_together={("raiden", "token_network", "identifier")},
        ),
    ]
