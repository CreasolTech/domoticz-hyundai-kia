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
<plugin key="domoticz-hyundai-kia" name="Hyundai Kia connect" author="CreasolTech" version="1.0.7" externallink="https://github.com/CreasolTech/domoticz-hyundai-kia">
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
                <option label="10 minutes" value="10" />
                <option label="20 minutes" value="20" />
                <option label="30 minutes" value="30" />
                <option label="60 minutes" value="60" />
                <option label="120 minutes" value="120" default="true" />
                <option label="240 minutes" value="240" />
            </options>
        </param>
        <param field="Mode2" label="Poll interval while driving">
            <options>
                <option label="5 minutes" value="5" />
                <option label="10 minutes" value="10" />
                <option label="20 minutes" value="20" default="true" />
                <option label="30 minutes" value="30" />
                <option label="60 minutes" value="60" />
                <option label="120 minutes" value="60" />
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz as Domoticz
import json
import re
import logging
from math import cos, asin, sqrt, pi
import requests
from datetime import datetime
from textwrap import fill
from hyundai_kia_connect_api import *


LANGS=[ "en", "it", "nl", "se", "hu", "pl", "fr" ] # list of supported languages, in DEVS dict below
LANGBASE=1  # item in the DEVS list where the first language starts 


#Dutch translation by Branko
#Swedish translation by Joakim W.
#Hungarian translation by Upo
#Polish translation by z1mEk
#French translation by Neutrino
#German translation by Gerhard M.
#If you want to add another language, please add, for each line:     , "your translation"
DEVS={ #topic:      [ num, "en name", "it name", "nl name", "se name", "hu name", "pl name", "fr name", "de_name"  ...other languages should follow  ],
    "EVSTATE":      [ 1, "EV state", "EV stato", "EV status", "EV status", "EV státusz", "EV staus", "Status VE", "EV Status" ],
    "EVBATTLEVEL":  [ 2, "EV battery level", "EV livello batteria", "batterijniveau", "EV batterinivå", "EV akku töltöttség", "EV poziom baterii", "Niveau de batterie", "EV Batterieladestand"],
    "EVRANGE":      [ 3, "EV range", "EV autonomia", "EV bereik" , "EV räckvidd", "EV hatótáv", "EV zasięg", "Autonomie VE", "EV Reichweite" ],
    "FUELLEVEL":    [ 4, "fuel level", "livello carburante", "brandstofniveau", "bränslenivå" , "üzemanyagszint", "poziom paliwa" ,"Niveau de carburant", "EV Ladestand"],
    "FUELRANGE":    [ 5, "fuel range", "autonomia carburante", "brandstof bereik", "bränsleräckvidd" , "üzemanyag hatótáv", "zasięg paliwa", "Autonomie Carburant", "Reichweite" ],
    "ENGINEON":     [ 6, "engine ON", "motore acceso", "motor aan", "motor på", "motor be", "silnik włączony" ,"Moteur démarré", "Motor ein"],
    "ODOMETER":     [ 7, "odometer", "contachilometri", "kilometerteller", "odometer" , "kilométer-számláló", "licznik kilometrów" , "Compteur", "Kilometerstand" ],
    "LOCATION":     [ 8, "location", "posizione", "locatie", "plats", "hely", "pozycja", "Position", "Position" ],
    "HOMEDIST":     [ 9, "distance", "distanza", "afstand", "avstånd", "távolság", "dystans" ,"distance", "Distanz"],
    "SPEED":        [ 10, "speed", "velocità", "snelheid", "hastighet", "sebesség", "prędkość" , "vitesse", "Geschwindigkeit"],
    "UPDATE":       [ 11, "update req.", "aggiorna", "bijwerken", "uppdatering", "frissítés", "aktualizacja" , "Mise à jour", "Update notwendig" ],
    "TEMPSET":      [ 12, "temp. settings", "imp. temperatura", "temperatuur inst.", "temperatur", "hőmérséklet beállítás", "ustawienie temperatury", "Réglage temp.", "Temperatureinstellungen"],
    "CLIMAON":      [ 13, "climate", "clima acceso", "airco", "klimat", "klíma", "klimatyzacja","Climatisation", "Klima" ],
    "DEFROSTON":    [ 14, "defrost", "scongelamento", "ontdooien", "defrost", "páramentesítő", "rozmrożenie" ,"Dégivrage", "Defrostung"],
    "REARWINDOWON": [ 15, "rear window", "lunotto termico", "achterruitverwarming", "bakrutevärme", "hátsó ablak", "tylne okno" ,"Dégivrage arrière", "Fenster hinten"],
    "STEERINGWHEELON": [ 16, "steering wheel", "volante termico", "stuurverwarming", "rattvärme", "kormány", "kierownica" ,"Volant Chauffant", "Lenkrad"],
    "SIDEMIRRORSON":[ 17, "side mirrors", "specchietti termici", "zijspiegel verwarming", "sidospeglar", "oldalsó tükrök", "lusterka boczne" , "Dégivrage rétroviseur", "Seitenspiegel" ],
    "SEATFL":       [ 18, "seat front-left", "sedile guidatore", "bestuurdersstoel", "förarstol", "bal első ülés", "siedzenie przednie lewe" ,"Siège conducteur", "Sitz vorne links"],
    "SEATFR":       [ 19, "seat front-right", "sedile passeggero", "bijrijdersstoel", "passagerarstol", "jobb első ülés", "siedzenie przednie prawe" ,"Siège passager", "Sitz vorne rechts"],
    "SEATRL":       [ 20, "seat rear-left", "sedile post.sx", "achterbank links", "baksäte vänster", "bal hátsó ülés", "siedzenie tylne lewe", "Siège arrière conducteur", "Sitz hinten links" ],
    "SEATRR":       [ 21, "seat rear-right", "sedile post.dx", "achterbank rechts", "baksäte höger", "jobb hátsó ülés", "siedzenie tylne prawe", "Siège arrière passager", "Sitz hinten rechts" ],
    "OPEN":         [ 22, "open", "aperta", "open", "öppen", "nyitva", "otwarte", "ouvrir", "offen" ],
    "TRUNK":        [ 23, "trunk open", "bagagliaio aperto", "kofferbak", "bagagelucka", "casomagtér nyitva", "bagażnik otwarty" , "coffre ouvert", "Kofferraum offen"],
    "HOOD":         [ 24, "hood open", "cofano aperto", "motorkap", "motorhuv", "motorháztető nyitva", "pokrywa silnika otwarta" , "capot ouvert", "Motorhaube offen" ],
    "12VBATT":      [ 25, "12V battery", "batteria 12V", "12V batterij", "batteri 12V", "12V akku", "akumulator 12V" , "Batterie 12V", "12V Batterie"],
    "KEYBATT":      [ 26, "key battery", "batteria radiocomando", "batterij afstandsbediening", "nyckelbatteri", "kulcs elem", "bateria kluczyka", "Pile clé", "Schlüsselbatterie" ],
    "WASHER":       [ 27, "washer fluid", "liquido tergicristallo", "ruitensproeiervloeistof", "spolarvätska", "ablakmosó", "płyn spryskiwaczy", "lave-glace", "Schweibenwischwasser" ],
    "BRAKE":        [ 28, "brake fluid", "olio freni", "rem", "bromsvätska", "fékfolyadék", "płyn hamulcowy", "liquide de frein", "Bremsflüssigkeit" ],
    "TIRES":        [ 29, "tyre pressure", "pressione gomme", "bandenspanning", "däcktryck", "guminyomás", "ciśnienie w oponie", "pression pneus", "Reifenluftdruck" ],
    "CLIMATEMP":    [ 30, "climate temperature", "temperatura clima", "airco temperatuur", "klimattemperatur", "klíma hőfok", "temperatura klimatyzacji", "Température clim", "Klimatemperatur" ],
    "EVLIMITAC": [ 31, "Charge limit AC", "Limite ricarica AC", "", "", "", "", "", "" ],
    "EVLIMITDC": [ 32, "Charge limit DC", "Limite ricarica DC", "", "", "", "", "", "" ],
    "EVCHARGEON": [ 33, "EV Charging", "In ricarica", "", "", "", "", "", "" ],

}

