from django.shortcuts import render, Http404, HttpResponse

import base64
from easysnmp import Session
from easysnmp import exceptions
import binascii
from subprocess import check_output, CalledProcessError
import re

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
        session.get('sysDescr.0')
        return True
    except exceptions.EasySNMPTimeoutError:
        return False


def check_connect_failure_return(ip):
    """
    A wrapper for the 'ping' function to return that there was a failure connecting to the device to the user
    """
    return NotImplemented


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


def make_base64_image(image_buffer):
    image_buffer.seek(0)

    graph_b64 = str(base64.b64encode(image_buffer.read()))

    return graph_b64.lstrip("b'").rstrip("'")

    # 'graph_image': graph_b64.lstrip("b'").rstrip("'")

    # print(ping('10.49.86.241'))

def sort_log(log, so):
    """
    Function used to sort the SNMP log file to order of importance and or date
    """
    return NotImplementedError


def ip_to_location():
    pass


def bin_to_hex_string(input):
    """
    Gets a binary string from the SNMP data of a switch, which we know is encoded in latin-1 from reading the
    easysnmp source. Converts this input to raw bytes and then converts to hexadecimal, then converts to a string.
    Returns a hex value of the data, allowing us to get MAC addresses from the switches.
    """
    return binascii.hexlify(bytes(input, 'latin-1')).decode('utf-8')


def get_mac_address(ip_address):
    """
    Uses the ARP MAC address table to get the MAC address for a specified IP address.
    """
    # Opens a new subprocess using the 'ping' command line utility. Pings the specified IP address once.
    try:
        ping_out = check_output(["/sbin/ping", "-c 1", ip_address])
    except CalledProcessError:
        return "ERR_PING_FAIL"

    # This means the MAC address is now in our arp table, so we can find it.
    try:
        arp_out = check_output(["/usr/sbin/arp", "-n", ip_address])
    except CalledProcessError:
        return "ERR_ARP_FAIL"

    # Uses a regular expression to search for the MAC address in the ARP ouput.
    mac = re.search("([a-fA-F0-9]{2}:){5}([a-fA-F0-9]{2})", str(arp_out))

    if mac == None:
        return "ERR_MALFORMED_MAC"

    # Gets what the regex search found
    mac_to_find = mac.group(0)

    mac_to_find = mac_to_find.replace(":", "")

    return mac_to_find
