from django import forms
from .models import Device


class NewDeviceForm(forms.Form):
    name = forms.CharField(max_length=255, label="Device Name")
    ipv4_address = forms.GenericIPAddressField(label="Device IPv4 Address")
    location_x = forms.DecimalField(max_digits=100, decimal_places=20, widget=forms.HiddenInput(), initial=0)
    location_y = forms.DecimalField(max_digits=100, decimal_places=20, widget=forms.HiddenInput(), initial=0)


class EditDeviceForm(forms.Form):
    class Meta:

        model = Device

        fields = ('name', 'ipv4_address', 'location_x', 'location_y')


class RemoveDeviceForm(forms.Form):
    choose_device = forms.ModelChoiceField(queryset=Device.objects.all(), label="Choose a device")