class BasePlugin:
    """ Base class for the plugin """

    def __init__(self):
        self._pollInterval = 120        # fetch data every 120 minutes, by default (but check parameter Mode1!)
        self._pollIntervalDriving = 30 # while charging, fetch data quickly 
        self.interval = 10              # current polling interval (depending by charging, moving, night time, ...) It's set by mustPoll()
        self._lastPoll = None           # last time I got vehicle status
        self._checkDevices = True       # if True, check that all devices are created (at startup and when update is forced)
        self._setChargeLimits = 0       # if > 0 => decrement every HeartBeat interval, and when zero set the charging limit
        self._fetchingData = 0          # 0 if system is not fetching data from cloud, >0 if it's fetching (incremented every onHeartBeat)
        self._isCharging = False  
        self._engineOn = False
        self._lang = "en"
        self._vehicleLoc = {}           # saved location for vehicles
        self._name2id = {}
        self.vm = None

    def getVehicleId(self, Unit):
            # get name and id for the vehicle associated to Devices[Unit]
            vehicleId = False
            Domoticz.Log(f"Device Name={Devices[Unit].Name}")
            name=re.findall(f"{Parameters['Name']} - ([a-zA-Z0-9-_]+) .*", Devices[Unit].Name)[0]
            if self._name2id == {}:
                # call onHeartbeat to load vehicles data
                Domoticz.Log("_name2id is empty => call onHeartBeat to init vehicles data")
                self.checkDevices = True
                self._lastPoll = None
                self.onHeartbeat()

            if name in self._name2id:
                vehicleId=self._name2id[name]
                Domoticz.Log(f"name={name} vehicleId={vehicleId} Unit={Unit}")
            else:
                # vehicleId not found
                Domoticz.Log(f"Vehicle ID not found: there is not a vehicle named {name} in the Hyundai/Kia cloud")
            return vehicleId
 
    def mustPoll(self):
        """ Return True if new data should be polled """
        if self._fetchingData != 0:
            return False    # fetching data already in progress
        if self._lastPoll == None: 
            return True
        elapsedTime = int( (datetime.now()-self._lastPoll).total_seconds() / 60)  # time in minutes
        self.interval = self._pollInterval
        if self._engineOn:
            self.interval = self._pollIntervalDriving   # while charging or driving, reduce the poll interval
        elif self._isCharging:
            self.interval = self._pollIntervalDriving*2
        elif datetime.now().hour>=22 or datetime.now().hour<6:
            self.interval*=4     # reduce polling during the night
            if self.interval > 120: self.interval = 120
        if elapsedTime >= self.interval: 
            return True
        return False

    def onStart(self):
        Domoticz.Log("Parameters="+str(Parameters))
        Domoticz.Debug("Settings="+str(Settings))
        Domoticz.Heartbeat(30)
        self._lang=Settings["Language"]
        # check if language set in domoticz exists
        if self._lang in LANGS:
            self._devlang=LANGBASE+LANGS.index(self._lang)
        else:
            Domoticz.Log(f"Language {self._lang} does not exist in dict DEVS, inside the domoticz_hyundai_kia plugin, but you can contribute adding it ;-) Thanks!")
            self._lang="en"
            self._devlang=LANGBASE # default: english text
        self._pollInterval = float(Parameters["Mode1"])
        self._pollIntervalDriving = float(Parameters["Mode2"])
        self.vm = VehicleManager(region=int(Parameters["Address"]), brand=int(Parameters["Port"]), username=Parameters["Username"], password=Parameters["Password"], pin=Parameters["Mode3"])
        self._lastPoll = None   # force reconnecting in 10 seconds 
        #self._lastPoll = datetime.now() # do not reconnect in 10 seconds, to avoid daily connection exceeding during testing #DEBUG 
        
        #logging.basicConfig(filename='/var/log/domoticz.log', encoding='utf-8', level=logging.INFO)
        logging.basicConfig(filename='/var/log/domoticz.log', encoding='utf-8', level=logging.DEBUG) #DEBUG

    def onHeartbeat(self):
        """ Called every 10 seconds or other interval set by Domoticz.Heartbeat() """
        Domoticz.Log("onHeartbeat()") 
        if self._fetchingData == 0:
            #it's not fetching data from cloud
            if (self._setChargeLimits&15) != 0: #_setChargeLimits=0bzyxw0010  where if w is set => changed limits for vehicle with base=0, x=1 => vehicle with base=64, ....
                self._setChargeLimits-=1
                if (self._setChargeLimits&15)==0:
                    bases=self._setChargeLimits&(~15)
                    base=0
                    while bases != 0:
                        if (bases&16):   #parse current base
                            Unit=base+DEVS['EVLIMITAC'][0]
                            vehicleId=self.getVehicleId(Unit) # get name and id for the vehicle
                            if vehicleId!=False:
                                ac=int(Devices[Unit].sValue)
                                dc=int(Devices[Unit+1].sValue)
                                Domoticz.Log(f"Set charge limits for device Unit={Unit}, AC={ac}, DC={dc}")
                                evchargelimits=self.vm.get_vehicle(vehicleId).ev_charge_limits
                                evchargelimits.ac=ac
                                evchargelimits.dc=dc
                                ret=self.vm.set_charge_limits(vehicleId, evchargelimits)
                        bases>>=1
                        base+=64   # is next base 
            elif self.mustPoll():   # check if vehicles data should be polled. return False if polling is already in progress 
                self._lastPoll = datetime.now()
                Domoticz.Log("check_and_refresh_token()...")
                ret=self.vm.check_and_refresh_token()
