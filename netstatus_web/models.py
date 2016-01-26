from django.db import models
from django.core.validators import RegexValidator

# Create your models here.


class MACAddressField(models.CharField):
    __metaclass__ = models.SubfieldBase



class Switch(models.Model):
    name = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    mac_address = models.CharField(validators=RegexValidator())
    location = models.CharField(max_length=255)
