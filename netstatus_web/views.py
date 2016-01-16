from django.shortcuts import render, Http404, HttpResponse
from easysnmp import Session
from easysnmp import exceptions
import os

# Create your views here.


def ping(ip):

    response = os.system("ping -c 1 " + ip)

    return response

def timeticks_to_days(timeticks):
    return timeticks / 8640000


def setup_snmp_session(request, ip):
    try:
        session = Session(hostname=ip, community='***REMOVED***', version=2)
        return session
    except exceptions.EasySNMPTimeoutError:
        pagevars = {'title': "device info", 'info': "Connection to device failed"}
        return render(request, "base_get_device_info.html", pagevars)


def main(request):

    pagevars = {'title': "NetStatus Dashboard"}
    return render(request, 'base_index.html', pagevars)


def device_list(request):
    pagevars = {'title': "NetStatus Device List"}
    return render(request, 'base_index.html', pagevars)


def new_device(request):
    pagevars = {'title': "NetStatus New Device"}
    return render(request, 'base_index.html', pagevars)


def remove_device(request):
    pagevars = {'title': "NetStatus Remove Device"}
    return render(request, 'base_index.html', pagevars)

def get_device_info(request):

    ip = '10.49.86.241'

    ip2 = '10.49.86.1'

    print(ping('10.49.86.1'))

    session = setup_snmp_session(request, ip2)

    try:
        sysdescr = session.get('sysDescr.0')
    except exceptions.EasySNMPTimeoutError as e:
        return HttpResponse(str(e))


    uptime = session.get('sysUpTime.0')

    info = timeticks_to_days(int(uptime.value))

    pagevars = {'title': "device info", 'info': info}
    return render(request, "base_get_device_info.html", pagevars)