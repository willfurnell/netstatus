from django.db import models
from django.core.validators import RegexValidator
import re

# Create your models here.


class Device(models.Model):
    name = models.CharField(max_length=30)
    ipv4_address = models.GenericIPAddressField()
    #mac_address = models.CharField(validators=[RegexValidator(regex='^([a-fA-F0-9]{2}:){5}([a-fA-F0-9]{2})$')], max_length=17)
    location_x = models.DecimalField(decimal_places=20, max_digits=100)
    location_y = models.DecimalField(decimal_places=20, max_digits=100)
    online = models.BooleanField()
    system_version = models.CharField(max_length=999)

    def __str__(self):
        return '{0}'.format(self.name)


class MACtoPort(models.Model):
    device = models.ForeignKey(Device)
    mac_address = models.CharField(max_length=12, validators=[RegexValidator(
        regex='^([a-fA-F0-9]{2}){5}([a-fA-F0-9]{2})$')])
    port = models.IntegerField()


class IgnoredPort(models.Model):
    device = models.ForeignKey(Device)
    port = models.IntegerField()


class LastUpdated(models.Model):
    mac_to_port = models.IntegerField()
    ignored_port = models.IntegerField()
