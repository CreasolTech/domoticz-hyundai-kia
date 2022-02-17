#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Hyundai Kia plugin
# Based on hyundai-kia-connect-api by Fuat Akgun
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

import Domoticz
import json

from datetime import datetime, timedelta
from enum import IntEnum, unique, auto
from hyundai_kia_connect_api import *

                # 1  EV state: ev_battery_is_charging: bool = None, ev_battery_is_plugged_in: bool = None
                # 2  EV battery level: ev_battery_percentage: int
                # 3  EV range: _ev_driving_distance_value: float, _total_driving_distance_unit: str
                # 4  fuel_level: float = None
                # 5  _fuel_driving_distance_value: float = None, _fuel_driving_distance_unit: str = None

                # 6  engine_is_running: engine_is_running: bool
                # 7  odometer: _odometer_value: float, _odometer_unit: str = None
                # 8  partial distance:  _ev_driving_distance_value: float = None, _ev_driving_distance_unit: str = None
                # 9  location: _location_latitude: float = None, _location_longitude: float = None
                # 10 distance from home: to be calculated
                # 11 speed: TODO
                

LANGS=[ "en", "it" ] # list of supported languages, in DEVS dict below
LANGBASE=1  # item in the DEVS list where the first language starts 

DEVS={ #topic:      [ num, "en name", "it name", ...other languages defined in LANGS[] ],
    "EVSTATE":      [ 1, "EV state", "EV stato" ],
    "EVBATTLEVEL":  [ 2, "EV lattery level", "EV livello batteria" ],
    "EVRANGE":      [ 3, "EV range", "EV autonomia" ],
    "FUELBATTLEVEL":[ 4, "Fuel level", "livello carburante" ],
    "FUELRANGE":    [ 5, "Fuel range", "autonomia carburante" ],
    "ENGINEONE":    [ 6, "Engine on", "motore acceso" ],
    "ODOMETER":     [ 7, "odometer", "contachilometri" ],

}
                # 12 air temperature: _air_temperature_value: float, _air_temperature_unit: str
                # 13 air_control_is_on: bool
                # 14 defrost_is_on: bool
                # 15 back_window_heater_is_on: bool = None
                # 16 steering_wheel_heater_is_on: bool = None
                # 17 side_mirror_heater_is_on: bool = None
                # 18 front_left_seat_status: str = None
                # 19 front_right_seat_status: str = None
                # 20 rear_left_seat_status: str = None
                # 21 rear_right_seat_status: str = None

                # 22 is_locked: bool = None
                #    front_left_door_is_open: bool = None
                #    front_right_door_is_open: bool = None
                #    back_left_door_is_open: bool = None
                #    back_right_door_is_open: bool = None
                # 23 trunk_is_open: bool = None
                # 24 hood_is_open: bool = None

                # 25 12V battery level: car_battery_percentage: int
                # 26 smart_key_battery_warning_is_on: bool
                # 27 washer_fluid_warning_is_on: bool = None
                # 28 brake_fluid_warning_is_on: bool = None

                # 29 tire_pressure_all_warning_is_on: bool = None
                # tire_pressure_rear_left_warning_is_on: bool = None
                # tire_pressure_front_left_warning_is_on: bool = None
                # tire_pressure_front_right_warning_is_on: bool = None
                # tire_pressure_rear_right_warning_is_on: bool = None

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
        Domoticz.Log(f"_lang={self._lang}, devlang={self._devlang}")
        self._pollInterval = float(Parameters["Mode1"])
        self._pollIntervalCharging = float(Parameters["Mode2"])
        self.vm = VehicleManager(region=int(Parameters["Address"]), brand=int(Parameters["Port"]), username=Parameters["Username"], password=Parameters["Password"], pin=Parameters["Mode3"])
        self.vm.check_and_refresh_token()
        self._lastPoll = None   # force reconnecting in 10 seconds

    def onHeartbeat(self):
        """ Called every 10 seconds or other interval set by Domoticz.Heartbeat() """
        if self.mustPoll():   # check if vehicles data should be polled 
            Domoticz.Log("Pull data from cloud")
            self.vm.check_and_refresh_token()
            self.vm.update_all_vehicles_with_cached_state()
            # Now self.vm.vehicles contains a table with the list of registered vehicles and their parameters
            for k in self.vm.vehicles:
                # k is the keyword associated to a Vehicle object
                v = self.vm.get_vehicle(k)
                name = v.name   # must be unique and identify the type of car, if more than 1 car is owned
                Domoticz.Log(f"Name={v.name} Odometer={v._odometer_value}{v._odometer_unit} Battery={v.car_battery_percentage}")
            
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
                
                if base < 256:
                    # car found: update values
                    Domoticz.Log(f"Car found at base {base}")
                elif baseFree < 256:
                    # car not found, but there is enough space for a new car
                    Domoticz.Log("Add devices for this new car")



                # 1  EV state: ev_battery_is_charging: bool = None, ev_battery_is_plugged_in: bool = None
                # 2  EV battery level: ev_battery_percentage: int
                # 3  EV range: _ev_driving_distance_value: float, _total_driving_distance_unit: str
                # 4  fuel_level: float = None
                # 5  _fuel_driving_distance_value: float = None, _fuel_driving_distance_unit: str = None

                # 6  engine_is_running: engine_is_running: bool
                # 7  odometer: _odometer_value: float, _odometer_unit: str = None
                # 8  partial distance:  _ev_driving_distance_value: float = None, _ev_driving_distance_unit: str = None
                # 9  location: _location_latitude: float = None, _location_longitude: float = None
                # 10 distance from home: to be calculated
                # 11 speed: TODO
                

                # 12 air temperature: _air_temperature_value: float, _air_temperature_unit: str
                # 13 air_control_is_on: bool
                # 14 defrost_is_on: bool
                # 15 back_window_heater_is_on: bool = None
                # 16 steering_wheel_heater_is_on: bool = None
                # 17 side_mirror_heater_is_on: bool = None
                # 18 front_left_seat_status: str = None
                # 19 front_right_seat_status: str = None
                # 20 rear_left_seat_status: str = None
                # 21 rear_right_seat_status: str = None

                # 22 is_locked: bool = None
                #    front_left_door_is_open: bool = None
                #    front_right_door_is_open: bool = None
                #    back_left_door_is_open: bool = None
                #    back_right_door_is_open: bool = None
                # 23 trunk_is_open: bool = None
                # 24 hood_is_open: bool = None

                # 25 12V battery level: car_battery_percentage: int
                # 26 smart_key_battery_warning_is_on: bool
                # 27 washer_fluid_warning_is_on: bool = None
                # 28 brake_fluid_warning_is_on: bool = None

                # 29 tire_pressure_all_warning_is_on: bool = None
                # tire_pressure_rear_left_warning_is_on: bool = None
                # tire_pressure_front_left_warning_is_on: bool = None
                # tire_pressure_front_right_warning_is_on: bool = None
                # tire_pressure_rear_right_warning_is_on: bool = None


            self.updatePollInterval()

####################################################################################
global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()
