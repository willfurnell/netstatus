# -*- coding: utf-8 -*-
# Generated by Django 1.9.3 on 2016-03-13 18:01
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('netstatus_web', '0002_auto_20160208_1227'),
    ]

    operations = [
        migrations.CreateModel(
            name='IgnoredPort',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('port', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='LastUpdated',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mac_to_port', models.IntegerField()),
                ('ignored_port', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='MACtoPort',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mac_address', models.CharField(max_length=12, validators=[django.core.validators.RegexValidator(regex='^([a-fA-F0-9]{2}){5}([a-fA-F0-9]{2})$')])),
                ('port', models.IntegerField()),
            ],
        ),
        migrations.AlterField(
            model_name='device',
            name='name',
            field=models.CharField(max_length=30),
        ),
        migrations.AddField(
            model_name='mactoport',
            name='device',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='netstatus_web.Device'),
        ),
        migrations.AddField(
            model_name='ignoredport',
            name='device',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='netstatus_web.Device'),
        ),
    ]
