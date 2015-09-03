#!/usr/bin/python
"""
Copyright (C) 2015 Hewlett Packard Enterprise Development LP
All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""
import os
import sys
import time
import re
from mininet.net import *
from mininet.topo import *
from mininet.node import *
from mininet.link import *
from mininet.cli import *
from mininet.log import *
from mininet.util import *
from subprocess import *
from halonvsi.docker import *
from halonvsi.halon import *
import select


class mgmtIntfTests( HalonTest ):
    #This class memeber used to retaining the IPv4 whcih is got from DHCP server
    Dhcp_Ipv4_submask=''

    def setupNet(self):
        # If you override this function, make sure to
        # either pass getNodeOpts() into hopts/sopts of the topology that
        # you build or into addHost/addSwitch calls.
        mgmt_topo = SingleSwitchTopo(k=0,
                                     hopts=self.getHostOpts(),
                                     sopts=self.getSwitchOpts())
        self.net = Mininet(topo=mgmt_topo,
                           switch=HalonSwitch,
                           host=HalonHost,
                           link=HalonLink, controller=None,
                           build=True)

    def mgmt_intf_config_commands_dhcp_ipv4(self):
        info('\n########## Test to configure Management interface with DHCP IPV4 ##########\n')
        # configuring Halon, in the future it would be through
        # proper Halon commands.
        s1 = self.net.switches[ 0 ]

        # DHCP client started on management interface
        output = s1.cmd("systemctl status dhclient@eth0.service")
        assert 'running' in output,'Test to verify dhcp client has started Failed'
        info('### Sucussfully verified dhcp client has started ###\n')

        # Mgmt Interface updated during bootup.
        output = s1.cmd("ovs-vsctl list open_vswitch")
        output += s1.cmd("echo")
        assert 'name="eth0"' in output,'Test to mgmt interface has updated from image.manifest file Failed'
        info('### Sucussfully verified mgmt interface has updated from image.manifest file ###\n')

        # Enter the management interface context.
        output = s1.cmdCLI("configure terminal")
        assert 'Unknown command' not in output,'Test to enter the management interface context Failed'
        output = s1.cmdCLI("interface mgmt")
        assert 'Unknown command' not in output,'Test to enter the management interface context Failed'
        info('### Sucussfully verified enter into the management interface context ###\n')

        # Set mode as DHCP
        s1.cmdCLI("ip dhcp")
        output = s1.cmdCLI(" ")
        cnt = 15
        tmp =[]
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmdCLI(" ")
            tmp = re.findall("IPv4 address/subnet-mask\s+: \d+.\d+.\d+.\d+/\d+.\d+.\d+.\d+",output)
            if tmp:
                break
            else:
                sleep(1)
                cnt -= 1
        self.Dhcp_Ipv4_submask = re.findall("\d+.\d+.\d+.\d+",tmp[0])
        assert 'dhcp' in output,'Test to set mode as DHCP Failed'
        output = s1.cmd("systemctl status dhclient@eth0.service")
        assert 'running' in output,'Test to set mode as DHCP Failed'
        info('### Sucussfully configured DHCP mode ###\n')

        #Add Default gateway in DHCP mode
        output = s1.cmdCLI("default-gateway 172.17.0.1")
        assert 'Configurations not allowed in dhcp mode' in output,'Test to add default gateway in DHCP mode Failed'
        output = s1.cmdCLI(" ")
        output = s1.cmdCLI("do show interface mgmt")
        temp = re.findall("Default gateway IPv4\s+: .*\n",output)
        assert temp[0] in output,'Test to add default gateway in DHCP mode Failed'
        info('### Sucussfully verified configuration of Deafult gateway in DHCP mode ###\n')

        # Add DNS Server 1 in DHCP mode.
        output = s1.cmdCLI("nameserver 10.10.10.1")
        assert 'Configurations not allowed in dhcp mode' in output,'Test to add Primary DNS in DHCP mode Failed'
        output = s1.cmdCLI(" ")
        output = s1.cmd("echo")
        output = s1.cmdCLI("do show interface mgmt")
        assert '10.10.10.1' not in output,'Test to add Primary DNS in DHCP mode Failed'
        info('### Sucussfully verified configuration of Primary DNS in DHCP mode ###\n')

        # Add DNS Server 2 in DHCP mode.
        output = s1.cmdCLI("nameserver 10.10.10.1 10.10.10.2")
        assert 'Configurations not allowed in dhcp mode' in output,'Test to add Secondary DNS in DHCP mode Failed'
        output = s1.cmdCLI(" ")
        output = s1.cmd("echo")
        output = s1.cmdCLI("do show interface mgmt")
        output += s1.cmd("echo")
        assert '10.10.10.2' not in output,'Test to add Secondary DNS in DHCP mode Failed'
        info('### Sucussfully verified configuration of Secondary DNS in DHCP mode ###\n')

    def mgmt_intf_config_commands_static_ipv4(self):
        info('\n########## Test to configure Management interface with static IPV4 ##########\n')
        s1 = self.net.switches[ 0 ]

        # Static IP config when mode is static.
        IPV4_static = re.sub('\d+$','128', self.Dhcp_Ipv4_submask[0])
        s1.cmdCLI("ip static "+IPV4_static+" "+self.Dhcp_Ipv4_submask[1])
        output = s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if IPV4_static in output and self.Dhcp_Ipv4_submask[1] in output:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("ifconfig")
                    output += s1.cmd("echo")
                    if IPV4_static in output and self.Dhcp_Ipv4_submask[1] in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert IPV4_static in output,'Test to add static IP address in static mode Failed'
        assert self.Dhcp_Ipv4_submask[1] in output,'Test to add static IP address in static mode Failed'
        info('### Sucussfully configured static IP address in static mode ###\n')

        # Reconfigure Sattic IP when mode is static
        IPV4_static = re.sub('\d+$','129', self.Dhcp_Ipv4_submask[0])
        s1.cmdCLI("ip static "+IPV4_static+" "+self.Dhcp_Ipv4_submask[1])
        output = s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if IPV4_static in output and self.Dhcp_Ipv4_submask[1] in output:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("ifconfig")
                    output += s1.cmd("echo")
                    if IPV4_static in output and self.Dhcp_Ipv4_submask[1] in output:
                        break
                    else:
                       cnt2 -= 1
                       sleep(1)
                break
            else:
               sleep(1)
               cnt -= 1
        assert IPV4_static in output,'Test to Reconfigure static IP address in static mode Failed'
        assert self.Dhcp_Ipv4_submask[1] in output,'Test to Reconfigure static IP address in static mode Failed'
        info('### Sucussfully Reconfigured static IP address in static mode ###\n')

        # Add Default gateway in Static mode.
        IPV4_default = re.sub('\d+$','130', self.Dhcp_Ipv4_submask[0])
        s1.cmdCLI("default-gateway "+IPV4_default)
        output = s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if IPV4_default in output:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("ip route show")
                    output += s1.cmd("echo")
                    if IPV4_default in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert IPV4_default in output,'Test to add Default gateway in static mode Failed'
        info('### Sucussfully configured Default gateway in static mode ###\n')

        # Remove Default gateway in static mode.
        s1.cmdCLI("no default-gateway "+IPV4_default)
        output = s1.cmdCLI(" ")
        output = s1.cmdCLI("do show interface mgmt")
        output += s1.cmdCLI(" ")
        temp = re.findall("Default gateway\s+: "+IPV4_default,output)
        buf = ''
        if temp:
            buf = ' '
        assert buf in output,'Test to remove default gateway Failed'
        cnt2 = 15
        while cnt2:
            output = s1.cmd("ip route show")
            output += s1.cmd("echo")
            if IPV4_default not in output:
                break
            else:
                cnt2 -= 1
                sleep(1)
        assert IPV4_default not in output,'Test to remove default gateway Failed'
        info('### Sucussfully Removed Default gateway in static mode ###\n')


        # Add DNS Server 1 in static mode.
        s1.cmdCLI("nameserver 10.10.10.5")
        output = s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            if '10.10.10.5' in output:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 10.10.10.5' in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '10.10.10.5' in output,'Test to add Primary DNS Failed'
        info('### Sucussfully configured Primary DNS in static mode ###\n')

        # Add another primary DNS server.
        s1.cmdCLI("nameserver 10.10.10.20")
        output = s1.cmdCLI(" ")
        output = s1.cmdCLI("do show interface mgmt")
        output = s1.cmd("cat /etc/resolv.conf")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if '10.10.10.20' in output:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 10.10.10.20' in output and 'nameserver 10.10.10.1' not in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '10.10.10.20' in output,'Test to Reconfigure Primary DNS Failed'
        assert '10.10.10.1' not in output,'Test to Reconfigure Primary DNS Failed'
        info('### Sucussfully Reconfigured Primary DNS in static mode ###\n')

        # Remove primary DNS server.
        s1.cmdCLI("no nameserver 10.10.10.20")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if 'Primary Nameserver            : 10.10.10.20' not in output:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 10.10.10.20' not in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '10.10.10.20' not in output,'Test to Remove Primary DNS Failed'
        info('### Sucussfully Removed Primary DNS in static mode ###\n')

        # Add Secondary DNS Server in static mode.
        s1.cmdCLI("nameserver 10.10.10.4 10.10.10.5")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if re.findall("Primary Nameserver\s+: 10.10.10.4",output) and \
               re.findall("Secondary Nameserver\s+: 10.10.10.5",output):
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 10.10.10.5' in output and 'nameserver 10.10.10.4' in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '10.10.10.5' in output,'Test to add Secondary DNS Failed'
        assert '10.10.10.4' in output,'Test to add Secondary DNS Failed'
        info('### Sucussfully Configured Secondary DNS in static mode ###\n')

        # Set the IP again another secondary DNS server.
        s1.cmdCLI("nameserver 10.10.10.4 10.10.10.20")
        output_show = s1.cmdCLI("do show interface mgmt")
        output += s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if re.findall("Primary Nameserver\s+: 10.10.10.4",output) and \
               re.findall("Secondary Nameserver\s+: 10.10.10.20",output):
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 10.10.10.4' in output and 'nameserver 10.10.10.5' not in output and \
                       'nameserver 10.10.10.20' in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '10.10.10.4' in output,'Test to Reconfigure Secondary DNS Failed'
        assert '10.10.10.5' not in output,'Test to Reconfigure Secondary DNS Failed'
        assert '10.10.10.20' in output,'Test to Reconfigure Secondary DNS Failed'
        info('### Sucussfully Reconfigured Secondary DNS in static mode ###\n')

        # Remove Secondary DNS server.
        s1.cmdCLI("no nameserver  10.10.10.4 10.10.10.20")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if '10.10.10.20' not in output:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 10.10.10.20' not in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '10.10.10.20' not in output,'Test to Remove Secondary DNS Failed'
        info('### Sucussfully Removed Secondary DNS in static mode ###\n')

        # Set Invalid IP on mgmt-intf.
        output=s1.cmdCLI("ip static 0.0.0.0 255.255.0.0")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to configure invalid static IP address Failed'
        info('### Sucussfully verified configure of Invalid IP in static mode ###\n')

        # Set Multicast IP on mgmt-intf.
        output=s1.cmdCLI("ip static 224.0.0.1 255.255.0.0")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to configure multicast IP address Failed'
        info('### Sucussfully verified configure of multicast IP in static mode ###\n')

        # Set broadcast IP on mgmt-intf.
        output=s1.cmdCLI("ip static 192.168.0.255 255.255.255.0")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to configure broadcast IP address Failed'
        info('### Sucussfully verified configure of broadcast IP in static mode ###\n')

        # Set loopback IP on mgmt-intf.
        output=s1.cmdCLI("ip static 127.0.0.1 255.255.255.0")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to configure loopback IP address Failed'
        info('### Sucussfully verified configure of loopback IP in static mode ###\n')

        # Add Default Invalid gateway IP in static mode.
        output=s1.cmdCLI("default-gateway 0.0.0.0")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add Invalid default gateway Failed'
        info('### Sucussfully Verified configure of Invalid default gateway IP in static mode ###\n')

        # Add multicast ip as default gateway in static mode.
        output=s1.cmdCLI("default-gateway 224.0.0.1")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add multicast default gateway Failed'
        info('### Sucussfully Verified configure of multicast default gateway IP in static mode ###\n')

        # Add broadcast ip as default gateway ip in static mode.
        output=s1.cmdCLI("default-gateway 192.168.0.255")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add broadcast default gateway ip Failed'
        info('### Sucussfully Verified configure of broadcast default gateway in static mode ###\n')

        # Add loopback address as default gateway ip in static mode.
        output=s1.cmdCLI("default-gateway 127.0.0.1")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add loopback default gateway ip Failed'
        info('### Sucussfully Verified configure of loopback default gateway in static mode ###\n')

        # Configure an invalid IP address as primary DNS.
        output=s1.cmdCLI("nameserver 0.0.0.0")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add invalid Primary DNS Failed'
        info('### Sucussfully Verified configure of invalid Primary DNS in static mode ###\n')

        # Configure a multicast address as primary DNS.
        output=s1.cmdCLI("nameserver 224.0.0.1")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add multicast Primary DNS Failed'
        info('### Sucussfully Verified configure of multicast Primary DNS in static mode ###\n')

        # Configure a broadcast address as primary DNS.
        output=s1.cmdCLI("nameserver 192.168.0.255")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add broadcast Primary DNS Failed'
        info('### Sucussfully Verified configure of broadcast Primary DNS in static mode ###\n')

        # Configure a loopback address as primary DNS.
        output=s1.cmdCLI("nameserver 127.0.0.1")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add loopback Primary DNS Failed'
        info('### Sucussfully Verified configure of loopback Primary DNS in static mode ###\n')

        # Configure an invalid IP as secondary DNS.
        output=s1.cmdCLI("nameserver 10.10.10.1 0.0.0.0")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add invalid Secondary DNS Failed'
        info('### Sucussfully Verified configure of invalid secondary DNS in static mode ###\n')

        # Change mode from static to dhcp.
        s1.cmdCLI("ip dhcp")
        output = s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if 'dhcp' in output:
                break
            else:
                sleep(1)
                cnt -= 1
        assert 'dhcp' in output,'Test to change mode to DHCP from static Failed'
        info('### Sucussfully changed the mode from static to DHCP ###\n')

        # Populate values as though populated from DHCP.
        time.sleep(5)
        s1.cmd("ifconfig eth0 172.17.0.100 netmask 255.255.255.0")
        s1.cmd("route add default gw 172.17.0.1 eth0")
        s1.cmd("echo nameserver 1.1.1.1  > /etc/resolv.conf")
        s1.cmd("echo nameserver 2.2.2.2 >> /etc/resolv.conf")

        # Test if IP got from DHCP is set.
        out = s1.cmd("ifconfig eth0")
        hostIpAddress = out.split("\n")[1].split()[1][5:]
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if hostIpAddress in output:
                break
            else:
                sleep(1)
                cnt -= 1
        assert hostIpAddress in output,'Test to verify IP got after changed the mode from static to dhcp Failed'
        info('### Sucussfully got the IP after changed the mode from static to dhcp ###\n')

        # Test if Default gateway got from DHCP is set.
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if '172.17.0.1' in output:
                break
            else:
                sleep(1)
                cnt -= 1
        assert '172.17.0.1' in output,'Test to verify Default gateway got after changed the mode from static to dhcp Failed'
        info('### Sucussfully got Default gateway IP after changed the mode from static to dhcp ###\n')

        # Test if DNS server got from DHCP is set.
        output = s1.cmd("cat /etc/resolv.conf")
        temp = re.findall("nameserver\s+.*\nnameserver\s+.*",output)
        assert temp[0] in output,'Test to verify DNS IP got after changed the mode from static to dhcp Failed'
        info('### Sucussfully got DNS IP after changed the mode from static to dhcp ###\n')

    def mgmt_intf_config_commands_dhcp_ipv6(self):
        info('\n########## Test to configure Management interface with Dhcp IPV6 ##########\n')
        s1 = self.net.switches[ 0 ]
        #Add Default gateway in DHCP mode
        s1.cmdCLI("end")
        s1.cmdCLI("configure terminal")
        s1.cmdCLI("interface mgmt")
        s1.cmdCLI("ip dhcp")
        s1.cmdCLI("default-gateway 2001:db8:0:1::128")
        output = s1.cmdCLI(" ")
        output = s1.cmdCLI("do show interface mgmt")
        assert '2001:db8:0:1::128' not in output,'Test to add default gateway in DHCP mode Failed'
        info('### Sucussfully verified configure of default gateway in DHCP mode ###\n')

        #Add DNS Server 1 in DHCP mode
        s1.cmdCLI("nameserver 2001:db8:0:1::128")
        output = s1.cmdCLI(" ")
        output = s1.cmd("echo")
        output = s1.cmdCLI("do show interface mgmt")
        assert '2001:db8:0:1::128' not in output,'Test to add Primary DNS in DHCP mode Failed'
        info('### Sucussfully verified configure of Primary DNS in DHCP mode ###\n')

        #Add DNS Server 2 in DHCP mode
        s1.cmdCLI("nameserver 2001:db8:0:1::106 2001:db8:0:1::128")
        output = s1.cmdCLI(" ")
        output = s1.cmd("echo")
        output = s1.cmdCLI("do show interface mgmt")
        output += s1.cmd("echo")
        assert '2001:db8:0:1::128' not in output,'Test to add Secondary in DHCP mode Failed'
        info('### Sucussfully verified configure of Secondary DNS in DHCP mode ###\n')

    def mgmt_intf_config_commands_static_ipv6(self):
        info('\n########## Test to configure Management interface with static IPV6 ##########\n')
        s1 = self.net.switches[ 0 ]

        #Static IP config when mode is static
        s1.cmdCLI("ip static 2001:db8:0:1::156/64")
        output = s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            output += s1.cmd("echo")
            if '2001:db8:0:1::156/64' in output:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("ip -6 addr show dev eth0")
                    output += s1.cmd("echo")
                    if '2001:db8:0:1::156/64' in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '2001:db8:0:1::156/64' in output,'Test to add static IP address Failed'
        info('### Sucussfully verified configure of Static IP ###\n')

        #Set the IP again
        s1.cmdCLI("ip static 2001:db8:0:1::157/64")
        output = s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmd("echo")
            if '2001:db8:0:1::157/64' in output :
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("ip -6 addr show dev eth0")
                    if '2001:db8:0:1::157/64' in output :
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '2001:db8:0:1::157/64' in output,'Test to Reconfigure static IP address Failed'
        info('### Sucussfully verified Reconfigure of Static IP ###\n')

        #Set Invalid IP on mgmt-intf
        output=s1.cmdCLI("ip static ::")
        assert 'Unknown command' in output,'Test to configure invalid static IP address Failed'
        info('### Sucussfully verified configure of invalid static IP address ###\n')

        #Test to verify Multicast IP on mgmt-intf
        output=s1.cmdCLI("ip static ff01:db8:0:1::101/64")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to configure multicast IP address in static mode Failed'
        info('### Sucussfully verified configure of multicast IP address in static mode ###\n')

        #Test to verify link-local IP on mgmt-intf
        output=s1.cmdCLI("ip static fe80::5484:7aff:fefe:9799/64")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to configure link-local IP address in static mode Failed'
        info('### Sucussfully verified configure of link-local IP in static mode ###\n')

        #Test to verify loopback IP on mgmt-intf
        output=s1.cmdCLI("ip static ::1")
        assert 'Unknown command' in output,'Test to configure loopback IP address in static mode Failed'
        info('### Sucussfully verified configure of loopback IP address in static mode ###\n')

        # Default gateway should be reachable. Otherwise test case will fail
        #Add Default gateway in Static mode
        s1.cmdCLI("default-gateway 2001:db8:0:1::128")
        output = s1.cmdCLI(" ")
        output = s1.cmdCLI("do show running-config")
        assert 'default-gateway 2001:db8:0:1::128' in output,'Test to add default gateway in static mode Failed'
        info('### Sucussfully verified configure of default gateway in static mode ###\n')

        #Add Default Invalid gateway IP in static mode
        output=s1.cmdCLI("default-gateway ::")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add Invalid default gateway ip in static mode Failed'
        info('### Sucussfully verified configure of Invalid default gateway ip in static mode ###\n')

        #Add Deafult  multicast gateway ip in static mode
        output=s1.cmdCLI("default-gateway ff01:db8:0:1::101")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add default multicast gateway ip in static mode Failed'
        info('### Sucussfully verified configure of multicast gateway ip in static mode ###\n')

        #Add Default link-local  gateway ip in static mode
        output=s1.cmdCLI("default-gateway fe80::5484:7aff:fefe:9799")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add default link-local gateway ip in static mode Failed'
        info('### Sucussfully verified configure of Default link-local  gateway ip in static mode ###\n')

        #Add Default loopback gateway ip in static mode
        output=s1.cmdCLI("default-gateway ::1")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to add default loopback gateway ip in static mode Failed'
        info('### Sucussfully verified configure of Default loopback gateway in static mode ###\n')

        #Remove Default gateway in static mode
        s1.cmdCLI("no default-gateway 2001:db8:0:1::128")
        output = s1.cmdCLI(" ")
        output = s1.cmdCLI("do show running-config")
        assert 'default-gateway 2001:db8:0:1::128' not in output,'Test to remove default gateway in static mode Failed'
        info('### Sucussfully Removed Default gateway in static mode ###\n')

        #Configure an invalid IP for primary DNS
        output=s1.cmdCLI("nameserver ::")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to configure invalid Primary DNS Failed'
        info('### Sucussfully verified configure of invalid Primary DNS static mode ###\n')

        #Configure an multicast for primary DNS
        output=s1.cmdCLI("nameserver ff01:db8:0:1::101")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to Configure an multicast for primary DNS Failed'
        info('### Sucussfully verified configure of multicast primary DNS in static mode ###\n')

        #Configure a link-local for primary DNS
        output=s1.cmdCLI("nameserver fe80::5484:7aff:fefe:9799")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to Configure a link-local for primary DNS Failed'
        info('### Sucussfully verified configure of link-local primary DNS in static mode ###\n')

        #Configure a loopback for primary DNS
        output=s1.cmdCLI("nameserver ::1")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to Configure a loopback for primary DNS Failed'
        info('### Sucussfully verified configure of loopback primary DNS in static mode ###\n')

        #Configure an invalid IP for secondary DNS
        output=s1.cmdCLI("nameserver 2001:db8:0:1::144 ::")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to Configure an invalid IP for secondary DNS Failed'
        info('### Sucussfully verified configure of invalid secondary DNS in static mode ###\n')

        #Configure an multicast for secondary DNS
        output=s1.cmdCLI("nameserver 2001:db8:0:1::144 ff01:db8:0:1::101")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to Configure an multicast for secondary DNS Failed'
        info('### Sucussfully verified configure of multicast secondary DNS in static mode ###\n')

        #Configure a link-local for secondary DNS
        output=s1.cmdCLI("nameserver 2001:db8:0:1::144 fe80::5484:7aff:fefe:9799")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to Configure a link-local for secondary DNS Failed'
        info('### Sucussfully verified configure of link-local secondary DNS in static mode ###\n')

        #Configure a loopback for secondary DNS
        output=s1.cmdCLI("nameserver 2001:db8:0:1::144 ::1")
        assert 'Invalid IPv4 or IPv6 address' in output,'Test to Configure a loopback for secondary DNS Failed'
        info('### Sucussfully verified configure of loopback secondary DNS in static mode ###\n')

        #Configure primary and secondary DNS as same
        output=s1.cmdCLI("nameserver 2001:db8:0:1::144 2001:db8:0:1::144")
        assert 'Duplicate value entered' in output,'Test to Configure primary and secondary DNS as same Failed'
        info('### Sucussfully verified configure of same primary and secondary DNS in static mode ###\n')

        #Add DNS Server 1 in static mode
        s1.cmdCLI("nameserver 2001:db8:0:1::144")
        output = s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output_show = s1.cmdCLI("do show interface mgmt")
            output_show += s1.cmdCLI(" ")
            if '2001:db8:0:1::144' in output_show:
                cnt2 = 100
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 2001:db8:0:1::144' in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '2001:db8:0:1::144' in output,'Test to add Primary DNS in static mode Failed'
        info('### Sucussfully configured the Primary DNS in static mode ###\n')

        #Add another DNS server 1
        s1.cmdCLI("nameserver 2001:db8:0:1::154")
        output = s1.cmdCLI(" ")
        cnt = 15
        while cnt:
            output_show = s1.cmdCLI("do show interface mgmt")
            output_show += s1.cmdCLI(" ")
            if '2001:db8:0:1::154' in output_show:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 2001:db8:0:1::154' in output and 'nameserver 2001:db8:0:1::144' not in output:
                        break
                    else:
                        cnt -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '2001:db8:0:1::154' in output,'Test to Reconfigure Primary DNS in static mode Failed'
        assert '2001:db8:0:1::144' not in output,'Test to Reconfigure Primary DNS in static mode Failed'
        info('### Sucussfully Reconfigured the Primary DNS in static mode ###\n')

        #Remove DNS server 1
        s1.cmdCLI("no nameserver 2001:db8:0:1::154")
        cnt = 15
        while cnt:
            output_show = s1.cmdCLI("do show interface mgmt")
            output_show += s1.cmdCLI(" ")
            if re.findall('Primary Nameserver\s+: 2001:db8:0:1::154',output_show):
                sleep(1)
                cnt -= 1
                cnt2 = 15
            else:
               while cnt2:
                   output = s1.cmd("cat /etc/resolv.conf")
                   output += s1.cmd("echo")
                   if 'nameserver 2001:db8:0:1::154' not in output:
                       break
                   else:
                       cnt2 -= 1
                       sleep(1)
               break
        assert '2001:db8:0:1::154' not in output,'Test to Remove Primary DNS in static mode Failed'
        info('### Sucussfully Removed Primary DNS in static mode ###\n')

        #Add DNS Server 2 in static mode
        output=s1.cmdCLI("nameserver 2001:db8:0:1::150 2001:db8:0:1::156")
        cnt = 15
        while cnt:
            output_show = s1.cmdCLI("do show interface mgmt")
            output_show += s1.cmdCLI(" ")
            if re.findall("Primary Nameserver\s+: 2001:db8:0:1::150",output_show) and \
                re.findall("Secondary Nameserver\s+: 2001:db8:0:1::156",output_show):
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 2001:db8:0:1::156' in output and 'nameserver 2001:db8:0:1::150' in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '2001:db8:0:1::156' in output,'Test to add Secondary DNS in static mode Failed'
        assert '2001:db8:0:1::150' in output,'Test to add Secondary DNS in static mode Failed'
        info('### Sucussfully Configured Secondary DNS in static mode ###\n')

        #Add another DNS server 2
        s1.cmdCLI("nameserver 2001:db8:0:1::150 2001:db8:0:1::154")
        cnt = 15
        while cnt:
            output_show = s1.cmdCLI("do show interface mgmt")
            output += s1.cmdCLI(" ")
            if re.findall("Primary Nameserver\s+: 2001:db8:0:1::150",output_show) and \
                re.findall("Secondary Nameserver\s+: 2001:db8:0:1::154",output_show):
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 2001:db8:0:1::150' in output and \
                        'nameserver 2001:db8:0:1::156' not in output and \
                        'nameserver 2001:db8:0:1::154' in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '2001:db8:0:1::150' in output,'Test to Reconfigure Secondary DNS in static mode Failed'
        assert '2001:db8:0:1::156' not in output,'Test to Reconfigure Secondary DNS in static mode Failed'
        assert '2001:db8:0:1::154' in output,'Test to Reconfigure Secondary DNS in static mode Failed'
        info('### Sucussfully Reconfigured Secondary DNS in static mode ###\n')

        #Remove DNS server 2
        s1.cmdCLI("no nameserver  2001:db8:0:1::150 2001:db8:0:1::154")
        cnt = 15
        while cnt:
            output_show = s1.cmdCLI("do show interface mgmt")
            output_show += s1.cmdCLI(" ")
            if '2001:db8:0:1::154' not in output_show:
                cnt2 = 15
                while cnt2:
                    output = s1.cmd("cat /etc/resolv.conf")
                    output += s1.cmd("echo")
                    if 'nameserver 2001:db8:0:1::154' not in output:
                        break
                    else:
                        cnt2 -= 1
                        sleep(1)
                break
            else:
                sleep(1)
                cnt -= 1
        assert '2001:db8:0:1::154' not in output,'Test to Remove Secondary DNS in static mode Failed'
        info('### Sucussfully Removed Secondary DNS in static mode ###\n')

        #Change mode from static to dhcp
        s1.cmdCLI("ip dhcp")
        output = s1.cmdCLI(" ")
        time.sleep(5)
        output = ''
        output = s1.cmdCLI("do show interface mgmt")
        output += s1.cmdCLI(" ")
        assert 'dhcp' in output,'Test to change mode from static to dhcp Failed'
        output = s1.cmd("ovs-vsctl list open_vswitch")
        output += s1.cmd("echo")
        assert 'ipv6-linklocal' in output,'Test to change mode from static to dhcp Failed'
        assert 'dns-server-1' not in output,'Test to change mode from static to dhcp Failed'
        assert 'dns-server-2' not in output,'Test to change mode from static to dhcp Failed'
        info('### Sucussfully changed mode to DHCP from static ###\n')

        #Populate values as though populated from DHCP
        time.sleep(5)
        s1.cmd("ip -6 addr add 2001:db8:0:1::150/64 dev eth0")
        s1.cmd("ip -6 route add default via 2001:db8:0:1::128")
        s1.cmd("echo nameserver 1.1.1.1  > /etc/resolv.conf")
        s1.cmd("echo nameserver 2.2.2.2 >> /etc/resolv.conf")

        output = s1.cmd("ip -6 addr show dev eth0")
        output = s1.cmd("cat /etc/resolv.conf")

        #Test if IP  got from DHCP is set
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmdCLI(" ")
            if "2001:db8:0:1::150/64" not in output:
                sleep(1)
                cnt -= 1
            else:
                break
        assert "2001:db8:0:1::150/64" in output,'Test to verify IP got after changed the mode from static to dhcp Failed'
        info('### Sucussfully got IP after changed the mode from static to dhcp ###\n')

        # Test if Default gateway got from DHCP is set
        cnt = 15
        while cnt:
            output = s1.cmdCLI("do show interface mgmt")
            output += s1.cmdCLI(" ")
            if "2001:db8:0:1::128" not in output:
                sleep(1)
                cnt -= 1
            else:
                break
        assert "2001:db8:0:1::128" in output,'Test to verify Default gateway got after changed the mode Failed'
        info('### Sucussfully got the Default gateway after changed the mode Passed ###\n')

    #Extra cleanup if test fails in middle
    def mgmt_intf_cleanup(self):
        s1 = self.net.switches[ 0 ]
        output = s1.cmd("ip netns exec swns ip addr show dev 1")
        if 'inet' in output:
            s1.cmd("ip netns exec swns ip address flush dev 1")



class Test_mgmt_intf:

    def setup_class(cls):
        # Create the Mininet topology based on mininet.
        Test_mgmt_intf.test = mgmtIntfTests()

    def teardown_class(cls):
        # Stop the Docker containers, and
        # mininet topology.
        Test_mgmt_intf.test.net.stop()

    def teardown_method(self, method):
        self.test.mgmt_intf_cleanup()

    def __del__(self):
        del self.test

    # mgmt intf tests.
    def test_mgmt_intf_config_commands_ipv4(self):
        self.test.mgmt_intf_config_commands_dhcp_ipv4()
        self.test.mgmt_intf_config_commands_static_ipv4()

    def test_mgmt_intf_config_commands_ipv6(self):
        self.test.mgmt_intf_config_commands_dhcp_ipv6()
        self.test.mgmt_intf_config_commands_static_ipv6()