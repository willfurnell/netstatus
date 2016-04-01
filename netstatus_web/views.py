from django.shortcuts import render, Http404, HttpResponse, HttpResponseRedirect
#import matplotlib.pyplot as plt
import pygal
import pygal.style
import io
from .utils import *
from .forms import NewDeviceForm, RemoveDeviceForm, EditDeviceForm
from .models import Device, LastUpdated, MACtoPort, IgnoredPort
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from easysnmp import exceptions
import socket
import time


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
    Returns an SVG image of the chart (which is never stored on disk - only in memory).
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

    # Returns a SVG image only - not a web page
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

            # Connect to SNMP agent, which we already know is online, so don't need to check status again.
            session = setup_snmp_session(form.cleaned_data['ipv4_address'])

            description = session.get('sysDescr')

            online = True  # We know this because we just 'pinged' the device

            # Create Device object with information the user submitted
            device = Device(name=form.cleaned_data['name'], ipv4_address=form.cleaned_data['ipv4_address'],
                            location_x=form.cleaned_data['location_x'], location_y=form.cleaned_data['location_y'],
                            online=online, system_version=description)

            # Add the entry to the database
            device.save()

            # Redirect the user to the success page
            return HttpResponseRedirect(reverse('new-device-success'))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = NewDeviceForm()

    # Output the page to the user
    pagevars = {'title': "NetStatus New Device", 'form': form.as_p()}
    return render(request, 'base_device_new.html', pagevars)


