# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import homepage_content.models
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Testimonials',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('name', models.CharField(max_length=200, null=True, blank=True)),
                ('quotes', models.TextField(null=True, blank=True)),
                ('profile_image', models.ImageField(max_length=200, upload_to=homepage_content.models.content_file_name)),
            ],
            options={
                'verbose_name': 'Testimonial',
                'verbose_name_plural': 'Testimonials',
            },
        ),
    ]
