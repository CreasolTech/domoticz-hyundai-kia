#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Hyundai Kia plugin
# Based on hyundai-kia-connect-api by Fuat Akgun and BlUVO domoticz plugin by Pierre Levres
#
# Source:  https://github.com/CreasolTech/domoticz-hyundai-kia.git
# Author:  CreasolTech ( https://www.creasol.it/domotics )
# License: MIT
#

"""
<plugin key="domoticz-hyundai-kia" name="Hyundai Kia connect" author="CreasolTech" version="1.0.0" externallink="https://github.com/CreasolTech/domoticz-hyundai-kia.git">
    <description>
        <h2>Domoticz Hyundai Kia connect plugin</h2>
        This plugin permits to access, through the Hyundai Kia account credentials, to information about owned Hyundai and Kia vehicles, such as odometer, EV battery charge, 
        tyres status, door lock status, and much more.<br/>
        <b>Before activating this plugin, assure that you've set the right name to your car</b> (through the Hyundai/Kia connect app): that name is used to identify devices in Domoticz.<br/>
        Also, do not change the name of the ODOMETER device!<br/>
    </description>
    <params>
        <param field="Username" label="Email address" width="150px" required="true" />
        <param field="Password" label="Password" width="100px" required="true" password="true" />
        <param field="Mode3" label="PIN" width="100px" required="true" password="true" />
        <param field="Port" label="Brand" >
            <options>
                <option label="Hyundai" value="2" />
                <option label="Kia" value="1" default="true" />
            </options>
        </param>
        <param field="Address" label="Region" >
            <options>
                <option label="Europe" value="1" default="true" />
                <option label="Canada" value="2" />
                <option label="USA" value="3" />
            </options>
        </param>
        <param field="Mode1" label="Poll interval">
            <options>
                <option label="30 minutes" value="30" />
                <option label="60 minutes" value="60" />
                <option label="120 minutes" value="120" default="true" />
                <option label="240 minutes" value="240" />
            </options>
        </param>
        <param field="Mode2" label="Poll interval while charging">
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

import Domoticz as Domoticz
import json

from datetime import datetime, timedelta
from enum import IntEnum, unique, auto
from hyundai_kia_connect_api import *


LANGS=[ "en", "it" ] # list of supported languages, in DEVS dict below
LANGBASE=1  # item in the DEVS list where the first language starts 

DEVS={ #topic:      [ num, "en name", "it name", ...other languages defined in LANGS[] ],
    "EVSTATE":      [ 1, "EV state", "EV stato" ],
    "EVBATTLEVEL":  [ 2, "EV battery level", "EV livello batteria" ],
    "EVRANGE":      [ 3, "EV range", "EV autonomia" ],
    "FUELLEVEL":    [ 4, "fuel level", "livello carburante" ],
    "FUELRANGE":    [ 5, "fuel range", "autonomia carburante" ],
    "ENGINEON":     [ 6, "engine ON", "motore acceso" ],
    "ODOMETER":     [ 7, "odometer", "contachilometri" ],
    "LOCATION":     [ 8, "location", "posizione" ],
    "HOMEDIST":     [ 9, "distance", "distanza" ],
    "SPEED":        [ 10, "speed", "velocità" ],
    "UPDATE":       [ 11, "update req.", "aggiorna" ],
    "TEMPSET":      [ 12, "temp. settings", "imp. temperatura" ],
    "CLIMAON":      [ 13, "climate", "clima acceso" ],
    "DEFROSTON":    [ 14, "defrost", "scongelamento" ],
    "REARWINDOWON": [ 15, "rear window", "lunotto termico" ],
    "STEERINGWHEELON": [ 16, "steering wheel", "volante termico" ],
    "SIDEMIRRORSON":[ 17, "side mirrors", "specchietti termici" ],
    "SEATFL":       [ 18, "seat front-left", "sedile guidatore" ],
    "SEATFR":       [ 19, "seat front-right", "sedile passeggero" ],
    "SEATRL":       [ 20, "seat rear-left", "sedile post.sx" ],
    "SEATRR":       [ 21, "seat rear-right", "sedile post.dx" ],
    "OPEN":         [ 22, "open", "aperta" ],
    "TRUNK":        [ 23, "trunk open", "bagagliaio aperto"],
    "HOOD":         [ 24, "hood open", "cofano aperto"],
    "12VBATT":      [ 25, "12V battery", "batteria 12V"],
    "KEYBATT":      [ 26, "key battery", "batteria radiocomando"],
    "WASHER":       [ 27, "washer fluid", "liquido tergicristallo" ], 
    "BRAKE":        [ 28, "brake fluid", "olio freni" ], 
    "TIRES":        [ 29, "tyre pressure", "pressione gomme" ],
}

class BasePlugin:
    """ Base class for the plugin """

    def __init__(self):
        self._pollInterval = 120        # fetch data every 120 minutes, by default (but check parameter Mode1!)
        self._pollIntervalCharging = 30 # while charging, fetch data quickly 
        self._lastPoll = None    # last time I got vehicle status
        self._isCharging = False  
        self._lang = "en"
        self.vm = None

    def mustPoll(self):
        """ Return True if new data should be polled """
        if self._lastPoll == None: 
            return True
        elapsedTime = int( (datetime.now()-self._lastPoll).total_seconds() / 60)  # time in minutes
        if (elapsedTime >= self._pollInterval or (self._isCharging and elapsedTime >= self._pollIntervalCharging)): 
            return True
        return False

    def updatePollInterval(self):
        self._lastPoll = datetime.now()

    def onStart(self):
        Domoticz.Debug("Parameters="+str(Parameters))
        Domoticz.Debug("Settings="+str(Settings))
        self._lang=Settings["Language"]
        # check if language set in domoticz exists
        try:
            self._devlang=LANGBASE+LANGS.index(self._lang)
        except ValueError:
            Domoticz.Log(f"Language {self._lang} does not exist in dict DEVS, inside the domoticz_hyundai_kia plugin, but you can contribute adding it ;-) Thanks!")
            self._devlang=LANGBASE # default: english text
        self._pollInterval = float(Parameters["Mode1"])
        self._pollIntervalCharging = float(Parameters["Mode2"])
        self.vm = VehicleManager(region=int(Parameters["Address"]), brand=int(Parameters["Port"]), username=Parameters["Username"], password=Parameters["Password"], pin=Parameters["Mode3"])
        self._lastPoll = None   # force reconnecting in 10 seconds

    def onHeartbeat(self):
        """ Called every 10 seconds or other interval set by Domoticz.Heartbeat() """
        if self.mustPoll():   # check if vehicles data should be polled 
            ret=self.vm.check_and_refresh_token()
            Domoticz.Log(f"self.vm.check_and_refresh_token() returned {ret}")
            ret=self.vm.update_all_vehicles_with_cached_state()
            Domoticz.Log(f"self.vm.update_all_vehicles_with_cached_state() returned {ret}")
            self.updatePollInterval()
            # Now self.vm.vehicles contains a table with the list of registered vehicles and their parameters
            for k in self.vm.vehicles:
                # k is the keyword associated to a Vehicle object
                v = self.vm.get_vehicle(k)
                name = v.name   # must be unique and identify the type of car, if more than 1 car is owned
                Domoticz.Log(f"Name={v.name} Odometer={v._odometer_value}{v._odometer_unit} Battery={v.ev_battery_percentage}")
            
                # base = Unit base = 0, 32, 64, 96  # up to 4 vehicle can be addressed, 32 devices per vehicle (Unit <= 255)
                # Find the right base
                baseFree = 256
                for base in range(0, 256+1, 32):
                    if base+DEVS["ODOMETER"][0] in Devices and Devices[base+DEVS["ODOMETER"][0]].Name == f"{name} {DEVS['ODOMETER'][self._devlang]}":   
                        # odometer exists: check that Domoticz device name correspond with vehicle name (set on Kia connect)
                        break
                    else:
                        if baseFree > base:
                            baseFree = base # free base where devices can be stored
                Domoticz.Log(f"base={base} baseFree={baseFree}")

                if base >= 256 and baseFree < 256:
                    # car not found, but there is enough space for a new car
                    base = baseFree
                    Domoticz.Log("Add devices for this new car")
                    ############################################ Create new devices #########################################
                    if v.ev_battery_is_charging != None: 
                        Domoticz.Device(Unit=base+DEVS['EVSTATE'][0], Name=f"{name} {DEVS['EVSTATE'][self._devlang]}", Type=243, Subtype=19, Used=1).Create()
                    if v.ev_battery_percentage != None:  
                        Domoticz.Device(Unit=base+DEVS['EVBATTLEVEL'][0], Name=f"{name} {DEVS['EVBATTLEVEL'][self._devlang]}", Type=243, Subtype=6, Used=1).Create()
                    if v.ev_driving_distance != None:
                        Domoticz.Device(Unit=base+DEVS['EVRANGE'][0], Name=f"{name} {DEVS['EVRANGE'][self._devlang]}", Type=243, Subtype=31, Options={'Custom': '1;'+v._ev_driving_distance_unit}, Used=1).Create()
                    if v.fuel_level != None:  
                        Domoticz.Device(Unit=base+DEVS['FUELLEVEL'][0], Name=f"{name} {DEVS['FUELLEVEL'][self._devlang]}", Type=243, Subtype=6, Used=1).Create()
                    if v.fuel_driving_distance != None:
                        Domoticz.Device(Unit=base+DEVS['FUELRANGE'][0], Name=f"{name} {DEVS['FUELRANGE'][self._devlang]}", Type=243, Subtype=31, Options={'Custom': '1;'+v._fuel_driving_distance_unit}, Used=1).Create()
                    if v.engine_is_running != None:
                        Domoticz.Device(Unit=base+DEVS['ENGINEON'][0], Name=f"{name} {DEVS['ENGINEON'][self._devlang]}", Type=244, Subtype=73, Used=1).Create()
                    if v.odometer != None:  
                        Domoticz.Device(Unit=base+DEVS['ODOMETER'][0], Name=f"{name} {DEVS['ODOMETER'][self._devlang]}", Type=113, Subtype=0, Used=1).Create()
                    # TODO: LOCATION

                    # TODO: HOMEDIST

                    # TODO: SPEED

                    Domoticz.Device(Unit=base+DEVS['UPDATE'][0], Name=f"{name} {DEVS['UPDATE'][self._devlang]}", Type=244, Subtype=73, Used=1).Create() 
                    # TODO: TEMPSET (thermostat)
                    if v.air_control_is_on != None:
                        Domoticz.Device(Unit=base+DEVS['CLIMAON'][0], Name=f"{name} {DEVS['CLIMAON'][self._devlang]}", Type=244, Subtype=73, Used=1).Create()
                    if v.defrost_is_on != None:
                        Domoticz.Device(Unit=base+DEVS['DEFROSTON'][0], Name=f"{name} {DEVS['DEFROSTON'][self._devlang]}", Type=244, Subtype=73, Used=1).Create()
                    if v.back_window_heater_is_on != None:
                        Domoticz.Device(Unit=base+DEVS['REARWINDOWON'][0], Name=f"{name} {DEVS['REARWINDOWON'][self._devlang]}", Type=244, Subtype=73, Used=1).Create()
                    if v.steering_wheel_heater_is_on != None:
                        Domoticz.Device(Unit=base+DEVS['STEERINGWHEELON'][0], Name=f"{name} {DEVS['STEERINGWHEELON'][self._devlang]}", Type=244, Subtype=73, Used=1).Create()
                    if v.side_mirror_heater_is_on != None:
                        Domoticz.Device(Unit=base+DEVS['SIDEMIRRORSON'][0], Name=f"{name} {DEVS['SIDEMIRRORSON'][self._devlang]}", Type=244, Subtype=73, Used=1).Create()
                    if v.front_left_seat_status != None:
                        Domoticz.Device(Unit=base+DEVS['SEATFL'][0], Name=f"{name} {DEVS['SEATFL'][self._devlang]}", Type=244, Subtype=19, Used=1).Create()
                    if v.front_right_seat_status != None:
                        Domoticz.Device(Unit=base+DEVS['SEATFR'][0], Name=f"{name} {DEVS['SEATFR'][self._devlang]}", Type=244, Subtype=19, Used=1).Create()
                    if v.rear_left_seat_status != None:
                        Domoticz.Device(Unit=base+DEVS['SEATRL'][0], Name=f"{name} {DEVS['SEATRL'][self._devlang]}", Type=244, Subtype=19, Used=1).Create()
                    if v.rear_right_seat_status != None:
                        Domoticz.Device(Unit=base+DEVS['SEATRR'][0], Name=f"{name} {DEVS['SEATRR'][self._devlang]}", Type=244, Subtype=19, Used=1).Create()
                    if v.is_locked != None:
                        Domoticz.Device(Unit=base+DEVS['OPEN'][0], Name=f"{name} {DEVS['OPEN'][self._devlang]}", Type=244, Subtype=73, Switchtype=19, Used=1).Create()
                    if v.trunk_is_open != None:
                        Domoticz.Device(Unit=base+DEVS['TRUNK'][0], Name=f"{name} {DEVS['TRUNK'][self._devlang]}", Type=244, Subtype=73, Switchtype=11, Used=1).Create()
                    if v.hood_is_open != None:
                        Domoticz.Device(Unit=base+DEVS['HOOD'][0], Name=f"{name} {DEVS['HOOD'][self._devlang]}", Type=244, Subtype=73, Switchtype=11, Used=1).Create()
                    if v.car_battery_percentage != None:
                        Domoticz.Device(Unit=base+DEVS['12VBATT'][0], Name=f"{name} {DEVS['12VBATT'][self._devlang]}", Type=243, Subtype=6, Used=1).Create()
                    if v.smart_key_battery_warning_is_on != None:
                        Domoticz.Device(Unit=base+DEVS['KEYBATT'][0], Name=f"{name} {DEVS['KEYBATT'][self._devlang]}", Type=243, Subtype=22, Used=1).Create()
                    if v.washer_fluid_warning_is_on != None:
                        Domoticz.Device(Unit=base+DEVS['WASHER'][0], Name=f"{name} {DEVS['WASHER'][self._devlang]}", Type=243, Subtype=6, Used=1).Create()
                    if v.brake_fluid_warning_is_on != None:
                        Domoticz.Device(Unit=base+DEVS['BRAKE'][0], Name=f"{name} {DEVS['BRAKE'][self._devlang]}", Type=243, Subtype=6, Used=1).Create()
                    if v.tire_pressure_all_warning_is_on != None:
                        Domoticz.Device(Unit=base+DEVS['TIRES'][0], Name=f"{name} {DEVS['TIRES'][self._devlang]}", Type=243, Subtype=6, Used=1).Create()

                if base < 256:
                    # car found or just created: update values
                    ############################################ Update devices #########################################
                    Domoticz.Log(f"Car found at base {base}")
                    if v.ev_battery_is_charging != None:
                        nValue=0
                        sValue="Disconnected"
                        if v.ev_battery_is_charging:
                            nValue=1
                            sValue="Charging"
                        elif v.ev_battery_is_plugged_in:
                            nValue=1
                            sValue="Connected"
                        Devices[base+DEVS['EVSTATE'][0]].Update(nValue=nValue, sValue=sValue)
                    if v.ev_battery_percentage != None:
                        nValue=v.ev_battery_percentage
                        Devices[base+DEVS['EVBATTLEVEL'][0]].Update(nValue=nValue, sValue=str(nValue))
                    nValue=v.ev_driving_distance
                    if nValue != None:
                        Devices[base+DEVS['EVRANGE'][0]].Update(nValue=nValue, sValue=str(nValue))
                    nValue=v.fuel_level
                    if nValue != None:
                        Devices[base+DEVS['FUELLEVEL'][0]].Update(nValue=nValue, sValue=str(nValue))
                    nValue=v.fuel_driving_distance
                    if nValue != None:
                        Devices[base+DEVS['FUELRANGE'][0]].Update(nValue=nValue, sValue=str(nValue))
                    value=v.engine_is_running
                    if value != None:
                        nValue=1 if value else 0
                        sValue="On" if value else "Off"
                        Devices[base+DEVS['ENGINEON'][0]].Update(nValue=nValue, sValue=sValue)
                    nValue=v.odometer
                    if nValue != None:
                        nValue=int(nValue)
                        Devices[base+DEVS['ODOMETER'][0]].Update(nValue=nValue, sValue=str(nValue))
                    # TODO: LOCATION

                    # TODO: HOMEDIST

                    # TODO: SPEED

                    value=v.air_control_is_on
                    if value != None:
                        nValue=1 if value else 0
                        sValue="On" if value else "Off"
                        Devices[base+DEVS['CLIMAON'][0]].Update(nValue=nValue, sValue=sValue)
                    value=v.defrost_is_on
                    if value != None:
                        nValue=1 if value else 0
                        sValue="On" if value else "Off"
                        Devices[base+DEVS['DEFROSTON'][0]].Update(nValue=nValue, sValue=sValue)
                    value=v.back_window_heater_is_on
                    if value != None:
                        nValue=1 if value else 0
                        sValue="On" if value else "Off"
                        Devices[base+DEVS['REARWINDOWON'][0]].Update(nValue=nValue, sValue=sValue)
                    value=v.steering_wheel_heater_is_on
                    if value != None:
                        nValue=1 if value else 0
                        sValue="On" if value else "Off"
                        Devices[base+DEVS['STEERINGWHEELON'][0]].Update(nValue=nValue, sValue=sValue)
                    value=v.side_mirror_heater_is_on
                    if value != None:
                        nValue=1 if value else 0
                        sValue="On" if value else "Off"
                        Devices[base+DEVS['SIDEMIRRORSON'][0]].Update(nValue=nValue, sValue=sValue)
                    sValue=v.front_left_seat_status
                    if sValue != None:
                        Devices[base+DEVS['SEATFL'][0]].Update(nValue=0, sValue=sValue)
                    sValue=v.front_right_seat_status
                    if sValue != None:
                        Devices[base+DEVS['SEATFR'][0]].Update(nValue=0, sValue=sValue)
                    sValue=v.rear_left_seat_status
                    if sValue != None:
                        Devices[base+DEVS['SEATRL'][0]].Update(nValue=0, sValue=sValue)
                    sValue=v.rear_right_seat_status
                    if sValue != None:
                        Devices[base+DEVS['SEATRR'][0]].Update(nValue=0, sValue=sValue)
                    value=v.is_locked
                    if value != None:
                        nValue=0 if value else 1
                        sValue="Locked" if value else "Unlocked"
                        Devices[base+DEVS['OPEN'][0]].Update(nValue=nValue, sValue=sValue)
                    value=v.trunk_is_open
                    if value != None:
                        nValue=1 if value else 0
                        sValue="Open" if value else "Closed"
                        Devices[base+DEVS['TRUNK'][0]].Update(nValue=nValue, sValue=sValue)
                    value=v.hood_is_open
                    if value != None:
                        nValue=1 if value else 0
                        sValue="Open" if value else "Closed"
                        Devices[base+DEVS['HOOD'][0]].Update(nValue=nValue, sValue=sValue)
                    nValue=v.car_battery_percentage
                    if nValue != None:
                        sValue="Good" if nValue > 60 else "Low"
                        Device[base+DEVS['12VBATT'][0]].Update(nValue=nValue, sValue=sValue)
                    nValue=v.smart_key_battery_warning
                    if nValue != None:
                        sValue="Ok" if nValue == 0 else "Low"
                        Device[base+DEVS['KEYBATT'][0]].Update(nValue=nValue, sValue=sValue)
                    nValue=v.washer_fluid_warning_is_on
                    if nValue != None:
                        sValue="Ok" if nValue == 0 else "Empty"
                        Device[base+DEVS['WASHER'][0]].Update(nValue=nValue, sValue=sValue)
                    nValue=v.brake_fluid_warning_is_on
                    if nValue != None:
                        sValue="Ok" if nValue == 0 else "Empty"
                        Device[base+DEVS['BRAKE'][0]].Update(nValue=nValue, sValue=sValue)
                    nValue=v.tire_pressure_all_warning_is_on
                    if nValue != None:
                        sValue="Ok" if nValue == 0 else "Low"
                        Device[base+DEVS['TIRES'][0]].Update(nValue=nValue, sValue=sValue)



####################################################################################
global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()
