def update_mac_to_port_old(device_list):
    """
    Adds entries to the MACtoPort model with a MAC address -> Port relationship, including the device which the port
    belongs to.

    The MAC Address Table output will contain the MAC address table for every port on the switch, all in one big list of
    EasySNMP objects.

    Likewise, the Port Address Table will contain all the ports on the switch, and also contains a decimal
    representation of the MAC address associated with that port, in a list of EasySNMP objects.

    """

    # Iterate over the device list
    for device in device_list:
        # Make sure the device isn't the core switch and is online
        if device.ipv4_address != "10.49.84.1" and device.online is True:

            # Establish an SNMP session with the device
            session = setup_snmp_session(device.ipv4_address)

            # OID for dot1dTpFdbAddress (MAC Address table)
            # http://oid-info.com/get/1.3.6.1.2.1.17.4.3.1.1
            mac_address_table = session.walk("1.3.6.1.2.1.17.4.3.1.1")
            # OID for dot1dTpFdbPort (Port table)
            # http://oid-info.com/get/1.3.6.1.2.1.17.4.3.1.2
            port_address_table = session.walk(".1.3.6.1.2.1.17.4.3.1.2")

            for mac_address in mac_address_table:
                for port in port_address_table:
                    # As the port address table and the mac address table have different OIDs, the port address
                    # table one needs to be changed to be the same as the MAC address one. They have exactly the
                    # same OID otherwise, which allows us to get a direct comparison.
                    port_oid = port.oid.replace('mib-2.17.4.3.1.2', 'mib-2.17.4.3.1.1')
                    if port_oid == mac_address.oid:
                        # Check that the port is not in our ignore list
                        if int(port.value) not in port_ignore_list(device):
                            print(port.value)
                            # Convert the MAC to hexadecimal and a string, and put it into our database.
                            entry = MACtoPort(device=device, mac_address=bin_to_hex_string(mac_address.value), port=port.value)
                            entry.save()

def make_base64_image(image_buffer):
    image_buffer.seek(0)

    graph_b64 = base64.b64encode(image_buffer.read())

    return graph_b64.decode('utf-8')

    # 'graph_image': graph_b64.lstrip("b'").rstrip("'")

    # print(ping('10.49.86.241'))


def bin_to_hex_string(input):
    """
    Gets a binary string from the SNMP data of a switch, which we know is encoded in latin-1 from reading the
    easysnmp source.

    Converts this input to raw bytes and then converts to hexadecimal, then converts to a string.
    Returns a hex value of the data, allowing us to get MAC addresses from the switches.
    """
    return binascii.hexlify(bytes(input, 'latin-1')).decode('utf-8')


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


    session = setup_snmp_session("10.49.86.241")

    port_address_table = session.walk(".1.3.6.1.2.1.17.4.3.1.2")

    def decimal_to_mac(input):
        input = input.replace("mib-2.17.4.3.1.2.","")
        parts = input.split(".")
        parts_hex = []
        for element in parts:
            parts_hex.append(format(int(element), "x"))

        mac_address = ''.join(parts_hex)

        return mac_address

    print(decimal_to_mac(port_address_table[0].oid))


    return HttpResponse("Null")
