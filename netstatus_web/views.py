from django.shortcuts import render, Http404, HttpResponse, HttpResponseRedirect
#import matplotlib.pyplot as plt
import pygal
import pygal.style
import io
from .utils import ping, setup_snmp_session, timeticks_to_days, sort_log, bin_to_hex_string, get_mac_address
from .forms import NewDeviceForm, RemoveDeviceForm, EditDeviceForm
from .models import Device
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from easysnmp import exceptions
import json
import socket

# make a timeline of errors/logs for a device on a graph


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

    custom_style = pygal.style.Style(
        background='transparent',
        colors=("#006600", "#ff0000") # Colours (red and green) for the offline/online status
    )

    pie_chart = pygal.Pie(style=custom_style, human_readable=True, print_values=True)

    pie_chart.title = "Number of online and offline devices on page load"

    pie_chart.add("Online devices", online)
    pie_chart.add("Offline devices", offline)

    #pie_chart.render_to_file(:memory:)

    # Returns a PNG image only - not a web page
    # The browser and user wouldn't know this is dynamically generated.
    return pie_chart.render_django_response()


def device_list(request):
    """
    Returns a list of SNMP enabled devices in the school. These will most likely be switches.
    Gets data from backend database.
    """

    set_of_devices = Device.objects.all()

    pagevars = {'title': "NetStatus Device List", 'set_of_devices': set_of_devices}

    return render(request, 'base_device_list.html', pagevars)


