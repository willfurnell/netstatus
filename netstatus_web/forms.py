from django import forms
from .models import Device


class NewDeviceForm(forms.Form):
    name = forms.CharField(max_length=255, label="Device Name")
    ipv4_address = forms.GenericIPAddressField(label="Device IPv4 Address")
    location = forms.CharField(max_length=255, label="Device Location")


class EditDeviceForm(forms.Form):
    class Meta:

        model = Device

        fields = ('name', 'ipv4_address', 'location')


class RemoveDeviceForm(forms.Form):
    choose_device = forms.ModelChoiceField(queryset=Device.objects.all(), label="Choose a device")