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
<plugin key="domoticz-hyundai-kia" name="Hyundai Kia connect" author="CreasolTech, WillemD61" version="2.1" externallink="https://github.com/CreasolTech/domoticz-hyundai-kia">
    <description>
        <h2>Domoticz Hyundai Kia connect plugin - 2.1</h2>
        This plugin permits to access, through the Hyundai Kia account credentials, to information about your Hyundai and Kia vehicles, such as odometer, EV battery charge, 
        tires status, door lock status, and much more.<br/>
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

import DomoticzEx as Domoticz
import json
import re
#import logging
from math import cos, asin, sqrt, pi
import time
import requests
from datetime import date,datetime
from textwrap import fill
from hyundai_kia_connect_api import *
from hyundai_kia_connect_api.exceptions import *

DomoticzIP="127.0.0.1"
DomoticzPort="8080"

LANGS=[ "en", "it", "nl", "se", "hu", "pl", "fr" ] # list of supported languages, in DEVS dict below
LANGBASE=5  # item in the DEVS list where the first language starts 

UNITMASK=63 # Unit for each car starts from 1, 65, 129, 193 (max 4 vehicles)

#Dutch translation by Branko
#Swedish translation by Joakim W.
#Hungarian translation by Upo
#Polish translation by z1mEk
#French translation by Neutrino
#German translation by Gerhard M.
#If you want to add another language, please add, for each line:     , "your translation"
DEVS={ #topic:      [ unit, Type, Subtype, Switchtype, "en name", "it name", "nl name", "se name", "hu name", "pl name", "fr name", "de_name"  ...other languages should follow  ],
    "EVSTATE":      [ 1, 243, 19, 0, {}, "EV state", "EV stato", "EV status", "EV status", "EV státusz", "EV staus", "Status VE", "EV Status" ],
    "EVBATTLEVEL":  [ 2, 243, 6, 0, {}, "EV battery level", "EV livello batteria", "batterijniveau", "EV batterinivå", "EV akku töltöttség", "EV poziom baterii", "Niveau de batterie", "EV Batterieladestand"],
    "EVRANGE":      [ 3, 243, 31, 0, {'Custom': '1;km'}, "EV range", "EV autonomia", "EV bereik" , "EV räckvidd", "EV hatótáv", "EV zasięg", "Autonomie VE", "EV Reichweite" ],
    "FUELLEVEL":    [ 4, 243, 6, 0, {}, "fuel level", "livello carburante", "brandstofniveau", "bränslenivå" , "üzemanyagszint", "poziom paliwa" ,"Niveau de carburant", "EV Ladestand"],
    "FUELRANGE":    [ 5, 243, 31, 0, {'Custom': '1;km'}, "fuel range", "autonomia carburante", "brandstof bereik", "bränsleräckvidd" , "üzemanyag hatótáv", "zasięg paliwa", "Autonomie Carburant", "Reichweite" ],
    "ENGINEON":     [ 6, 244, 73, 0, {}, "engine ON", "motore acceso", "motor aan", "motor på", "motor be", "silnik włączony" ,"Moteur démarré", "Motor ein"],
    "ODOMETER":     [ 7, 113, 0, 3, {}, "odometer", "contachilometri", "kilometerteller", "odometer" , "kilométer-számláló", "licznik kilometrów" , "Compteur", "Kilometerstand" ],
    "LOCATION":     [ 8, 243, 19, 0, {}, "location", "posizione", "locatie", "plats", "hely", "pozycja", "Position", "Position" ],
    "HOMEDIST":     [ 9, 243, 31, 0, {}, "distance", "distanza", "afstand", "avstånd", "távolság", "dystans" ,"distance", "Distanz"],
    "SPEED":        [ 10, 243, 31, 0, {}, "speed", "velocità", "snelheid", "hastighet", "sebesség", "prędkość" , "vitesse", "Geschwindigkeit"],
    "UPDATE":       [ 11, 244, 73, 0, {}, "update req.", "aggiorna", "bijwerken", "uppdatering", "frissítés", "aktualizacja" , "Mise à jour", "Update notwendig" ],
    "TEMPSET":      [ 12, 0, 0, 0, {}, "NOT USEDtemp. settings", "imp. temperatura", "temperatuur inst.", "temperatur", "hőmérséklet beállítás", "ustawienie temperatury", "Réglage temp.", "Temperatureinstellungen"],
    "CLIMAON":      [ 13, 244, 73, 0, {}, "climate control", "clima acceso", "airco", "klimat", "klíma", "klimatyzacja","Climatisation", "Klima" ],
    "DEFROSTON":    [ 14, 244, 73, 0, {}, "defrost", "scongelamento", "ontdooien", "defrost", "páramentesítő", "rozmrożenie" ,"Dégivrage", "Defrostung"],
    "REARWINDOWON": [ 15, 244, 73, 0, {}, "rear window heater", "lunotto termico", "achterruitverwarming", "bakrutevärme", "hátsó ablak", "tylne okno" ,"Dégivrage arrière", "Fenster hinten"],
    "STEERINGWHEELON": [ 16, 244, 73, 0, {}, "steering wheel heater", "volante termico", "stuurverwarming", "rattvärme", "kormány", "kierownica" ,"Volant Chauffant", "Lenkrad"],
    "SIDEMIRRORSON":[ 17, 244, 73, 0, {}, "side mirrors heater", "specchietti termici", "zijspiegel verwarming", "sidospeglar", "oldalsó tükrök", "lusterka boczne" , "Dégivrage rétroviseur", "Seitenspiegel" ],
    "SEATFL":       [ 18, 243, 19, 0, {}, "seat front-left", "sedile guidatore", "bestuurdersstoel", "förarstol", "bal első ülés", "siedzenie przednie lewe" ,"Siège conducteur", "Sitz vorne links"],
    "SEATFR":       [ 19, 243, 19, 0, {}, "seat front-right", "sedile passeggero", "bijrijdersstoel", "passagerarstol", "jobb első ülés", "siedzenie przednie prawe" ,"Siège passager", "Sitz vorne rechts"],
    "SEATRL":       [ 20, 243, 19, 0, {}, "seat rear-left", "sedile post.sx", "achterbank links", "baksäte vänster", "bal hátsó ülés", "siedzenie tylne lewe", "Siège arrière conducteur", "Sitz hinten links" ],
    "SEATRR":       [ 21, 243, 19, 0, {}, "seat rear-right", "sedile post.dx", "achterbank rechts", "baksäte höger", "jobb hátsó ülés", "siedzenie tylne prawe", "Siège arrière passager", "Sitz hinten rechts" ],
    "OPEN":         [ 22, 244, 73, 0, {}, "open", "aperta", "open", "öppen", "nyitva", "otwarte", "ouvrir", "offen" ],
    "TRUNK":        [ 23, 244, 73, 0, {}, "trunk open", "bagagliaio aperto", "kofferbak", "bagagelucka", "casomagtér nyitva", "bagażnik otwarty" , "coffre ouvert", "Kofferraum offen"],
    "HOOD":         [ 24, 244, 73, 0, {}, "hood open", "cofano aperto", "motorkap", "motorhuv", "motorháztető nyitva", "pokrywa silnika otwarta" , "capot ouvert", "Motorhaube offen" ],
    "12VBATT":      [ 25, 243, 6, 0, {}, "12V battery", "batteria 12V", "12V batterij", "batteri 12V", "12V akku", "akumulator 12V" , "Batterie 12V", "12V Batterie"],
    "KEYBATT":      [ 26, 243, 22, 0, {}, "key battery", "batteria radiocomando", "batterij afstandsbediening", "nyckelbatteri", "kulcs elem", "bateria kluczyka", "Pile clé", "Schlüsselbatterie" ],
    "WASHER":       [ 27, 243, 22, 0, {}, "washer fluid", "liquido tergicristallo", "ruitensproeiervloeistof", "spolarvätska", "ablakmosó", "płyn spryskiwaczy", "lave-glace", "Schweibenwischwasser" ],
    "BRAKE":        [ 28, 243, 22, 0, {}, "brake fluid", "olio freni", "rem", "bromsvätska", "fékfolyadék", "płyn hamulcowy", "liquide de frein", "Bremsflüssigkeit" ],
    "TIRES":        [ 29, 243, 22, 0, {}, "tires pressure", "pressione gomme", "bandenspanning", "däcktryck", "guminyomás", "ciśnienie w oponie", "pression pneus", "Reifenluftdruck" ],
    "CLIMATEMP":    [ 30, 242, 1, 0, {'ValueStep':'0.5', 'ValueMin':'15', 'ValueMax':'27', 'ValueUnit':'°C'}, "climate temperature", "temperatura clima", "airco temperatuur", "klimattemperatur", "klíma hőfok", "temperatura klimatyzacji", "Température clim", "Klimatemperatur" ],
    "EVLIMITAC": [ 31, 244, 62, 7, {}, "Charge limit AC", "Limite ricarica AC", "", "", "", "", "", "" ],
    "EVLIMITDC": [ 32, 244, 62, 7, {}, "Charge limit DC", "Limite ricarica DC", "", "", "", "", "", "" ],
    "EVCHARGEON": [ 33, 244, 73, 0, {}, "EV Charging", "In ricarica", "", "", "", "", "", "" ],
    "EVENERGYCONS90DAYS": [ 34, 113, 0, 0, {}, "EV energy in 90d", "energia consumata in 90gg","EV verbruik 90d", "", "", "", "", "" ],
    "EVESTCHGDURATION": [ 35, 243, 31, 0, {'Custom': '1;min'}, "estimated charge duration", "tempo ricarica stimata", "oplaadduur", "", "", "", "", "" ],
    "EVTARGETCHGRANGE": [ 36, 243, 31, 0, {'Custom': '1;km'}, "Target Charge Range", "autonomia finale", "doelactieradius", "", "", "", "", "" ],
    "EVENERGYREGEN90DAYS": [ 37, 113, 0, 4, {}, "EV energy Regen.90d", "energia rigenerata 90gg","EV opwek 90d", "", "", "", "", "" ],
    "EVENERGYCONSTOTAL": [ 38, 243, 28, 0, {}, "EV energy Consumed", "energia consumata","EV verbruik", "", "", "", "", "" ],
    "EVENERGYREGENTOTAL": [ 39, 243, 28, 4, {}, "EV energy Regenerated", "energia rigenerata","EV opwek", "", "", "", "", "" ],
}

