# Generated by Django 4.0 on 2022-05-19 13:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('ethereum_money', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpreferences',
            name='tokens',
            field=models.ManyToManyField(to='ethereum_money.EthereumToken'),
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='preferences', to='auth.user'),
        ),
        migrations.AddField(
            model_name='useraccount',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='account', to='auth.user'),
        ),
        migrations.AddField(
            model_name='transferreceipt',
            name='transfer',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='receipt', to='core.transfer'),
        ),
        migrations.AddField(
            model_name='transferfailure',
            name='transfer',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='failure', to='core.transfer'),
        ),
        migrations.AddField(
            model_name='transferconfirmation',
            name='transfer',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='confirmation', to='core.transfer'),
        ),
        migrations.AddField(
            model_name='transfercancellation',
            name='canceled_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='auth.user'),
        ),
        migrations.AddField(
            model_name='transfercancellation',
            name='transfer',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cancellation', to='core.transfer'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ethereum_money.ethereumtoken'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='sender',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transfers_sent', to='auth.user'),
        ),
        migrations.AddField(
            model_name='storersakeypair',
            name='store',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='rsa', to='core.store'),
        ),
        migrations.AddField(
            model_name='store',
            name='accepted_token_list',
            field=models.ForeignKey(help_text='The list of tokens that will be accepted for payment', null=True, on_delete=django.db.models.deletion.SET_NULL, to='ethereum_money.usertokenlist'),
        ),
        migrations.AddField(
            model_name='store',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user'),
        ),
        migrations.AddField(
            model_name='paymentroute',
            name='deposit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='routes', to='core.deposit'),
        ),
        migrations.AddField(
            model_name='paymentconfirmation',
            name='payment',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='confirmation', to='core.payment'),
        ),
        migrations.AddField(
            model_name='payment',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ethereum_money.ethereumtoken'),
        ),
        migrations.AddField(
            model_name='payment',
            name='route',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='core.paymentroute'),
        ),
        migrations.AddField(
            model_name='deposit',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ethereum_money.ethereumtoken'),
        ),
        migrations.AddField(
            model_name='deposit',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user'),
        ),
        migrations.AddField(
            model_name='debit',
            name='book',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='debits', to='core.book'),
        ),
        migrations.AddField(
            model_name='debit',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ethereum_money.ethereumtoken'),
        ),
        migrations.AddField(
            model_name='debit',
            name='reference_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='credit',
            name='book',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credits', to='core.book'),
        ),
        migrations.AddField(
            model_name='credit',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ethereum_money.ethereumtoken'),
        ),
        migrations.AddField(
            model_name='credit',
            name='reference_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='checkout',
            name='store',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.store'),
        ),
        migrations.AddField(
            model_name='book',
            name='owner_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='book',
            name='token',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='books', to='ethereum_money.ethereumtoken'),
        ),
    ]
