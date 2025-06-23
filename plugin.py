"""
Swimming pool full control with Flipr Analyzer
Author: Ronelabs Team,
Version:    0.0.1: alpha
            0.0.2: beta
            0.1.1: test
"""
"""
<plugin key="SPWithFlipronDZ" name="ZZ - Swimming Pool Control with Flipr analyzer" author="Ronelabs Team" version="0.1.6" externallink="https://github.com/Erwanweb/SPWithFlipronDZ">
    <description>
        <h2>Swimming Pool Full Control</h2><br/>
        Easily implement in Domoticz an full control of Swimming Pool by using a Flipr analyzer<br/>
        <h3>Set-up and Configuration</h3>
    </description>
    <params>
        <param field="Address" label="Flipr module ID" width="300px" required="true" default=""/>
        <param field="Username" label="Flipr account Email" width="400px" required="true" default=""/>
        <param field="Password" label="Flipr account Psw" width="400px" required="true" default=""/>
        <param field="Mode2" label="filtration power" width="300px">
            <options>
                <option label="Overpowered +++" value="0.6"/>
                <option label="Overpowered ++" value="0.7"/>
                <option label="Overpowered" value="0.8"/>
                <option label="Normal" value="1"  default="true"/>
                <option label="Underpowered" value="1.2"/>
                <option label="Underpowered ++" value="1.3"/>
                <option label="Underpowered +++" value="1.4"/>
            </options>
        </param>
        <param field="Mode3" label="Actuators (0 for not): Pump, Heater, PH-, Chlor. (csv list of idx)" width="100px" required="true" default="0,0,0,0"/>
        <param field="Mode4" label="Outdoor temperature (csv list of idx)" width="200px" required="false" default="0"/>
        <param field="Mode5" label="Opt.In Flow Water Temp. (csv list of idx)" width="100px" required="flase" default=""/>
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
import time
import math
import html
import requests
import os
import subprocess as sp
from distutils.version import LooseVersion


class deviceparam:

    def __init__(self, unit, nvalue, svalue):
        self.unit = unit
        self.nvalue = nvalue
        self.svalue = svalue
        self.debug = False

class BasePlugin:
        
    def __init__(self):
        self.lastDateTime = None
        self.isStarted = False
        # default values of the Flipr
        self.PHVal = 0.0
        self.PHText = "Waiting values"
        self.RedoxVal = 0
        self.RedoxText = "Waiting values"
        self.FliprTemp = 10
        self.SPTemp = 10
        self.SPTempCheck = 5
        self.OppSPTempSens = False
        self.nexttemps = datetime.now()
        self.nextAnalyzer = datetime.now()
        self.PHValNet = 0
        self.RedoxValNet = 0
        self.FiltrationVarNextRefresh = datetime.now()
        self.PumpTemp = 0
        self.PLUGINstarteddtime = datetime.now()
        self.SunAtSouthHour = 14
        self.SunAtSouthMin = 0
        self.SunAtSouth = datetime.now()
        self.startpump = datetime.now()
        self.stoppump = datetime.now()
        self.Daily = datetime.now()
        self.pumpon = False
        self.Heating = False
        self.pumpidx = 0
        self.pumporderchangedtime = datetime.now()
        self.pumponstarttime = datetime.now()
        self.setpoint = 28
        self.heateridx = 0
        self.heaterorderchangedtime = datetime.now()
        self.PHValidx = 0
        self.RedoxValidx = 0
        self.TempSensors = []
        self.TempSensorsOpp = []
        self.pumppower = 1
        self.AntiFreeze = False
        self.PHanalyzer = False
        self.Redoxanalyzer = False
        self.OutTempSensors = []
        self.TempExt = 10
        self.nextouttemps = datetime.now()
        self.InternalsDefaults = {
            'SPTemp': 10,  # defaut temp
            'SPPH': 0,  # defaut ph
            'SPRedox': 0,  # defaut redox
            'SPTime': 0,  # defaut Calculated filtration time
            'OutTemp': 10}  # defaut outdoor temp
        self.Internals = self.InternalsDefaults.copy()
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
            Domoticz.Device(Name="PH", Unit=7, TypeName="Alert", Used=1).Create()
            devicecreated.append(deviceparam(7, 0, "waiting for value"))  # default is clear
        if 8 not in Devices:
            Domoticz.Device(Name="PH Value", Unit=8, Type=243, Subtype=31, Used=1).Create()
            devicecreated.append(deviceparam(8, 0, ""))  # default is 0
        if 9 not in Devices:
            Domoticz.Device(Name="Redox", Unit=9, TypeName="Alert", Used=1).Create()
            devicecreated.append(deviceparam(9, 0, "waiting for value"))  # default is clear
        if 10 not in Devices:
            Domoticz.Device(Name="Redox Value", Unit=10, Type=243, Subtype=31, Used=1).Create()
            devicecreated.append(deviceparam(10, 0, ""))  # default is 0
        if 11 not in Devices:
            Domoticz.Device(Name="Info", Unit=11, Type=243, Subtype=19, Used=1).Create()
            devicecreated.append(deviceparam(11, 0, "waiting for value"))  # default is clear
        if 12 not in Devices:
            Domoticz.Device(Name="Forced ECO", Unit=12, TypeName="Switch", Image=9).Create()
            devicecreated.append(deviceparam(12, 0, ""))  # default is Off
        if 13 not in Devices:
            Domoticz.Device(Name="Solar-PV+", Unit=13, TypeName="Switch", Image=9).Create()
            devicecreated.append(deviceparam(13, 0, ""))  # default is Off

        # if any device has been created in onStart(), now is time to update its defaults
        for device in devicecreated:
            Devices[device.unit].Update(nValue=device.nvalue, sValue=device.svalue)

        # splits parameters
        self.pumppower = float(Parameters["Mode2"])

        # splits additional parameters

        # pump and heater
        params3 = parseCSV(Parameters["Mode3"])
        if len(params3) == 4:
            self.pumpidx = CheckParam("Filtration", params3[0], 0)
            self.heateridx = CheckParam("Heater", params3[1], 0)
        else:
            Domoticz.Error("Error reading Mode3 parameters")

        # build lists of temp sensors

        params4 = parseCSV(Parameters["Mode4"])
        if len(params4) > 0:
            self.OutTempSensors = parseCSV(Parameters["Mode4"])
            Domoticz.Debug("Outdoor Temperature sensors = {}".format(self.TempSensors))
        else:
            Domoticz.Error("Error reading Mode4 parameters")

        params5 = parseCSV(Parameters["Mode5"])
        if len(params5) > 0 :
            self.OppSPTempSens = True
            self.TempSensorsOpp = parseCSV(Parameters["Mode5"])
            Domoticz.Debug("Additional Temperature sensors = {}".format(self.TempSensorsOpp))


        # analyzer
        # New Flipr API key and module ID
        # Recup du token Flipr
        self.email = Parameters["Username"]
        self.password = Parameters["Password"]
        self.module_id = Parameters["Address"]
        self.loginFlipr()

        # updating temp, timers and filtration
        now = datetime.now()
        self.readTemps()
        self.readOutTemps()
        self.readAnalyzer()
        Devices[3].Update(nValue=0, sValue=Devices[3].sValue)
        #self.readTemps = now - timedelta(hours=36)
        self.FiltrationVarNextRefresh = now - timedelta(hours=36)
        self.pumporderchangedtime = now - timedelta(hours=36)

        # Check if the used control mode is ok
        if (Devices[1].sValue == "10"):
            self.powerOn = 1
            self.forced = 0

        elif (Devices[1].sValue == "20"):
            self.powerOn = 1
            self.forced = 1

        elif (Devices[1].sValue == "0"):
            self.powerOn = 0
            self.forced = 0

        # update PH and Redox to 0 at starting
        Devices[8].Update(nValue=0, sValue="0")
        Devices[7].Update(nValue=0, sValue="Waiting values")
        Devices[10].Update(nValue=0, sValue="0")
        Devices[9].Update(nValue=0, sValue="Waiting values")
                
        # Set domoticz heartbeat to 20 s (onheattbeat() will be called every 20 )
        Domoticz.Heartbeat(20)

        # creating user variable if doesn't exist or update it
        self.getUserVar()

        # Now we can enabling the plugin
        self.isStarted = True


# Plugin STOP  ---------------------------------------------------------

    def onStop(self):
        Domoticz.Debug("onStop called")
        # prevent error messages during disabling plugin
        self.isStarted = False

# DZ Widget actions  ---------------------------------------------------

    def onCommand(self, Unit, Command, Level, Color):

        Domoticz.Debug("onCommand called for Unit {}: Command '{}', Level: {}".format(Unit, Command, Level))

        if (Unit == 1):
            Devices[1].Update(nValue=self.powerOn, sValue=str(Level))
            if (Devices[1].sValue == "10"):  # Mode auto
                self.powerOn = 1
                self.forced = 0
                Devices[1].Update(nValue=1, sValue=Devices[1].sValue)
            elif (Devices[1].sValue == "20"):  # Manual Mode
                self.powerOn = 1
                self.forced = 1
                Devices[1].Update(nValue=1, sValue=Devices[1].sValue)
            else : # Off
                Devices[1].Update(nValue=0, sValue=Devices[1].sValue)
                self.powerOn = 0
                self.forced = 0
                Devices[2].Update(nValue=self.powerOn, sValue=Devices[2].sValue)
            # Update child devices
            if not (Devices[2].sValue == "0"):  # Heating Off
                Devices[2].Update(nValue=self.powerOn, sValue=Devices[2].sValue)

        if (Unit == 2):  # Heating
            Devices[2].Update(nValue=self.powerOn, sValue=str(Level))
            if (Devices[2].sValue == "0"):  # Off
                Devices[2].Update(nValue=0, sValue=Devices[2].sValue)
            else :
                Devices[2].Update(nValue=self.powerOn, sValue=str(Level))

        if (Unit == 5):  # Setpoint
            Devices[5].Update(nValue=self.powerOn, sValue=str(Level))
            self.setpoint = round(float(Devices[5].sValue))

        self.onHeartbeat()


# Heartbeat  ---------------------------------------------------

    def onHeartbeat(self):

        Domoticz.Debug("onHeartbeat called")
        now = datetime.now()

        # Recup user variables
        self.PHVal = self.Internals['SPPH']
        self.RedoxVal = self.Internals['SPRedox']
        self.PumpTemp = self.Internals['SPTime']
        self.SPTemp = self.Internals['SPTemp']
        self.TempExt = self.Internals['OutTemp']

      # Regul-regul --------------------------------------------------

        if not Devices[1].sValue == "0":  # Off
            if Devices[1].sValue == "10":  # auto
                self.powerOn = 1
                self.forced = 0
            if Devices[1].sValue == "20":  # forced
                self.powerOn = 1
                self.forced = 1
        else :
            self.powerOn = 0
            self.forced = 0

        # Check Temp ---------------------------------------------------

        if self.nexttemps + timedelta(minutes=5) <= now:
            self.readTemps()

        self.SPTempCheck = round(float(self.SPTemp))

        if self.nextouttemps + timedelta(minutes=10) <= now:
            self.readOutTemps()

        # Check Analyzer------------------------------------------------

        if self.pumpon :
            if self.pumponstarttime + timedelta(minutes=15) <= now:
                if self.nextAnalyzer + timedelta(minutes=60) <= now:
                    self.readAnalyzer()

        # Filtration ---------------------------------------------------
        # Check mode and set all good
        if Devices[1].sValue == "0": # Off
            self.forced = 0
            self.pumpon = False
            if Devices[3].nValue == 1:
                Devices[3].Update(nValue=0, sValue=Devices[3].sValue)
                DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Off".format(self.pumpidx))
                self.pumporderchangedtime = datetime.now()
            Domoticz.Debug("System is OFF - ALL OFF")
            Devices[11].Update(nValue=0, sValue="OFF")
        elif Devices[1].sValue == "20": # Manual
            self.forced = 1
            if Devices[3].nValue == 0:
                Devices[3].Update(nValue=1, sValue=Devices[3].sValue)
                DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=On".format(self.pumpidx))
                self.pumpon = True
                self.pumporderchangedtime = datetime.now()
                self.pumponstarttime = datetime.now()
            Domoticz.Debug("System is ON - Filtration in MANUAL Mode")
            Devices[11].Update(nValue=0, sValue="ON - Manual Mode")
        else : # Auto
            Domoticz.Debug("System is ON - Filtration in AUTO Mode")
            self.forced = 0
            # If Auto :
            now = datetime.now()
            # We check time needed for filtration, every 15 minutes
            if self.FiltrationVarNextRefresh <= now:
                #self.FiltrationVarNextRefresh = now + timedelta(minutes=30)
                if self.SPTempCheck >= 30:
                    self.PumpTemp = 24
                    self.FiltrationVarNextRefresh = now + timedelta(hours=12)
                    Domoticz.Debug("Filtration is all the time because of high SP Temp at : " + str(self.SPTemp))
                    #Devices[16].Update(nValue=0, sValue="Auto - Calc. 24h/24")
                    #Devices[16].Update(nValue=0, sValue="Auto - "+ str(self.SPTemp))
                else :
                    if self.SPTempCheck <= 15:
                        if self.TempExt <= -2 :
                        #if self.SPTempCheck <= 2:
                            self.PumpTemp = 24
                            self.AntiFreeze = True
                            self.FiltrationVarNextRefresh = now + timedelta(minutes=30)
                            Domoticz.Debug("Filtration is in AntiFreeze function because of low out. Temp. and exactly at : " + str(self.TempExt))
                            #Devices[16].Update(nValue=0, sValue="Auto - Calc. 2h")
                        elif self.SPTempCheck <= 10:
                            self.PumpTemp = round(2 * self.pumppower, 1)
                            self.AntiFreeze = False
                            self.FiltrationVarNextRefresh = now + timedelta(hours=2)
                            Domoticz.Debug("Filtration is fixed at 2h per day because SP Temp lower than 10 and exactly at : " + str(self.SPTemp))
                            #Devices[16].Update(nValue=0, sValue="Auto - Calc. 2h")
                        else :
                            self.SPTempCheck = round(3 * self.pumppower, 1)
                            self.AntiFreeze = False
                            self.FiltrationVarNextRefresh = now + timedelta(hours=2)
                            Domoticz.Debug("Filtration is fixed at 3h per day because low SP Temp between 10 and 15, and exactly at : " + str(self.SPTemp))
                            #Devices[16].Update(nValue=0, sValue="Auto - Calc. 3h")
                    else :
                        self.AntiFreeze = False
                        if self.SPTempCheck <= 24:
                            self.PumpTemp = round((self.SPTempCheck / 3) * self.pumppower, 1)
                            self.FiltrationVarNextRefresh = now + timedelta(hours=4)
                            Domoticz.Debug("Filtration calcul. dur. is 1/3 of SP Temp and so fixed at (h): " + str(self.PumpTemp))
                            #Devices[16].Update(nValue=0, sValue="Auto - Calc. 3h")
                        else:
                            self.PumpTemp = round((self.SPTempCheck / 2) * self.pumppower, 1)
                            self.FiltrationVarNextRefresh = now + timedelta(hours=4)
                            Domoticz.Debug("Filtration calcul. dur. is 1/2 of SP Temp and so fixed at (h): " + str(self.PumpTemp))
                # modif des users variable
                self.Internals['SPPH'] = self.PHVal
                self.Internals['SPRedox'] = self.RedoxVal
                self.Internals['SPTime'] = self.PumpTemp
                self.Internals['SPTemp'] = self.SPTemp
                self.Internals['OutTemp'] = self.TempExt
                self.saveUserVar()  # update user variables with latest values
                # Now we set timers
                jsonData = DomoticzAPI("type=command&param=getSunRiseSet")
                if jsonData :
                # datetime(year, month, day, hour, minute, second, microsecond)
                    SunAtSouthHour = int(jsonData['SunAtSouth'].split(':')[0])
                    SunAtSouthMin = int(jsonData['SunAtSouth'].split(':')[1])
                    if SunAtSouthMin >= 59 :
                        SunAtSouthMin = 59
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
                    DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=On".format(self.pumpidx))
                    self.pumporderchangedtime = datetime.now()
                    self.pumponstarttime = datetime.now()
                Domoticz.Debug("Pump is ON since "+ str(self.startpump))
                Domoticz.Debug("Filtration calcul. dur. is : " + str(self.PumpTemp))
                Domoticz.Debug("Pump will turn OFF at " + str(self.stoppump))
            else :
                self.pumpon = False # We are not yet in the period of filtration
                if Devices[3].nValue == 1:
                    Devices[3].Update(nValue=0, sValue=Devices[3].sValue)
                    DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Off".format(self.pumpidx))
                    self.pumporderchangedtime = datetime.now()
                Domoticz.Debug("Pump is OFF - Will turn ON at " + str(self.startpump))
                Domoticz.Debug("Next Filtration calcul. dur. will be : " + str(self.PumpTemp))
            if self.pumpon :
                if self.stoppump < now : # We are in the period of filtration and we leave it, stop pump
                    self.pumpon = False
                    if Devices[3].nValue == 1:
                        Devices[3].Update(nValue=0, sValue=Devices[3].sValue)
                        DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Off".format(self.pumpidx))
                        self.pumporderchangedtime = datetime.now()
                    Domoticz.Debug("Pump turned OFF after daily period at : " + str(self.stoppump))
                    Domoticz.Debug("Past Filtration calcul. dur. was : " + str(self.PumpTemp))
            self.PumpTempRounded = round(float(self.PumpTemp))  # pas chiffre apres la virgule
            #Devices[11].Update(nValue=0, sValue="Auto - Calcul. {}H/24".format(self.PumpTempRounded))
            #(self.startpump.hour, self.startpump.minute, self.stoppump.hour, self.stoppump.minute)
            T1 = self.startpump
            Domoticz.Debug("T1 is {}".format(T1))
            T2 = self.stoppump
            Domoticz.Debug("T2 is {}".format(T2))
            StartH = T1.strftime("%-H")
            StartM = T1.strftime("%M")
            StopH = T2.strftime("%-H")
            StopM = T2.strftime("%M")
            Domoticz.Debug("Start is {}:{} stop at {}:{} ".format(StartH, StartM, StopH, StopM))
            if self.AntiFreeze :
                Devices[11].Update(nValue=0, sValue="Auto - Protect. Antigel - TºExt {}ºC Eau {}ºC".format(self.TempExt, self.SPTemp))
            else :
                Devices[11].Update(nValue=0, sValue="Auto - Calcul.~{}h : {}:{}--{}:{}".format(self.PumpTempRounded, StartH, StartM, StopH, StopM))
        # be sure each 15 mins relay take the real good order and position, main for auto mode
        if not self.forced :
            if self.pumporderchangedtime + timedelta(minutes=15) < now:
                self.pumporderchangedtime = datetime.now()
                if self.pumpon :
                    DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=On".format(self.pumpidx))
                else :
                    DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Off".format(self.pumpidx))
        else :
            if Devices[3].nValue == 0:
                Devices[3].Update(nValue=1, sValue=Devices[3].sValue)
                DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=On".format(self.pumpidx))
                self.pumpon = True
                self.pumponstarttime = datetime.now()

        # Temp ---------------------------------------------------
        if self.powerOn and Devices[3].nValue == 1:  # On in manual or in Auto and filtration is On
            if (Devices[2].sValue == "20"): # Heating forced
                self.Heating = True
                if Devices[6].nValue == 0:
                    Devices[6].Update(nValue=1, sValue=Devices[6].sValue)
                    Domoticz.Debug("Heating is FORCED ON")
            elif (Devices[2].sValue == "10"): # Heating Auto with 1 for hysterisis low
                if self.SPTemp < (float(Devices[5].sValue) - 0.3):
                    self.Heating = True
                    if Devices[6].nValue == 0:
                        Devices[6].Update(nValue=1, sValue=Devices[6].sValue)
                    Domoticz.Debug("Heating is AUTO ON - Heating requested")
                if self.SPTemp > (float(Devices[5].sValue) + 0.2):
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

# Read Flipr Analyzer---------------------------------------------------------------------------------------------
    def loginFlipr(self):
        Domoticz.Debug("Authenticating with Flipr API...")
        try:
            login_url = "https://api.goflipr.com/users/sign_in"
            credentials = {"user": {"email": self.email, "password": self.password}}
            response = requests.post(login_url, json=credentials, timeout=10)
            if response.status_code == 200:
                self.token = response.json()["authentication_token"]
                Domoticz.Debug(f"Flipr Token: {self.token}")
            else:
                Domoticz.Error(f"Flipr login failed: HTTP {response.status_code}")
        except Exception as e:
            Domoticz.Error(f"Flipr login exception: {str(e)}")

    def readAnalyzer(self):
        Domoticz.Debug("Fetching Flipr data...")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Token {self.token}"
        }
        url = f"https://api.goflipr.com/modules/{self.module_id}/last_measurement"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.PHVal = round(float(data["ph"]), 1)
                self.RedoxVal = round(float(data["orp"]), 0)
                self.FliprTemp = round(float(data["temperature"]), 1)
                #Devices[8].Update(nValue=0, sValue=str(self.PHVal))
                #Devices[10].Update(nValue=0, sValue=str(self.RedoxVal))
                #Devices[4].Update(nValue=0, sValue=str(self.SPTemp))
                Domoticz.Debug(f"Flipr: PH={self.PHVal}, Redox={self.RedoxVal}, Temp={self.FliprTemp}")
            elif response.status_code == 401:
                Domoticz.Error("Flipr token expired. Re-authenticating...")
                self.loginFlipr()
            else:
                Domoticz.Error(f"Flipr API HTTP error: {response.status_code}")
        except Exception as e:
            Domoticz.Error(f"Flipr API exception: {str(e)}")

        # Mettre à jour les devices Domoticz
        Devices[8].Update(nValue=0, sValue=str(self.PHVal))
        if 7 in Devices:
            if 7.2 <= self.PHVal < 7.6:
                Devices[7].Update(nValue=1, sValue="Parfait")
            elif 6.9 <= self.PHVal < 7.2:
                Devices[7].Update(nValue=3, sValue="Légèrement bas")
            elif self.PHVal < 6.9:
                Devices[7].Update(nValue=4, sValue="Trop bas")
            elif 7.6 <= self.PHVal < 7.8:
                Devices[7].Update(nValue=3, sValue="Légèrement haut")
            else:
                Devices[7].Update(nValue=4, sValue="Trop haut")

        Devices[10].Update(nValue=0, sValue=str(self.RedoxVal))
        if 9 in Devices:
            if 650 <= self.RedoxVal < 750:
                Devices[9].Update(nValue=1, sValue="Parfait")
            elif 620 <= self.RedoxVal < 650:
                Devices[9].Update(nValue=3, sValue="Légèrement bas")
            elif self.RedoxVal < 620:
                Devices[9].Update(nValue=4, sValue="Trop bas")
            elif 751 <= self.RedoxVal < 800:
                Devices[9].Update(nValue=3, sValue="Légèrement haut")
            else:
                Devices[9].Update(nValue=4, sValue="Trop haut")

        if not self.pumpon :
            self.SPTemp = round(float(self.FliprTemp), 1)
            self.SPTempCheck = round(float(self.SPTemp))
            Devices[4].Update(nValue=0, sValue=str(self.SPTemp))

        # modif des users variable
        self.Internals['SPPH'] = self.PHVal
        self.Internals['SPRedox'] = self.RedoxVal
        self.Internals['SPTime'] = self.PumpTemp
        self.Internals['SPTemp'] = self.SPTemp
        self.Internals['OutTemp'] = self.TempExt
        self.saveUserVar()  # update user variables with latest values


# Read water temp-------------------------------------------------------------------------------------------------
    def readTemps(self):
        if not self.OppSPTempSens :
            Domoticz.Debug("No optional in tube temp sensors")
            self.SPTemp = round(float(self.FliprTemp), 1)
            self.SPTempCheck = round(float(self.SPTemp))
        else :
            Domoticz.Debug("readTemps called")
            self.nexttemps = datetime.now()
            # fetch all the devices from the API and scan for sensors
            noerror = True
            listintemps = []
            devicesAPI = DomoticzAPI("type=command&param=getdevices&filter=temp&used=true&order=Name")
            if devicesAPI:
                for device in devicesAPI["result"]:  # parse the devices for temperature sensors
                    idx = int(device["idx"])
                    if self.OppSPTempSens :
                        if self.pumpon :
                            now = datetime.now()
                            if self.pumponstarttime + timedelta(minutes=15) <= now:
                                if idx in self.TempSensorsOpp:
                                    if "Temp" in device:
                                        Domoticz.Debug(
                                            "device: {}-{} = {}".format(device["idx"], device["Name"], device["Temp"]))
                                        listintemps.append(device["Temp"])
                                    else:
                                        Domoticz.Error(
                                            "device: {}-{} is not a Temperature sensor".format(device["idx"], device["Name"]))

            # calculate the average temperature
            nbtemps = len(listintemps)
            if nbtemps > 0:
                self.intemp = round(sum(listintemps) / nbtemps, 1)
                Devices[4].Update(nValue=0, sValue=str(self.intemp))  # update the dummy device
                self.SPTemp = round(float(self.intemp),1)
                self.SPTemp = round((self.SPTemp + self.FliprTemp) / 2, 1)
                self.SPTempCheck = round(float(self.SPTemp))
            else:
                Domoticz.Debug("No optional SP Temperature found... ")
                noerror = False

            Domoticz.Debug("SP Temperature = {}".format(self.SPTemp))

            # modif des users variable
            self.Internals['SPPH'] = self.PHVal
            self.Internals['SPRedox'] = self.RedoxVal
            self.Internals['SPTime'] = self.PumpTemp
            self.Internals['SPTemp'] = self.SPTemp
            self.Internals['OutTemp'] = self.TempExt
            self.saveUserVar()  # update user variables with latest values

            #self.OutTempSensors = []
            self.TempExt = 10

            return noerror

# Read outdoor temp-------------------------------------------------------------------------------------------------
    def readOutTemps(self):
        Domoticz.Debug("readOutTemps called")
        self.nextouttemps = datetime.now()
        # fetch all the devices from the API and scan for sensors
        noerror = True
        listintemps = []
        devicesAPI = DomoticzAPI("type=command&param=getdevices&filter=temp&used=true&order=Name")
        if devicesAPI:
            for device in devicesAPI["result"]:  # parse the devices for temperature sensors
                idx = int(device["idx"])
                if idx in self.OutTempSensors:
                    if "Temp" in device:
                        Domoticz.Debug("device: {}-{} = {}".format(device["idx"], device["Name"], device["Temp"]))
                        listintemps.append(device["Temp"])
                    else:
                        Domoticz.Error(
                            "device: {}-{} is not a Temperature sensor".format(device["idx"], device["Name"]))
                if self.OppSPTempSens:
                    if self.pumpon:
                        now = datetime.now()
                        if self.pumponstarttime + timedelta(minutes=15) <= now:
                            if idx in self.TempSensorsOpp:
                                if "Temp" in device:
                                    Domoticz.Debug(
                                        "device: {}-{} = {}".format(device["idx"], device["Name"], device["Temp"]))
                                    listintemps.append(device["Temp"])
                                else:
                                    Domoticz.Error(
                                        "device: {}-{} is not a Temperature sensor".format(device["idx"],
                                                                                           device["Name"]))

        # calculate the average temperature
        nbtemps = len(listintemps)
        if nbtemps > 0:
            self.intemp = round(sum(listintemps) / nbtemps, 1)
            #Devices[4].Update(nValue=0, sValue=str(self.intemp))  # update the dummy device
            self.TempExt = round(float(self.intemp), 1)
        else:
            Domoticz.Debug("No Outdoor Temperature found... ")
            noerror = False

        Domoticz.Debug("Outdoor Temperature = {}".format(self.SPTemp))

        # modif des users variable
        self.Internals['SPPH'] = self.PHVal
        self.Internals['SPRedox'] = self.RedoxVal
        self.Internals['SPTime'] = self.PumpTemp
        self.Internals['SPTemp'] = self.SPTemp
        self.Internals['OutTemp'] = self.TempExt
        self.saveUserVar()  # update user variables with latest values

        return noerror

# User variable  ---------------------------------------------------

    def getUserVar(self):
        variables = DomoticzAPI("type=command&param=getuservariables")
        if variables:
            # there is a valid response from the API but we do not know if our variable exists yet
            novar = True
            varname = Parameters["Name"] + "-InternalVariables"
            valuestring = ""
            if "result" in variables:
                for variable in variables["result"]:
                    if variable["Name"] == varname:
                        valuestring = variable["Value"]
                        novar = False
                        break
            if novar:
                # create user variable since it does not exist
                Domoticz.Debug("User Variable {} does not exist. Creation requested".format(varname), "Verbose")

                # check for Domoticz version:
                # there is a breaking change on dzvents_version 2.4.9, API was changed from 'saveuservariable' to 'adduservariable'
                # using 'saveuservariable' on latest versions returns a "status = 'ERR'" error

                # get a status of the actual running Domoticz instance, set the parameter accordigly
                parameter = "saveuservariable"
                domoticzInfo = DomoticzAPI("type=command&param=getversion")
                if domoticzInfo is None:
                    Domoticz.Error("Unable to fetch Domoticz info... unable to determine version")
                else:
                    if domoticzInfo and LooseVersion(domoticzInfo["dzvents_version"]) >= LooseVersion("2.4.9"):
                        Domoticz.Debug("Use 'adduservariable' instead of 'saveuservariable'", "Verbose")
                        parameter = "adduservariable"

                # actually calling Domoticz API
                DomoticzAPI("type=command&param={}&vname={}&vtype=2&vvalue={}".format(parameter, varname, str(self.InternalsDefaults)))
                self.Internals = self.InternalsDefaults.copy()  # we re-initialize the internal variables
            else:
                try:
                    self.Internals.update(eval(valuestring))
                except:
                    self.Internals = self.InternalsDefaults.copy()
                return
        else:
            Domoticz.Error("Cannot read the uservariable holding the persistent variables")
            self.Internals = self.InternalsDefaults.copy()


    def saveUserVar(self):
        varname = Parameters["Name"] + "-InternalVariables"
        DomoticzAPI("type=command&param=updateuservariable&vname={}&vtype=2&vvalue={}".format(varname, str(self.Internals)))

# Global  ---------------------------------------------------

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

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
