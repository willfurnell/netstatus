from django.db import models
from django.core.validators import RegexValidator

# Create your models here.


class Device(models.Model):
    name = models.CharField(max_length=255)
    ipv4_address = models.GenericIPAddressField()
    #mac_address = models.CharField(validators=[RegexValidator(regex='^([a-fA-F0-9]{2}:){5}([a-fA-F0-9]{2})$')], max_length=17)
    location_x = models.DecimalField(decimal_places=20, max_digits=100)
    location_y = models.DecimalField(decimal_places=20, max_digits=100)
    online = models.BooleanField()
    system_version = models.CharField(max_length=999)

    def __str__(self):
        return '{0}'.format(self.name)