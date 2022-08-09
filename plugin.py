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
from datetime import datetime, timedelta
import time
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
        
    nextRefresh = datetime.now()
    # boolean: to check that we are started, to prevent error messages when disabling or restarting the plugin
    isStarted = None
    # object: http connection
    httpConn = None
    # ??
    sConnectionStep = None
    # string: username for flipr website
    sUser = None
    # string: password for flipr website
    sPassword = None
    # string : serial number of the fliper device
    sSerial = None
    # store the token
    token = None
    lastDateTime = None

    def __init__(self):
        self.isStarted = False
        self.httpConn = None
        self.sConnectionStep = "idle"
        self.bHasAFail = False
        # default values of the Flipr
        self.tempVal = 20.11
        self.PHVal = 7.22
        self.PHText = "Parfait"
        self.RedoxVal = 600
        self.RedoxText = "Parfait"
        self.batVal = 100
        self.SPTemp = 20
        self.PHValNet = 7
        self.PumpTemp = 12
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
            Domoticz.Device(Name="Filtration control", Unit=1, TypeName="Selector Switch", Switchtype=18, Image=15, Options=Options, Used=1).Create()
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
            Options = {"LevelActions": "||", "LevelNames": "Off|Auto|Manual", "LevelOffHidden": "false", "SelectorStyle": "0"}
            Domoticz.Device(Name="Water treatment control", Unit=12, TypeName="Selector Switch", Switchtype=18, Image=15, Options=Options, Used=1).Create()
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

    def onCommand(self, Unit, Command, Level, Color):

        Domoticz.Debug("onCommand called for Unit {}: Command '{}', Level: {}".format(Unit, Command, Level))

        now = datetime.now()

        if (Unit == 15):
            Devices[15].Update(nValue=1, sValue=Devices[15].sValue)
            Domoticz.Debug("Verification etat piscine")
            self.verifSP()

# Heartbeat  ---------------------------------------------------

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")
        now = datetime.now()

        # Updating Flipr mesured values (the device update it to the server about each 30 minutes)
        if self.nextRefresh <= now:
            self.nextRefresh = now + timedelta(minutes=15)
            self.handleConnection()
            # On arrondit les valeurss -- // syntaxe : round (nombre, nombre de chiffres apres la virgule si on veut) exemple : round(value, 1) = 1 chiffre apres la virgule
            self.SPTemp = round(float(self.tempVal),1)  # 1 chiffre apres la virgule
            self.PHValNet = round(float(self.PHVal),1)  # 1 chiffre apres la virgule
            # Updating devices values
            Domoticz.Debug("Updating Devices from Flipr Values")
            Devices[4].Update(nValue = 0,sValue = str(self.SPTemp))
            Devices[7].Update(nValue= 0, sValue=str(self.PHText))
            Devices[8].Update(nValue= 0, sValue=str(self.PHValNet))
            Devices[9].Update(nValue= 0, sValue=str(self.RedoxText))
            Devices[10].Update(nValue= 0, sValue=str(self.RedoxVal))
            Devices[11].Update(nValue= 0, sValue=str(self.batVal))

        # Regul regul
        # Filtration :
        if self.SPTemp > 30 :
            self.PumpTemp = 24
        else : 
            self.PumpTemp = round((self.SPTemp / 2))
            if self.PumpTemp < 6 :
                self.PumpTemp = 6
        Domoticz.Debug("Filtration Calculded duration is : " + str(self.PumpTemp))
        # Temp
        #self.setpoint = float(Devices[5].sValue)
        # PH
        # Redox

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
        AlexaAPI("La piscine est a {} degré, son P-H est {} avec une valeur de {} et le niveau de desinfectant est {} avec une valeur redox de {}".format(self.SPTemp, self.PHText, self.PHValNet, self.RedoxText, self.RedoxVal))
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
