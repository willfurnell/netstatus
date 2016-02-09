from django.shortcuts import render, Http404, HttpResponse, HttpResponseRedirect
# from easysnmp import Session
# from easysnmp import exceptions
# import os
import matplotlib.pyplot as plt
import io
# import base64
from netstatus.settings import BASE_DIR
from .utils import ping, setup_snmp_session, timeticks_to_days
from .forms import NewDeviceForm, RemoveDeviceForm
from .models import Device
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from numbers import Number


def main(request):
    """
    Returns the front page of the website.
    Please note that the online chart is generated separately and embedded into this page.
    """

    pagevars = {'title': "NetStatus Dashboard"}

    return render(request, 'base_index.html', pagevars)


def piechart_online(request):
    """
    Generates a pie chart based on the number of online/offline devices on the network (those tracked by NetStatus).
    Returns a PNG image of the chart (which is never stored on disk - only in memory).
    """

    # Queries the database to get all the device rows
    devlist = Device.objects.all()

    online = 0
    offline = 0

    # Checks if every device in the list is online or offline by using the 'ping' funtion. A total of online/offline
    # devices is created and each individual device's status is updated in the database.
    for device in devlist:
        if ping(device.ipv4_address):
            online = online + 1
            device.online = True
            device.save()
        else:
            offline = offline + 1
            device.online = False
            device.save()

    labels = 'Offline', 'Online'

    sizes = [offline, online]

    colors = ['red', 'green']

    # This plots a pie chart - the autopct lambda function is used to reformat the percentage back into raw values.
    plt.pie(sizes, labels=labels, colors=colors,
        autopct=lambda f: '{:.0f}'.format(f * sum(sizes) / 100), shadow=False, startangle=90)
    # Set aspect ratio to be equal so that pie is drawn as a circle.
    plt.axis('equal')

    # This is used to save the image into memory (a buffer) instead of a file.
    # This increases performance as it saves on HDD writes and reads.
    image_buffer = io.BytesIO()

    plt.gcf().savefig(image_buffer, format='png')

    image_buffer.seek(0)

    # Returns a PNG image only - not a web page
    # The browser and user wouldn't know this is dynamically generated.
    return HttpResponse(image_buffer.read(), content_type="image/png")


def device_list(request):
    """
    Returns a list of SNMP enabled devices in the school. These will most likely be switches.
    Gets data from backend database.
    """

    set_of_devices = Device.objects.all()

    pagevars = {'title': "NetStatus Device List", 'set_of_devices': set_of_devices}

    return render(request, 'base_device_list.html', pagevars)


def new_device(request):
    """
    A page for creating a new entry in the database for a new device
    """

    # Only go if user submits a form
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = NewDeviceForm(request.POST)

        # Checks if x and y are actually numbers, in case the user has played with the Javascript
        if form.is_valid():

            if not ping(form.cleaned_data['ipv4_address']):

                # If the server cannot contact the device that the user has been specified, then let the user know
                # and do not let them add the device.
                return render(request, 'base_new_device.html', {'title': "NetStatus New Device",
                                                                'error': "Error: A SNMP session could not be set up "
                                                                         "with the device you entered. Please make sure"
                                                                         " that the IPv4 address is correct and the "
                                                                         "device is online before continuing.",
                                                                'form': form.as_p()})

            session = setup_snmp_session(form.cleaned_data['ipv4_address'])

            description = session.get('sysDescr')

            online = True  # We know this because we just 'pinged' the device

            device = Device(name=form.cleaned_data['name'], ipv4_address=form.cleaned_data['ipv4_address'],
                            location_x=form.cleaned_data['location_x'], location_y=form.cleaned_data['location_y'],
                            online=online, system_version=description)

            device.save()

            return HttpResponseRedirect(reverse('new-device_success'))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = NewDeviceForm()

    pagevars = {'title': "NetStatus New Device", 'form': form.as_p()}
    return render(request, 'base_new_device.html', pagevars)


def new_device_location(request):

    # There is very little Python here as most of the map logic is done in Javascript.

    return render(request, "base_new_device_location.html")


def new_device_success(request):
    """
    Lets the user know their device was added successfully and gives them options on what to do next.
    This is effectively a static view.
    """
    pagevars = {'title': "NetStatus New Device Success"}
    return render(request, 'base_new_device_success.html', pagevars)

def remove_device(request):
    """
    A page for removing devices from the database. Could be used for missentered devices, or devices that are no longer
    in use.
    """

        # Only go if user submits a form
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = RemoveDeviceForm(request.POST)

        if form.is_valid():

            id = form.cleaned_data['choose_device'].id

            device = Device.objects.get(pk=id)

            device.delete()

            return HttpResponseRedirect(reverse('remove-device'))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = RemoveDeviceForm()


    pagevars = {'title': "NetStatus Remove Device", 'form': form.as_p()}
    return render(request, 'base_remove_device.html', pagevars)


def device_info(request, id):
    """
    Sample testing page for getting information via SNMP from a device.
    """

    device = Device.objects.get(pk=id)

    ip = device.ipv4_address

    if not ping(ip):
        pagevars = {'title': 'Connection to device failed', 'info': 'Error, connection to the device specified failed. '
                                                                    'The device may be offline, or not accepting SNMP '
                                                                    'requests.'}
        return render(request, "base_get_device_info.html", pagevars)

    session = setup_snmp_session(ip)

    system_items = session.walk('system')

    system_information = {}

    for i in system_items:
        if i.oid != 'sysUpTimeInstance':
            system_information[i.oid] = i.value
        else:
            system_information[i.oid] = int(timeticks_to_days(int(i.value)))

    log_items = session.walk('mib-2.16.9.2.1.4')

    log_items_strings = []

    for item in log_items:
        # This means that only items that are classed as warnings will be shown to the user.
        # Informational alerts are less useful eg. show when a port has been connected and disconnected.
        if item.value.startswith('W'):
            log_items_strings.append(item.value)

    pagevars = {'title': "device info", 'system_information': system_information, 'log_items_strings': log_items_strings}

    return render(request, "base_device_info.html", pagevars)