def device_new(request):
    """
    A page for creating a new entry in the database for a new device, gets the user submitted values from the form.
    X and Y co-ordinates are also obtained from the Javascript in the HTML page.
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
                return render(request, 'base_device_new.html', {'title': "NetStatus New Device",
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

            return HttpResponseRedirect(reverse('new-device-success'))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = NewDeviceForm()

    pagevars = {'title': "NetStatus New Device", 'form': form.as_p()}
    return render(request, 'base_device_new.html', pagevars)


def device_new_success(request):
    """
    Lets the user know their device was added successfully and gives them options on what to do next.
    This is effectively a static view.
    """
    pagevars = {'title': "NetStatus New Device Success"}
    return render(request, 'base_device_new_success.html', pagevars)


def device_remove(request):
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
    return render(request, 'base_device_remove.html', pagevars)


def device_edit_db(request, id):
    """
    A page for editing the database attributes of a device, uses a ModelForm to populate data from the database, and
    changes are reflected from user changes when submitting the form.
    """
    # Checks that the requested ID does actually belong to a device
    try:
        device = Device.objects.get(pk=id)
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        # Test in int field
        raise Http404

    if request.method == "POST":
        form = EditDeviceForm(request.POST, instance=device)

        if form.is_valid():

            form.save()

            print(device.id)

            return HttpResponseRedirect(reverse('device-edit-success'))

    else:
        form = EditDeviceForm(instance=device)

    pagevars = {'title': "NetStatus Edit Device", 'form': form.as_p(), 'id': id, 'device': device}

    return render(request, "base_device_edit_db.html", pagevars)


def device_edit_snmp(request, id):
    """
    Page for editing the SNMP attributes of a device. Returns form with pre-entered values from the device.
    Sets SNMP attributes based on submitted form.
    """
    # Checks that the requested ID does actually belong to a device
    try:
        device = Device.objects.get(pk=id)
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        # Text in int field
        raise Http404

    # Check the device is online before getting or changing attributes
    if not ping(device.ipv4_address):
        pagevars = {'title': 'Connection to device failed', 'info': 'Error, connection to the device specified failed. '
                                                                    'The device may be offline, or not accepting SNMP '
                                                                    'requests. Sorry, this means that the system will '
                                                                    'be unable to edit the SNMP based attributes of the'
                                                                    ' device.'}
        return render(request, "base_error.html", pagevars)

    if request.method == "POST":
        # Get users input from form
        sysName = request.POST.get('sysName')
        sysLocation = request.POST.get('sysLocation')
        sysContact = request.POST.get('sysContact')

        # Establish SNMP session with device
        session = setup_snmp_session(device.ipv4_address)

        # Set device SNMP variables to user input values
        try:
            session.set("sysName.0", sysName)
            session.set("sysLocation.0", sysLocation)
            session.set("sysContact.0", sysContact)
        except (exceptions.EasySNMPTimeoutError, exceptions.EasySNMPError):
            # For some reason the EasySNMP library returns a timeout error when it cannot set attributes for certain
            # models of switches. The EasySNMPError exception covers noAccess.
            pagevars = {'title': 'Editing attributes failed!', 'info': 'Error! The device you are trying to edit has'
                                                                       ' its community string set to read only mode. '
                                                                       'Unfortunately, this means NetStatus cannot edit'
                                                                       ' the SNMP attributes of the device.'}
            return render(request, "base_error.html", pagevars)

        return HttpResponseRedirect(reverse('device-edit-success'))

    session = setup_snmp_session(device.ipv4_address)

    system_items = session.walk('system')

    system_information = {}

    for i in system_items:
        system_information[i.oid] = i.value

    pagevars = {'title': "NetStatus Edit Device", 'device': device, 'system_information': system_information, 'id': id}
    return render(request, "base_device_edit_snmp.html", pagevars)


def device_edit_success(request):
    """
    Tell the user that editing the device was a success.
    """
    pagevars = {'title': "NetStatus Edit Device success"}
    return render(request, "base_device_edit_success.html", pagevars)


def device_info(request, id):
    """
    Page for getting information via SNMP from a device, and outputting it to the user. Gets system based attributes
    and logging information.
    """
    # Checks that the requested ID does actually belong to a device
    try:
        device = Device.objects.get(pk=id)
    except ObjectDoesNotExist:
        return Http404
    except ValueError:
        return Http404

    ip = device.ipv4_address

    if not ping(ip):
        pagevars = {'title': 'Connection to device failed', 'info': 'Error, connection to the device specified failed. '
                                                                    'The device may be offline, or not accepting SNMP '
                                                                    'requests.'}
        return render(request, "base_error.html", pagevars)

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

    pagevars = {'title': "NetStatus for " + device.name, 'system_information': system_information,
                'log_items_strings': log_items_strings, 'device': device}

    return render(request, "base_device_info.html", pagevars)

def testing(request):


    # if the sysname from the output matches one that is already in our database, then we can assume it is an uplink or
    # downlink to another switch. If it isn't in the database, then we can assume the device is an IP phone or something
    # and we'll treat it as an end device and ignore it being shown as a switch as this will get really complicated
    # otherwise

    # if there is more than one sysname AND its not a phone, then the switch is NOT a total end device, but could be
    # providing services to some end devices. Then we just ignore both ports!

    #oid = out[0].oid

    #port = oid[:-2]

    #port = out[0].oid.replace("iso.0.8802.1.1.2.1.4.1.1.9.0.", "")
    #port = port[:-2]

    return HttpResponse("Null")


def search(request):

    if request.method == "POST":
        user_input = request.POST.get('ipv4_address')

        try:
            socket.inet_aton(user_input)
        except socket.error:
            pagevars = {'title': "Search for a device", 'info': "Error: The IPv4 address you specified was not valid!"}

            return render(request, "base_error.html", pagevars)

        mac_to_find = get_mac_address(user_input)

        if mac_to_find == "ERR_PING_FAIL":
            pagevars = {'title': "Search for a device", 'info': "Error: The system could not ping the device you "
                                                                "specified! <br /> The device firewall may be "
                                                                "preventing this."}

            return render(request, "base_error.html", pagevars)

        if mac_to_find == "ERR_ARP_FAIL" or mac_to_find == "ERR_MALFORMED_MAC":
            pagevars = {'title': "Search for a device", 'info': "Error: The system could not get the MAC address of "
                                                                "the device you specified."}

            return render(request, "base_error.html", pagevars)

        device_list = Device.objects.all()

        ports_to_ignore = {}

        for device in device_list:
            if device.online is True and device.ipv4_address != "10.49.84.1":
                session = setup_snmp_session(device.ipv4_address)
                lldp_output = session.walk("1.0.8802.1.1.2.1.4.1.1.4")
                ports_to_ignore[device.id] = []
                for i in lldp_output:
                    # The whole OID is returned. Becuase we only want the port, we need to remove all the preceeding parts of the OID. We also need to remove the last 2
                    # characters as they are integers incrementing per port.
                    if (i.oid.replace("iso.0.8802.1.1.2.1.4.1.1.4.0.", "")[:-2] not in ports_to_ignore) and (i.oid.replace("iso.0.8802.1.1.2.1.4.1.1.4.0.", "")[:-2] != ""):
                        ports_to_ignore[device.id].append(i.oid.replace("iso.0.8802.1.1.2.1.4.1.1.4.0.", "")[:-2])

        # .1.3.6.1.2.1.17.4.3.1.1

        mac_to_port = {}

        for device in device_list:
            if device.ipv4_address != "10.49.84.1" and device.online is True:
                mac_to_port[device.id] = {}

                session = setup_snmp_session(device.ipv4_address)

                # OID for dot1dTpFdbAddress (MAC Address table)
                # http://oid-info.com/get/1.3.6.1.2.1.17.4.3.1.1
                mac_address_table = session.walk("1.3.6.1.2.1.17.4.3.1.1")
                # OID for dot1dTpFdbPort (Port table)
                # http://oid-info.com/get/1.3.6.1.2.1.17.4.3.1.2
                port_address_table = session.walk(".1.3.6.1.2.1.17.4.3.1.2")

                for mac_address in mac_address_table:
                    for port in port_address_table:
                        port_oid = port.oid.replace('mib-2.17.4.3.1.2', 'mib-2.17.4.3.1.1')
                        if port_oid == mac_address.oid:
                            if port.value not in ports_to_ignore[device.id]:
                                # Using .replace("b'", "") gets rid of any b char on the end of the mac address string.
                                # this causes us some serious problems...!
                                mac_to_port[device.id][bin_to_hex_string(mac_address.value)] = port.value

        out = "Could not find device!"
        for switch in mac_to_port:
            for mac_address in mac_to_port[switch]:
                if mac_address == mac_to_find:
                    out = "MAC: " + str(mac_to_find) + " Switch: " + str(switch) + " Port: " + mac_to_port[switch][mac_address]
                    break

        return HttpResponse(out)

    pagevars = {'title': "Search for a device"}

    return render(request, "base_search.html", pagevars)