def device_new_success(request):
    """
    Lets the user know their device was added successfully and gives them options on what to do next.
    This is effectively a static view.
    """

    # Output the page to the user
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

            # Get the primary key of the item chosen in the dropdown menu
            id = form.cleaned_data['choose_device'].id

            # Get the Device object relating to that primary key
            device = Device.objects.get(pk=id)

            # Remove this from the database
            device.delete()
            # Redirect the user back to the remove device page
            return HttpResponseRedirect(reverse('remove-device'))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = RemoveDeviceForm()

    # Output page to users browser
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
        # ID does not belong to a device
        raise Http404
    except ValueError:
        # Test in int field
        raise Http404

    # If the user submits the form...
    if request.method == "POST":
        # Using the POST data to populate the EditDeviceForm, editing an existing object, in this case the device
        # defined earlier
        form = EditDeviceForm(request.POST, instance=device)

        if form.is_valid():

            # Update form information in the database
            form.save()
            # Redirect the user to the editing device success page
            return HttpResponseRedirect(reverse('device-edit-success'))

    else:
        # Create a new form instance, pre populating it with data from the device object so it can be edited by the
        # user.
        form = EditDeviceForm(instance=device)

    # Output page to users browser with the following information sent to the page template
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
        # ID does not belong to a device
        raise Http404
    except ValueError:
        # Text in int field
        raise Http404

    # Check the device is online before getting or changing attributes - this is important as we are editing SNMP
    # attributes, which are stored directly on the device.
    if not ping(device.ipv4_address):
        # If its not online, then we won't be able to get and therefore change these attributes
        pagevars = {'title': 'Connection to device failed', 'info': 'Error, connection to the device specified failed. '
                                                                    'The device may be offline, or not accepting SNMP '
                                                                    'requests. Sorry, this means that the system will '
                                                                    'be unable to edit the SNMP based attributes of the'
                                                                    ' device.'}
        return render(request, "base_error.html", pagevars)

    # If the user submits the form
    if request.method == "POST":
        # Get users input from form
        sysName = request.POST.get('sysName')
        sysLocation = request.POST.get('sysLocation')
        sysContact = request.POST.get('sysContact')

        # Establish SNMP session with device
        session = setup_snmp_session(device.ipv4_address)

        # Set device SNMP variables to user input values
        # .0 is required here to edit the element
        try:
            session.set("sysName.0", sysName)
            session.set("sysLocation.0", sysLocation)
            session.set("sysContact.0", sysContact)
        except (exceptions.EasySNMPTimeoutError, exceptions.EasySNMPError):
            # For some reason the EasySNMP library returns a timeout error when it cannot set attributes for certain
            # models of switches. (HP 1910-16G). The EasySNMPError exception covers noAccess (permission denied to edit)
            pagevars = {'title': 'Editing attributes failed!', 'info': 'Error! The device you are trying to edit has'
                                                                       ' its community string set to read only mode. '
                                                                       'Unfortunately, this means NetStatus cannot edit'
                                                                       ' the SNMP attributes of the device.'}
            return render(request, "base_error.html", pagevars)

        # To get to this stage, editing will have been successful so redirect the user to the editing device success
        # page
        return HttpResponseRedirect(reverse('device-edit-success'))

    # Establish SNMP session with device
    session = setup_snmp_session(device.ipv4_address)

    # Get the system attributes we want the user to be able to edit from the device
    sysName = session.get("sysName.0")
    sysLocation = session.get("sysLocation.0")
    sysContact = session.get("sysContact.0")

    # Output the page to the user, with the following information sent to the page template
    pagevars = {'title': "NetStatus Edit Device", 'device': device, 'sysName': sysName, 'sysLocation': sysLocation,
                'sysContact': sysContact, 'id': id}
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
        # ID does not belong to a device
        raise Http404
    except ValueError:
        # Text in an int only field
        raise Http404

    # Make sure device is online before trying to get any information from it
    if not ping(device.ipv4_address):
        pagevars = {'title': 'Connection to device failed', 'info': 'Error, connection to the device specified failed. '
                                                                    'The device may be offline, or not accepting SNMP '
                                                                    'requests.'}
        return render(request, "base_error.html", pagevars)

    # Establish SNMP session with the device
    session = setup_snmp_session(device.ipv4_address)

    # Get a list of system items from the device
    system_items = session.walk('system')

    system_information = {}

    # Iterate over this list and put the items in a dictionary with OID -> OID Value (the rest of the information has
    # little use to us)
    for i in system_items:
        if i.oid != 'sysUpTimeInstance':
            system_information[i.oid] = i.value
        else:
            # Convert the timeticks value of this OID to days so its easier for the user to read
            system_information[i.oid] = int(timeticks_to_days(int(i.value)))

    # Get a list of log items from the device
    log_items = session.walk('mib-2.16.9.2.1.4')

    log_items_strings = []

    # Iterate over this list
    for item in log_items:
        # This means that only items that are classed as warnings will be shown to the user.
        # Informational alerts are less useful eg. show when a port has been connected and disconnected.
        if item.value.startswith('W'):
            log_items_strings.append(item.value)

    # Output the page to the user with the following attributes sent to the template
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
    """
    Lets the user search for a device on the whole network, assuming it is connected to one of the switches tracked
    by NetStatus.

    First gets the MAC address of the device to find, and then gets the LLDP port tables (to get a list of ports to
    ignore), MAC address tables and port tables from all of the switches on the system.
    Checks the MAC address against the filtered MAC address tables to see where on the network the device is.
    """

    # If the user submits the form...
    if request.method == "POST":
        # Get the (hopefully) IPv4 address the user entered
        user_input = request.POST.get('ipv4_address')

        # If the user has requested to delete the cached objects
        if 'delcache' in request.POST:
            # The user has requested that we delete all cached items
            try:
                # Get first row of the LastUpdated model
                last_updated = LastUpdated.objects.get(pk=1)
                # Setting the time stamps to 0 will force the system to regrab any results as 0 indicates that the
                # last updated time was Thurs 1st Jan 1970 at 00:00:00 GMT.
                last_updated.ignored_port = 0
                last_updated.mac_to_port = 0
                # Update database entry
                last_updated.save()
            except:
                # This is in case the user clicks 'Delete cache' before any searches have even been made!
                # Initialises the first object in the LastUpdated table
                last_updated = LastUpdated(mac_to_port=0, ignored_port=0)
                last_updated.save()
            # Delete all the objects in the IgnoredPort and MACtoPort models
            IgnoredPort.objects.all().delete()
            MACtoPort.objects.all().delete()

            # Output page with message telling user the cache was cleared
            pagevars = {'title': "Search for a device", 'message': "Cache cleared successfully!"}

            return render(request, "base_search.html", pagevars)


        try:
            # Tries to establish a socket with the IP address the user provided. Will error if the address is not
            # correct/valid etc.
            socket.inet_aton(user_input)
        except socket.error:
            pagevars = {'title': "Search for a device", 'message': "Error: The IPv4 address you specified was not "
                                                                   "valid!"}

            return render(request, "base_search.html", pagevars)

        # Call the get_mac_address function in utils.py to get the MAC address of the IP address the user provided.
        mac_to_find = get_mac_address(user_input)

        # ERR_PING_FAIL returned when get_mac_address cannot ping the specified device
        if mac_to_find == "ERR_PING_FAIL":
            pagevars = {'title': "Search for a device", 'message': "Error: The system could not ping the device you "
                                                                "specified! The device firewall may be "
                                                                "preventing this."}

            return render(request, "base_search.html", pagevars)

        # get_mac_address either didn't get a MAC address at all, or the one it did get wasn't the correct number of
        # characters
        if mac_to_find == "ERR_ARP_FAIL" or mac_to_find == "ERR_MALFORMED_MAC":
            pagevars = {'title': "Search for a device", 'message': "Error: The system could not get the MAC address of "
                                                                "the device you specified."}

            return render(request, "base_search.html", pagevars)

        device_list = Device.objects.all()

        # To speed things up, the search system will generally used cached results in the database.
        # The ignored ports will only be rechecked if a week has passed, as these are likely to rarely change.
        # The MAC address to port results need to be updated more regularly as this data changes more often, so a value
        # of 1 day has been chosen. The user can always choose to clear the cached results and start a search from
        # scratch if they are having problems finding a correct location.

        # Note: EasySNMPTimeoutError will be thrown when EasySNMP has problems connecting to a switch (even if it is
        # online)

        # A try statement is used in case this is the first run of the program. In this instance, the LastUpdated object
        # with PK 1 will not exist yet. If the search function has been run before, then PK 1 will exist so the system
        # can continue as normal.
        try:
            last_updated = LastUpdated.objects.get(pk=1)

            # 604800 seconds = 1 week
            if int(time.time()) >= last_updated.ignored_port + 604800:
                last_updated.ignored_port = int(time.time())
                last_updated.save()
                # We delete the existing objects every time to 'purge' the cache
                IgnoredPort.objects.all().delete()

                try:
                    # Run the update_ignored_ports function in utils.py
                    update_ignored_ports(device_list)
                except exceptions.EasySNMPTimeoutError:
                    # If sonnecting to a switch does fail...
                    pagevars = {'title': "Search for a device", 'message':
                        "Error: The system could not contact a switch during the search."}

                    return render(request, "base_search.html", pagevars)

            # 8600 seconds = 1 day
            if int(time.time()) >= last_updated.mac_to_port + 8600:
                last_updated.mac_to_port = time.time()
                last_updated.save()
                # We delete the existing objects every time to 'purge' the cache
                MACtoPort.objects.all().delete()

                try:
                    # Run the update_mac_to_port function in utils.py
                    update_mac_to_port(device_list)
                except exceptions.EasySNMPTimeoutError:
                    # If connecting to a switch does fail...
                    pagevars = {'title': "Search for a device", 'message':
                        "Error: The system could not contact a switch during the search."}

                    return render(request, "base_error.html", pagevars)

        except ObjectDoesNotExist:
            # This is the first run of the searching algorithm, so we need to initialise the PK 1 of LastUpdated
            last_updated = LastUpdated(mac_to_port=int(time.time()), ignored_port=int(time.time()))
            last_updated.save()

            try:
                # Run through the algorithm fully. We don't need to check last updated times as this is the first run.
                update_ignored_ports(device_list)
                update_mac_to_port(device_list)
            except exceptions.EasySNMPTimeoutError:
                # If connecting to a switch does fail...
                pagevars = {'title': "Search for a device", 'message':
                    "Error: The system could not contact a switch during the search."}

                return render(request, "base_search.html", pagevars)

        # .1.3.6.1.2.1.17.4.3.1.1

        try:
            # Get the first result from the database in the MACtoPort table corresponding with the MAC address of the
            # device the user entered.
            mac_to_port_info = MACtoPort.objects.all().filter(mac_address__exact=mac_to_find).first()
            # Get the corresponding switch attributes from the database, this is so we can tell the user the switch
            # and which port the device is connected to.
            device = Device.objects.get(id=mac_to_port_info.device_id)

            pagevars = {'title': "Device search results", 'device': device, 'mac_to_port_info': mac_to_port_info}

            return render(request, "base_search_result.html", pagevars)

        except ObjectDoesNotExist:
            # The MAC address could not be found in the database - so the device could have been added recently,
            # or its on a switch that we just don't track (eg. behind an IP phone).
            pagevars = {'title': "Device search returned no results"}

            return render(request, "base_search_noresult.html", pagevars)

    # Output the search page to the user
    pagevars = {'title': "Search for a device"}

    return render(request, "base_search.html", pagevars)
