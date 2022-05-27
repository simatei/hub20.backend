# Generated by Django 4.0 on 2022-05-27 02:01

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import hub20.apps.core.fields
import hub20.apps.core.models.payments
import hub20.apps.core.models.store
import model_utils.fields
import taggit.managers
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('taggit', '0004_alter_taggeditem_content_type_alter_taggeditem_tag'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=500)),
                ('symbol', models.CharField(max_length=16)),
                ('decimals', models.PositiveIntegerField(default=18)),
                ('logoURI', hub20.apps.core.fields.TokenlistStandardURLField(blank=True, max_length=512, null=True)),
                ('is_listed', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner_id', models.PositiveIntegerField()),
                ('owner_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('token', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='books', to='core.basetoken')),
            ],
            options={
                'unique_together': {('token', 'owner_type', 'owner_id')},
            },
        ),
        migrations.CreateModel(
            name='Deposit',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('session_key', models.SlugField(null=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.basetoken')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('amount', hub20.apps.core.fields.TokenAmountField(decimal_places=18, max_digits=32)),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.basetoken')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PaymentNetwork',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300, unique=True)),
                ('description', models.TextField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentNetworkProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True)),
                ('synced', models.BooleanField(default=False)),
                ('connected', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentRoute',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('identifier', models.BigIntegerField(default=hub20.apps.core.models.payments.generate_payment_route_id, unique=True)),
                ('deposit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='routes', to='core.deposit')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=300)),
                ('url', models.URLField(help_text='URL for your store public site or information page')),
                ('checkout_webhook_url', models.URLField(help_text='URL to receive checkout updates', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Transfer',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('amount', hub20.apps.core.fields.TokenAmountField(decimal_places=18, max_digits=32)),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('memo', models.TextField(blank=True, null=True)),
                ('identifier', models.CharField(blank=True, max_length=300, null=True)),
                ('execute_on', models.DateTimeField(auto_now_add=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.basetoken')),
                ('network', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transfers', to='core.paymentnetwork')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transfers_sent', to='auth.user')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='InternalPayment',
            fields=[
                ('payment_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.payment')),
                ('memo', models.TextField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('core.payment',),
        ),
        migrations.CreateModel(
            name='InternalPaymentRoute',
            fields=[
                ('paymentroute_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.paymentroute')),
            ],
            options={
                'abstract': False,
            },
            bases=('core.paymentroute',),
        ),
        migrations.CreateModel(
            name='PaymentOrder',
            fields=[
                ('deposit_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.deposit')),
                ('amount', hub20.apps.core.fields.TokenAmountField(decimal_places=18, max_digits=32)),
                ('reference', models.CharField(blank=True, max_length=200, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('core.deposit', models.Model),
        ),
        migrations.CreateModel(
            name='UUIDTaggedItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.UUIDField(db_index=True, verbose_name='object ID')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_tagged_items', to='contenttypes.contenttype', verbose_name='content type')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_items', to='taggit.tag')),
            ],
            options={
                'verbose_name': 'Tag',
                'verbose_name_plural': 'Tags',
            },
        ),
        migrations.CreateModel(
            name='UserTokenList',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64)),
                ('description', models.TextField(null=True)),
                ('keywords', taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='core.UUIDTaggedItem', to='taggit.Tag', verbose_name='Tags')),
                ('tokens', models.ManyToManyField(related_name='%(app_label)s_%(class)s_tokenlists', to='core.BaseToken')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='token_lists', to='auth.user')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='UserPreferences',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tokens', models.ManyToManyField(to='core.BaseToken')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='preferences', to='auth.user')),
            ],
        ),
        migrations.CreateModel(
            name='UserAccount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='account', to='auth.user')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TransferReceipt',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('transfer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='receipt', to='core.transfer')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TransferFailure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('transfer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='failure', to='core.transfer')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TransferConfirmation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('transfer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='confirmation', to='core.transfer')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TransferCancellation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('canceled_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='auth.user')),
                ('transfer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cancellation', to='core.transfer')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StoreRSAKeyPair',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_key_pem', models.TextField()),
                ('private_key_pem', models.TextField()),
                ('store', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='rsa', to='core.store')),
            ],
        ),
        migrations.AddField(
            model_name='store',
            name='accepted_token_list',
            field=models.ForeignKey(help_text='The list of tokens that will be accepted for payment', null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.usertokenlist'),
        ),
        migrations.AddField(
            model_name='store',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user'),
        ),
        migrations.CreateModel(
            name='StableTokenPair',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('algorithmic_peg', models.BooleanField(default=True)),
                ('currency', models.CharField(choices=[('AED', 'United Arab Emirates dirham'), ('AFN', 'Afghan afghani'), ('ALL', 'Albanian lek'), ('AMD', 'Armenian dram'), ('ANG', 'Netherlands Antillean guilder'), ('AOA', 'Angolan kwanza'), ('ARS', 'Argentine peso'), ('AUD', 'Australian dollar'), ('AWG', 'Aruban florin'), ('AZN', 'Azerbaijani manat'), ('BAM', 'Bosnia and Herzegovina convertible mark'), ('BBD', 'Barbados dollar'), ('BDT', 'Bangladeshi taka'), ('BGN', 'Bulgarian lev'), ('BHD', 'Bahraini dinar'), ('BIF', 'Burundian franc'), ('BMD', 'Bermudian dollar'), ('BND', 'Brunei dollar'), ('BOB', 'Boliviano'), ('BOV', 'Bolivian Mvdol (funds code)'), ('BRL', 'Brazilian real'), ('BSD', 'Bahamian dollar'), ('BTN', 'Bhutanese ngultrum'), ('BWP', 'Botswana pula'), ('BYN', 'Belarusian ruble'), ('BZD', 'Belize dollar'), ('CAD', 'Canadian dollar'), ('CDF', 'Congolese franc'), ('CHE', 'WIR euro (complementary currency)'), ('CHF', 'Swiss franc'), ('CHW', 'WIR franc (complementary currency)'), ('CLF', 'Unidad de Fomento (funds code)'), ('CLP', 'Chilean peso'), ('CNY', 'Chinese yuan[8]'), ('COP', 'Colombian peso'), ('COU', 'Unidad de Valor Real (UVR) (funds code)[9]'), ('CRC', 'Costa Rican colon'), ('CUC', 'Cuban convertible peso'), ('CUP', 'Cuban peso'), ('CVE', 'Cape Verdean escudo'), ('CZK', 'Czech koruna'), ('DJF', 'Djiboutian franc'), ('DKK', 'Danish krone'), ('DOP', 'Dominican peso'), ('DZD', 'Algerian dinar'), ('EGP', 'Egyptian pound'), ('ERN', 'Eritrean nakfa'), ('ETB', 'Ethiopian birr'), ('EUR', 'Euro'), ('FJD', 'Fiji dollar'), ('FKP', 'Falkland Islands pound'), ('GBP', 'Pound sterling'), ('GEL', 'Georgian lari'), ('GHS', 'Ghanaian cedi'), ('GIP', 'Gibraltar pound'), ('GMD', 'Gambian dalasi'), ('GNF', 'Guinean franc'), ('GTQ', 'Guatemalan quetzal'), ('GYD', 'Guyanese dollar'), ('HKD', 'Hong Kong dollar'), ('HNL', 'Honduran lempira'), ('HRK', 'Croatian kuna'), ('HTG', 'Haitian gourde'), ('HUF', 'Hungarian forint'), ('IDR', 'Indonesian rupiah'), ('ILS', 'Israeli new shekel'), ('INR', 'Indian rupee'), ('IQD', 'Iraqi dinar'), ('IRR', 'Iranian rial'), ('ISK', 'Icelandic króna (plural: krónur)'), ('JMD', 'Jamaican dollar'), ('JOD', 'Jordanian dinar'), ('JPY', 'Japanese yen'), ('KES', 'Kenyan shilling'), ('KGS', 'Kyrgyzstani som'), ('KHR', 'Cambodian riel'), ('KMF', 'Comoro franc'), ('KPW', 'North Korean won'), ('KRW', 'South Korean won'), ('KWD', 'Kuwaiti dinar'), ('KYD', 'Cayman Islands dollar'), ('KZT', 'Kazakhstani tenge'), ('LAK', 'Lao kip'), ('LBP', 'Lebanese pound'), ('LKR', 'Sri Lankan rupee'), ('LRD', 'Liberian dollar'), ('LSL', 'Lesotho loti'), ('LYD', 'Libyan dinar'), ('MAD', 'Moroccan dirham'), ('MDL', 'Moldovan leu'), ('MGA', 'Malagasy ariary'), ('MKD', 'Macedonian denar'), ('MMK', 'Myanmar kyat'), ('MNT', 'Mongolian tögrög'), ('MOP', 'Macanese pataca'), ('MRU', 'Mauritanian ouguiya'), ('MUR', 'Mauritian rupee'), ('MVR', 'Maldivian rufiyaa'), ('MWK', 'Malawian kwacha'), ('MXN', 'Mexican peso'), ('MXV', 'Mexican Unidad de Inversion (UDI) (funds code)'), ('MYR', 'Malaysian ringgit'), ('MZN', 'Mozambican metical'), ('NAD', 'Namibian dollar'), ('NGN', 'Nigerian naira'), ('NIO', 'Nicaraguan córdoba'), ('NOK', 'Norwegian krone'), ('NPR', 'Nepalese rupee'), ('NZD', 'New Zealand dollar'), ('OMR', 'Omani rial'), ('PAB', 'Panamanian balboa'), ('PEN', 'Peruvian sol'), ('PGK', 'Papua New Guinean kina'), ('PHP', 'Philippine peso[13]'), ('PKR', 'Pakistani rupee'), ('PLN', 'Polish złoty'), ('PYG', 'Paraguayan guaraní'), ('QAR', 'Qatari riyal'), ('RON', 'Romanian leu'), ('RSD', 'Serbian dinar'), ('RUB', 'Russian ruble'), ('RWF', 'Rwandan franc'), ('SAR', 'Saudi riyal'), ('SBD', 'Solomon Islands dollar'), ('SCR', 'Seychelles rupee'), ('SDG', 'Sudanese pound'), ('SEK', 'Swedish krona (plural: kronor)'), ('SGD', 'Singapore dollar'), ('SHP', 'Saint Helena pound'), ('SLL', 'Sierra Leonean leone'), ('SOS', 'Somali shilling'), ('SRD', 'Surinamese dollar'), ('SSP', 'South Sudanese pound'), ('STN', 'São Tomé and Príncipe dobra'), ('SVC', 'Salvadoran colón'), ('SYP', 'Syrian pound'), ('SZL', 'Swazi lilangeni'), ('THB', 'Thai baht'), ('TJS', 'Tajikistani somoni'), ('TMT', 'Turkmenistan manat'), ('TND', 'Tunisian dinar'), ('TOP', 'Tongan paʻanga'), ('TRY', 'Turkish lira'), ('TTD', 'Trinidad and Tobago dollar'), ('TWD', 'New Taiwan dollar'), ('TZS', 'Tanzanian shilling'), ('UAH', 'Ukrainian hryvnia'), ('UGX', 'Ugandan shilling'), ('USD', 'United States dollar'), ('USN', 'United States dollar (next day) (funds code)'), ('UYI', 'Uruguay Peso en Unidades Indexadas (URUIURUI) (funds code)'), ('UYU', 'Uruguayan peso'), ('UYW', 'Unidad previsional[15]'), ('UZS', 'Uzbekistan som'), ('VED', 'Venezuelan bolívar digital[16]'), ('VES', 'Venezuelan bolívar soberano[13]'), ('VND', 'Vietnamese đồng'), ('VUV', 'Vanuatu vatu'), ('WST', 'Samoan tala'), ('XAF', 'CFA franc BEAC'), ('XAG', 'Silver (one troy ounce)'), ('XAU', 'Gold (one troy ounce)'), ('XBA', 'European Composite Unit (EURCO) (bond market unit)'), ('XBB', 'European Monetary Unit (E.M.U.-6) (bond market unit)'), ('XBC', 'European Unit of Account 9 (E.U.A.-9) (bond market unit)'), ('XBD', 'European Unit of Account 17 (E.U.A.-17) (bond market unit)'), ('XCD', 'East Caribbean dollar'), ('XDR', 'Special drawing rights'), ('XOF', 'CFA franc BCEAO'), ('XPD', 'Palladium (one troy ounce)'), ('XPF', 'CFP franc (franc Pacifique)'), ('XPT', 'Platinum (one troy ounce)'), ('XSU', 'SUCRE'), ('XTS', 'Code reserved for testing'), ('XUA', 'ADB Unit of Account'), ('XXX', 'No currency'), ('YER', 'Yemeni rial'), ('ZAR', 'South African rand'), ('ZMW', 'Zambian kwacha'), ('ZWL', 'Zimbabwean dollar')], max_length=3)),
                ('token', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stable_pair', to='core.basetoken')),
            ],
        ),
        migrations.CreateModel(
            name='PaymentNetworkAccount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_network', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='account', to='core.paymentnetwork')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PaymentConfirmation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('payment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='confirmation', to='core.payment')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='payment',
            name='route',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='core.paymentroute'),
        ),
        migrations.AddField(
            model_name='deposit',
            name='network',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.paymentnetwork'),
        ),
        migrations.AddField(
            model_name='deposit',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user'),
        ),
        migrations.CreateModel(
            name='WrappedToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wrapped', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wrapping_tokens', to='core.basetoken')),
                ('wrapper', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='core.basetoken')),
            ],
            options={
                'unique_together': {('wrapped', 'wrapper')},
            },
        ),
        migrations.CreateModel(
            name='TokenList',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64)),
                ('description', models.TextField(null=True)),
                ('url', hub20.apps.core.fields.TokenlistStandardURLField()),
                ('version', models.CharField(max_length=32)),
                ('keywords', taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='core.UUIDTaggedItem', to='taggit.Tag', verbose_name='Tags')),
                ('tokens', models.ManyToManyField(related_name='%(app_label)s_%(class)s_tokenlists', to='core.BaseToken')),
            ],
            options={
                'unique_together': {('url', 'version')},
            },
        ),
        migrations.CreateModel(
            name='InternalTransfer',
            fields=[
                ('transfer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.transfer')),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='internal_transfers_received', to='auth.user')),
            ],
            options={
                'abstract': False,
            },
            bases=('core.transfer',),
        ),
        migrations.CreateModel(
            name='InternalPaymentNetwork',
            fields=[
                ('paymentnetwork_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.paymentnetwork')),
                ('site', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='treasury', to='sites.site')),
            ],
            bases=('core.paymentnetwork',),
        ),
        migrations.CreateModel(
            name='Debit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('amount', hub20.apps.core.fields.TokenAmountField(decimal_places=18, max_digits=32)),
                ('reference_id', models.UUIDField()),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='debits', to='core.book')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.basetoken')),
                ('reference_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'abstract': False,
                'unique_together': {('book', 'reference_type', 'reference_id')},
            },
        ),
        migrations.CreateModel(
            name='Credit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('amount', hub20.apps.core.fields.TokenAmountField(decimal_places=18, max_digits=32)),
                ('reference_id', models.UUIDField()),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credits', to='core.book')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.basetoken')),
                ('reference_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'abstract': False,
                'unique_together': {('book', 'reference_type', 'reference_id')},
            },
        ),
        migrations.CreateModel(
            name='Checkout',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('expires_on', models.DateTimeField(default=hub20.apps.core.models.store.calculate_checkout_expiration_time)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.store')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='checkout', to='core.paymentorder')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
