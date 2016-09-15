# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('edx_haystack_extensions', '0002_auto_20160826_1750'),
    ]

    operations = [
        migrations.AddField(
            model_name='elasticsearchboostconfig',
            name='simple_query_boost',
            field=models.DecimalField(max_digits=6, default=1.0, verbose_name='Simple Query Boost', decimal_places=2, help_text='Boost amount for simple query results.'),
        ),
    ]