#               self.vm.force_refresh_all_vehicles_states() # it does not update location and speed!
#               Domoticz.Log(f"self.vm.force_refresh_all_vehicles_states()")
#               ret=self.vm.check_and_force_update_vehicles(self.interval)     # suggested by fuatakgun
#               Domoticz.Log(f"self.vm.check_and_force_update_vehicles({self.interval}) returned {ret}")
#               self.vm.update_all_vehicles_with_cached_state()    # not needed
                Domoticz.Log("force_refresh_all_vehicles_states()..")
                self.vm.force_refresh_all_vehicles_states() # suggested by P.Levres: fetch data from vehicle to the cloud
                Domoticz.Log("update_all_vehicles_with_cached_state()...")
                self.vm.update_all_vehicles_with_cached_state()  # suggested by P.Levres: download data from the cloud
                self._isCharging=False  # set to false: if one vehicle is charging, this flag will be set by updateDevices()
                self._engineOn=False    # set to false: if one vehicle is moving,   this flag will be set by updateDevices()
                # Now self.vm.vehicles contains a table with the list of registered vehicles and their parameters
                for k in self.vm.vehicles:
                    # k is the keyword associated to a Vehicle object
                    v = self.vm.get_vehicle(k)
                    name = re.sub(r'\W+', '', v.name)   # must be unique and identify the type of car, if more than 1 car is owned
                    if name not in self._name2id:
                        self._name2id[name]=k   # save the corresponding between vehicle name and id in vm.vehicles dict
                    Domoticz.Log(f"Name={name} Odometer={v._odometer_value}{v._odometer_unit} Battery={v.ev_battery_percentage}")
                    Domoticz.Log(f"Vehicle={v}")
                
                    # base = Unit base = 0, 64, 128, 192 # up to 4 vehicles can be addressed, 64 devices per vehicle (Unit <= 255)
                    # Find the right Unit for the current car
                    baseFree = 256
                    for base in range(0, 256-1, 64):
                        if base+(DEVS['ODOMETER'][0]) in Devices:
                            if name in Devices[base+(DEVS['ODOMETER'][0])].Name:   
                                # odometer exists: check that Domoticz device name correspond with vehicle name (set on Kia connect)
                                break
                        else:
                            if baseFree > base:
                                baseFree = base # free base where devices can be stored
                    Domoticz.Log(f"base={base} baseFree={baseFree}")

                    if base >= 256 and baseFree < 256:
                        # car not found, but there is enough space for a new car
                        base = baseFree
                        self.addDevices(base, name, v)
                    if base < 256:
                        # car found or just created: update values
                        if self._checkDevices == True: self.addDevices(base, name, v)
                        self.updateDevices(base, name, v)

                self._checkDevices=False
                self._fetchingData=0    # fetching data from API ended correctly
        else:
            #self._fetchingData>1 => system is fetching data from cloud
            self._fetchingData += 1 # still fetching data from cloud API
            Domoticz.Log(f"onHeartbeat: fetching data has been started since {self._fetchingData}0 seconds")
            if self._fetchingData > 10:
                # fetching started more than 100s ago!
                Domoticz.Log(f"onHeartbeat: fetching data has been started more than {self._fetchingData}0 seconds ago")


    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log(f"onCommand(Unit={Unit}, Command={Command}, Level={Level}, Hue={Hue})")
        if (Unit&63) == DEVS["UPDATE"][0]:  #force status update
            Devices[Unit].Update(nValue=1 if Command=="On" else 0, sValue=Command)
            if Command=="On":
                if self._fetchingData == 0:
                    Domoticz.Log("Force update command")
                    self._checkDevices = True
                    self._lastPoll = None
                    self.onHeartbeat()
            else:
                #Update button has been switched OFF
                Domoticz.Log(f"UPDATE button has been switched OFF")
        else:
            vehicleId=self.getVehicleId(Unit) # get name and id for the vehicle
            if vehicleId==False:
                Domoticz.Log("vehicleId not found => ignore command")
                return  # vehicleId not found

            if (Unit&63) == DEVS["CLIMAON"][0]:   # start/stop climate control
                if Command == "On":
                    options=ClimateRequestOptions()
                    options.set_temp=float(Devices[(Unit&(~63))+DEVS["CLIMATEMP"][0]].sValue)
                    if options.set_temp<15:
                        options.set_temp=15
                    elif options.set_temp>27:
                        options.set_temp=27
                    options.climate=True if options.set_temp<23 else False
                    options.heating=True if options.set_temp>=23 else False
                    ret=self.vm.start_climate(vehicleId, options)
                    Domoticz.Log(f"start_climate() with options={options}. Returned {ret}")
                    Devices[Unit].Update(nValue=1, sValue="On")
                else:   # Off command
                    ret=self.vm.stop_climate(vehicleId)
                    Domoticz.Log(f"stop_climate() returned {ret}")
                    Devices[Unit].Update(nValue=0, sValue="Off")
            elif (Unit&63) == DEVS["CLIMATEMP"][0]:   # air temperature
                airTemp=float(Level)
                if airTemp<15: 
                    airTemp=15
                elif airTemp>27: 
                    airTemp=27
                Devices[Unit].Update(nValue=0, sValue=str(airTemp))
            elif (Unit&63) == DEVS["OPEN"][0]:   # open/close
                if Command == "On": # => lock
                    Domoticz.Log(f"lock command")
                    ret=self.vm.lock(vehicleId)
                    Devices[Unit].Update(nValue=1, sValue="On")
                else:   # Off command => unlock
                    Domoticz.Log(f"unlock command")
                    ret=self.vm.unlock(vehicleId)
                    Devices[Unit].Update(nValue=0, sValue="Off")
            elif (Unit&63) == DEVS["EVLIMITAC"][0] or (Unit&63) == DEVS["EVLIMITDC"][0]:
                # Battery limit was changed: send new value to the car
                self._setChargeLimits=1  # set charge limits after 2*HeartBeat 
                self._setChargeLimits|=16<<(Unit>>6)    #store in setChargeLimits which devices have been changed 0bzyxw0010 where w=1 if base=0, x=1 if base=64, y=1 if base=128, ...
                Level=Level-Level%10    # Level should be 0, 10, 20, 30, ...
                Domoticz.Log(f"New value={Level}")
                Devices[Unit].Update(nValue=1, sValue=str(Level))
            elif (Unit&63) == DEVS["EVCHARGEON"][0]:    # Start or stop charging
                if Command == "On":
                    Domoticz.Log(f"Received command to start charging")
                    Devices[Unit].Update(nValue=1, sValue="On")
                    ret=self.vm.start_charge(vehicleId)
                else:
                    Domoticz.Log(f"Received command to stop charging")
                    Devices[Unit].Update(nValue=0, sValue="Off")
                    ret=self.vm.stop_charge(vehicleId)


    def addDevices(self, base, name, v):
        """ Add devices for car named {name}, starting from base unit {base}, using vehicle parameters in {v} """
        Domoticz.Log(f"Add devices for car {name} with base index {base}")

        dev=DEVS['EVSTATE']; var=v.ev_battery_is_charging
        if var != None and base+dev[0] not in Devices: 
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=19, Used=1).Create()

        dev=DEVS['EVCHARGEON']; var=v.ev_battery_is_charging
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        dev=DEVS['EVBATTLEVEL']; var=v.ev_battery_percentage
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=6, Used=1).Create()

        dev=DEVS['EVRANGE']; var=v.ev_driving_distance
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Options={'Custom': '1;'+v._ev_driving_distance_unit}, Used=1).Create()

        dev=DEVS['EVLIMITAC']; var=v._ev_charge_limits.ac
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=62, Switchtype=7, Used=1).Create()

        dev=DEVS['EVLIMITDC']; var=v._ev_charge_limits.dc
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=62, Switchtype=7, Used=1).Create()

        dev=DEVS['FUELLEVEL']; var=v.fuel_level
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=6, Used=1).Create()

        dev=DEVS['FUELRANGE']; var=v.fuel_driving_distance
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Options={'Custom': '1;'+v._fuel_driving_distance_unit}, Used=1).Create()

        dev=DEVS['ENGINEON']; var=v.engine_is_running
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        dev=DEVS['ODOMETER']; var=v.odometer
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=113, Subtype=0, Switchtype=3, Used=1).Create()

        dev=DEVS['LOCATION']; var=v.location_latitude
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=19, Used=1).Create()
        
        dev=DEVS['HOMEDIST']; var=v.location_latitude
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Used=1).Create()

        dev=DEVS['SPEED']; var=v.data
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Used=1).Create()
        
        dev=DEVS['UPDATE']
        if base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create() 

        dev=DEVS['CLIMAON']; var=v.air_control_is_on
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        dev=DEVS['CLIMATEMP']; var=v.air_temperature    # Thermostat
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=242, Subtype=1, Used=1).Create()

        dev=DEVS['DEFROSTON']; var=v.defrost_is_on
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        dev=DEVS['REARWINDOWON']; var=v.back_window_heater_is_on
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        dev=DEVS['STEERINGWHEELON']; var=v.steering_wheel_heater_is_on
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        dev=DEVS['SIDEMIRRORSON']; var=v.side_mirror_heater_is_on
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        dev=DEVS['SEATFL']; var=v.front_left_seat_status
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=19, Used=1).Create()

        dev=DEVS['SEATFR']; var=v.front_right_seat_status
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=19, Used=1).Create()

        dev=DEVS['SEATRL']; var=v.rear_left_seat_status
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=19, Used=1).Create()

        dev=DEVS['SEATRR']; var=v.rear_right_seat_status
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=19, Used=1).Create()

        dev=DEVS['OPEN']; var=v.is_locked
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Switchtype=19, Used=1).Create()

        dev=DEVS['TRUNK']; var=v.trunk_is_open
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Switchtype=11, Used=1).Create()

        dev=DEVS['HOOD']; var=v.hood_is_open
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Switchtype=11, Used=1).Create()

        dev=DEVS['12VBATT']; var=v.car_battery_percentage
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=6, Used=1).Create()

        dev=DEVS['KEYBATT']; var=v.smart_key_battery_warning_is_on
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=22, Used=1).Create()

        dev=DEVS['WASHER']; var=v.washer_fluid_warning_is_on
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=6, Used=1).Create()

        dev=DEVS['BRAKE']; var=v.brake_fluid_warning_is_on
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=6, Used=1).Create()

        dev=DEVS['TIRES']; var=v.tire_pressure_all_warning_is_on
        if var != None and base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=6, Used=1).Create()

    def updateDevices(self, base, name, v):
        """ Update devices for car named {name}, starting from base unit {base}, using vehicle parameters in {v} """
        Domoticz.Log(f"Car found at base {base}")

        if v.ev_battery_is_charging != None:
            nValue=0
            sValue="Disconnected"
            if v.ev_battery_is_charging == True:
                nValue=1
                sValue="Charging"
                self._isCharging=True
            elif v.ev_battery_is_plugged_in>0:
                nValue=1
                sValue="Connected"
            Devices[base+DEVS['EVSTATE'][0]].Update(nValue=nValue, sValue=sValue)
            if self._isCharging == True:
                Devices[base+DEVS['EVCHARGEON'][0]].Update(nValue=1, sValue="On")
            else:
                Devices[base+DEVS['EVCHARGEON'][0]].Update(nValue=0, sValue="Off")
            #Domoticz.Log(f"v.ev_battery_is_charging={v.ev_battery_is_charging}, nValue={nValue}, sValue={sValue}")
        
        batteryLevel=None   # show batteryLevel in the debug messages
        if v.ev_battery_percentage != None:
            nValue=v.ev_battery_percentage
            batteryLevel=v.ev_battery_percentage
            Devices[base+DEVS['EVBATTLEVEL'][0]].Update(nValue=nValue, sValue=str(nValue))
        
        nValue=v.ev_driving_distance
        if nValue != None:
            Devices[base+DEVS['EVRANGE'][0]].Update(nValue=nValue, sValue=str(nValue))
        
        nValue=v._ev_charge_limits.ac
        if nValue != None:
            Devices[base+DEVS['EVLIMITAC'][0]].Update(nValue=1, sValue=str(nValue))
        
        nValue=v._ev_charge_limits.dc
        if nValue != None:
            Devices[base+DEVS['EVLIMITDC'][0]].Update(nValue=1, sValue=str(nValue))
        
        nValue=v.fuel_level
        if nValue != None:
            Devices[base+DEVS['FUELLEVEL'][0]].Update(nValue=nValue, sValue=str(nValue))
        
        nValue=v.fuel_driving_distance
        if nValue != None:
            Devices[base+DEVS['FUELRANGE'][0]].Update(nValue=nValue, sValue=str(nValue))
        
        value=v.engine_is_running
        if value != None:
            nValue=0; sValue="Off"
            if (value):
                nValue=1; sValue="On"
                self._engineOn=True
            Devices[base+DEVS['ENGINEON'][0]].Update(nValue=nValue, sValue=sValue)
        
        nValue=v.odometer
        if nValue != None:
            nValue=int(nValue)
            Devices[base+DEVS['ODOMETER'][0]].Update(nValue=nValue, sValue=str(nValue))
        
        if (v.location_latitude != None and (name not in self._vehicleLoc or (v.location_latitude!=self._vehicleLoc[name]['latitude'] and v.location_longitude!=self._vehicleLoc[name]['longitude']))):
            # LOCATION changed or not previously set
            # get address
            get_address_url = 'https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=16&lat=' + str(v.location_latitude) + '&lon=' + str(v.location_longitude)
            response = requests.get(get_address_url)
            if response.status_code == 200:
                response = json.loads(response.text)
                locAddr=response['display_name']
                locMap = '<a href="http://www.google.com/maps/search/?api=1&query=' + str(v.location_latitude) + ',' + str(v.location_longitude) + '" target="_new"><em style="color:blue;">Map</em></a>'
                Domoticz.Log(f"Location address: {locAddr}")
                sValue=fill(locAddr, 40) + ' ' + locMap
                Devices[base+DEVS['LOCATION'][0]].Update(nValue=0, sValue=sValue)

            # HOME DISTANCE: compute distance from home
            homeloc=Settings['Location'].split(';')
            distance=round(self.distance(v.location_latitude, v.location_longitude, float(homeloc[0]), float(homeloc[1])), 1)
            Devices[base+DEVS['HOMEDIST'][0]].Update(nValue=0, sValue=str(distance))

            value=v.data
            if value != None:
                nValue=value['vehicleLocation']['speed']['value']
                sValue=str(nValue)
                Devices[base+DEVS['SPEED'][0]].Update(nValue=nValue, sValue=sValue)
                Domoticz.Log(f"Vehicle {name} has odometer={v.odometer} speed={nValue} distance_from_home={distance} battery_level={batteryLevel}")

        # Reset force update button
        Devices[base+DEVS['UPDATE'][0]].Update(nValue=0, sValue="Off")
        
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
            nValue=value
            sValue="On" if value>0 else "Off"
            Devices[base+DEVS['REARWINDOWON'][0]].Update(nValue=nValue, sValue=sValue)
        
        value=v.steering_wheel_heater_is_on
        if value != None:
            nValue=value
            sValue="On" if value>0 else "Off"
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
            sValue=str(nValue)
            Devices[base+DEVS['12VBATT'][0]].Update(nValue=nValue, sValue=sValue)
        
        nValue=v.smart_key_battery_warning_is_on
        if nValue != None:
            sValue="Ok" if nValue == 0 else "Low"
            Devices[base+DEVS['KEYBATT'][0]].Update(nValue=nValue, sValue=sValue)
        
        nValue=v.washer_fluid_warning_is_on
        if nValue != None:
            sValue="Ok" if nValue == 0 else "Empty"
            Devices[base+DEVS['WASHER'][0]].Update(nValue=nValue, sValue=sValue)
        
        nValue=v.brake_fluid_warning_is_on
        if nValue != None:
            sValue="Ok" if nValue == 0 else "Empty"
            Devices[base+DEVS['BRAKE'][0]].Update(nValue=nValue, sValue=sValue)
        
        nValue=v.tire_pressure_all_warning_is_on
        if nValue != None:
            sValue="Ok" if nValue == 0 else "Low"
            Devices[base+DEVS['TIRES'][0]].Update(nValue=nValue, sValue=sValue)

    def distance(self, lat1, lon1, lat2, lon2):
        """ Compute the distance between two locations """
        p = pi / 180
        a = 0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
        return 12742 * asin(sqrt(a))

    def onTimeout(self, Connection):    #DEBUG
        Domoticz.Log(f"onTimeout({Connection})")
        

####################################################################################
global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onTimeout(Connection): #DEBUG
    global _plugin
    _plugin.onTimeout(Connection)