#DEVLIST used to convert from unit to DEVS keyword (DEVS[DEVLIST[Unit&UNITMASK]])
DEVLIST=[None, 'EVSTATE', 'EVBATTLEVEL', 'EVRANGE', 'FUELLEVEL', 'FUELRANGE', 'ENGINEON', 'ODOMETER', 'LOCATION', 'HOMEDIST', 'SPEED', 'UPDATE', 'TEMPSET', 'CLIMAON', 'DEFROSTON', 'REARWINDOWON', 'STEERINGWHEELON', 'SIDEMIRRORSON', 'SEATFL', 'SEATFR', 'SEATRL', 'SEATRR', 'OPEN', 'TRUNK', 'HOOD', '12VBATT', 'KEYBATT', 'WASHER', 'BRAKE', 'TIRES', 'CLIMATEMP', 'EVLIMITAC', 'EVLIMITDC', 'EVCHARGEON', 'EVENERGYCONS90DAYS', 'EVESTCHGDURATION', 'EVTARGETCHGRANGE', 'EVENERGYREGEN90DAYS', 'EVENERGYCONSTOTAL', 'EVENERGYREGENTOTAL']

class BasePlugin:
    """ Base class for the plugin """

    def __init__(self):
        self._pollInterval = 120        # fetch data every 120 minutes, by default (but check parameter Mode1!)
        self._pollIntervalDriving = 30 # while charging, fetch data quickly 
        self.interval = 10              # current polling interval (depending by charging, moving, night time, ...) It's set by mustPoll()
        self._lastPoll = None           # last time I got vehicle status
        self._setChargeLimits = 0       # if > 0 => decrement every HeartBeat interval, and when zero set the charging limit
        self._fetchingData = 0          # 0 if system is not fetching data from cloud, >0 if it's fetching (incremented every onHeartBeat)
        self._isCharging = False  
        self._engineOn = False
        self._lang = "en"
        self._vehicleLoc = {}           # saved location for vehicles
        self._name2vehicleId = {}
        self.vehileName = ""            # Name for each vehicle, used by updateDevices() and update()
        self._getAddress = 1            # force device to get address associated to the current latitude/longitude
        self.vm = None
        self.verbose=True                  # if 1 => add extra debugging messages. Default: False
        self.firstRun=False
        self.hwid=0
        self.devID=""

    def getDevID(self, Unit):
        self.devID="{:04X}{:04X}".format(self.hwid, Unit)    # DeviceID compatible with previous plugin version

    def getVehicleId(self, Unit):
            # get name and id for the vehicle associated to Devices[Unit]
            vehicleId = False
            self.getDevID(Unit)
            Domoticz.Status(f"Device Name={Devices[self.devID].Units[Unit].Name}")
            self.vehicleName=re.findall(f"([a-zA-Z0-9-_]+): .*", Devices[self.devID].Units[Unit].Name)[0]
            if self._name2vehicleId == {}:
                # call onHeartbeat to load vehicles data
                Domoticz.Status("_name2vehicleId is empty => call onHeartBeat to init vehicles data")
                self._lastPoll = None
                self.onHeartbeat()

            if self.vehicleName in self._name2vehicleId:
                vehicleId=self._name2vehicleId[self.vehicleName]
                Domoticz.Status(f"name={self.vehicleName} vehicleId={vehicleId} Unit={Unit}")
            else:
                # vehicleId not found
                Domoticz.Status(f"Vehicle ID not found: there is not a vehicle named {self.vehicleName} in the Hyundai/Kia cloud")
            return vehicleId

    def update(self, Unit, nValue, sValue):
        """ update device with DeviceID=self.devID, Unit=Unit, nValue=nValue, sValue=sValue """
        #Domoticz.Status(f"Update({Unit}, {nValue}, {sValue}) devID={self.devID}") 
        if Unit>=256:
            Domoticz.Error(f"No enough space to store new devices: max 4 vehicles!")
            return
        if (self.devID not in Devices) or (Unit not in Devices[self.devID].Units):
            dev=DEVS[DEVLIST[Unit&UNITMASK]]
            Domoticz.Status(f"Creating device {dev[0]} {dev[LANGBASE]}...")
            Domoticz.Unit(DeviceID=self.devID, Unit=Unit, Name=f"{self.vehicleName}: {dev[self._devlang] or dev[LANGBASE]}", Type=dev[1], Subtype=dev[2], Switchtype=dev[3], Options=dev[4], Used=1).Create()

        Devices[self.devID].Units[Unit].nValue=int(nValue)
        Devices[self.devID].Units[Unit].sValue=str(sValue)
        Devices[self.devID].Units[Unit].Update()

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
        #Domoticz.Status("Parameters="+str(Parameters))
        #Domoticz.Debug("Settings="+str(Settings))
        Domoticz.Status("onStart()")
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
        self.hwid=Parameters['HardwareID']

        #logging.basicConfig(filename='/var/log/domoticz.log', encoding='utf-8', level=logging.INFO)
        #logging.basicConfig(filename='/var/log/domoticz.log', encoding='utf-8', level=logging.DEBUG) #DEBUG

    def onHeartbeat(self):
        """ Called every 10 seconds or other interval set by Domoticz.Heartbeat() """
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
                            self.getDevID(Unit)
                            vehicleId=self.getVehicleId(Unit) # get name and id for the vehicle
                            if vehicleId!=False:
                                ac=int(Devices[self.devID].Units[Unit].sValue)
                                self.getDevID(Unit+1)
                                dc=int(Devices[self.devID].Units[Unit+1].sValue)
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
                    self.vehicleName = re.sub(r'\W+', '', v.name)   # must be unique and identify the type of car, if more than 1 car is owned
                    if self.vehicleName not in self._name2vehicleId:
                        self._name2vehicleId[self.vehicleName]=k   # save the corresponding between vehicle name and id in vm.vehicles dict
                    if hasattr(v,'v.ev_battery_percentage') and v.ev_battery_percentage != None:
                        batterySOC=v.ev_battery_percentage
                    else: 
                        batterySOC=0
                        
                    Domoticz.Status(f"Name={self.vehicleName} Odometer={v._odometer_value}{v._odometer_unit} Battery={batterySOC}")

                    # split v structure in more lines (too big to be printed in one line)
                    var=str(v)
                    for i in range(0,len(var),4000):    
                        Domoticz.Status(var[i:i+4000])
                
                    # base = Unit base = 0, 64, 128, 192 # up to 4 vehicles can be addressed, 64 devices per vehicle (Unit <= 255)
                    # Find the right Unit for the current car
                    baseFree = 256
                    found = 0
                    for base in range(0, 256-1, UNITMASK+1):
                        unit=base+(DEVS['ODOMETER'][0]); self.getDevID(unit)
                        if self.devID in Devices and unit in Devices[self.devID].Units:
                            if self.vehicleName in Devices[self.devID].Units[unit].Name:   
                                # odometer exists: check that Domoticz device name correspond with vehicle name (set on Kia connect)
                                found=1
                                break
                        else:
                            if baseFree > base:
                                baseFree = base # free base where devices can be stored
                    if found==0:    
                        # car not found, but there is enough space for a new car
                        if baseFree < 256:  # Add new devices for this new car
                            base = baseFree
                            found=1    # set found=1 to let device updating
                        else: # car not found, but no space for a new car (max 4!)
                            Domoticz.Error("No more space to store another vehicle (max 4 vehicles are supported)")
                    if found==1: # car found or enough space to create devices for this car
                        # update devices: if one or more devices do not exist, create it/them
                        self.updateDevices(base, v) 

                self._fetchingData=0    # fetching data from API ended correctly
        else:
            #self._fetchingData>1 => system is fetching data from cloud
            self._fetchingData += 1 # still fetching data from cloud API
            Domoticz.Status(f"onHeartbeat: fetching data has been started since {self._fetchingData}0 seconds")
            if self._fetchingData > 10:
                # fetching started more than 100s ago!
                Domoticz.Status(f"onHeartbeat: fetching data has been started more than {self._fetchingData}0 seconds ago")


    def onCommand(self, DeviceID, Unit, Command, Level, Color):
        Domoticz.Status(f"onCommand(Unit={Unit}, Command={Command}, Level={Level}, Color={Color})")
        if (Unit&UNITMASK) == DEVS["UPDATE"][0]:  #force status update
            self.devID=DeviceID
            self.update(Unit, 1 if Command=="On" else 0, Command)
            if Command=="On":
                if self._fetchingData == 0:
                    Domoticz.Status("Force update command")
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

            self.getDevID(Unit)
            if (Unit&UNITMASK) == DEVS["CLIMAON"][0]:   # start/stop climate control
                if Command == "On":
                    options=ClimateRequestOptions()
                    unit=(Unit&(~UNITMASK))+DEVS["CLIMATEMP"][0]
                    self.getDevID(unit)
                    if Devices[self.devID].Units[unit].sValue!='':
                        options.set_temp=float(Devices[self.devID].Units[unit].sValue)
                    else:
                        Domoticz.Status("Unknown clima temperature from vehicle: set to 23°C")
                        option.set_temp=23
                    if options.set_temp<15:
                        options.set_temp=15
                    elif options.set_temp>27:
                        options.set_temp=27
                    options.climate=True if options.set_temp<23 else False
                    options.heating=True if options.set_temp>23 else False
                    ret=self.vm.start_climate(vehicleId, options)
                    Domoticz.Status(f"start_climate() with options={options}. Returned {ret}")
                    self.getDevID(Unit)
                    self.update(Unit, 1, "On")   # Update device 
                else:   # Off command
                    ret=self.vm.stop_climate(vehicleId)
                    Domoticz.Status(f"stop_climate() returned {ret}")
                    self.getDevID(Unit)
                    self.update(Unit, 0, "Off")
            elif (Unit&UNITMASK) == DEVS["CLIMATEMP"][0]:   # air temperature
                airTemp=float(Level)
                if airTemp<15: 
                    airTemp=15
                elif airTemp>27: 
                    airTemp=27
                self.update(Unit, 0, str(airTemp))
            elif (Unit&UNITMASK) == DEVS["OPEN"][0]:   # open/close
                if Command == "On": # => lock
                    Domoticz.Status(f"lock command")
                    ret=self.vm.lock(vehicleId)
                    self.update(Unit, 1, "On")
                else:   # Off command => unlock
                    Domoticz.Log(f"unlock command")
                    ret=self.vm.unlock(vehicleId)
                    self.update(Unit, 0, "Off")
            elif (Unit&UNITMASK) == DEVS["EVLIMITAC"][0] or (Unit&UNITMASK) == DEVS["EVLIMITDC"][0]:
                # Battery limit was changed: send new value to the car
                self._setChargeLimits=1  # set charge limits after 2*HeartBeat 
                self._setChargeLimits|=16<<(Unit>>6)    #store in setChargeLimits which devices have been changed 0bzyxw0010 where w=1 if base=0, x=1 if base=64, y=1 if base=128, ...
                Level=Level-Level%10    # Level should be 0, 10, 20, 30, ...
                Domoticz.Status(f"New value={Level}")
                self.update(Unit, 1, str(Level))
            elif (Unit&UNITMASK) == DEVS["EVCHARGEON"][0]:    # Start or stop charging
                if Command == "On":
                    Domoticz.Status(f"Received command to start charging")
                    self.update(Unit, 1, "On")
                    ret=self.vm.start_charge(vehicleId)
                else:
                    Domoticz.Status(f"Received command to stop charging")
                    self.update(Unit, 0, "Off")
                    ret=self.vm.stop_charge(vehicleId)


    def updateDevices(self, base, v):
        """ Update devices for car named {self.vehicleName}, starting from base unit {base}, using vehicle parameters in {v}. If a device does not exist, automatically create it """
        Domoticz.Status(f"Car found at base {base}")

        k='EVSTATE'; dev=DEVS[k]; var=getattr(v, 'ev_battery_is_charging', None)
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
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            if self._isCharging == True:
                nValue=1; sValue="On"
            else:
                nValue=0; sValue="Off"
            unit=base+DEVS['EVCHARGEON'][0]; self.getDevID(unit); self.update(unit, nValue, sValue)
        
        batteryLevel=None   # show batteryLevel in the debug messages
        k='EVBATTLEVEL'; dev=DEVS[k]; var=getattr(v, 'ev_battery_percentage', None)
        if var != None:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, str(nValue))
        
        k='EVRANGE'; dev=DEVS[k]; var=getattr(v, '_ev_driving_range', None)
        if var == None: var=getattr(v, 'ev_driving_distance', None)
        if var != None:
            nValue=int(var)
            if self.verbose: Domoticz.Status(f"{k}={var}")
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, str(nValue))
            
        k='EVLIMITAC'; dev=DEVS[k]; var=getattr(v, 'ev_charge_limits_ac', None)
        if var==None: var=getattr(v, '_ev_charge_limits.ac', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nVar=int(var)
            nValue=2
            sValue=var
            if nVar==100: nValue=1
            if nVar==0: nValue=0
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='EVLIMITDC'; dev=DEVS[k]; var=getattr(v, 'ev_charge_limits_dc', None)
        if var==None: var=getattr(v, '_ev_charge_limits.dc', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nVar=int(var)
            nValue=2
            sValue=var
            if nVar==100: nValue=1
            if nVar==0: nValue=0
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='FUELLEVEL'; dev=DEVS[k]; var=getattr(v, 'fuel_level', None)
        if var != None:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, str(nValue))
            
        k='FUELRANGE'; dev=DEVS[k]; var=getattr(v, '_fuel_driving_range', None)
        if var != None:
            nValue=int(var)
            if self.verbose: Domoticz.Status(f"{k}={var}")
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, str(nValue))
            
        k='ENGINEON'; dev=DEVS[k]; var=getattr(v, 'engine_is_running', None)
        if var != None:
            value=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=0; sValue="Off"
            if (value):
                nValue=1; sValue="On"
                self._engineOn=True
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='ODOMETER'; dev=DEVS[k]; var=getattr(v, 'odometer', None)
        if var != None and var != 0:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=int(nValue)
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, str(nValue))


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
            if self.vehicleName not in self._vehicleLoc:
                #initialize vehicleLoc
                self._vehicleLoc[self.vehicleName]={'latitude': lat, 'longitude': lon+0.000001} # initialize variable but force a minimum variation to compute the real position

            if self._getAddress==1 or lat!=self._vehicleLoc[self.vehicleName]['latitude'] or lon!=self._vehicleLoc[self.vehicleName]['longitude']:
                # LOCATION changed or not previously set
                # get address
                if self.verbose: Domoticz.Status(f"Latitude or Longitude have changed")
                get_address_url = 'https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=16&lat=' + str(lat) + '&lon=' + str(lon)
                response = requests.get(get_address_url, headers={'User-Agent': 'Domoticz Hyundai/Kia plugin'})
                if response.status_code == 200:
                    response = json.loads(response.text)
                    locAddr=response['display_name']
                    Domoticz.Status(f"Location address: {locAddr}")
                else:
                    Domoticz.Error(f"Trying to get location address, but got response_code {response.status_code}\nURL={get_address_url}")
                    self._getAddress=1 # retry to get address again
                    locAddr='Unknown'
                locMap = f"<a href=\"http://www.google.com/maps/search/?api=1&query={lat},{lon}\" target=\"_new\"><em style=\"color:blue;\">Map</em></a>"
                sValue=fill(locAddr, 40) + ' ' + locMap
                unit=base+DEVS['LOCATION'][0]; self.getDevID(unit); self.update(unit, 0, sValue)
                self._getAddress=0 # Address get successfully: update it only in case that location changes.
                # HOME DISTANCE: compute distance from home
                homeloc=Settings['Location'].split(';')
                distance=round(self.distance(lat, lon, float(homeloc[0]), float(homeloc[1])), 1)
                unit=base+DEVS['HOMEDIST'][0]; self.getDevID(unit); self.update(unit, 0, str(distance))

                if hasattr(v,'data'):
                    value=v.data
                    if value != None:
                        nValue=value['vehicleLocation']['speed']['value']
                        sValue=str(nValue)
                        unit=base+DEVS['SPEED'][0]; self.getDevID(unit); self.update(unit, nValue, sValue)
                        Domoticz.Status(f"Vehicle {self.vehicleName} has odometer={v.odometer} speed={nValue} distance_from_home={distance} EV battery={batteryLevel}%")

                self._vehicleLoc[self.vehicleName]['latitude']=lat
                self._vehicleLoc[self.vehicleName]['longitude']=lon
            else:
                if self.verbose: Domoticz.Status(f"Latitude or Longitude NOT changed: lat={lat}, lon={lon}")
        else: 
            if self.verbose: Domoticz.Status(f"Latitude or Longitude NOT found")

        k='CLIMAON'; dev=DEVS[k]; var=getattr(v, 'air_control_is_on', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            value=var
            nValue=1 if value else 0
            sValue="On" if value else "Off"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)

        k='CLIMATEMP'; dev=DEVS[k]; var=getattr(v, '_air_temperature', None)
        if var != None:
            nValue=float(var)
            if self.verbose: Domoticz.Status(f"{k}={var}")
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, nValue)
            
        k='DEFROSTON'; dev=DEVS[k]; var=getattr(v, 'defrost_is_on', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="On" if var else "Off"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='REARWINDOWON'; dev=DEVS[k]; var=getattr(v, 'back_window_heater_is_on', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="On" if var>0 else "Off"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='STEERINGWHEELON'; dev=DEVS[k]; var=getattr(v, 'steering_wheel_heater_is_on', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="On" if var>0 else "Off"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)

        k='SIDEMIRRORSON'; dev=DEVS[k]; var=getattr(v, 'side_mirror_heater_is_on', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="On" if var else "Off"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='SEATFL'; dev=DEVS[k]; var=getattr(v, 'front_left_seat_status', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=0; sValue=var
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='SEATFR'; dev=DEVS[k]; var=getattr(v, 'front_right_seat_status', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=0; sValue=var
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='SEATRL'; dev=DEVS[k]; var=getattr(v, 'rear_left_seat_status', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=0; sValue=var
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
           
        k='SEATRR'; dev=DEVS[k]; var=getattr(v, 'rear_right_seat_status', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=0; sValue=var
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='OPEN'; dev=DEVS[k]; var=getattr(v, 'is_locked', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="Unlocked" if var else "Locked"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='TRUNK'; dev=DEVS[k]; var=getattr(v, 'trunk_is_open', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="Open" if var else "Closed"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='HOOD'; dev=DEVS[k]; var=getattr(v, 'hood_is_open', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=1 if var else 0
            sValue="Open" if var else "Closed"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='12VBATT'; dev=DEVS[k]; var=getattr(v, 'car_battery_percentage', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue=str(nValue)
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='KEYBATT'; dev=DEVS[k]; var=getattr(v, 'smart_key_battery_warning_is_on', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="Ok" if nValue == 0 else "Low"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='WASHER'; dev=DEVS[k]; var=getattr(v, 'washer_fluid_warning_is_on', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="Ok" if nValue == 0 else "Empty"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='BRAKE'; dev=DEVS[k]; var=getattr(v, 'brake_fluid_warning_is_on', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="Ok" if nValue == 0 else "Empty"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
            
        k='TIRES'; dev=DEVS[k]; var=getattr(v, 'tire_pressure_all_warning_is_on', None)
        if var != None:
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=var
            sValue="Ok" if nValue == 0 else "Low"
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)

        k='EVENERGYCONS90DAYS'; dev=DEVS[k]; var=getattr(v, 'total_power_consumed', None)
        if var != None and var != 0:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=int(nValue); 
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, nValue)

        k='EVESTCHGDURATION'; dev=DEVS[k]; var=getattr(v, '_ev_estimated_current_charge_duration', None)
        if var != None:
            nValue=int(var); 
            if self.verbose: Domoticz.Status(f"{k}={var}")
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, nValue)

        k='EVTARGETCHGRANGE'; dev=DEVS[k]; var=getattr(v, '_ev_target_range_charge_AC', None)
        if var != None:
            nValue=int(var); 
            if self.verbose: Domoticz.Status(f"{k}={var}")
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, nValue)

        k='EVENERGYREGEN90DAYS'; dev=DEVS[k]; var=getattr(v, 'total_power_regenerated', None)
        if var != None and var != 0:
            nValue=var
            if self.verbose: Domoticz.Status(f"{k}={var}")
            nValue=int(nValue)
            unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, nValue)

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
                k='EVENERGYCONSTOTAL'; dev=DEVS[k]
                unit=base+dev[0]; self.getDevID(unit)
                if self.devID in Devices:
                    TotalPwrConsID=Devices[self.devID].Units[unit].ID
                    result,Counter,CounterToday=getCounter(TotalPwrConsID)
                else:
                    result=True; Counter=todayPwrConsumed; CounterToday=todayPwrConsumed    # Device does not exist yet: initialize to the current value
                if result:
                    incrementValue=todayPwrConsumed-CounterToday
                    Domoticz.Status(f"Energy consumed Counter {Counter} counterToday {CounterToday} daily stat {todayPwrConsumed} Increment {incrementValue}") 
                    nValue=0; sValue=str(incrementValue)
                    unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
                else:
                    Domoticz.Error(f"Counter Check of device {k} failed. Postponing update till next time")

            if todayPwrRegenerated>0:
                k='EVENERGYREGENTOTAL'; dev=DEVS[k]
                unit=base+dev[0]; self.getDevID(unit)
                if self.devID in Devices:
                    TotalPwrRegenID=Devices[self.devID].Units[unit].ID
                    result,Counter,CounterToday=getCounter(TotalPwrRegenID)
                else:
                    result=True; Counter=todayPwrRegenerated; CounterToday=todayPwrRegenerated    # Device does not exist yet: initialize to the current value
                if result:
                    incrementValue=todayPwrRegenerated-CounterToday
                    Domoticz.Status(f"PwrRegenerated Counter {Counter} counterToday {CounterToday} daily stat {todayPwrRegenerated} Increment {incrementValue}")
                    nValue=0; sValue=str(incrementValue)
                    unit=base+dev[0]; self.getDevID(unit); self.update(unit, nValue, sValue)
                else:
                    Domoticz.Error(f"Counter Check of device {k} failed. Postponing update till next time")
        else:
            if self.firstRun==True:
                Domoticz.Status(f"Not updating new PWR devices on first run with today's values")


        # Reset force update button
        nValue=0; sValue="Off"
        unit=base+DEVS['UPDATE'][0]; self.getDevID(unit); self.update(unit, nValue, sValue)

    def distance(self, lat1, lon1, lat2, lon2):
        """ Compute the distance between two locations """
        p = pi / 180
        a = 0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
        return 12742 * asin(sqrt(a))

    def onTimeout(self, Connection):    #DEBUG
        Domoticz.Status(f"onTimeout({Connection})")

    def onStop(self):
        Domoticz.Status(f"onStop()")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Status(f"onConnect({Connection}, {Status}, {Description})")

    def onMessage(self, Connection, Data):
        Domoticz.Status(f"onMessage({Connection}, {Data})")

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Status(f"onNotification({Name}, {Subject}, {Text}, {Status}, {Priority}, {Sound}, {ImageFile})")

    def onDisconnect(self, Connection):
        Domoticz.Status(f"onDisconnect({Connection})")

    def onDeviceAdded(self, DeviceID, Unit):
        Domoticz.Status(f"onDeviceAdded({DeviceID}, {Unit})")

    def onDeviceModified(self, DeviceID, Unit):
        Domoticz.Status(f"onDeviceModified({DeviceID}, {Unit})")

    def onDeviceRemoved(self, DeviceID, Unit):
        Domoticz.Status(f"onDeviceRemoved({DeviceID}, {Unit})")

    def onSecurityEvent(self, DeviceID, Unit, Level, Description):
        Domoticz.Status(f"onSecurityEvent({DeviceID}, {Unit}, {Level}, {Description})")

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
        Domoticz.Error(f"ERROR: unable to retrieve the value of device with IDX {varIDX} {response}\nURL={apiCall}")
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

def onCommand(DeviceID, Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(DeviceID, Unit, Command, Level, Color)

def onTimeout(Connection): #DEBUG
    global _plugin
    _plugin.onTimeout(Connection)

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onDeviceAdded(DeviceID, Unit):
    global _plugin
    _plugin.onDeviceAdded(DeviceID, Unit)

def onDeviceModified(DeviceID, Unit):
    global _plugin
    _plugin.onDeviceModified(DeviceID, Unit)

def onDeviceRemoved(DeviceID, Unit):
    global _plugin
    _plugin.onDeviceRemoved(DeviceID, Unit)

def onSecurityEven(DeviceID, Unit, Level, Description):
    global _plugin
    _plugin.onSecurityEvent(DeviceID, Unit, Level, Description)


