# Generated by Django 4.0 on 2022-04-08 00:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blockchain', '0003_create_chain_metadata'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chainmetadata',
            name='rollup_for',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='rollups', to='blockchain.chain'),
        ),
        migrations.AlterField(
            model_name='chainmetadata',
            name='sidechain_for',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sidechains', to='blockchain.chain'),
        ),
        migrations.AlterField(
            model_name='chainmetadata',
            name='testing_for',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='testnets', to='blockchain.chain'),
        ),
    ]