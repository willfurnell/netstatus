from django.shortcuts import render, Http404, HttpResponse

import base64
from easysnmp import Session
from easysnmp import exceptions
import binascii
from subprocess import check_output, CalledProcessError
import re
from .models import MACtoPort, IgnoredPort
import sys

def ping(ip):
    """
    'Pings' a specified IP address to check if it is online or not.
     Returns True if online, False if offline.

     True means that an SNMP session has successfuly been established and the system description has been got.
     False means that an SNMP session could not be established - however, the device may still actually be online.
     For my purposes, if a device does not establish an SNNP session, I can assume it is offline.
    """
    try:
        # The low timeout value is to decrease page loading time, as this is mainly for quickly checking
        # device status. We don't NEED to make a connection.
        session = Session(hostname=ip, community='***REMOVED***', version=2, timeout=0.1)
    except (exceptions.EasySNMPTimeoutError, exceptions.EasySNMPConnectionError):
        return False

    try:
        # Try and get sysDescr.0 from the device. It doesn't matter which element we choose, just that we can actually
        # get one, as we might be able to establish a connection but not get
        session.get('sysDescr.0')
        return True
    except exceptions.EasySNMPTimeoutError:
        return False


def timeticks_to_days(timeticks):
    """
    Converts SNMP timeticks to a value in days, which is much more human readable.
    """
    return timeticks / 8640000


def setup_snmp_session(ip):
    """
    Sets up an SNMP session with a device and returns this session.
    """
    session = Session(hostname=ip, community='***REMOVED***', version=2, timeout=2)
    return session


def get_mac_address(ip_address):
    """
    Uses the ARP MAC address table to get the MAC address for a specified IP address.
    """
    # Opens a new subprocess using the 'ping' command line utility. Pings the specified IP address once.
    try:
        # We have to do this as the ping binary location differs on OSX (Darwin) and Linux
        if sys.platform == "linux" or sys.platform == "linux2":
            ping_out = check_output(["/bin/ping", "-c 1", ip_address])
        elif sys.platform == "darwin":
            ping_out = check_output(["/sbin/ping", "-c 1", ip_address])
    except CalledProcessError:
        return "ERR_PING_FAIL"

    # This means the MAC address is now in our arp table, so we can find it. Opens a new subprocess using the arp
    # command line utility, passing the IP address as an argument, and gets its output so we can search through it.
    try:
        arp_out = check_output(["/usr/sbin/arp", "-n", ip_address])
    except CalledProcessError:
        return "ERR_ARP_FAIL"

    # Uses a regular expression to search for the MAC address in the ARP output.
    mac = re.search("([a-fA-F0-9]{2}:){5}([a-fA-F0-9]{2})", str(arp_out))

    if mac is None:
        return "ERR_MALFORMED_MAC"

    # Gets what the regex search found
    mac_to_find = mac.group(0)

    # Replaces colons in the output, as the HP switches used on the network don't use colon delimited MAC addresses in
    # their output
    mac_to_find = mac_to_find.replace(":", "")

    return mac_to_find


def port_ignore_list(device):
    """
    Returns a list of ports that have already been added to the IgnoredPort model for a specific device.
    """

    port_list = IgnoredPort.objects.all().filter(device=device).values_list('port', flat=True).order_by('port')
    return port_list


def update_ignored_ports(device_list):
    """
    Adds entries to the IgnoredPort model of uplink and downlink ports on a switch, using the LLDP information.

    The LLDP output will tell us, via the OIDs, which ports on a switch are uplink or downlink ports. These are the
    ones we want to ignore when searching, as they will likely have a MAC address table containing every device in the
    school! This isn't very useful as it will show every uplink/downlink port being the location of the device.
    """

    # Iterate over every device in the device list
    for device in device_list:
        # Check that it is online, and isn't the core switch
        if device.online is True and device.ipv4_address != "10.49.84.1":

            # Establish an SNMP session
            session = setup_snmp_session(device.ipv4_address)

            # Get a list of the LLDP output via SNMP.
            lldp_output = session.walk("1.0.8802.1.1.2.1.4.1.1.4")

            # Iterate over the elements in the LLDP output
            for i in lldp_output:
                # The whole OID is returned. Becuase we only want the port, which is actually a part of the OID itself, we need to
                # remove all the preceeding parts of the OID. We also need to remove the last 2
                # characters as they are integers incrementing per port.
                # This check makes sure that the port we are using isn't already in the ports to ignore,
                # and the OID is actually a port.
                if (i.oid.replace("iso.0.8802.1.1.2.1.4.1.1.4.0.", "")[:-2] not in port_ignore_list(device)) and (i.oid.replace("iso.0.8802.1.1.2.1.4.1.1.4.0.", "")[:-2] != ""):
                    # Add a new entry to the database containing the device and ignored port relationship, for this port.
                    entry = IgnoredPort(device=device, port=i.oid.replace("iso.0.8802.1.1.2.1.4.1.1.4.0.", "")[:-2])
                    entry.save()


def decimal_to_mac(input):
    """
    Converts the decimal representation of a MAC address used in an SNMP OID to the hexadecimal one most widely used.
    """
    input = input.replace("mib-2.17.4.3.1.2.", "")  # Replace the identifier part of the OID
    octets = input.split(".")  # Split up at the . denominator for each octet
    octets_hex = []
    for octet in octets:
        octets_hex.append(format(int(octet), "x"))  # Add the hexadecimal representation of each octet to a list

    mac_address = ''.join(octets_hex)  # Convert this list into a single string

    return mac_address


def update_mac_to_port(device_list):
    """
    Adds entries to the MACtoPort model with a MAC address -> Port relationship, including the device which the port
    belongs to.

    The Port Address Table will contain all the ports on the switch, and also contains a decimal
    representation of the MAC address associated with that port, in a list of EasySNMP objects.

    The OID of the element contains the MAC address in decimal form, and the value of the element contains the port.

    This iterates through every OID in the list, and checks that the value (port) is not in the port ignore list -
    if not, it adds an entry with the hexadecimal represenation of the MAC address and the port it belongs to.
    """

    # Iterate over the device list
    for device in device_list:
        # Make sure the device isn't the core switch and is online
        if device.ipv4_address != "10.49.84.1" and device.online is True:

            # Establish an SNMP session with the device
            session = setup_snmp_session(device.ipv4_address)

            # OID for dot1dTpFdbPort (Port table)
            # http://oid-info.com/get/1.3.6.1.2.1.17.4.3.1.2
            port_address_table = session.walk(".1.3.6.1.2.1.17.4.3.1.2")

            for item in port_address_table:
                # item.oid contains the MAC address and item.value is the name of the port itself

                # Check that the port is not in our ignore list
                if int(item.value) not in port_ignore_list(device):
                    # Convert the decimal MAC to a hexadecimal representation, which is widely used,
                    # and add a new object with this information.
                    entry = MACtoPort(device=device, mac_address=decimal_to_mac(item.oid), port=item.value)
                    entry.save()

