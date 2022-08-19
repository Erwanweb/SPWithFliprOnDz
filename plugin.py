"""
Swimming pool full control using Flipr analyzer
Author: EMA Team,
Version:    0.0.1: alpha
            0.0.2: beta
            0.1.1: test with alexa speaking
"""
"""

<plugin key="SPWithFliprOnDzByEMA" name="ZZ - Swimming Pool Control with Flipr analyzer" author="EMA Team" version="1.1.2" externallink="https://github.com/Erwanweb/SPWithFliprOnDz">
    <params>
        <param field="Username" label="Adresse e-mail (Flipr Account)" width="200px" required="true" default=""/>
        <param field="Password" label="Psw (Flipr Account)" width="200px" required="true" default="" password="true"/>
        <param field="Mode1" label="Serial of Flipr" required="true" default=""/>
        <param field="Mode6" label="Logging Level" width="200px">
            <options>
                <option label="Normal" value="Normal"  default="true"/>
                <option label="Verbose" value="Verbose"/>
                <option label="Debug - Python Only" value="2"/>
                <option label="Debug - Basic" value="62"/>
                <option label="Debug - Basic+Messages" value="126"/>
                <option label="Debug - Connections Only" value="16"/>
                <option label="Debug - Connections+Queue" value="144"/>
                <option label="Debug - All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import sys
from base64 import b64encode
import base64
import json
from urllib.parse import quote
import urllib.parse as parse
import urllib.request as request
import itertools
import re
from datetime import datetime, timedelta, time
import math
import html
import requests
import os
import subprocess as sp
from distutils.version import LooseVersion


baseUrl = "https://apis.goflipr.com"
oauth2data = {'grant_type':'password', 'password':'', 'username':''}
oauth2Url = baseUrl + "/OAuth2/token"
headerData = { 'Content-Type':'application/json', 'Authorization':''}


class deviceparam:

    def __init__(self, unit, nvalue, svalue):
        self.unit = unit
        self.nvalue = nvalue
        self.svalue = svalue

class BasePlugin:
        
    def __init__(self):
        self.FliprVarNextRefresh = datetime.now()
        self.lastDateTime = None
        self.isStarted = False
        self.httpConn = None
        self.sConnectionStep = "idle"
        self.bHasAFail = False
        # Flipr connex
        # string: username for flipr website
        self.sUser = None
        # string: password for flipr website
        self.sPassword = None
        # string : serial number of the fliper device
        self.sSerial = None
        # store the token
        self.token = None
        # default values of the Flipr
        self.tempVal = 20.11
        self.PHVal = 7.22
        self.PHText = "Parfait"
        self.RedoxVal = 600
        self.RedoxText = "Parfait"
        self.batVal = 100
        self.SPTemp = 24
        self.PHValNet = 7
        self.RedoxValNet = 600
        self.FiltrationVarNextRefresh = datetime.now()
        self.PumpTemp = 12
        self.SPTempCheck = 24
        self.PLUGINstarteddtime = datetime.now()
        self.SunAtSouthHour = 14
        self.SunAtSouthMin = 0
        self.SunAtSouth = datetime.now()
        self.startpump = datetime.now()
        self.stoppump = datetime.now()
        self.Daily = datetime.now()
        self.pumpon = False
        self.Heating = False
        return

    def onStart(self):

        # setup the appropriate logging level
        try:
            debuglevel = int(Parameters["Mode6"])
        except ValueError:
            debuglevel = 0
            self.loglevel = Parameters["Mode6"]
        if debuglevel != 0:
            self.debug = True
            Domoticz.Debugging(debuglevel)
            DumpConfigToLog()
            self.loglevel = "Verbose"
        else:
            self.debug = False
            Domoticz.Debugging(0)

        # Infos for Flipr connect
        self.sUser = Parameters["Username"]
        self.sPassword = Parameters["Password"]
        self.sSerial = Parameters["Mode1"]

        # most init ?¿?¿
        #self.__init__()

        # create the child devices if these do not exist yet
        devicecreated = []
        if 1 not in Devices:
            Options = {"LevelActions": "||", "LevelNames": "Off|Auto|Forced", "LevelOffHidden": "false", "SelectorStyle": "0"}
            Domoticz.Device(Name="Filtration control", Unit=1, TypeName="Selector Switch", Switchtype=18, Image=9, Options=Options, Used=1).Create()
            devicecreated.append(deviceparam(1, 0, "0"))  # default is Off state
        if 2 not in Devices:
            Options = {"LevelActions": "||", "LevelNames": "Off|Auto|Forced", "LevelOffHidden": "false", "SelectorStyle": "0"}
            Domoticz.Device(Name="Heating control", Unit=2, TypeName="Selector Switch", Switchtype=18, Image=15, Options=Options, Used=1).Create()
            devicecreated.append(deviceparam(2, 0, "0"))  # default is Off state
        if 3 not in Devices:
            Domoticz.Device(Name="Filtration", Unit=3, TypeName="Switch", Image=9, Used=1).Create()
            devicecreated.append(deviceparam(3, 0, ""))  # default is Off
        if 4 not in Devices:
            Domoticz.Device(Name="Water temp", Unit=4, TypeName="Temperature", Used=1).Create()
            devicecreated.append(deviceparam(4, 0, "20"))  # default is 20 degrees
        if 5 not in Devices:
            Domoticz.Device(Name="Setpoint", Unit=5, Type=242, Subtype=1, Used=1).Create()
            devicecreated.append(deviceparam(5, 0, "28"))  # default is 28 degrees
        if 6 not in Devices:
            Domoticz.Device(Name="Heating request", Unit=6, TypeName="Switch", Image=9).Create()
            devicecreated.append(deviceparam(6, 0, ""))  # default is Off
        if 7 not in Devices:
            Domoticz.Device(Name="PH", Unit=7, Type=243, Subtype=19, Used=1).Create()
            devicecreated.append(deviceparam(7, 0, "waiting for value"))  # default is clear
        if 8 not in Devices:
            Domoticz.Device(Name="PH Value", Unit=8, Type=243, Subtype=31, Used=1).Create()
            devicecreated.append(deviceparam(8, 0, ""))  # default is 0
        if 9 not in Devices:
            Domoticz.Device(Name="Redox", Unit=9, Type=243, Subtype=19, Used=1).Create()
            devicecreated.append(deviceparam(9, 0, "waiting for value"))  # default is clear
        if 10 not in Devices:
            Domoticz.Device(Name="Redox Value", Unit=10, Type=243, Subtype=31, Used=1).Create()
            devicecreated.append(deviceparam(10, 0, ""))  # default is 0
        if 11 not in Devices:
            Domoticz.Device(Name="Flipr Battery", Unit=11, Type=243, Subtype=6, Used=1).Create()
            devicecreated.append(deviceparam(11, 0, ""))  # default is 0
        if 12 not in Devices:
            Options = {"LevelActions": "||", "LevelNames": "Off|Auto", "LevelOffHidden": "false", "SelectorStyle": "0"}
            Domoticz.Device(Name="Water treatment control", Unit=12, TypeName="Selector Switch", Switchtype=18, Image=9, Options=Options, Used=1).Create()
            devicecreated.append(deviceparam(12, 0, "0"))  # default is Off state
        if 13 not in Devices:
            Domoticz.Device(Name="Ph Minus request", Unit=13, TypeName="Switch", Image=9).Create()
            devicecreated.append(deviceparam(13, 0, ""))  # default is Off
        if 14 not in Devices:
            Domoticz.Device(Name="Chlorine request", Unit=14, TypeName="Switch", Image=9).Create()
            devicecreated.append(deviceparam(14, 0, ""))  # default is Off
        if 15 not in Devices:
            Domoticz.Device(Name="Check", Unit=15, TypeName="Switch", Image=9, Used=1).Create()
            devicecreated.append(deviceparam(15, 0, ""))  # default is Off

        # if any device has been created in onStart(), now is time to update its defaults
        for device in devicecreated:
            Devices[device.unit].Update(nValue=device.nvalue, sValue=device.svalue)

        # Now we can enabling the plugin
        self.isStarted = True

        # We upadte the last Flipr's datas
        #self.handleConnection()

        # Check if the used control mode is ok
        if (Devices[1].sValue == "10"):
            self.powerOn = 1

        elif (Devices[1].sValue == "20"):
            self.powerOn = 1

        elif (Devices[1].sValue == "0"):
            self.powerOn = 0

    def onStop(self):
        Domoticz.Debug("onStop called")
        # prevent error messages during disabling plugin
        self.isStarted = False

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called")
        if self.isStarted and (Connection == self.httpConn):
            self.handleConnection()

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")
        # if started and not stopping
        if self.isStarted and (Connection == self.httpConn):
            self.handleConnection(Data)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called")

# DZ Widget actions  ---------------------------------------------------

    def onCommand(self, Unit, Command, Level, Color):

        Domoticz.Debug("onCommand called for Unit {}: Command '{}', Level: {}".format(Unit, Command, Level))

        if (Unit == 1):
            Devices[1].Update(nValue=self.powerOn, sValue=str(Level))
            if (Devices[1].sValue == "10"):  # Mode auto
                self.powerOn = 1
                Devices[1].Update(nValue=1, sValue=Devices[1].sValue)
            elif (Devices[1].sValue == "20"):  # Manual Mode
                self.powerOn = 1
                Devices[1].Update(nValue=1, sValue=Devices[1].sValue)
            else : # Off
                Devices[1].Update(nValue=0, sValue=Devices[1].sValue)
                self.powerOn = 0
                Devices[2].Update(nValue=self.powerOn, sValue=Devices[2].sValue)
                Devices[12].Update(nValue=self.powerOn, sValue=Devices[12].sValue)
            # Update child devices
            if not (Devices[2].sValue == "0"):  # Heating Off
                Devices[2].Update(nValue=self.powerOn, sValue=Devices[2].sValue)
            if not (Devices[12].sValue == "0"):  # WT Off
                Devices[12].Update(nValue=self.powerOn, sValue=Devices[12].sValue)

        if (Unit == 2):  # Heating
            Devices[2].Update(nValue=self.powerOn, sValue=str(Level))
            if (Devices[2].sValue == "0"):  # Off
                Devices[2].Update(nValue=0, sValue=Devices[2].sValue)
            else :
                Devices[2].Update(nValue=self.powerOn, sValue=str(Level))

        if (Unit == 12):  # Water treatment
            Devices[12].Update(nValue=self.powerOn, sValue=str(Level))
            if (Devices[12].sValue == "0"):  # Off
                Devices[12].Update(nValue=0, sValue=Devices[2].sValue)
            else :
                Devices[12].Update(nValue=self.powerOn, sValue=str(Level))

        if (Unit == 15): # Alexa check
            Devices[15].Update(nValue=1, sValue=Devices[15].sValue)
            Domoticz.Debug("Verification etat piscine")
            self.verifSP()


# Heartbeat  ---------------------------------------------------

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")
        now = datetime.now()

        # Updating Flipr mesured values (the device update it from the server about each x minutes)
        if self.FliprVarNextRefresh <= now:
            self.FliprVarNextRefresh = now + timedelta(minutes=5)
            self.handleConnection()
            # On arrondit les valeurs -- // syntaxe : round (nombre, nombre de chiffres apres la virgule si on veut) exemple : round(value, 1) = 1 chiffre apres la virgule
            self.SPTemp = round(float(self.tempVal),1)  # 1 chiffre apres la virgule
            self.PHValNet = round(float(self.PHVal),1)  # 1 chiffre apres la virgule
            self.RedoxValNet = round(float(self.RedoxVal))  # pas chiffre apres la virgule
            # On arrondit les valeurs de temp sans virgules, en valeur haute
            self.SPTempCheck = math.ceil(float(self.tempVal))  # pas de chiffre apres la virgule, et arrondi au dessus ou egal
            Domoticz.Debug("SP rounded up temp is : " + str(self.SPTempCheck))
            # Updating devices values
            Domoticz.Debug("Updating Devices from Flipr Values")
            Devices[4].Update(nValue = 0,sValue = str(self.SPTemp))
            Devices[7].Update(nValue= 0, sValue=str(self.PHText))
            Devices[8].Update(nValue= 0, sValue=str(self.PHValNet))
            Devices[9].Update(nValue= 0, sValue=str(self.RedoxText))
            Devices[10].Update(nValue= 0, sValue=str(self.RedoxValNet))
            Devices[11].Update(nValue= 0, sValue=str(self.batVal))

        # Regul-regul --------------------------------------------------

        # Filtration ---------------------------------------------------
        # Check mode and set all good
        if Devices[1].sValue == "0": # Off
            if Devices[3].nValue == 1:
                Devices[3].Update(nValue=0, sValue=Devices[3].sValue)
            Domoticz.Debug("System is OFF - ALL OFF")
        elif Devices[1].sValue == "20": # Manual
            if Devices[3].nValue == 0:
                Devices[3].Update(nValue=1, sValue=Devices[3].sValue)
            Domoticz.Debug("System is ON - Filtration in MANUAL Mode")
        else : # Auto
            Domoticz.Debug("System is ON - Filtration in AUTO Mode")
            # If Auto :
            now = datetime.now()
            # We check time needed for filtration, every 15 minutes
            if self.FiltrationVarNextRefresh <= now:
                self.FiltrationVarNextRefresh = now + timedelta(minutes=15)
                if self.SPTempCheck > 31:
                    self.PumpTemp = 24
                    Domoticz.Debug("Filtration is all the time because of high SP Temp at : " + str(self.SPTemp))
                else :
                    if self.SPTempCheck < 10:
                        self.PumpTemp = 3
                        Domoticz.Debug("Filtration is fixed at 3h per day because low SP Temp at : " + str(self.SPTemp))
                    else:
                        self.PumpTemp = round((self.SPTempCheck / 2))
                        Domoticz.Debug("Filtration calcul. dur. is : " + str(self.PumpTemp))
                    # Now we set timers
                    jsonData = DomoticzAPI("type=command&param=getSunRiseSet")
                    if jsonData :
                    # datetime(year, month, day, hour, minute, second, microsecond)
                        SunAtSouthHour = int(jsonData['SunAtSouth'].split(':')[0])
                        SunAtSouthMin = int(jsonData['SunAtSouth'].split(':')[1])
                        now = datetime.now()
                        self.SunAtSouth = datetime(year=now.year, month=now.month, day=now.day, hour=SunAtSouthHour, minute=SunAtSouthMin, second=0, microsecond=0)
                        Domoticz.Debug("Sun at south at : " + str(self.SunAtSouth))
                        self.startpump = self.SunAtSouth - timedelta(hours=(self.PumpTemp/ 2))
                        Domoticz.Debug("Pump ON timer fixed at : " + str(self.startpump))
                        self.stoppump = self.startpump + timedelta(hours=(self.PumpTemp))
                        Domoticz.Debug("Pump OFF timer fixed at : " + str(self.stoppump))
                    else : # timers by default
                        now = datetime.now()
                        self.SunAtSouth = datetime(year=now.year, month=now.month, day=now.day, hour=14, minute=0, second=0, microsecond=0)
                        self.startpump = self.SunAtSouth - timedelta(hours=(self.PumpTemp / 2))
                        Domoticz.Debug("Pump ON timer default value at : " + str(self.startpump))
                        self.stoppump = self.startpump + timedelta(hours=(self.PumpTemp))
                        Domoticz.Debug("Pump OFF timer default value at : " + str(self.stoppump))
            # And now, we check state and turn on or off the pump
            now = datetime.now()
            if self.startpump < now and self.stoppump > now : # We are in the period of filtration
                self.pumpon = True
                if Devices[3].nValue == 0:
                    Devices[3].Update(nValue=1, sValue=Devices[3].sValue)
                Domoticz.Debug("Pompe is ON since "+ str(self.startpump))
                Domoticz.Debug("Pompe will turn OFF at " + str(self.stoppump))
            else :
                self.pumpon = False # We are not yet in the period of filtration
                if Devices[3].nValue == 1:
                    Devices[3].Update(nValue=0, sValue=Devices[3].sValue)
                Domoticz.Debug("Pompe is OFF - Will turn ON today at " + str(self.startpump))
            if self.pumpon :
                if self.stoppump < now : # We are in the period of filtration and we leave it, stop pump
                    self.pumpon = False
                    if Devices[3].nValue == 1:
                        Devices[3].Update(nValue=0, sValue=Devices[3].sValue)
                    Domoticz.Debug("Pump is OFF after daily period - It stop at : " + str(self.stoppump))
                    Domoticz.Debug("Pompe will turn ON tommorow at " + str(self.startpump))

        # Temp ---------------------------------------------------
        if self.powerOn:  # On in manual or in Auto
            if (Devices[2].sValue == "20"): # Heating forced
                self.Heating = True
                if Devices[6].nValue == 0:
                    Devices[6].Update(nValue=1, sValue=Devices[6].sValue)
                    Domoticz.Debug("Heating is FORCED ON")
            elif (Devices[2].sValue == "20"): # Heating Auto with 1 for hysterisis low
                if self.SPTemp < (float(Devices[5].sValue) - 1):
                    self.Heating = True
                    if Devices[6].nValue == 0:
                        Devices[6].Update(nValue=1, sValue=Devices[6].sValue)
                    Domoticz.Debug("Heating is AUTO ON - Heating requested")
                if self.SPTemp > float(Devices[5].sValue) + 0.1):
                    self.Heating = False
                    if Devices[6].nValue == 1:
                        Devices[6].Update(nValue=0, sValue=Devices[6].sValue)
                    Domoticz.Debug("Heating is AUTO OFF - No heating requested")
            else : # Heating off
                self.Heating = False
                if Devices[6].nValue == 1:
                    Devices[6].Update(nValue=0, sValue=Devices[6].sValue)
                Domoticz.Debug("Heating is OFF")
        else :
            self.Heating = False
            if Devices[6].nValue == 1:
                Devices[6].Update(nValue=0, sValue=Devices[6].sValue)
            Domoticz.Debug("Heating is OFF Because of system OFF")
        # PH ---------------------------------------------------
        # if self.powerOn:  # On in manual or in Auto

        # Redox ---------------------------------------------------
        # if self.powerOn:  # On in manual or in Auto

# Flipr Part  ---------------------------------------------------

    # getToken : get the bearer type token
    def getToken(self):
        oauth2data['password'] = self.sPassword
        oauth2data['username'] = self.sUser
        response = requests.post(oauth2Url, data = oauth2data)
        #print the response text (the content of the requested file):
        jsontoken = response.json()
        return jsontoken['access_token']

    # getData : get the flipr data
    def getData(self):
        urlData = baseUrl + '/modules/' + self.sSerial + '/survey/Last'
        headerData['Authorization'] = 'Bearer ' + self.token
        x = requests.get(url = urlData, headers = headerData, verify=False)
        return x.json()

    # Handle the connection state machine
    def handleConnection(self, Data = None):
    # def handleConnection(self):
        jsonData = None
        self.token = self.getToken()
        jsonData = self.getData()
        if self.lastDateTime != jsonData['DateTime']:
            Domoticz.Debug("Enregistrement des donnees" + str(jsonData) + " --- "+ str(jsonData['DateTime']))
            self.tempVal = str(jsonData['Temperature'])
            self.PHVal = str(jsonData['PH']['Value'])
            self.PHText = str(jsonData['PH']['Message'])
            self.RedoxVal = str(jsonData['OxydoReductionPotentiel']['Value'])
            self.RedoxText = str(jsonData['Desinfectant']['Message'])
            self.batVal = str(jsonData['Battery']['Deviation'] * 100)
        self.lastDateTime = jsonData['DateTime']

# Alexa  ---------------------------------------------------

    def verifSP(self):
        if self.PHValNet <= 7.2 and self.PHValNet >= 6.8 and self.RedoxValNet <= 650 and self.RedoxValNet >= 550 :
            AlexaAPI("La piscine est a {} degré. la qualité de l'eau est parfaite, avec un P-H a {} et une valeur rédox de {}".format(self.SPTempCheck, self.PHValNet, self.RedoxValNet))
        else :
            AlexaAPI("La piscine est a {} degré, son P-H est {} avec une valeur de {} et le niveau de desinfectant est {} avec une valeur rédox de {}".format(self.SPTempCheck, self.PHText, self.PHValNet, self.RedoxText, self.RedoxValNet))
        Devices[15].Update(nValue=0, sValue=Devices[15].sValue)

# Global  ---------------------------------------------------

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Plugin utility functions ---------------------------------------------------

def parseCSV(strCSV):

    listvals = []
    for value in strCSV.split(","):
        try:
            val = int(value)
        except:
            pass
        else:
            listvals.append(val)
    return listvals


def DomoticzAPI(APICall):

    resultJson = None
    url = "http://127.0.0.1:8080/json.htm?{}".format(parse.quote(APICall, safe="&="))
    Domoticz.Debug("Calling domoticz API: {}".format(url))
    try:
        req = request.Request(url)
        response = request.urlopen(req)
        if response.status == 200:
            resultJson = json.loads(response.read().decode('utf-8'))
            if resultJson["status"] != "OK":
                Domoticz.Error("Domoticz API returned an error: status = {}".format(resultJson["status"]))
                resultJson = None
        else:
            Domoticz.Error("Domoticz API: http error = {}".format(response.status))
    except:
        Domoticz.Error("Error calling '{}'".format(url))
    return resultJson

def CheckParam(name, value, default):

    try:
        param = int(value)
    except ValueError:
        param = default
        Domoticz.Error("Parameter '{}' has an invalid value of '{}' ! defaut of '{}' is instead used.".format(name, value, default))
    return param

def AlexaAPI(APICall):
    cmd = 'sudo /home/pi/script/alexa_remote_control.sh -lastalexa {} cut -d"=" -f1'.format("|")
    output = sp.getoutput(cmd)
    Domoticz.Debug("Last alexa speaking : {}".format(output))

    time.sleep(1)

    cmd = 'sudo /home/pi/script/alexa_remote_control.sh -d {} -e speak:"{}"'.format(output, APICall)
    Domoticz.Debug("Calling Alexa API: {}".format(cmd))
    os.system(cmd)

# Generic helper functions ---------------------------------------------------

def dictToQuotedString(dParams):
    result = ""
    for sKey, sValue in dParams.items():
        if result:
            result += "&"
        result += sKey + "=" + quote(str(sValue))
    return result

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
