#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Hyundai Kia plugin
# Based on hyundai-kia-connect-api by Fuat Akgun and BlUVO domoticz plugin by Pierre Levres
#
# Source:   https://github.com/CreasolTech/domoticz-hyundai-kia.git
# Authors:  CreasolTech ( https://www.creasol.it/domotics )
#           WillemD61 ()
# License: MIT
#

"""
<plugin key="domoticz-hyundai-kia" name="Hyundai Kia connect" author="CreasolTech, WillemD61" version="1.1.7" externallink="https://github.com/CreasolTech/domoticz-hyundai-kia">
    <description>
        <h2>Domoticz Hyundai Kia connect plugin - 1.1.7</h2>
        This plugin permits to access, through the Hyundai Kia account credentials, to information about your Hyundai and Kia vehicles, such as odometer, EV battery charge, 
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
                <option label="480 minutes" value="480" />
                <option label="720 minutes" value="720" />
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
import time
import requests
from datetime import date,datetime
from textwrap import fill
from hyundai_kia_connect_api import *
from hyundai_kia_connect_api.exceptions import *

import os, psutil   #DEBUG !!!

DomoticzIP="127.0.0.1"
DomoticzPort="8080"

LANGS=[ "en", "it", "nl", "se", "hu", "pl", "fr" ] # list of supported languages, in DEVS dict below
LANGBASE=2  # item in the DEVS list where the first language starts 

UNITMASK=63 # Unit for each car starts from 1, 65, 129, 193 (max 4 vehicles)

#Dutch translation by Branko
#Swedish translation by Joakim W.
#Hungarian translation by Upo
#Polish translation by z1mEk
#French translation by Neutrino
#German translation by Gerhard M.
#If you want to add another language, please add, for each line:     , "your translation"
DEVS={ #topic:      [ num, "devname", "en name", "it name", "nl name", "se name", "hu name", "pl name", "fr name", "de_name"  ...other languages should follow  ],
    "EVSTATE":      [ 1, None, "EV state", "EV stato", "EV status", "EV status", "EV státusz", "EV staus", "Status VE", "EV Status" ],
    "EVBATTLEVEL":  [ 2, None, "EV battery level", "EV livello batteria", "batterijniveau", "EV batterinivå", "EV akku töltöttség", "EV poziom baterii", "Niveau de batterie", "EV Batterieladestand"],
    "EVRANGE":      [ 3, None, "EV range", "EV autonomia", "EV bereik" , "EV räckvidd", "EV hatótáv", "EV zasięg", "Autonomie VE", "EV Reichweite" ],
    "FUELLEVEL":    [ 4, None, "fuel level", "livello carburante", "brandstofniveau", "bränslenivå" , "üzemanyagszint", "poziom paliwa" ,"Niveau de carburant", "EV Ladestand"],
    "FUELRANGE":    [ 5, None, "fuel range", "autonomia carburante", "brandstof bereik", "bränsleräckvidd" , "üzemanyag hatótáv", "zasięg paliwa", "Autonomie Carburant", "Reichweite" ],
    "ENGINEON":     [ 6, None, "engine ON", "motore acceso", "motor aan", "motor på", "motor be", "silnik włączony" ,"Moteur démarré", "Motor ein"],
    "ODOMETER":     [ 7, None, "odometer", "contachilometri", "kilometerteller", "odometer" , "kilométer-számláló", "licznik kilometrów" , "Compteur", "Kilometerstand" ],
    "LOCATION":     [ 8, None, "location", "posizione", "locatie", "plats", "hely", "pozycja", "Position", "Position" ],
    "HOMEDIST":     [ 9, None, "distance", "distanza", "afstand", "avstånd", "távolság", "dystans" ,"distance", "Distanz"],
    "SPEED":        [ 10, None, "speed", "velocità", "snelheid", "hastighet", "sebesség", "prędkość" , "vitesse", "Geschwindigkeit"],
    "UPDATE":       [ 11, None, "update req.", "aggiorna", "bijwerken", "uppdatering", "frissítés", "aktualizacja" , "Mise à jour", "Update notwendig" ],
    "TEMPSET":      [ 12, None, "temp. settings", "imp. temperatura", "temperatuur inst.", "temperatur", "hőmérséklet beállítás", "ustawienie temperatury", "Réglage temp.", "Temperatureinstellungen"],
    "CLIMAON":      [ 13, None, "climate control", "clima acceso", "airco", "klimat", "klíma", "klimatyzacja","Climatisation", "Klima" ],
    "DEFROSTON":    [ 14, None, "defrost", "scongelamento", "ontdooien", "defrost", "páramentesítő", "rozmrożenie" ,"Dégivrage", "Defrostung"],
    "REARWINDOWON": [ 15, None, "rear window heater", "lunotto termico", "achterruitverwarming", "bakrutevärme", "hátsó ablak", "tylne okno" ,"Dégivrage arrière", "Fenster hinten"],
    "STEERINGWHEELON": [ 16, None, "steering wheel heater", "volante termico", "stuurverwarming", "rattvärme", "kormány", "kierownica" ,"Volant Chauffant", "Lenkrad"],
    "SIDEMIRRORSON":[ 17, None, "side mirrors heater", "specchietti termici", "zijspiegel verwarming", "sidospeglar", "oldalsó tükrök", "lusterka boczne" , "Dégivrage rétroviseur", "Seitenspiegel" ],
    "SEATFL":       [ 18, None, "seat front-left", "sedile guidatore", "bestuurdersstoel", "förarstol", "bal első ülés", "siedzenie przednie lewe" ,"Siège conducteur", "Sitz vorne links"],
    "SEATFR":       [ 19, None, "seat front-right", "sedile passeggero", "bijrijdersstoel", "passagerarstol", "jobb első ülés", "siedzenie przednie prawe" ,"Siège passager", "Sitz vorne rechts"],
    "SEATRL":       [ 20, None, "seat rear-left", "sedile post.sx", "achterbank links", "baksäte vänster", "bal hátsó ülés", "siedzenie tylne lewe", "Siège arrière conducteur", "Sitz hinten links" ],
    "SEATRR":       [ 21, None, "seat rear-right", "sedile post.dx", "achterbank rechts", "baksäte höger", "jobb hátsó ülés", "siedzenie tylne prawe", "Siège arrière passager", "Sitz hinten rechts" ],
    "OPEN":         [ 22, None, "open", "aperta", "open", "öppen", "nyitva", "otwarte", "ouvrir", "offen" ],
    "TRUNK":        [ 23, None, "trunk open", "bagagliaio aperto", "kofferbak", "bagagelucka", "casomagtér nyitva", "bagażnik otwarty" , "coffre ouvert", "Kofferraum offen"],
    "HOOD":         [ 24, None, "hood open", "cofano aperto", "motorkap", "motorhuv", "motorháztető nyitva", "pokrywa silnika otwarta" , "capot ouvert", "Motorhaube offen" ],
    "12VBATT":      [ 25, None, "12V battery", "batteria 12V", "12V batterij", "batteri 12V", "12V akku", "akumulator 12V" , "Batterie 12V", "12V Batterie"],
    "KEYBATT":      [ 26, None, "key battery", "batteria radiocomando", "batterij afstandsbediening", "nyckelbatteri", "kulcs elem", "bateria kluczyka", "Pile clé", "Schlüsselbatterie" ],
    "WASHER":       [ 27, None, "washer fluid", "liquido tergicristallo", "ruitensproeiervloeistof", "spolarvätska", "ablakmosó", "płyn spryskiwaczy", "lave-glace", "Schweibenwischwasser" ],
    "BRAKE":        [ 28, None, "brake fluid", "olio freni", "rem", "bromsvätska", "fékfolyadék", "płyn hamulcowy", "liquide de frein", "Bremsflüssigkeit" ],
    "TIRES":        [ 29, None, "tyre pressure", "pressione gomme", "bandenspanning", "däcktryck", "guminyomás", "ciśnienie w oponie", "pression pneus", "Reifenluftdruck" ],
    "CLIMATEMP":    [ 30, None, "climate temperature", "temperatura clima", "airco temperatuur", "klimattemperatur", "klíma hőfok", "temperatura klimatyzacji", "Température clim", "Klimatemperatur" ],
    "EVLIMITAC": [ 31, None, "Charge limit AC", "Limite ricarica AC", "", "", "", "", "", "" ],
    "EVLIMITDC": [ 32, None, "Charge limit DC", "Limite ricarica DC", "", "", "", "", "", "" ],
    "EVCHARGEON": [ 33, None, "EV Charging", "In ricarica", "", "", "", "", "", "" ],
    "EVPWRCONS90DAYS": [ 34, None, "EV Power Cons.90d", "","EV verbruik 90d", "", "", "", "", "" ],
    "EVESTCHGDURATION": [ 35, None, "Est. Charge Duration", "", "oplaadduur", "", "", "", "", "" ],
    "EVTARGETCHGRANGE": [ 36, None, "Target Charge Range", "", "doelactieradius", "", "", "", "", "" ],
    "EVPWRREGEN90DAYS": [ 37, None, "EV Power Regen.90d", "","EV opwek 90d", "", "", "", "", "" ],
    "EVPWRCONSTOTAL": [ 38, None, "EV Power Consumed", "","EV verbruik", "", "", "", "", "" ],
    "EVPWRREGENTOTAL": [ 39, None, "EV Power Regenerated", "","EV opwek", "", "", "", "", "" ],
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
        self._name2vehicleId = {}
        self._getAddress = 1            # force device to get address associated to the current latitude/longitude
        self.vm = None
        self.verbose=True                  # if 1 => add extra debugging messages. Default: False
        self.firstRun=False

    def getVehicleId(self, Unit):
            # get name and id for the vehicle associated to Devices[Unit]
            vehicleId = False
            Domoticz.Status(f"Device Name={Devices[Unit].Name}")
            name=re.findall(f"{Parameters['Name']} - ([a-zA-Z0-9-_]+) .*", Devices[Unit].Name)[0]
            if self._name2vehicleId == {}:
                # call onHeartbeat to load vehicles data
                Domoticz.Status("_name2vehicleId is empty => call onHeartBeat to init vehicles data")
                self.checkDevices = True
                self._lastPoll = None
                self.onHeartbeat()

            if name in self._name2vehicleId:
                vehicleId=self._name2vehicleId[name]
                Domoticz.Status(f"name={name} vehicleId={vehicleId} Unit={Unit}")
            else:
                # vehicleId not found
                Domoticz.Status(f"Vehicle ID not found: there is not a vehicle named {name} in the Hyundai/Kia cloud")
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
        Domoticz.Status("Parameters="+str(Parameters))
        Domoticz.Debug("Settings="+str(Settings))
        Domoticz.Heartbeat(30)
        self._lang=Settings["Language"]
        # check if language set in domoticz exists
        if self._lang in LANGS:
            self._devlang=LANGBASE+LANGS.index(self._lang)
        else:
            Domoticz.Error(f"Language {self._lang} does not exist in dict DEVS, inside the domoticz_hyundai_kia plugin, but you can contribute adding it ;-) Thanks!")
            self._lang="en"
            self._devlang=LANGBASE # default: english text
        self._pollInterval = int(Parameters["Mode1"])
        self._pollIntervalDriving = int(Parameters["Mode2"])
        self.vm = VehicleManager(region=int(Parameters["Address"]), brand=int(Parameters["Port"]), username=Parameters["Username"], password=Parameters["Password"], pin=Parameters["Mode3"])
        self._lastPoll = None   # force reconnecting in 10 seconds 
        #self._lastPoll = datetime.now() # do not reconnect in 10 seconds, to avoid daily connection exceeding during testing #DEBUG 
        
        #logging.basicConfig(filename='/var/log/domoticz.log', encoding='utf-8', level=logging.INFO)
        #logging.basicConfig(filename='/var/log/domoticz.log', encoding='utf-8', level=logging.DEBUG) #DEBUG

    def onHeartbeat(self):
        """ Called every 10 seconds or other interval set by Domoticz.Heartbeat() """
        Domoticz.Debug("onHeartbeat()") 
        Domoticz.Log(f"Memory used by Domoticz: RSS={psutil.Process(os.getpid()).memory_info().rss / 1024}kB") #DEBUG
        self.firstRun=False
        if self._fetchingData == 0:
            #it's not fetching data from cloud
            if (self._setChargeLimits&15) != 0: #_setChargeLimits=0bzyxw0010  where if w is set => changed limits for vehicle with base=0, x=1 => vehicle with base=UNITMASK+1 (64), ....
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
                                Domoticz.Status(f"Set charge limits for device Unit={Unit}, AC={ac}, DC={dc}")
                                ret=self.vm.set_charge_limits(vehicleId, ac, dc)
                        bases>>=1
                        base+=UNITMASK+1   # is next base 
            elif self.mustPoll():   # check if vehicles data should be polled. return False if polling is already in progress 
                self._lastPoll = datetime.now()
                Domoticz.Status("*** check_and_refresh_token()...")
                #ret=self.vm.check_and_refresh_token()
                try:
                    self.vm.check_and_refresh_token()
                except AuthenticationError as AuthError:
                    Domoticz.Status(f"AuthError: {AuthError}")
                except:
                    Domoticz.Status(f"Unknown error")

                Domoticz.Status(f"*** check_and_force_update_vehicles({self.interval*30})...")
                #Domoticz.Status(f"*** force_refresh_all_vehicles_states()...")
                try:
                    #self.vm.check_and_force_update_vehicles(self.interval*30)  # get state from cloud if fresh (less than interval minutes), or automatically request a car upate
                    # whether it is time to get data is determine by the "mustPoll()" check above, no need to test again in the API
                    self.vm.force_refresh_all_vehicles_states()  # Get data from the cloud, new and existing. Note not all data is continuously updated in the cloud. 
                    self.vm.update_all_vehicles_with_cached_state() # Both these statements are needed to get data for all variables.
                except Exception:
                    Domoticz.Status(f"Exception")

                self._isCharging=False  # set to false: if one vehicle is charging, this flag will be set by updateDevices()
                self._engineOn=False    # set to false: if one vehicle is moving,   this flag will be set by updateDevices()
                # Now self.vm.vehicles contains a table with the list of registered vehicles and their parameters
                for k in self.vm.vehicles:
                    # k is the keyword associated to a Vehicle object
                    v = self.vm.get_vehicle(k)
                    name = re.sub(r'\W+', '', v.name)   # must be unique and identify the type of car, if more than 1 car is owned
                    if name not in self._name2vehicleId:
                        self._name2vehicleId[name]=k   # save the corresponding between vehicle name and id in vm.vehicles dict
                    if hasattr(v,'v.ev_battery_percentage') and v.ev_battery_percentage != None:
                        batterySOC=v.ev_battery_percentage
                    else: 
                        batterySOC=0
                        
                    Domoticz.Status(f"Name={name} Odometer={v._odometer_value}{v._odometer_unit} Battery={batterySOC}")
                    Domoticz.Status(f"Vehicle=")
                    # split v structure in more lines (too big to be printed in one line)
                    var=str(v)
                    for i in range(0,len(var),4096):
                        Domoticz.Status(var[i:i+4096])
                
                    # base = Unit base = 0, 64, 128, 192 # up to 4 vehicles can be addressed, 64 devices per vehicle (Unit <= 255)
                    # Find the right Unit for the current car
                    baseFree = 256
                    for base in range(0, 256-1, UNITMASK+1):
                        if base+(DEVS['ODOMETER'][0]) in Devices:
                            if name in Devices[base+(DEVS['ODOMETER'][0])].Name:   
                                # odometer exists: check that Domoticz device name correspond with vehicle name (set on Kia connect)
                                break
                        else:
                            if baseFree > base:
                                baseFree = base # free base where devices can be stored
                    Domoticz.Status(f"base={base} baseFree={baseFree}")

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
            Domoticz.Status(f"onHeartbeat: fetching data has been started since {self._fetchingData}0 seconds")
            if self._fetchingData > 10:
                # fetching started more than 100s ago!
                Domoticz.Status(f"onHeartbeat: fetching data has been started more than {self._fetchingData}0 seconds ago")


    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Status(f"onCommand(Unit={Unit}, Command={Command}, Level={Level}, Hue={Hue})")
        if (Unit&UNITMASK) == DEVS["UPDATE"][0]:  #force status update
            Devices[Unit].Update(nValue=1 if Command=="On" else 0, sValue=Command)
            if Command=="On":
                if self._fetchingData == 0:
                    Domoticz.Status("Force update command")
                    self._checkDevices = True
                    self._lastPoll = None
                    self.interval=1
                    self.onHeartbeat()
            else:
                #Update button has been switched OFF
                Domoticz.Status(f"UPDATE button has been switched OFF")
        else:
            vehicleId=self.getVehicleId(Unit) # get name and id for the vehicle
            if vehicleId==False:
                Domoticz.Status("vehicleId not found => ignore command")
                return  # vehicleId not found

            if (Unit&UNITMASK) == DEVS["CLIMAON"][0]:   # start/stop climate control
                if Command == "On":
                    options=ClimateRequestOptions()
                    options.set_temp=float(Devices[(Unit&(~UNITMASK))+DEVS["CLIMATEMP"][0]].sValue)
                    if options.set_temp<15:
                        options.set_temp=15
                    elif options.set_temp>27:
                        options.set_temp=27
                    options.climate=True if options.set_temp<23 else False
                    options.heating=True if options.set_temp>=23 else False
                    ret=self.vm.start_climate(vehicleId, options)
                    Domoticz.Status(f"start_climate() with options={options}. Returned {ret}")
                    Devices[Unit].Update(nValue=1, sValue="On")
                else:   # Off command
                    ret=self.vm.stop_climate(vehicleId)
                    Domoticz.Status(f"stop_climate() returned {ret}")
                    Devices[Unit].Update(nValue=0, sValue="Off")
            elif (Unit&UNITMASK) == DEVS["CLIMATEMP"][0]:   # air temperature
                airTemp=float(Level)
                if airTemp<15: 
                    airTemp=15
                elif airTemp>27: 
                    airTemp=27
                Devices[Unit].Update(nValue=0, sValue=str(airTemp))
            elif (Unit&UNITMASK) == DEVS["OPEN"][0]:   # open/close
                if Command == "On": # => lock
                    Domoticz.Status(f"lock command")
                    ret=self.vm.lock(vehicleId)
                    Devices[Unit].Update(nValue=1, sValue="On")
                else:   # Off command => unlock
                    Domoticz.Error(f"unlock command")
                    ret=self.vm.unlock(vehicleId)
                    Devices[Unit].Update(nValue=0, sValue="Off")
            elif (Unit&UNITMASK) == DEVS["EVLIMITAC"][0] or (Unit&UNITMASK) == DEVS["EVLIMITDC"][0]:
                # Battery limit was changed: send new value to the car
                self._setChargeLimits=1  # set charge limits after 2*HeartBeat 
                self._setChargeLimits|=16<<(Unit>>6)    #store in setChargeLimits which devices have been changed 0bzyxw0010 where w=1 if base=0, x=1 if base=64, y=1 if base=128, ...
                Level=Level-Level%10    # Level should be 0, 10, 20, 30, ...
                Domoticz.Status(f"New value={Level}")
                Devices[Unit].Update(nValue=1, sValue=str(Level))
            elif (Unit&UNITMASK) == DEVS["EVCHARGEON"][0]:    # Start or stop charging
                if Command == "On":
                    Domoticz.Status(f"Received command to start charging")
                    Devices[Unit].Update(nValue=1, sValue="On")
                    ret=self.vm.start_charge(vehicleId)
                else:
                    Domoticz.Status(f"Received command to stop charging")
                    Devices[Unit].Update(nValue=0, sValue="Off")
                    ret=self.vm.stop_charge(vehicleId)

    def addDevices(self, base, name, v):
        """ Add devices for car named {name}, starting from base unit {base}, using vehicle parameters in {v} """
        Domoticz.Status(f"Add devices for car {name} with base index {base}")

        k='EVSTATE'; dev=DEVS[k]
        if hasattr(v,'ev_battery_is_charging'):
            dev[1]='ev_battery_is_charging'
        if dev[1]!=None: 
            var=getattr(v, dev[1], None)
            if var != None and base+dev[0] not in Devices: 
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=19, Used=1).Create()

                k='EVCHARGEON'; dev=DEVS[k]
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        k='EVBATTLEVEL'; dev=DEVS[k]
        if hasattr(v,'ev_battery_percentage'):
            dev[1] = 'ev_battery_percentage'
            var=getattr(v, dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=6, Used=1).Create()

        k='EVRANGE'; dev=DEVS[k]
        if hasattr(v,'_ev_driving_range'):
            dev[1]='_ev_driving_range'
        elif hasattr(v,'ev_driving_distance'):  #older name
            dev[1]='ev_driving_distance'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            # now check for unit of measure
            var2='km'
            if hasattr(v, '_ev_driving_range_unit'):
                var2=v._ev_driving_range_unit
            elif hasattr(v, '_ev_driving_distance_unit'):
                var2=v._ev_driving_distance_unit
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Options={'Custom': '1;'+var2}, Used=1).Create()

        k='EVLIMITAC'; dev=DEVS[k]
        if hasattr(v,'ev_charge_limits_ac'):
            dev[1]='ev_charge_limits_ac'
        elif hasattr(v,'_ev_charge_limits.ac'):
            dev[1]='ev_charge_limits.ac'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=62, Switchtype=7, Used=1).Create()

        k='EVLIMITDC'; dev=DEVS[k]
        if hasattr(v, 'ev_charge_limits_dc'):
            dev[1]='ev_charge_limits_dc'
        elif hasattr(v, '_ev_charge_limits.dc'):
            dev[1]='_ev_charge_limits.dc'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=62, Switchtype=7, Used=1).Create()

        k='FUELLEVEL'; dev=DEVS[k]
        if hasattr(v, 'fuel_level'):
            dev[1]='fuel_level'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=6, Used=1).Create()

        k='FUELRANGE'; dev=DEVS[k]
        if hasattr(v, '_fuel_driving_range'):
            dev[1]='_fuel_driving_range'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Options={'Custom': '1;'+v._fuel_driving_range_unit}, Used=1).Create()

        k='ENGINEON'; dev=DEVS[k]
        if hasattr(v, 'engine_is_running'):
            dev[1] =  'engine_is_running'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        k='ODOMETER'; dev=DEVS[k]
        if hasattr(v, 'odometer'):
            dev[1] =  'odometer'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=113, Subtype=0, Switchtype=3, Used=1).Create()


        k='LOCATION'; dev=DEVS[k]
        if hasattr(v, 'location_latitude'):
            dev[1] =  'location_latitude'
        elif hasattr(v, '_location_latitude'):
            dev[1] = '_location_latitude'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=19, Used=1).Create()
                dev=DEVS['HOMEDIST']
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Used=1).Create()

        k='SPEED'; dev=DEVS[k]
        if hasattr(v, 'data'):
            dev[1] =  'data'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Used=1).Create()
            
        dev=DEVS['UPDATE']
        if base+dev[0] not in Devices:
            Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create() 

        k='CLIMAON'; dev=DEVS[k]
        if hasattr(v, 'air_control_is_on'):
            dev[1] =  'air_control_is_on'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        k='CLIMATEMP'; dev=DEVS[k]
        if hasattr(v, '_air_temperature'):
            dev[1] =  '_air_temperature'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=242, Subtype=1, Used=1).Create()

        k='DEFROSTON'; dev=DEVS[k]
        if hasattr(v, 'defrost_is_on'):
            dev[1] =  'defrost_is_on'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        k='REARWINDOWON'; dev=DEVS[k]
        if hasattr(v, 'back_window_heater_is_on'):
            dev[1] =  'back_window_heater_is_on'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        k='STEERINGWHEELON'; dev=DEVS[k]
        if hasattr(v, 'steering_wheel_heater_is_on'):
            dev[1] =  'steering_wheel_heater_is_on'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        k='SIDEMIRRORSON'; dev=DEVS[k]
        if hasattr(v, 'side_mirror_heater_is_on'):
            dev[1] =  'side_mirror_heater_is_on'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Used=1).Create()

        k='SEATFL'; dev=DEVS[k]
        if hasattr(v, 'front_left_seat_status'):
            dev[1] =  'front_left_seat_status'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=19, Used=1).Create()

        k='SEATFR'; dev=DEVS[k]
        if hasattr(v, 'front_right_seat_status'):
            dev[1] =  'front_right_seat_status'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=19, Used=1).Create()

        k='SEATRL'; dev=DEVS[k]
        if hasattr(v, 'rear_left_seat_status'):
            dev[1] =  'rear_left_seat_status'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=19, Used=1).Create()

        k='SEATRR'; dev=DEVS[k]
        if hasattr(v, 'rear_right_seat_status'):
            dev[1] =  'rear_right_seat_status'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=19, Used=1).Create()

        k='OPEN'; dev=DEVS[k]
        if hasattr(v, 'is_locked'):
            dev[1] =  'is_locked'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Switchtype=19, Used=1).Create()

        k='TRUNK'; dev=DEVS[k]
        if hasattr(v, 'trunk_is_open'):
            dev[1] =  'trunk_is_open'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Switchtype=11, Used=1).Create()

        k='HOOD'; dev=DEVS[k]
        if hasattr(v, 'hood_is_open'):
            dev[1] =  'hood_is_open'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=244, Subtype=73, Switchtype=11, Used=1).Create()

        k='12VBATT'; dev=DEVS[k]
        if hasattr(v, 'car_battery_percentage'):
            dev[1] =  'car_battery_percentage'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=6, Used=1).Create()

        k='KEYBATT'; dev=DEVS[k]
        if hasattr(v, 'smart_key_battery_warning_is_on'):
            dev[1] =  'smart_key_battery_warning_is_on'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=22, Used=1).Create()

        k='WASHER'; dev=DEVS[k]
        if hasattr(v, 'washer_fluid_warning_is_on'):
            dev[1] =  'washer_fluid_warning_is_on'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=22, Used=1).Create()

        k='BRAKE'; dev=DEVS[k]
        if hasattr(v, 'brake_fluid_warning_is_on'):
            dev[1] =  'brake_fluid_warning_is_on'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=22, Used=1).Create()

        k='TIRES'; dev=DEVS[k]
        if hasattr(v, 'tire_pressure_all_warning_is_on'):
            dev[1] =  'tire_pressure_all_warning_is_on'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=22, Used=1).Create()

        k='EVPWRCONS90DAYS'; dev=DEVS[k]
        # note the total power provided by hyundai/kia cloud is actually the total for 90 days
        if hasattr(v, 'total_power_consumed'):
            dev[1] =  'total_power_consumed'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=113, Subtype=0, Switchtype=0, Used=1).Create()

        k='EVESTCHGDURATION'; dev=DEVS[k]
        if hasattr(v, '_ev_estimated_current_charge_duration'):
            dev[1]= '_ev_estimated_current_charge_duration'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Options={'Custom': '1;'+v._ev_estimated_current_charge_duration_unit}, Used=1).Create()

        k='EVTARGETCHGRANGE'; dev=DEVS[k]
        if hasattr(v, '_ev_target_range_charge_AC'):
            dev[1]= '_ev_target_range_charge_AC'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=31, Options={'Custom': '1;'+v._ev_target_range_charge_AC_unit}, Used=1).Create()


        k='EVPWRREGEN90DAYS'; dev=DEVS[k]
        # note the total power provided by hyundai/kia cloud is actually the total for 90 days
        if hasattr(v, 'total_power_regenerated'):
            dev[1] =  'total_power_regenerated'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=113, Subtype=0, Switchtype=0, Used=1).Create()

        k='EVPWRCONSTOTAL'; dev=DEVS[k]
        # the all time total power consumed will be tracked using daily stats values from the cloud onto an incremental counter      
        if hasattr(v, 'daily_stats'):
            dev[1] = 'daily_stats'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                self.firstRun=True
                Domoticz.Status(f"creating device {k}")
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=28, Switchtype=0, Used=1).Create()
                Devices[base+dev[0]].Update(nValue=0, sValue=str(0))

        k='EVPWRREGENTOTAL'; dev=DEVS[k]
        # the all time total power regenerated will be tracked using daily stats values from the cloud onto an incremental counter      
        if hasattr(v, 'daily_stats'):
            dev[1] = 'daily_stats'
        if dev[1]!=None:
            var=getattr(v,dev[1], None)
            if var != None and base+dev[0] not in Devices:
                self.firstRun=True
                Domoticz.Status(f"creating device {k}")
                Domoticz.Device(Unit=base+dev[0], Name=f"{name} {dev[self._devlang] or dev[LANGBASE]}", Type=243, Subtype=28, Switchtype=0, Used=1).Create()
                Devices[base+dev[0]].Update(nValue=0, sValue=str(0))
    

    def updateDevices(self, base, name, v):
        """ Update devices for car named {name}, starting from base unit {base}, using vehicle parameters in {v} """
        Domoticz.Status(f"Car found at base {base}")

        k='EVSTATE'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        var2=getattr(v, 'ev_battery_is_plugged_in', 0)
        if var != None:
            nValue=0
            sValue="Disconnected"
            if var == True:
                nValue=1
                sValue="Charging"
                self._isCharging=True
            elif var2>0:
                nValue=1
                sValue="Connected"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            if self._isCharging == True:
                Devices[base+DEVS['EVCHARGEON'][0]].Update(nValue=1, sValue="On")
            else:
                Devices[base+DEVS['EVCHARGEON'][0]].Update(nValue=0, sValue="Off")
        
        batteryLevel=None   # show batteryLevel in the debug messages
        k='EVBATTLEVEL'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            nValue=var
            batteryLevel=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            Devices[base+dev[0]].Update(nValue=nValue, sValue=str(nValue))
        
        k='EVRANGE'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            nValue=int(var)
            if self.verbose: Domoticz.Status(f"{k}={var}")
            Devices[base+dev[0]].Update(nValue=nValue, sValue=str(nValue))
            
        k='EVLIMITAC'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            Devices[base+dev[0]].Update(nValue=1, sValue=str(nValue))
            
        k='EVLIMITDC'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            Devices[base+dev[0]].Update(nValue=1, sValue=str(nValue))
            
        k='FUELLEVEL'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            Devices[base+dev[0]].Update(nValue=nValue, sValue=str(nValue))
            
        k='FUELRANGE'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            nValue=int(var)
            if self.verbose: Domoticz.Status(f"{k}={var}")
            Devices[base+dev[0]].Update(nValue=nValue, sValue=str(nValue))
            
        k='ENGINEON'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            value=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=0; sValue="Off"
            if (value):
                nValue=1; sValue="On"
                self._engineOn=True
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='ODOMETER'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None and var != 0:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=int(nValue)
            Devices[base+dev[0]].Update(nValue=nValue, sValue=str(nValue))


        # get coordinates and compute distance    
        lat=None
        lon=None
        if hasattr(v,'location_latitude'):
            lat=getattr(v, 'location_latitude')
        elif hasattr(v,'_location_latitude'):
            lat=getattr(v, '_location_latitude')
        if hasattr(v,'location_longitude'):
            lon=getattr(v, 'location_longitude')
        elif hasattr(v,'_location_longitude'):
            lon=getattr(v, '_location_longitude')

        if lat!=None and lon!=None:
            if name not in self._vehicleLoc:
                #initialize vehicleLoc
                self._vehicleLoc[name]={'latitude': lat, 'longitude': lon+0.000001} # initialize variable but force a minimum variation to compute the real position

            if self._getAddress==1 or lat!=self._vehicleLoc[name]['latitude'] or lon!=self._vehicleLoc[name]['longitude']:
                # LOCATION changed or not previously set
                # get address
                if self.verbose: Domoticz.Status(f"Latitude or Longitude have changed")
                get_address_url = 'https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=16&lat=' + str(lat) + '&lon=' + str(lon)
                response = requests.get(get_address_url)
                if response.status_code == 200:
                    response = json.loads(response.text)
                    locAddr=response['display_name']
                    Domoticz.Status(f"Location address: {locAddr}")
                else:
                    Domoticz.Error(f"Trying to get address, but got response_code {response.status_code}")
                    self._getAddress=1 # retry to get address again
                    locAddr='Unknown'
                locMap = f"<a href=\"http://www.google.com/maps/search/?api=1&query={lat},{lon}\" target=\"_new\"><em style=\"color:blue;\">Map</em></a>"
                sValue=fill(locAddr, 40) + ' ' + locMap
                Devices[base+DEVS['LOCATION'][0]].Update(nValue=0, sValue=sValue)
                self._getAddress=0 # Address get successfully: update it only in case that location changes.
                # HOME DISTANCE: compute distance from home
                homeloc=Settings['Location'].split(';')
                distance=round(self.distance(lat, lon, float(homeloc[0]), float(homeloc[1])), 1)
                Devices[base+DEVS['HOMEDIST'][0]].Update(nValue=0, sValue=str(distance))

                if hasattr(v,'data'):
                    value=v.data
                    if value != None:
                        nValue=value['vehicleLocation']['speed']['value']
                        sValue=str(nValue)
                        Devices[base+DEVS['SPEED'][0]].Update(nValue=nValue, sValue=sValue)
                        Domoticz.Status(f"Vehicle {name} has odometer={v.odometer} speed={nValue} distance_from_home={distance} EV battery={batteryLevel}%")

                self._vehicleLoc[name]['latitude']=lat
                self._vehicleLoc[name]['longitude']=lon
            else:
                if self.verbose: Domoticz.Status(f"Latitude or Longitude NOT changed: lat={lat}, lon={lon}")
        else: 
            if self.verbose: Domoticz.Status(f"Latitude or Longitude NOT found")

        k='CLIMAON'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            value=var
            nValue=1 if value else 0
            sValue="On" if value else "Off"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)

        k='CLIMATEMP'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            nValue=float(var)
            if self.verbose: Domoticz.Status(f"{k}={var}")
            Devices[base+dev[0]].Update(nValue=0, sValue=str(nValue))
            
        k='DEFROSTON'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="On" if var else "Off"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='REARWINDOWON'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="On" if var>0 else "Off"
            Devices[base+DEVS['REARWINDOWON'][0]].Update(nValue=nValue, sValue=sValue)
            
        k='STEERINGWHEELON'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="On" if var>0 else "Off"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)

        k='SIDEMIRRORSON'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="On" if var else "Off"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='SEATFL'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            sValue=var
            Devices[base+dev[0]].Update(nValue=0, sValue=sValue)
            
        k='SEATFR'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            sValue=var
            Devices[base+dev[0]].Update(nValue=0, sValue=sValue)
            
        k='SEATRL'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            sValue=var
            Devices[base+dev[0]].Update(nValue=0, sValue=sValue)
           
        k='SEATRR'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            sValue=var
            Devices[base+dev[0]].Update(nValue=0, sValue=sValue)
            
        k='OPEN'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="Unlocked" if var else "Locked"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='TRUNK'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="Open" if var else "Closed"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='HOOD'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="Open" if var else "Closed"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='12VBATT'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue=str(nValue)
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='KEYBATT'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="Ok" if nValue == 0 else "Low"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='WASHER'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="Ok" if nValue == 0 else "Empty"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='BRAKE'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="Ok" if nValue == 0 else "Empty"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)
            
        k='TIRES'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="Ok" if nValue == 0 else "Low"
            Devices[base+dev[0]].Update(nValue=nValue, sValue=sValue)

        k='EVPWRCONS90DAYS'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None and var != 0:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=int(nValue)
            Devices[base+dev[0]].Update(nValue=nValue, sValue=str(nValue))

        k='EVESTCHGDURATION'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            nValue=int(var)
            if self.verbose: Domoticz.Status(f"{k}={var}")
            Devices[base+dev[0]].Update(nValue=nValue, sValue=str(nValue))

        k='EVTARGETCHGRANGE'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None:
            nValue=int(var)
            if self.verbose: Domoticz.Status(f"{k}={var}")
            Devices[base+dev[0]].Update(nValue=nValue, sValue=str(nValue))

        k='EVPWRREGEN90DAYS'; dev=DEVS[k]; var=getattr(v, dev[1], None)
        if var != None and var != 0:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=int(nValue)
            Devices[base+dev[0]].Update(nValue=nValue, sValue=str(nValue))

        if hasattr(v, 'daily_stats') and self.firstRun==False:
            var=getattr(v,'daily_stats',None)
            todayPwrConsumed=0
            todayPwrRegenerated=0
            today=date.today()
            todayString=datetime.strftime(today,'%Y-%m-%d 00:00:00')
            for day in range(len(var)):
                # normally the first record is the last day with pwr consumption, but looping through the list anyway to be sure
                dailystat=var[day]
                statDay=getattr(dailystat,'date',None)
                statConsumed=getattr(dailystat,'total_consumed',None)
                statRegenerated=getattr(dailystat,'regenerated_energy',None)
                if str(statDay)==todayString:
                    Domoticz.Status(f"copying today's values")
                    Domoticz.Status(f"today {todayString} date {statDay}")
                    Domoticz.Status(f"consumed {statConsumed}")
                    Domoticz.Status(f"regenerated {statRegenerated}")
                    todayPwrConsumed+=statConsumed
                    todayPwrRegenerated+=statRegenerated

            if todayPwrConsumed>0:
                k='EVPWRCONSTOTAL'; dev=DEVS[k]
                TotalPwrConsID=Devices[base+dev[0]].ID
                result,Counter,CounterToday=getCounter(TotalPwrConsID)
                if result:
                    incrementValue=todayPwrConsumed-CounterToday
                    Domoticz.Status(f"PwrConsumed Counter {Counter} counterToday {CounterToday} daily stat {todayPwrConsumed} Increment {incrementValue}") 
                    Devices[base+dev[0]].Update(nValue=0, sValue=str(incrementValue))
                else:
                    Domoticz.Error(f"Counter Check of device {k} failed. Postponing update till next time")

            if todayPwrRegenerated>0:
                k='EVPWRREGENTOTAL'; dev=DEVS[k]
                TotalPwrRegenID=Devices[base+dev[0]].ID
                result,Counter,CounterToday=getCounter(TotalPwrRegenID)
                if result:
                    incrementValue=todayPwrRegenerated-CounterToday
                    Domoticz.Status(f"PwrRegenerated Counter {Counter} counterToday {CounterToday} daily stat {todayPwrRegenerated} Increment {incrementValue}")
                    Devices[base+dev[0]].Update(nValue=0, sValue=str(incrementValue))
                else:
                    Domoticz.Error(f"Counter Check of device {k} failed. Postponing update till next time")
        else:
            if self.firstRun==True:
                Domoticz.Status(f"Not updating new PWR devices on first run with today's values")



        if self.verbose: Domoticz.Status(f"updateDevices() completed!")
        # Reset force update button
        Devices[base+DEVS['UPDATE'][0]].Update(nValue=0, sValue="Off")
        

    def distance(self, lat1, lon1, lat2, lon2):
        """ Compute the distance between two locations """
        p = pi / 180
        a = 0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
        return 12742 * asin(sqrt(a))

    def onTimeout(self, Connection):    #DEBUG
        Domoticz.Status(f"onTimeout({Connection})")
        

def getCounter(varIDX):
    # function to get the Counter and Countertoday value of a counter device indicated by the varIDX number
    try:
        responseResult=False
        apiCall="http://"+DomoticzIP+":"+DomoticzPort+"/json.htm?type=command&param=getdevices&rid="+str(varIDX)
        response = requests.get(apiCall)
        responseResult=str(response.json()["status"])
        if responseResult=="ERR":
            raise Exception
        else:
            divider=response.json()["result"][0]["Divider"]
            counterValue=int(divider*float(str(response.json()["result"][0]["Counter"]).split()[0]))
            counterTodayValue=int(divider*float(str(response.json()["result"][0]["CounterToday"]).split()[0]))
            responseResult=True
    except:
        Domoticz.Error(f"ERROR: unable to retrieve the value of device with IDX {varIDX} {response}")
        responseResult=False
        counterValue=None
        counterTodayValue=None
    return responseResult,counterValue,counterTodayValue


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
