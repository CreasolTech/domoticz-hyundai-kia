#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Hyundai Kia plugin
#
# Source:  https://github.com/CreasolTech/domoticz-hyundai-kia.git
# Author:  CreasolTech ( https://www.creasol.it/domotics )
# License: MIT
#

"""
<plugin key="domoticz-hyundai-kia" name="Hyundai Kia connect" author="CreasolTech" version="1.0.0" externallink="https://github.com/CreasolTech/domoticz-hyundai-kia.git">
    <params>
        <param field="Email" label="Email address" width="150px" required="true" />
        <param field="Password" label="Password" width="100px" required="true" />
        <param field="Pin" label="PIN" width="100px" required="true" />
        <param field="Brand" label="Brand" width="100px" required="true" default="1" >
            <options>
                <options label="Hyundai" value="1" default="true" />
                <options label="Kia" value="2" />
            </options>
        </param>
        <param field="VIN" label="VIN" width="150px" required="true" />
        <param filed="Interval" label="Poll interval">
            <options>
                <option label="30 minutes" value="30" />
                <option label="60 minutes" value="60" />
                <option label="120 minutes" value="120" default="true" />
                <option label="240 minutes" value="240" />
            </options>
        </param>
        <param filed="IntervalCharging" label="Poll interval while charging">
            <options>
                <option label="10 minutes" value="10" />
                <option label="20 minutes" value="20" />
                <option label="30 minutes" value="30" default="true" />
                <option label="60 minutes" value="60" />
                <option label="120 minutes" value="60" />
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import json

from datetime import datetime, timedelta
from enum import IntEnum, unique, auto
from hyundai_kia_connect_api import *


class BasePlugin:
    """ Base class for the plugin """

    def __init__(self):
        self._lastPoll=0    # last time I got vehicle status

    def onStart(self):

        self.inverter = solaredge_modbus.Inverter(
            host=Parameters["Address"],
            port=Parameters["Port"],
            timeout=3,
            unit=1
        )

        # Lets get in touch with the inverter.

        self.contactInverter()


    #
    # OnHeartbeat is called by Domoticz at a specific interval as set in onStart()
    #

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat")

        # We need to make sure that we have a table to work with.
        # This will be set by contactInverter and will be None till it is clear
        # that the inverter responds and that a matching table is available.

        if self._LOOKUP_TABLE:

            inverter_values = None
            try:
                inverter_values = self.inverter.read_all()
            except ConnectionException:
                inverter_values = None
                Domoticz.Debug("ConnectionException")
            else:
                if inverter_values:

                    if "Mode5" in Parameters and Parameters["Mode5"] == "Extra":
                        to_log = inverter_values
                        if "c_serialnumber" in to_log:
                            to_log.pop("c_serialnumber")
                        Domoticz.Log("inverter values: {}".format(json.dumps(to_log, indent=4, sort_keys=False)))

                    # Just for cosmetics in the log

                    updated = 0
                    device_count = 0

                    # Now process each unit in the table.

                    for unit in self._LOOKUP_TABLE:
                        Domoticz.Debug(str(unit))

                        # Skip a unit when the matching device got deleted.

                        if unit[Column.ID] in Devices:
                            Domoticz.Debug("-> found in Devices")

                            # For certain units the table has a lookup table to replace the value with something else.

                            if unit[Column.LOOKUP]:
                                Domoticz.Debug("-> looking up...")

                                lookup_table = unit[Column.LOOKUP]
                                to_lookup = int(inverter_values[unit[Column.MODBUSNAME]])

                                if to_lookup >= 0 and to_lookup < len(lookup_table):
                                    value = lookup_table[to_lookup]
                                else:
                                    value = "Key not found in lookup table: {}".format(to_lookup)

                            # When a math object is setup for the unit, update the samples in it and get the calculated value.

                            elif unit[Column.MATH]:
                                Domoticz.Debug("-> calculating...")
                                m = unit[Column.MATH]
                                if unit[Column.MODBUSSCALE]:
                                    m.update(inverter_values[unit[Column.MODBUSNAME]], inverter_values[unit[Column.MODBUSSCALE]])
                                else:
                                    m.update(inverter_values[unit[Column.MODBUSNAME]])

                                value = m.get()

                            # When there is no math object then just store the latest value.
                            # Some values from the inverter need to be scaled before they can be stored.

                            elif unit[Column.MODBUSSCALE]:
                                Domoticz.Debug("-> calculating...")
                                # we need to do some calculation here
                                value = inverter_values[unit[Column.MODBUSNAME]] * (10 ** inverter_values[unit[Column.MODBUSSCALE]])

                            # Some values require no action but storing in Domoticz.

                            else:
                                Domoticz.Debug("-> copying...")
                                value = inverter_values[unit[Column.MODBUSNAME]]

                            Domoticz.Debug("value = {}".format(value))

                            # Time to store the value in Domoticz.
                            # Some devices require multiple values, in which case the plugin will combine those values.
                            # Currently, there is only a need to prepend one value with another.

                            if unit[Column.PREPEND]:
                                Domoticz.Debug("-> has prepend")
                                prepend = Devices[unit[Column.PREPEND]].sValue
                                Domoticz.Debug("prepend = {}".format(prepend))
                                sValue = unit[Column.FORMAT].format(prepend, value)
                            else:
                                Domoticz.Debug("-> no prepend")
                                sValue = unit[Column.FORMAT].format(value)

                            Domoticz.Debug("sValue = {}".format(sValue))

                            # Only store the value in Domoticz when it has changed.
                            # TODO:
                            #   We should not store certain values when the inverter is sleeping.
                            #   That results in a strange graph; it would be better just to skip it then.

                            if sValue != Devices[unit[Column.ID]].sValue:
                                Devices[unit[Column.ID]].Update(nValue=0, sValue=str(sValue), TimedOut=0)
                                updated += 1

                            device_count += 1

                        else:
                            Domoticz.Debug("-> NOT found in Devices")

                    Domoticz.Log("Updated {} values out of {}".format(updated, device_count))
                else:
                    Domoticz.Log("Inverter returned no information")

        # Try to contact the inverter when the lookup table is not yet initialized.

        else:
            self.contactInverter()


    #
    # Contact the inverter and find out what type it is.
    # Initialize the lookup table when the type is supported.
    #
    
    def contactInverter(self):

        # Do not stress the inverter when it did not respond in the previous attempt to contact it.

        if self.retryafter <= datetime.now():

            # Here we go...
            inverter_values = None
            try:
                inverter_values = self.inverter.read_all()
            except ConnectionException:

                # There are multiple reasons why this may fail.
                # - Perhaps the ip address or port are incorrect.
                # - The inverter may not be connected to the networ,
                # - The inverter may be turned off.
                # - The inverter has a bad hairday....
                # Try again in the future.

                self.retryafter = datetime.now() + self.retrydelay
                inverter_values = None

                Domoticz.Log("Connection Exception when trying to contact: {}:{}".format(Parameters["Address"], Parameters["Port"]))
                Domoticz.Log("Retrying to communicate with inverter after: {}".format(self.retryafter))

            else:

                if inverter_values:
                    Domoticz.Log("Connection established with: {}:{}".format(Parameters["Address"], Parameters["Port"]))

                    inverter_type = solaredge_modbus.sunspecDID(inverter_values["c_sunspec_did"])
                    Domoticz.Log("Inverter type: {}".format(inverter_type))

                    # The plugin currently has 2 supported types.
                    # This may be updated in the future based on user feedback.

                    if inverter_type == solaredge_modbus.sunspecDID.SINGLE_PHASE_INVERTER:
                        self._LOOKUP_TABLE = SINGLE_PHASE_INVERTER
                    elif inverter_type == solaredge_modbus.sunspecDID.THREE_PHASE_INVERTER:
                        self._LOOKUP_TABLE = THREE_PHASE_INVERTER
                    else:
                        Domoticz.Log("Unsupported inverter type: {}".format(inverter_type))

                    if self._LOOKUP_TABLE:

                        # Set the number of samples on all the math objects.

                        for unit in self._LOOKUP_TABLE:
                            if unit[Column.MATH]:
                                unit[Column.MATH].set_max_samples(self.max_samples)


                        # We updated some device types over time.
                        # Let's make sure that we have the correct type setup.

                        for unit in self._LOOKUP_TABLE:
                            if unit[Column.ID] in Devices:
                                device = Devices[unit[Column.ID]]
                                
                                if (device.Type != unit[Column.TYPE] or
                                    device.SubType != unit[Column.SUBTYPE] or
                                    device.SwitchType != unit[Column.SWITCHTYPE] or
                                    device.Options != unit[Column.OPTIONS]):

                                    Domoticz.Log("Updating device \"{}\"".format(device.Name))

                                    nValue = device.nValue
                                    sValue = device.sValue

                                    device.Update(
                                            Type=unit[Column.TYPE],
                                            Subtype=unit[Column.SUBTYPE],
                                            Switchtype=unit[Column.SWITCHTYPE],
                                            Options=unit[Column.OPTIONS],
                                            nValue=nValue,
                                            sValue=sValue
                                    )

                        # Add missing devices if needed.

                        if self.add_devices:
                            for unit in self._LOOKUP_TABLE:
                                if unit[Column.ID] not in Devices:
                                    Domoticz.Device(
                                        Unit=unit[Column.ID],
                                        Name=unit[Column.NAME],
                                        Type=unit[Column.TYPE],
                                        Subtype=unit[Column.SUBTYPE],
                                        Switchtype=unit[Column.SWITCHTYPE],
                                        Options=unit[Column.OPTIONS],
                                        Used=1,
                                    ).Create()
                else:
                    Domoticz.Log("Connection established with: {}:{}. BUT... inverter returned no information".format(Parameters["Address"], Parameters["Port"]))
                    Domoticz.Log("Retrying to communicate with inverter after: {}".format(self.retryafter))
        else:
            Domoticz.Log("Retrying to communicate with inverter after: {}".format(self.retryafter))


#
# Instantiate the plugin and register the supported callbacks.
# Currently that is only onStart() and onHeartbeat()
#

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()
