# Generated by Django 4.0 on 2022-01-09 02:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ethereum_money', '0003_ethereumtoken_logouri'),
    ]

    operations = [
        migrations.CreateModel(
            name='WrappedToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wrapped', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wrapping_tokens', to='ethereum_money.ethereumtoken')),
                ('wrapper', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='ethereum_money.ethereumtoken')),
            ],
            options={
                'unique_together': {('wrapped', 'wrapper')},
            },
        ),
    ]