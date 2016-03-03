from django.shortcuts import render, Http404, HttpResponse

import base64
from easysnmp import Session
from easysnmp import exceptions


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
    session = Session(hostname=ip, community='***REMOVED***', version=2, timeout=0.1)
    return session


def make_base64_image(image_buffer):
    image_buffer.seek(0)

    graph_b64 = str(base64.b64encode(image_buffer.read()))

    return graph_b64.lstrip("b'").rstrip("'")

    # 'graph_image': graph_b64.lstrip("b'").rstrip("'")

    # print(ping('10.49.86.241'))
