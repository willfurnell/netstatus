from django.shortcuts import render, Http404, HttpResponse
# from easysnmp import Session
# from easysnmp import exceptions
# import os
import matplotlib.pyplot as plt
import io
# import base64
from netstatus.settings import BASE_DIR
from .utils import ping, setup_snmp_session, timeticks_to_days


def main(request):
    """
    Returns the front page of the website.
    """

    print(ping('10.49.86.1'))

    pagevars = {'title': "NetStatus Dashboard"}

    return render(request, 'base_index.html', pagevars)


def piechart_online(request):

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

    return HttpResponse(image_buffer.read(), content_type="image/png")


def device_list(request):
    """
    Returns a list of SNMP enabled devices in the school. These will most likely be switches.
    Gets data from backend database.
    """
    pagevars = {'title': "NetStatus Device List"}
    return render(request, 'base_index.html', pagevars)


def new_device(request):
    """
    A page for creating a new entry in the database for a new device
    """
    pagevars = {'title': "NetStatus New Device"}
    return render(request, 'base_index.html', pagevars)


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

    ip = '10.49.86.241'

    if not ping(ip):
        pagevars = {'title': 'Connection to device failed', 'info': 'Error, connection to the device specified failed. '
                                                                    'The device may be offline, or not accepting SNMP '
                                                                    'requests.'}
        return render(request, "base_get_device_info.html", pagevars)

    session = setup_snmp_session(ip)

    system_items = session.walk('system')

    attributes = []

    for item in system_items:
        attributes.append(item.value)

    print(attributes)

    # info = timeticks_to_days(int(uptime.value))

    pagevars = {'title': "device info",}
    return render(request, "base_get_device_info.html", pagevars)