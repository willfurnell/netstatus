from django.shortcuts import render, Http404, HttpResponse, HttpResponseRedirect
# from easysnmp import Session
# from easysnmp import exceptions
# import os
import matplotlib.pyplot as plt
import io
# import base64
from netstatus.settings import BASE_DIR
from .utils import ping, setup_snmp_session, timeticks_to_days
from .forms import NewDeviceForm
from .models import Device
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger



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

    devlist = ['10.49.86.241', '10.49.84.1', '10.49.84.108', '10.49.87.17']

    online = 0
    offline = 0

    for device in devlist:
        if ping(device):
            online = online + 1
        else:
            offline = offline + 1

    labels = 'Offline', 'Online'

    sizes = [offline, online]

    colors = ['red', 'green']

    plt.pie(sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', shadow=True, startangle=90)
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

    all_devices = Device.objects.all()

    paginator = Paginator(all_devices, 25) # Show 25 devices per page

    page = request.GET.get('page')
    try:
         set_of_devices = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        set_of_devices = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        set_of_devices = paginator.page(paginator.num_pages)


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
                                location=form.cleaned_data['location'], description=description, online=online)

            device.save()

            return HttpResponseRedirect(reverse('new-device_success'))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = NewDeviceForm()

    pagevars = {'title': "NetStatus New Device", 'form': form.as_p()}
    return render(request, 'base_new_device.html', pagevars)


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
    pagevars = {'title': "NetStatus Remove Device"}
    return render(request, 'base_index.html', pagevars)


def get_device_info(request):
    """
    Sample testing page for getting information via SNMP from a device.
    """

    ip2 = '10.49.85.64'

    ip = '10.49.86.241'

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