# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import util.models
import openedx.core.djangoapps.micro_masters.models
import openedx.core.djangoapps.xmodule_django.models
from django.conf import settings
import django.core.validators
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Courses',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('course_key', openedx.core.djangoapps.xmodule_django.models.CourseKeyField(max_length=255, db_index=True)),
                ('name', models.CharField(max_length=200)),
            ],
            options={
                'verbose_name': 'Course',
                'verbose_name_plural': 'Courses',
            },
        ),
        migrations.CreateModel(
            name='Institution',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('name', models.CharField(unique=True, max_length=200)),
                ('website_url', models.TextField(blank=True, null=True, validators=[django.core.validators.URLValidator()])),
                ('logo', models.ImageField(max_length=200, upload_to=openedx.core.djangoapps.micro_masters.models.content_file_name)),
            ],
            options={
                'verbose_name': 'Institution',
                'verbose_name_plural': 'Institution',
            },
        ),
        migrations.CreateModel(
            name='Instructor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('name', models.CharField(max_length=200, null=True, blank=True)),
                ('designation', models.CharField(max_length=200, null=True, blank=True)),
                ('profile_image', models.ImageField(max_length=200, upload_to=openedx.core.djangoapps.micro_masters.models.content_file_name)),
                ('institution', models.ForeignKey(blank=True, to='micro_masters.Institution', null=True)),
            ],
            options={
                'verbose_name': 'Instructor',
                'verbose_name_plural': 'Instructor',
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('name', models.CharField(unique=True, max_length=200)),
                ('code', models.CharField(max_length=20, null=True, blank=True)),
            ],
            options={
                'verbose_name': 'Language',
                'verbose_name_plural': 'Language',
            },
        ),
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('name', models.CharField(unique=True, max_length=200)),
                ('start', models.DateField(null=True)),
                ('end', models.DateField(null=True, blank=True)),
                ('short_description', models.TextField(null=True, blank=True)),
                ('price', models.IntegerField()),
                ('banner_image', models.ImageField(max_length=200, upload_to=openedx.core.djangoapps.micro_masters.models.content_file_name)),
                ('introductory_video', models.FileField(upload_to=openedx.core.djangoapps.micro_masters.models.content_file_name)),
                ('overview', models.TextField(null=True, blank=True)),
                ('sample_certificate_pdf', models.FileField(upload_to=openedx.core.djangoapps.micro_masters.models.content_file_name)),
                ('average_length', models.CharField(help_text=b'e.g. 6-7 weeks per course', max_length=40, null=True, blank=True)),
                ('effort', models.CharField(help_text=b'e.g. 8-10 hours per week, per course', max_length=40, null=True, blank=True)),
                ('courses', models.ManyToManyField(to='micro_masters.Courses')),
                ('institution', models.ForeignKey(blank=True, to='micro_masters.Institution', null=True)),
                ('instructors', models.ManyToManyField(to='micro_masters.Instructor')),
                ('language', models.ForeignKey(related_name='program_language', blank=True, to='micro_masters.Language', null=True)),
            ],
            options={
                'verbose_name': 'Program',
                'verbose_name_plural': 'Programs',
            },
        ),
        migrations.CreateModel(
            name='ProgramEnrollment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('is_active', models.BooleanField(default=0)),
                ('program', models.ForeignKey(to='micro_masters.Program')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Program Enrollment',
                'verbose_name_plural': 'Program Enrollment',
            },
        ),
        migrations.CreateModel(
            name='ProgramOrder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('status', models.CharField(default=b'initiate', max_length=32, choices=[(b'initiate', b'initiate'), (b'purchased', b'purchased'), (b'refunded', b'refunded')])),
                ('processor_response_json', util.models.CompressedTextField(null=True, verbose_name=b'Processor Response JSON', blank=True)),
                ('purchase_time', models.DateTimeField(null=True, blank=True)),
                ('refunded_time', models.DateTimeField(null=True, blank=True)),
                ('bill_to_first', models.CharField(max_length=64, blank=True)),
                ('bill_to_last', models.CharField(max_length=64, blank=True)),
                ('bill_to_street1', models.CharField(max_length=128, blank=True)),
                ('bill_to_street2', models.CharField(max_length=128, blank=True)),
                ('bill_to_city', models.CharField(max_length=64, blank=True)),
                ('bill_to_state', models.CharField(max_length=8, blank=True)),
                ('bill_to_postalcode', models.CharField(max_length=16, blank=True)),
                ('bill_to_country', models.CharField(max_length=64, blank=True)),
                ('program', models.ForeignKey(to='micro_masters.Program')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Program Order',
                'verbose_name_plural': 'Program Order',
            },
        ),
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('name', models.CharField(unique=True, max_length=200)),
            ],
            options={
                'verbose_name': 'Subject',
                'verbose_name_plural': 'Subjects',
            },
        ),
        migrations.AddField(
            model_name='program',
            name='subject',
            field=models.ForeignKey(blank=True, to='micro_masters.Subject', null=True),
        ),
        migrations.AddField(
            model_name='program',
            name='video_transcripts',
            field=models.ForeignKey(related_name='transcript_language', blank=True, to='micro_masters.Language', null=True),
        ),
    ]
