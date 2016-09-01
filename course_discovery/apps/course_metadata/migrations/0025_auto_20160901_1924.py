# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import sortedm2m.fields


class Migration(migrations.Migration):

    dependencies = [
        ('course_metadata', '0024_auto_20160901_1426'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='courses',
            field=sortedm2m.fields.SortedManyToManyField(to='course_metadata.Course', help_text=None, related_name='programs'),
        ),
    ]
