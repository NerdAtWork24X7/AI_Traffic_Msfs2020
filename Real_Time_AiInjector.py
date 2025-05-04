import os
import pandas as pd
import time
from selenium import webdriver as uc
#import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from sqlalchemy import create_engine, text
from timezonefinder import TimezoneFinder
import pytz
from tzlocal import get_localzone
import re
from datetime import datetime,timedelta
import warnings
from geopy.distance import geodesic
from geopy import Point
import random
import xml.etree.ElementTree as ET
import time
from Sim_Connect_Custom.SimConnect import SimConnect 
#import SimConnect
import json
import requests
from haversine import haversine, Unit
import math
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

warnings.filterwarnings('ignore')


flt_plan = ""


SRC_AIRPORT_IACO = ""
DES_AIRPORT_IACO = ""
SRC_ACTIVE_RUNWAY = ""
DES_ACTIVE_RUNWAY = ""

ACTIVE_RUNWAY_TAKEOFF = ""
ACTIVE_RUNWAY_LANDING = ""

USE_FSTRAFFIC_LIVERY = True
USE_AIG_LIVERY = True
USE_FSLTL_LIVERY = True

MAX_ARRIVAL_AI_FLIGHTS = 30
MAX_DEPARTURE_AI_FLIGHTS = 30
MAX_CRUISE_AI_FLIGHTS = 30
MAX_PARKED_AI_FLIGHTS = 50

CRUISE_ALTITUDE = 10000
SRC_GROUND_RANGE = 50
DES_GROUND_RANGE = 150
SPWAN_DIST = 200
SPWAN_ALTITUDE = 20000

GROUND_INJECTION_TIME_ARR = 2
GROUND_INJECTION_TIME_DEP = 2
CRUISE_INJECTION_TIME = 5
DEPART_REALTIME = True

MIN_SEPARATION = 10 #KM


ADBS_key = ""
ADBS_host = ""
simbrief_username = ""

current_dir = os.getcwd()


class Common:
   
  chrome_options = Options()
  chrome_options.add_argument("--headless")  # Run in headless mode
  chrome_options.add_argument("--no-sandbox")  # Disable sandboxing (sometimes required)
  chrome_options.add_argument("--disable-dev-shm-usage")  # Disable /dev/shm usage (optional)
  chrome_options.add_argument('--disable-gpu')
  chrome_options.add_argument('--enable-unsafe-swiftshader')
  chrome_options.add_argument('log-level=3')
  chrome_options.add_argument('-uc')

   
  engine_airport_db = create_engine('sqlite:///./Database/Airport.sqlite')
  engine_airline_db = create_engine('sqlite:///./Database/callsign_data.sqlite')
  engine_approach_db = create_engine('sqlite:///./Database/Approach.sqlite')
  engine_waypoint_db = create_engine('sqlite:///./Database/Waypoints.sqlite')

  Global_req_id = 1000
  
  Retry_SRC = 0
  Retry_DES = 0

 
  Src_Airport = pd.DataFrame(columns=['Src', 'Lat', "Lon","Altitude"])
  Des_Airport = pd.DataFrame(columns=['Src', 'Lat', "Lon","Altitude"]) 

  Shift_Src_Cruise = False
  Shift_Cruise_Des = False

  prev_model  = ""
  prev_icao = ""

  Skip_injection = 1 # For Flight spacing

  State_Machine = 0
  
  def Read_Config_file():
    global ADBS_key,ADBS_host,simbrief_username
    global USE_FSTRAFFIC_LIVERY,USE_AIG_LIVERY,MAX_ARRIVAL_AI_FLIGHTS,MAX_DEPARTURE_AI_FLIGHTS,MAX_CRUISE_AI_FLIGHTS
    global MAX_PARKED_AI_FLIGHTS,CRUISE_ALTITUDE,SRC_GROUND_RANGE,DES_GROUND_RANGE,SPWAN_DIST,USE_FSLTL_LIVERY,DEPART_REALTIME
    global SPWAN_ALTITUDE,GROUND_INJECTION_TIME_ARR,GROUND_INJECTION_TIME_DEP,CRUISE_INJECTION_TIME,MIN_SEPARATION
    
    try:
      with open('config_user.json', 'r') as file:
        data = json.load(file)
        ADBS_key = data["key"]
        ADBS_host = data["host"]
        simbrief_username = data["simbrief_username"]
    except:
      ("print config_user.json file not found")  
    
    try:
      with open('config_msfs.json', 'r') as file:
        data = json.load(file)
        USE_FSTRAFFIC_LIVERY = bool(data["USE_FSTRAFFIC_LIVERY"])
        USE_AIG_LIVERY = bool(data["USE_AIG_LIVERY"])
        USE_FSLTL_LIVERY = bool(data["USE_FSLTL_LIVERY"])
        DEPART_REALTIME = bool(data["DEPART_REALTIME"])
        
        MAX_ARRIVAL_AI_FLIGHTS = int(data["MAX_ARRIVAL_AI_FLIGHTS"])
        MAX_DEPARTURE_AI_FLIGHTS = int(data["MAX_DEPARTURE_AI_FLIGHTS"])
        MAX_CRUISE_AI_FLIGHTS = int(data["MAX_CRUISE_AI_FLIGHTS"])
        MAX_PARKED_AI_FLIGHTS = int(data["MAX_PARKED_AI_FLIGHTS"])
        
        CRUISE_ALTITUDE = int(data["CRUISE_ALTITUDE"])
        SRC_GROUND_RANGE = int(data["SRC_GROUND_RANGE"])
        DES_GROUND_RANGE = int(data["DES_GROUND_RANGE"])
        SPWAN_DIST = int(data["SPWAN_DIST"])
        SPWAN_ALTITUDE = int(data["SPWAN_ALTITUDE"])
        
        GROUND_INJECTION_TIME_ARR = int(data["GROUND_INJECTION_TIME_ARR"])
        GROUND_INJECTION_TIME_DEP = int(data["GROUND_INJECTION_TIME_DEP"])
        CRUISE_INJECTION_TIME = int(data["CRUISE_INJECTION_TIME"])
        
        MIN_SEPARATION = int(data["MIN_SEPARATION"])
    except:
      ("print config_msfs.json file not found")  

  def Get_Flight_plan():
    global SRC_AIRPORT_IACO,DES_AIRPORT_IACO,SRC_ACTIVE_RUNWAY,DES_ACTIVE_RUNWAY
    global simbrief_username

    if SRC_ACTIVE_RUNWAY == "" or DES_ACTIVE_RUNWAY == "" or SRC_AIRPORT_IACO == "" or DES_AIRPORT_IACO == "":
      response = requests.get("https://www.simbrief.com/api/xml.fetcher.php?username=" + simbrief_username)
  
      xml_data = response.text
      
      root = ET.fromstring(xml_data)
      # Extract information from the XML
      SRC_AIRPORT_IACO = root.find('api_params/orig').text
      DES_AIRPORT_IACO = root.find('api_params/dest').text
      Route = root.find('api_params/route').text
      SRC_ACTIVE_RUNWAY = root.find('api_params/origrwy').text
      DES_ACTIVE_RUNWAY = root.find('api_params/destrwy').text

    
    if SRC_ACTIVE_RUNWAY == "" or DES_ACTIVE_RUNWAY == "" or SRC_AIRPORT_IACO == "" or DES_AIRPORT_IACO == "":
      print("ERROR:: Please file a flight plan in Simbrief") 
      exit(1)
   
     
  def Get_Timezone(src,specific_time_str):
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+src+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    lon = src_df.iloc[-1]["lonx"]
    lat = src_df.iloc[-1]["laty"]
    
    tf = TimezoneFinder()
    timezone = tf.timezone_at(lng=lon, lat=lat)
    from_zone = pytz.timezone(timezone)
    to_zone = get_localzone()
    
    specific_time = datetime.strptime(specific_time_str, '%Y-%m-%d %H:%M:%S')
    localized_time = from_zone.localize(specific_time)
    converted_time = localized_time.astimezone(to_zone)
    
    return converted_time


  def decimal_to_dms(degrees, is_latitude=True):

    abs_deg = abs(degrees)
    d = int(abs_deg)
    minutes = (abs_deg - d) * 60
    m = int(minutes)
    seconds = (minutes - m) * 60
    s = round(seconds, 2) 

    if is_latitude:
        direction = "N" if degrees >= 0 else "S"
    else:
        direction = "E" if degrees >= 0 else "W"
    
    return f"{direction}{d}° {m}' {s}\""


  def format_coordinates(lat, lon, altitude):

    lat_dms = Common.decimal_to_dms(lat, is_latitude=True)
    lon_dms = Common.decimal_to_dms(lon, is_latitude=False)
    
    altitude_str = f"{altitude:+010.2f}"
    
    return f"{lat_dms},{lon_dms},{altitude_str}"

   
  def get_close_waypoint(src_lat,src_lon,des,des_lat,des_lon,max_dis,min_dis):

    qry_str = f"""SELECT "_rowid_",* FROM "main"."waypoint" WHERE "airport_ident" LIKE '%""" + des +"""%'"""
    with Common.engine_waypoint_db.connect() as conn:
      des_waypoint_df = pd.read_sql(sql=qry_str, con=conn.connection)

    point_src = (src_lat,src_lon) 
    point_des = (des_lat,des_lon) 
    df_close_waypoint = pd.DataFrame()
    pre_dis = 99999999.0
    for index, waypoint in des_waypoint_df.iterrows():
      point2 = (waypoint["laty"], waypoint["lonx"])
      Cur_Dis = geodesic(point_src, point2).km
      Des_Dis = geodesic(point_des, point2).km
      if Cur_Dis < pre_dis and Des_Dis < max_dis and Des_Dis > min_dis:
        df_close_waypoint = waypoint
        pre_dis = Cur_Dis
    
    return df_close_waypoint
 

  def Get_flight_match(callsign,typecode):
    global USE_FSLTL_LIVERY,USE_AIG_LIVERY,USE_FSTRAFFIC_LIVERY
    

    livery_found = False
    try: 
      IATA_call = callsign[:2]
      with Common.engine_airline_db.connect() as conn:
        qry_str = '''SELECT "_rowid_",* FROM "main"."callsigns" WHERE "iata" LIKE '%'''+IATA_call+'''%' '''
        src_df = pd.read_sql(sql=qry_str, con=conn.connection)

      for index, icao_iata in src_df.iterrows():
        icao = icao_iata["icao"]
        new_callsign = callsign.replace(IATA_call,icao)
        if livery_found == False and USE_AIG_LIVERY == True:  
          tree = ET.parse('AIG.vmr')
          root_AIG = tree.getroot()
          for model_match_rule in root_AIG.findall('ModelMatchRule'):
            # Check if the TypeCode matches
            if icao == model_match_rule.get('CallsignPrefix'):
              model_name_cur = (model_match_rule.get('ModelName')).split("//")
              if model_match_rule.get('TypeCode') == typecode :
                model_name_cur = (model_match_rule.get('ModelName')).split("//")
                livery_found = True
                break
        
        if livery_found == False and USE_FSTRAFFIC_LIVERY == True:  
          tree = ET.parse('FSTraffic.vmr')
          root_FSTraffic = tree.getroot()
          for model_match_rule in root_FSTraffic.findall('ModelMatchRule'):
            # Check if the TypeCode matches
            if icao == model_match_rule.get('CallsignPrefix'):
              model_name_cur = (model_match_rule.get('ModelName')).split("//")
              if model_match_rule.get('TypeCode') == typecode:
                model_name_cur = (model_match_rule.get('ModelName')).split("//")
                livery_found = True
                break   
        
        if livery_found == False and USE_FSLTL_LIVERY == True: 
          tree = ET.parse('FSLTL_Rules.vmr')
          root_Fsltl = tree.getroot()
          # Iterate over all ModelMatchRule elements
          for model_match_rule in root_Fsltl.findall('ModelMatchRule'):
            # Check if the TypeCode matches
            if icao == model_match_rule.get('CallsignPrefix'):
                model_name_cur = (model_match_rule.get('ModelName')).split("//")
                if model_match_rule.get('TypeCode') == typecode:
                  model_name_cur = (model_match_rule.get('ModelName')).split("//")
                  livery_found = True
                  break 
      
        if livery_found == True:
          Common.prev_model  = random.choice(model_name_cur)
          Common.prev_icao = icao
          break          
      
      model_name = random.choice(model_name_cur)
      #print(model_name)
  
    except:
      print("Error in flight matching")

    if livery_found == False:
      if Common.prev_model == "":
        #Default Livaery
        model_name = "FSLTL_FSPXAI_B788_Airindia"
        new_callsign = "AIC" + str(random.randint(100,9999))
      else:
        model_name = Common.prev_model
        new_callsign = Common.prev_icao + str(random.randint(100,9999))

  
    return model_name , new_callsign

      
  def Get_User_Aircraft():
    
    sm.AIAircraft_GetPosition(2,1)
    time.sleep(1)
    
    
    point1=(SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Lat"] ,SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Log"])
    
    #Get Src Distance
    point2= (Common.Src_Airport.iloc[-1]["Lat"] ,Common.Src_Airport.iloc[-1]["Lon"])
    dist = geodesic(point1, point2).km
    SimConnect.MSFS_User_Aircraft.loc[1,"Dis_Src"] = dist

    #Get Des Distance
    point2= (Common.Des_Airport.iloc[-1]["Lat"] ,Common.Des_Airport.iloc[-1]["Lon"])
    dist = geodesic(point1, point2).km
    SimConnect.MSFS_User_Aircraft.loc[1,"Dis_Des"] = dist

    #print(SimConnect.MSFS_User_Aircraft)

  def CopyArrivalCruise(airport):
    try:
      for index, flight in SimConnect.MSFS_Cruise_Traffic.iterrows(): 
        last_element = len(SimConnect.MSFS_AI_Arrival_Traffic)
        Estimate_time = 0.0
        Call = flight["Call"]
        Type = flight["Type"]
        Src  = flight["Src"]
        Des = flight["Des"]
        Cur_Lat = flight["Cur_Lat"]
        Cur_Log = flight["Cur_Log"]
        Prv_Lat = 0.0
        Prv_Log = 0.0
        Par_log = 0.0
        Par_lat = 0.0
        altitude = flight["Altitude"]
        Stuck = 0
        Req_Id = flight["Req_Id"]
        Obj_Id = flight["Obj_Id"]
        Airspeed = flight["Speed"]
        Landing_light = 0.0
        ON_Ground = 0.0
        Heading = 0.0
        Gear = 0.0
        Landed = 0
        if Des == airport:
          SimConnect.MSFS_AI_Arrival_Traffic.loc[last_element] = [Estimate_time, Call,Type,Src, Des,Par_lat,Par_log,Cur_Lat,Cur_Log,altitude,Prv_Lat,Prv_Log,Stuck,Airspeed,Landing_light,ON_Ground,Landed,Heading,Gear,Req_Id,Obj_Id] 
    except:
      print("Unable to copy Arrival Cruise to Arrival")

  
  def Check_Arrival_Departure(airport):
    try:
      for index, flight in SimConnect.MSFS_AI_Departure_Traffic.iterrows():
        Call = flight["Call"]
        Src  = flight["Src"]
        Des = flight["Des"]
        Obj_Id = flight["Obj_Id"]
        if Src != airport:
          if Obj_Id != 0:
            sm.AIRemoveObject(flight["Obj_Id"],flight["Req_Id"])
          SimConnect.MSFS_AI_Departure_Traffic = SimConnect.MSFS_AI_Departure_Traffic[SimConnect.MSFS_AI_Departure_Traffic['Call'] != Call]
    except:
      print("Unable to remove old Departure aircraft")
    
    try:
      for index, flight in SimConnect.MSFS_AI_Arrival_Traffic.iterrows():
        Call = flight["Call"]
        Src  = flight["Src"]
        Des = flight["Des"]
        Obj_Id = flight["Obj_Id"]
        if Des != airport:
          if Obj_Id != 0:
            sm.AIRemoveObject(flight["Obj_Id"],flight["Req_Id"])
          SimConnect.MSFS_AI_Departure_Traffic = SimConnect.MSFS_AI_Departure_Traffic[SimConnect.MSFS_AI_Departure_Traffic['Call'] != Call]
    except:
      print("Unable to remove old Arrival aircraft")

  
  def Run():
    global SRC_AIRPORT_IACO,DES_AIRPORT_IACO,SRC_ACTIVE_RUNWAY,DES_ACTIVE_RUNWAY,SRC_GROUND_RANGE,DES_GROUND_RANGE
    global GROUND_INJECTION_TIME_DEP,GROUND_INJECTION_TIME_ARR,MAX_DEPARTURE_AI_FLIGHTS,MAX_ARRIVAL_AI_FLIGHTS
    global CRUISE_ALTITUDE,SRC_GROUND_RANGE,CRUISE_INJECTION_TIME,MAX_CRUISE_AI_FLIGHTS

    Common.Read_Config_file()

    Common.Get_Flight_plan()

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+SRC_AIRPORT_IACO+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    Lat = src_df.iloc[-1]["laty"]
    Lon = src_df.iloc[-1]["lonx"]
    Altitude = src_df.iloc[-1]["altitude"]
    Common.Src_Airport.loc[-1] = [SRC_AIRPORT_IACO,Lat,Lon,Altitude] 
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+DES_AIRPORT_IACO+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    if len(src_df["iata"].iloc[-1]) == 0: 
      print("IATA Code for " + src_df["ident"].iloc[-1] + " not found in database")
      return
    
    if len(des_df["iata"].iloc[-1]) == 0: 
      print("IATA Code for " + des_df["ident"].iloc[-1] + " not found in database")
      return
    
    
    Lat = des_df.iloc[-1]["laty"]
    Lon = des_df.iloc[-1]["lonx"]
    Altitude = des_df.iloc[-1]["altitude"]
    Common.Des_Airport.loc[-1] = [DES_AIRPORT_IACO,Lat,Lon,Altitude]  
    
    print("-----------------User Aircraft------------------")
    Common.Get_User_Aircraft()
    print(SimConnect.MSFS_User_Aircraft)
    
    prev_min = 0
    
    while (True):
      now = datetime.now()
      min = now.minute
      
      if prev_min != min:
      
        Common.Get_User_Aircraft()
               
        # if User aircraft within 50KM of Departure airport
        if (SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Src"]  < SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Des"]) and Common.Shift_Cruise_Des == False:
          Fr24_Dep_len = len(Departure.FR24_Departure_Traffic)
          Fr24_Arr_len = len(Arrival.FR24_Arrival_Traffic)  
          Common.State_Machine = 1  
          
          if (Fr24_Dep_len == 0 or Fr24_Arr_len == 0) and Common.Retry_SRC < 2:
            print("--------------At Departure Airport-------------------") 
            Arrival.Get_Arrival(SRC_AIRPORT_IACO,100)
            Arrival.inject_Traffic_Arrival(SRC_ACTIVE_RUNWAY)
            
            Departure.Get_Departure(SRC_AIRPORT_IACO,100)
            Departure.Inject_Parked_Traffic()
            Departure.Assign_Flt_plan(SRC_ACTIVE_RUNWAY)
            
            Common.Retry_SRC += 1             #Retry only once if Flight Radar data is available
            
          else:
            if (Departure.Departure_Index < 5 or min % GROUND_INJECTION_TIME_DEP == 0) and Departure.Departure_Index < MAX_DEPARTURE_AI_FLIGHTS:   
              if Departure.Departure_Index < Fr24_Dep_len:
                  Departure.Assign_Flt_plan(SRC_ACTIVE_RUNWAY)
                  
              else:
                print("Departure injection Completed at Departure airport")

            if (Arrival.Arrival_Index < 5 or min % GROUND_INJECTION_TIME_ARR == 0) and len(SimConnect.MSFS_AI_Arrival_Traffic) < MAX_ARRIVAL_AI_FLIGHTS:
              if Arrival.Arrival_Index < len(Arrival.FR24_Arrival_Traffic) :
                if Common.Skip_injection % 5 != 0:
                  Arrival.inject_Traffic_Arrival(SRC_ACTIVE_RUNWAY)
              else:
                print("Arrival injection Completed at Departure airport")
              Common.Skip_injection += 1 

        # if User aircraft within 100KM of Arrival airport  
        if SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Des"] < DES_GROUND_RANGE and \
          SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Des"]  < SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Src"]:
          Fr24_Dep_len = len(Departure.FR24_Departure_Traffic)
          Fr24_Arr_len = len(Arrival.FR24_Arrival_Traffic)
          Common.State_Machine = 3
          
          if ((Fr24_Dep_len == 0 or Fr24_Arr_len == 0) or (Common.Shift_Cruise_Des == False)) and Common.Retry_DES < 2:
            print("--------------At Destination Airport-------------------")   
            #Clear Arrival and Departure FR24 dataframe
            Common.Shift_Cruise_Des = True 
            Arrival.FR24_Arrival_Traffic = pd.DataFrame(columns=['Estimate_time', 'Scheduled_time', "Call","Src", "Type","Reg",'Ocio',"Src_ICAO","Des_ICAO","Local_arrival_time"])
            Arrival.Arrival_Index = 0
            Departure.FR24_Departure_Traffic = pd.DataFrame(columns=['Estimate_time', 'Scheduled_time', "Call","des", "Type","Reg",'Ocio',"Src_ICAO","Des_ICAO","Local_depart_time"])
            Departure.Departure_Index = 0
            Common.Check_Arrival_Departure(DES_AIRPORT_IACO)
            Arrival.Get_Arrival(DES_AIRPORT_IACO,100)  
            Departure.Get_Departure(DES_AIRPORT_IACO,100)                  
            Common.Retry_DES += 1             #Retry only once if Flight Radar data is available
          
          else:
            if Departure.Departure_Index == 0 and Arrival.Arrival_Index == 0 and (SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Src"]) < 80:
              Arrival.inject_Traffic_Arrival(DES_ACTIVE_RUNWAY)
              
              Departure.Inject_Parked_Traffic()
              Departure.Assign_Flt_plan(DES_ACTIVE_RUNWAY)
            
            
            if (Departure.Departure_Index < 5 or min % GROUND_INJECTION_TIME_DEP == 0) and Departure.Departure_Index < MAX_DEPARTURE_AI_FLIGHTS:
              if Departure.Departure_Index < Fr24_Dep_len :
                  if (SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Src"]) < 80:
                    Departure.Assign_Flt_plan(DES_ACTIVE_RUNWAY)
              else:
                print("Departure injection Completed at destination airport")

            if (Arrival.Arrival_Index < 5 or min % GROUND_INJECTION_TIME_ARR == 0) and len(SimConnect.MSFS_AI_Arrival_Traffic) < MAX_ARRIVAL_AI_FLIGHTS:
              if Arrival.Arrival_Index < len(Arrival.FR24_Arrival_Traffic) :
                if Common.Skip_injection % 5 != 0 and (SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Src"]) < 80:
                  Arrival.inject_Traffic_Arrival(DES_ACTIVE_RUNWAY)
              else:
                print("Arrival injection Completed at destination airport")  
              Common.Skip_injection += 1
          
          if min % 3 == 0 and Common.Shift_Src_Cruise == True:
            Cruise.Check_Traffic_Cruise()
            Common.Shift_Src_Cruise = False
            Common.CopyArrivalCruise(DES_AIRPORT_IACO)
        
        # if User aircraft is Crusing
        if SimConnect.MSFS_User_Aircraft.iloc[-1]["Altitude"] > CRUISE_ALTITUDE and SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Src"] > SRC_GROUND_RANGE  and SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Des"] > DES_GROUND_RANGE:   
          Common.State_Machine = 2
          if Common.Shift_Src_Cruise == False:
            print("--------------Crusing------------------")  
            Cruise.Create_Cruise_Traffic_database_Arrival_des(DES_AIRPORT_IACO,100)
            Cruise.Inject_Cruise_Traffic_Arrival_des()
            Cruise.Cruise_Arr_des_Index += 1
            Cruise.Create_Cruise_Traffic_database_Arrival_src(SRC_AIRPORT_IACO,100)
            Cruise.Inject_Cruise_Traffic_Arrival_src()
            Cruise.Cruise_Arr_src_Index += 1
          
          if (min % CRUISE_INJECTION_TIME == 0) or Common.Shift_Src_Cruise == False:
            Cruise.Get_Cruise_Traffic_ADS_S(SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Lat"] ,SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Log"],25)
            if Common.Shift_Src_Cruise == False:
              Cruise.Inject_Cruise_Traffic_ADB_S()
            Common.Shift_Src_Cruise = True

          if min % 2 == 0 and len(SimConnect.MSFS_Cruise_Traffic) < MAX_CRUISE_AI_FLIGHTS:
            Cruise.Inject_Cruise_Traffic_Arrival_src()
            Cruise.Cruise_Arr_src_Index += 1
          
          if min % 3 == 0 and len(SimConnect.MSFS_Cruise_Traffic) < MAX_CRUISE_AI_FLIGHTS:
            Cruise.Inject_Cruise_Traffic_Arrival_des()
            Cruise.Cruise_Arr_des_Index += 1
          
          if min % 3 == 0:
            Departure.Check_Traffic_Departure()
          if min % 3 == 0:
            Arrival.Check_Traffic_Arrival()
          if min % 3 == 0:
            Cruise.Check_Traffic_Cruise()
            

        prev_min = min
      
      if Common.State_Machine == 1:
        Arrival.Check_Traffic_onRunway_Arrival(SRC_ACTIVE_RUNWAY)
      elif Common.State_Machine == 3:
        Arrival.Check_Traffic_onRunway_Arrival(DES_ACTIVE_RUNWAY)
      Arrival.Check_Traffic_MinSeparation()
      
      time.sleep(2)


class Cruise:
  Cruise_Traffic_ADB = pd.DataFrame(columns=["Call", "Type","Src_ICAO","Des_ICAO","Lat","Lon","Altitude","Heading","Speed"])
  FR24_Cruise_Arrival_des_Traffic = pd.DataFrame(columns=["Call", "Type","Src_ICAO","Des_ICAO"])
  FR24_Cruise_Arrival_src_Traffic = pd.DataFrame(columns=["Call", "Type","Src_ICAO","Des_ICAO"])
  Cruise_Arr_des_Index = 0
  Cruise_Arr_src_Index = 0

  def Create_Cruise_Traffic_database_Arrival_des(airport,max_cruise):
    
    driver = uc.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    print("------------Get Cruise Arrival FR24 Traffic---------------------")

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "icao" LIKE '%"""+airport+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      des_air = pd.read_sql(sql=qry_str, con=conn.connection)
    airport_iata = des_air["iata"].iloc[-1]
    
    try:
      url = "https://www.flightradar24.com/data/airports/" + airport_iata +"/arrivals"
      driver.get(url)
      #Arrival.Get_Arrival_ADB_S(des_air["laty"].iloc[-1],des_air["lonx"].iloc[-1],25)
      time.sleep(10)
    except:
      print("Check internet connection = " + url)
      return


    flight_elements = driver.find_elements(By.XPATH, "//td")
  
    prev_lin = ""
    for flight in flight_elements:
      flight_info = flight.text 
      if  prev_lin != flight_info:
        flight_info_list = flight_info.split("\n") 
                
        if flight_info_list[0].split(" ")[0] == "Scheduled" or flight_info_list[0].split(" ")[0] == "Estimated" or flight_info_list[0].split(" ")[0] == "Delayed":
          if flight_info_list[2] in Cruise.FR24_Cruise_Arrival_des_Traffic['Call'].values:
            continue
          last_element = len(Cruise.FR24_Cruise_Arrival_des_Traffic)
          if last_element < max_cruise:
            try:
              last_element = len(Cruise.FR24_Cruise_Arrival_des_Traffic)
              Call =  flight_info_list[2]
              Src =  flight_info_list[3]
              Type =  flight_info_list[4]             
              qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+re.search(r'\((.*?)\)', Src).group(1).upper()+"""%'"""
              with Common.engine_airport_db.connect() as conn:
                  src_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              Src_ICAO = src_air["icao"].iloc[-1]
              Des_ICAO = airport
              Cruise.FR24_Cruise_Arrival_des_Traffic.loc[last_element] = [Call,Type,Src_ICAO,Des_ICAO]
            except:
              print(str(flight_info_list) + " FR24 Arrival not found")
      
      prev_lin = flight_info
    
    print(Cruise.FR24_Cruise_Arrival_des_Traffic)

    driver.quit()
    #time.sleep(5)


  def Create_Cruise_Traffic_database_Arrival_src(airport,max_cruise):
    driver = uc.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    print("------------Get Cruise Arrival FR24 Traffic---------------------")

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "icao" LIKE '%"""+airport+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      des_air = pd.read_sql(sql=qry_str, con=conn.connection)
    airport_iata = des_air["iata"].iloc[-1]
    
    try:
      url = "https://www.flightradar24.com/data/airports/" + airport_iata +"/arrivals"
      driver.get(url)
      #Arrival.Get_Arrival_ADB_S(des_air["laty"].iloc[-1],des_air["lonx"].iloc[-1],25)
      time.sleep(10)
    except:
      print("Check internet connection = " + url)
      return


    flight_elements = driver.find_elements(By.XPATH, "//td")
  
    prev_lin = ""
    for flight in flight_elements:
      flight_info = flight.text 
      if  prev_lin != flight_info:
        flight_info_list = flight_info.split("\n") 
                
        if flight_info_list[0].split(" ")[0] == "Scheduled" or flight_info_list[0].split(" ")[0] == "Estimated" or flight_info_list[0].split(" ")[0] == "Delayed":
          if flight_info_list[2] in Cruise.FR24_Cruise_Arrival_src_Traffic['Call'].values:
            continue
          last_element = len(Cruise.FR24_Cruise_Arrival_src_Traffic)
          if last_element < max_cruise:
            try:
              last_element = len(Cruise.FR24_Cruise_Arrival_src_Traffic)
              Call =  flight_info_list[2]
              Src =  flight_info_list[3]
              Type =  flight_info_list[4]             
              qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+re.search(r'\((.*?)\)', Src).group(1).upper()+"""%'"""
              with Common.engine_airport_db.connect() as conn:
                  src_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              Src_ICAO = src_air["icao"].iloc[-1]
              Des_ICAO = airport
              Cruise.FR24_Cruise_Arrival_src_Traffic.loc[last_element] = [Call,Type,Src_ICAO,Des_ICAO]
            except:
              print(str(flight_info_list) + " FR24 Cruise Arrival not found")
      
      prev_lin = flight_info
    
    print(Cruise.FR24_Cruise_Arrival_src_Traffic)

    driver.quit()
    #time.sleep(5)

  
  def Get_Cruise_Traffic_ADS_S(lat,lon,dist):
    global ADBS_host,ADBS_key
    url = "https://adsbx-flight-sim-traffic.p.rapidapi.com/api/aircraft/json/lat/" + str(lat) + "/lon/" + str(lon) +"/dist/" + str(dist) +"/"
    headers = {
    	"x-rapidapi-key": ADBS_key,
    	"x-rapidapi-host": ADBS_host
    }
    response = requests.get(url, headers=headers)
    traffic_data = response.json()
    

    print("------------Cruise Traffic---------------------")
    try:
      for flight in traffic_data["ac"]:
        if int(flight["gnd"]) == 0:
          if flight["call"] in Cruise.Cruise_Traffic_ADB['Call'].values:
            continue
          last_element = len(Cruise.Cruise_Traffic_ADB)
          if int(flight["alt"]) > CRUISE_ALTITUDE:
            Call = flight["call"]
            Type = flight["type"]
            Lat = flight["lat"]
            Lon = flight["lon"]
            Altitude = flight["alt"]
            Heading = flight["trak"]
            Speed = float(flight["spd"])
             
            qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+flight["from"].split(" ")[0]+"""%'"""
            with Common.engine_airport_db.connect() as conn:
              src_air = pd.read_sql(sql=qry_str, con=conn.connection)
            Src_ICAO = src_air["icao"].iloc[-1]
            
            qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+flight["to"].split(" ")[0]+"""%'"""
            with Common.engine_airport_db.connect() as conn:
              des_air = pd.read_sql(sql=qry_str, con=conn.connection)
            Des_ICAO = des_air["icao"].iloc[-1]
                        
            Cruise.Cruise_Traffic_ADB.loc[last_element] = [Call,Type,Src_ICAO,Des_ICAO,Lat,Lon,Altitude,Heading,Speed]
    except:
      print("Cruise ADB-S Flight not found")
          
    #if len(Cruise.Cruise_Traffic_ADB) > 0:
    #  print(Cruise.Cruise_Traffic_ADB)
      
  def Inject_Cruise_Traffic_ADB_S():
    global current_dir
    for flight in Cruise.Cruise_Traffic_ADB.iterrows():
      Call = flight[1]["Call"]
      if Call in SimConnect.MSFS_Cruise_Traffic['Call'].values:
        continue
      last_element = len(SimConnect.MSFS_Cruise_Traffic)
      Type = flight[1]["Type"]
      Src  = flight[1]["Src_ICAO"]
      Des = flight[1]["Des_ICAO"]
      Cur_Lat = flight[1]["Lat"]
      Cur_Log = flight[1]["Lon"]
      Altitude = flight[1]["Altitude"]
      Heading = flight[1]["Heading"]
      Speed = flight[1]["Speed"]
      Bank = 0
      Pitch = 0
      Flt_plan = 0
      Gnd = 0
      Req_Id = Common.Global_req_id
      Obj_Id = 0
      SimConnect.MSFS_Cruise_Traffic.loc[last_element] = [Call,Type,Src,Des,Cur_Lat,Cur_Log,Altitude,Heading,Speed,Flt_plan,Req_Id,Obj_Id]
      try:
        Livery_name , callsign = Common.Get_flight_match(Call,Type)
        flt_plan = Cruise.Create_flt_Plan(Src,Des,float(Cur_Lat),float(Cur_Log),float(Speed),float(Altitude))
        print("Crusing----" + callsign + " " + Type + " " + str(Livery_name))
        result = sm.AICreateEnrouteATCAircraft(Livery_name,callsign,int(re.findall(r'\d+', Call)[0]),current_dir + "/fln_plan_cruise",float(1),False,Req_Id)
        Common.Global_req_id+=1
        time.sleep(2)
        if SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0] > 1:
          sm.AIAircraftAirspeed(SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0],float(Speed))
      except:
        print("Cannot Inject Cruise Flight")
  

  def Inject_Cruise_Traffic_Arrival_des():
    global current_dir
    #add departed traffic to fill in sky
    if Cruise.Cruise_Arr_des_Index  < len(Cruise.FR24_Cruise_Arrival_des_Traffic) :
      Index = Cruise.FR24_Cruise_Arrival_des_Traffic.index[-Cruise.Cruise_Arr_des_Index]
      if not (Cruise.FR24_Cruise_Arrival_des_Traffic.loc[Index,"Call"] in SimConnect.MSFS_Cruise_Traffic['Call'].values):
        last_element = len(SimConnect.MSFS_Cruise_Traffic)
        try:
          Src = Cruise.FR24_Cruise_Arrival_des_Traffic.loc[Index,"Src_ICAO"]
          Des =  Cruise.FR24_Cruise_Arrival_des_Traffic.loc[Index,"Des_ICAO"]
          Call = Cruise.FR24_Cruise_Arrival_des_Traffic.loc[Index,"Call"]
          Type = Cruise.FR24_Cruise_Arrival_des_Traffic.loc[Index,"Type"]
          Cur_Lat = SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Lat"]
          Cur_Log = SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Log"]
          Altitude = float(SimConnect.MSFS_User_Aircraft.iloc[-1]["Altitude"])
          Heading  = 0
          Speed = -1
          Obj_Id =  0
          Flt_plan = 0
          Req_Id = Common.Global_req_id
          SimConnect.MSFS_Cruise_Traffic.loc[last_element] = [Call,Type,Src,Des,Cur_Lat,Cur_Log,Altitude,Heading,Speed,Flt_plan,Req_Id,Obj_Id]
          Livery_name , callsign = Common.Get_flight_match(Call,Type)
          Altitude_offset = random.choice([-1000,-2000,-3000,-4000,-5000,1000,2000,3000])
          flt_plan = Cruise.Create_flt_Plan(Src,Des,float(Cur_Lat), float(Cur_Log) ,Speed,float(int(Altitude) + int(Altitude_offset)))
          print("Crusing----" + callsign + " " + Type + " " + str(Livery_name))
          result = sm.AICreateEnrouteATCAircraft(Livery_name,callsign,int(re.findall(r'\d+', Call)[0]),current_dir + "/fln_plan_cruise",float(1),False,Req_Id)
          Common.Global_req_id+=1
          time.sleep(2)
          if SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0] > 1:
            sm.AIAircraftAirspeed(SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0],500)
        except:
          print("Cannot create Arrival Des Cruise flight plan")  


  def Inject_Cruise_Traffic_Arrival_src():
    global current_dir
    #add departed traffic to fill in sky
    if Cruise.Cruise_Arr_src_Index  < len(Cruise.FR24_Cruise_Arrival_src_Traffic) :
      Index = Cruise.Cruise_Arr_src_Index
      if not (Cruise.FR24_Cruise_Arrival_src_Traffic.loc[Index,"Call"] in SimConnect.MSFS_Cruise_Traffic['Call'].values):
        last_element = len(SimConnect.MSFS_Cruise_Traffic)
        try:
          Src = Cruise.FR24_Cruise_Arrival_src_Traffic.loc[Index,"Src_ICAO"]
          Des =  Cruise.FR24_Cruise_Arrival_src_Traffic.loc[Index,"Des_ICAO"]
          Call = Cruise.FR24_Cruise_Arrival_src_Traffic.loc[Index,"Call"]
          Type = Cruise.FR24_Cruise_Arrival_src_Traffic.loc[Index,"Type"]
          Cur_Lat = SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Lat"]
          Cur_Log = SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Log"]
          Altitude = float(SimConnect.MSFS_User_Aircraft.iloc[-1]["Altitude"])
          Heading  = 0
          Speed = -1
          Obj_Id =  0
          Flt_plan = 0
          Req_Id = Common.Global_req_id
          SimConnect.MSFS_Cruise_Traffic.loc[last_element] = [Call,Type,Src,Des,Cur_Lat,Cur_Log,Altitude,Heading,Speed,Flt_plan,Req_Id,Obj_Id]
          Livery_name, callsign = Common.Get_flight_match(Call,Type)
          Altitude_offset = random.choice([-1000,-2000,-3000,-4000,-5000,1000,2000,3000])
          flt_plan = Cruise.Create_flt_Plan(Src,Des,float(Cur_Lat), float(Cur_Log) ,Speed,float(int(Altitude) + int(Altitude_offset)))
          print("Crusing----" + callsign + " " + Type + " " + str(Livery_name))
          result = sm.AICreateEnrouteATCAircraft(Livery_name,callsign,int(re.findall(r'\d+', Call)[0]),current_dir + "/fln_plan_cruise",float(1),False,Req_Id)
          Common.Global_req_id+=1
          time.sleep(2)
          if SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0] > 1:
            sm.AIAircraftAirspeed(SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0],500)
        except:
          print("Cannot create Arrival src Cruise flight plan")  

    #print(SimConnect.MSFS_Cruise_Traffic)

  def Create_flt_Plan(Src,Des,Lat,Lon,Speed,crusing_alt):

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+Src+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    src_name = src_df.iloc[-1]["name"]
    src_Pos = Common.format_coordinates(float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]),float(src_df.iloc[-1]["altitude"]))
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+Des+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    des_name = des_df.iloc[-1]["name"] 
    des_Pos =  Common.format_coordinates(float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]),float(des_df.iloc[-1]["altitude"]))
    
    with Common.engine_waypoint_db.connect() as conn:
      qry_str = '''SELECT"_rowid_",* FROM "main"."waypoint" WHERE "laty" > '''  + str(int(Lat)-3) + ''' AND "laty" < '''  + str(int(Lat) + 3) + ''' AND "lonx" > '''  + str(int(Lon)-3) + '''  AND "lonx" < '''  + str(int(Lon) + 3) + ''' '''
      way_df = pd.read_sql(sql=qry_str, con=conn.connection)

    R = 6371.0
    distance = random.uniform(2, 50)
    bearing = random.uniform(0, 2 * math.pi)

    lat_rad = math.radians(Lat)
    lon_rad = math.radians(Lon)

    # Calculate new latitude and longitude
    new_lat_rad = math.asin(math.sin(lat_rad) * math.cos(distance / R) + math.cos(lat_rad) * math.sin(distance / R) * math.cos(bearing))
    new_lon_rad = lon_rad + math.atan2(math.sin(bearing) * math.sin(distance / R) * math.cos(lat_rad),
                                       math.cos(distance / R) - math.sin(lat_rad) * math.sin(new_lat_rad))

    # Convert radians back to degrees
    new_lat = math.degrees(new_lat_rad)
    new_lon = math.degrees(new_lon_rad)

    waypoint_Pos = Common.format_coordinates(float(new_lat),float(new_lon),float(crusing_alt))
    waypoint_id = "USERWP"
    waypoint_reg = "USER"


    
    fln_plan = \
"""<?xml version="1.0" encoding="UTF-8"?>
<SimBase.Document Type="AceXML" version="1,0">
    <Descr>AceXML Document</Descr>
    <FlightPlan.FlightPlan>
        <Title>"""+Src + """ to """+ Des +"""</Title>
        <FPType>IFR</FPType>
        <CruisingAlt>""" + str(crusing_alt) + """</CruisingAlt>
        <DepartureID>""" + Src + """</DepartureID>
        <DepartureLLA>""" + src_Pos +"""</DepartureLLA>
        <DestinationID>""" + Des + """</DestinationID>
        <DestinationLLA>"""+des_Pos+"""</DestinationLLA>
        <Descr>""" + Src + """, """ + Des + """</Descr>
        <DepartureName>""" + src_name + """</DepartureName>
        <DestinationName>""" + des_name + """</DestinationName>
        <AppVersion>
            <AppVersionMajor>10</AppVersionMajor>
            <AppVersionBuild>60327</AppVersionBuild>
        </AppVersion>
        <ATCWaypoint id=\""""+Src + """\">
            <ATCWaypointType>Airport</ATCWaypointType>
            <WorldPosition>"""+src_Pos+"""</WorldPosition>
            <ICAO>
                <ICAOIdent>"""+Src + """</ICAOIdent>
            </ICAO>
        </ATCWaypoint>
        <ATCWaypoint id=\"""" + waypoint_id + """\">
            <ATCWaypointType>Intersection</ATCWaypointType>
            <WorldPosition>"""+waypoint_Pos+"""</WorldPosition>
            <SpeedMaxFP>"""+str(Speed)+"""</SpeedMaxFP>
            <ICAO>
                <ICAORegion>""" + waypoint_reg + """</ICAORegion>
                <ICAOIdent>""" + waypoint_id + """</ICAOIdent>
            </ICAO>
        </ATCWaypoint>
        <ATCWaypoint id=\""""+ Des +"""\">
            <ATCWaypointType>Airport</ATCWaypointType>
            <WorldPosition>"""+des_Pos+"""</WorldPosition>
            <ICAO>
                <ICAOIdent>"""+ Des +"""</ICAOIdent>
            </ICAO>
        </ATCWaypoint>
    </FlightPlan.FlightPlan>
</SimBase.Document>
"""
    with open("fln_plan_cruise.pln", "w", encoding="utf-8-sig") as file:
      file.write(fln_plan)
    return fln_plan

  def Check_Traffic_Cruise():

    point1  = (SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Lat"] ,SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Log"])
    Altitude1 = float(SimConnect.MSFS_User_Aircraft.iloc[-1]["Altitude"])
    for index, flight in SimConnect.MSFS_Cruise_Traffic.iterrows():
      sm.AIAircraft_GetPosition(flight["Req_Id"],flight["Obj_Id"])
      time.sleep(1)
      try:
        if flight["Cur_Lat"] != 0.0 and flight["Cur_Log"] != 0.0:
          #Check Dist
          point2 = (flight["Cur_Lat"] ,flight["Cur_Log"])
          dis = geodesic(point1, point2).km
    
          Altitude2 = float(flight["Altitude"])
          Alt = abs(Altitude1 - Altitude2)
          if dis > SPWAN_DIST or Alt > SPWAN_ALTITUDE:
            print("Cruise Remove----" + flight["Call"] + " " + flight["Type"] + " Distance " + str(dis) + " Altitude diff" + str(Alt))
            sm.AIRemoveObject(flight["Obj_Id"],flight["Req_Id"])
            SimConnect.MSFS_Cruise_Traffic = SimConnect.MSFS_Cruise_Traffic[SimConnect.MSFS_Cruise_Traffic['Obj_Id'] != flight["Obj_Id"]]
            time.sleep(2)
      except:
        print("Error: Cruise " + str(flight))
    SimConnect.MSFS_Cruise_Traffic = SimConnect.MSFS_Cruise_Traffic.reset_index(drop=True)
    #print(SimConnect.MSFS_Cruise_Traffic)

class Arrival:

  FR24_Arrival_Traffic = pd.DataFrame(columns=['Estimate_time', 'Scheduled_time', "Call","Src", "Type","Reg",'Ocio',"Src_ICAO","Des_ICAO","Local_arrival_time"])
  ADBS_Arrival_Traffic = pd.DataFrame(columns=[ "Call","Lat","Lon","Altitude","Speed","Reg"])
 
  Arrival_Index = 0

  def Get_Arrival_ADB_S(lat,lon,dist):
    global ADBS_key,ADBS_host

    print("------------Get Arrival ADB-S Traffic---------------------")

    url = "https://adsbx-flight-sim-traffic.p.rapidapi.com/api/aircraft/json/lat/" + str(lat) + "/lon/" + str(lon) +"/dist/" + str(dist) +"/"
    
    headers = {
    	"x-rapidapi-key": ADBS_key,
    	"x-rapidapi-host": ADBS_host
    }
    response = requests.get(url, headers=headers)
    traffic_data = response.json()

    for flight in traffic_data["ac"]:
      try:
        if int(flight["gnd"]) == 0:
          if flight["call"] in Arrival.ADBS_Arrival_Traffic['Call'].values:
            continue
          last_element = len(Arrival.ADBS_Arrival_Traffic)
          Call = str(flight["call"])
          Lat = str(flight["lat"])
          Lon = str(flight["lon"])
          Altitude = str(flight["alt"])
          Speed = str(flight["spd"])                         
          Reg = str(flight["reg"])                         
          Arrival.ADBS_Arrival_Traffic.loc[last_element] = [Call,Lat,Lon,Altitude,Speed,Reg]
      except:
        print(str(flight) + "ADB_S Arrival Flight not found")
    #print(Arrival.ADBS_Arrival_Traffic)
      
  def Get_Arrival(airport,max_Arrival):
    global ACTIVE_RUNWAY_TAKEOFF,ACTIVE_RUNWAY_LAND

    ACTIVE_RUNWAY_LAND = ""
    ACTIVE_RUNWAY_TAKEOFF = ""

    driver = uc.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    print("------------Get Arrival FR24 Traffic---------------------")

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "icao" LIKE '%"""+airport+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      des_air = pd.read_sql(sql=qry_str, con=conn.connection)
    airport_iata = des_air["iata"].iloc[-1]
    
    try:
      url = "https://www.flightradar24.com/data/airports/" + airport_iata +"/arrivals"
      driver.get(url)
      #Arrival.Get_Arrival_ADB_S(des_air["laty"].iloc[-1],des_air["lonx"].iloc[-1],25)
      time.sleep(10)
 
      driver.execute_script("window.open('https://www.airnavradar.com/data/airports/" + airport +"', '_blank');")
      time.sleep(5)
    except:
      print("Check internet connection = " + url)
      return

    current_datetime = datetime.now()
    next_day_datetime = current_datetime + timedelta(days=1)

    flight_elements = driver.find_elements(By.XPATH, "//td")
 
    prev_lin = ""
    Check_New_Day = False
    prev_time = current_datetime.strftime('%H')
    for flight in flight_elements:
      flight_info = flight.text 
      if prev_lin != flight_info:
        flight_info_list = flight_info.split("\n")
        if flight_info_list[0].split(" ")[0] == "Estimated" or flight_info_list[0].split(" ")[0] == "Delayed":
          if flight_info_list[2] in Arrival.FR24_Arrival_Traffic['Call'].values:
            continue
          last_element = len(Arrival.FR24_Arrival_Traffic)
          if last_element < max_Arrival:
            try:
              last_element = len(Arrival.FR24_Arrival_Traffic)
              #print(flight_info_list)
              Estimate_time_list = flight_info_list[0].split(" ")
              if len(Estimate_time_list) == 3:
                Estimate_time = (datetime.strptime(str(Estimate_time_list[1] +" "+ Estimate_time_list[2]), '%I:%M %p')).strftime('%H:%M')
                Scheduled_time  =  (datetime.strptime(str(flight_info_list[1]), '%I:%M %p')).strftime('%H:%M')
              else:
                Estimate_time = datetime.strptime(Estimate_time_list[1],'%H:%M').strftime('%H:%M')
                Scheduled_time  = datetime.strptime(str(flight_info_list[1]),'%H:%M').strftime('%H:%M')

              Call =  flight_info_list[2]
              Src =  flight_info_list[3]
              Type =  flight_info_list[4]
              Ocio =  flight_info_list[-1]
              Reg =  flight_info_list[-2]
              
              qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+re.search(r'\((.*?)\)', Src).group(1).upper()+"""%'"""
              with Common.engine_airport_db.connect() as conn:
                  src_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              Src_ICAO = src_air["icao"].iloc[-1]
              Des_ICAO = airport

              if int(prev_time) - int(Estimate_time.split(":")[0]) > 2 :
                Check_New_Day = True
              if Check_New_Day == True:
                day = next_day_datetime.day
                month = next_day_datetime.month
                year = next_day_datetime.year
              else:
                day = current_datetime.day
                month = current_datetime.month
                year = current_datetime.year

              Specific_Time = str(year)+"-"+str(month)+"-"+str(day)+ " " + Estimate_time.split(":")[0] + ":" + Estimate_time.split(":")[1] + ":00" 
              Local_arrival_time =  Common.Get_Timezone(Des_ICAO,Specific_Time)
              Arrival.FR24_Arrival_Traffic.loc[last_element] = [Estimate_time, Scheduled_time, Call, Src,Type,Reg,Ocio,Src_ICAO,Des_ICAO,Local_arrival_time]
              prev_time = Estimate_time.split(":")[0]
            except:
              print(str(flight_info_list) + " FR24 Arrival not found")
      
      prev_lin = flight_info
    
    Arrival.FR24_Arrival_Traffic = Arrival.FR24_Arrival_Traffic.sort_values(by='Local_arrival_time',ascending=True).reset_index(drop=True)
    print(Arrival.FR24_Arrival_Traffic)

    # Get active Runway
    # Switch to the new tab (usually at index 1)
    driver.switch_to.window(driver.window_handles[1])
    
    time.sleep(2)
    #WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[6]/div[2]/div[2]/div[2]/div[2]/button[1]"))).click()
    try:
      consent_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".fc-cta-consent")))
      consent_button.click()
    except:
        print("Consent button not found or already accepted.")
    
    
    time.sleep(2)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH,"//li[contains(@class, 'ListItemClickable')]//span[text()='Airport Info']/ancestor::li"))).click()
    found_data = False
    try:
      Landing_RW = driver.find_element(By.XPATH, f"//div[@id='title' and contains(text(), 'in Use for Landing')]/following-sibling::div[@id='value']").text
      Takeoff_RW = driver.find_element(By.XPATH, f"//div[@id='title' and contains(text(), 'in Use for Takeoff')]/following-sibling::div[@id='value']").text
   
      ACTIVE_RUNWAY_LAND = Landing_RW.split(" ")[0]
      ACTIVE_RUNWAY_TAKEOFF = Takeoff_RW.split(" ")[0]
  
      print("ACTIVE_RUNWAY_LAND: " + ACTIVE_RUNWAY_LAND)
      print("ACTIVE_RUNWAY_TAKEOFF: " + ACTIVE_RUNWAY_TAKEOFF)
    
    except:
      print("Runway data not found")



    driver.quit()
    #time.sleep(5)

  def Create_flight_plan_arr(src,des,RW):

    global ACTIVE_RUNWAY_LAND
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+src+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    src_name = src_df.iloc[-1]["name"]
    src_Pos = Common.format_coordinates(float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]),float(src_df.iloc[-1]["altitude"]))
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+des+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    des_name = des_df.iloc[-1]["name"] 
    des_Pos =  Common.format_coordinates(float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]),float(des_df.iloc[-1]["altitude"]))
       
    #if Arrival.Arrival_Index < 10:
    #    crusing_alt = str(4000 + (500 * Arrival.Arrival_Index))
    #else :
    crusing_alt = str(7000)
    
    if ACTIVE_RUNWAY_LAND != "":
      RW = ACTIVE_RUNWAY_LAND

    #fill lat and log
    RW_num =  str(int((re.findall(r'\d+', RW))[0]))
    RW_des = re.findall(r'[A-Za-z]', RW)
    
    if len(RW_des) > 0:
      if RW_des[0]== "C":
        RW_designa = "CENTER"
      if RW_des[0] == "L":
        RW_designa = "LEFT"
      if RW_des[0] == "R":
        RW_designa = "RIGHT"
      
    with Common.engine_approach_db.connect() as conn:
      qry_str = '''SELECT "_rowid_", * FROM "main"."approach" WHERE "airport_ident" LIKE '%'''+des+'''%' ESCAPE '\\' AND "type" LIKE '%GPS%' ESCAPE '\\' AND "suffix" LIKE '%A%' ESCAPE '\\' AND "runway_name" LIKE '%'''+RW+'''%' ESCAPE '\\'LIMIT 0, 49999;'''
      approach_df = pd.read_sql(sql=qry_str, con=conn.connection)
    

    point1 = (float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]))
    prev_distance = 99999999999
    Cur_app_leg_df = pd.DataFrame()
    approach_string = ""
    if len(approach_df) > 0:
      for index,app in approach_df.iterrows():
        app_id = app["approach_id"].iloc[-1]
        with Common.engine_approach_db.connect() as conn:
          qry_str = '''SELECT "_rowid_", * FROM "main"."approach_leg" WHERE "approach_id" = "'''+str(app_id) + '''" '''
          app_leg = pd.read_sql(sql=qry_str, con=conn.connection)
          with Common.engine_waypoint_db.connect() as conn:
            qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+app_leg.iloc[0]["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+app_leg.iloc[0]["fix_region"]+'''%' '''
            way_df = pd.read_sql(sql=qry_str, con=conn.connection)
            point2 = (way_df.iloc[-1]["laty"], way_df.iloc[-1]["lonx"]) 
            distance = geodesic(point1, point2).km
            if distance < prev_distance :
              Cur_app_leg_df = app_leg
              App_Name = app["fix_ident"]
              prev_distance = distance
      
    first_way_point = 0
    Num_Waypoint = 0
    if len(Cur_app_leg_df) > 5:
      Outer_dis = 70
    else:
      Outer_dis = 100
    
    Injection_Waypoint = pd.DataFrame(columns=["waypoint","dis"])
    if len(Cur_app_leg_df) > 0:
      for index, app_leg in Cur_app_leg_df.iterrows():
        with Common.engine_waypoint_db.connect() as conn:
          qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+app_leg["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+app_leg["fix_region"]+'''%' '''
          way_df = pd.read_sql(sql=qry_str, con=conn.connection)
          if len(way_df) > 0 :
            point2 = (way_df.iloc[-1]["laty"], way_df.iloc[-1]["lonx"]) 
            distance = geodesic((float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"])), point2).km         
            if distance < Outer_dis and app_leg["fix_type"] != "V" :
              if first_way_point == 0 and distance > 35:
                first_way_lat = float(way_df["laty"].iloc[-1])
                first_way_lon = float(way_df["lonx"].iloc[-1])
                first_way_point = 1
              if first_way_point == 1:
                Num_Waypoint += 1
                app_waypoint_Pos = Common.format_coordinates(float(way_df["laty"].iloc[-1]),float(way_df["lonx"].iloc[-1]),float(5000))  
                Injection_Waypoint.loc[Num_Waypoint] = [app_leg["fix_ident"],distance]
                approach_string += """        <ATCWaypoint id=\"""" + app_leg["fix_ident"] + """\">
            <ATCWaypointType>Intersection</ATCWaypointType>
            <WorldPosition>"""+app_waypoint_Pos+"""</WorldPosition>
            <SpeedMaxFP>-1</SpeedMaxFP>
            <ICAO>
                <ICAORegion>""" + app_leg["fix_region"] + """</ICAORegion>
                <ICAOIdent>""" + app_leg["fix_ident"] + """</ICAOIdent>
                <ICAOAirport>""" + des + """</ICAOAirport>
            </ICAO>
        </ATCWaypoint>\n"""
  	
   
    if Num_Waypoint < 1:
      # Define the source and destination points
      source_point = Point(float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]))
      destination_point = Point(float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]))
      lat1 = float(src_df.iloc[-1]["laty"])
      lon1 = float(src_df.iloc[-1]["lonx"])
      lat2 = float(des_df.iloc[-1]["laty"])
      lon2 = float(des_df.iloc[-1]["lonx"])
      # Calculate the bearing (direction) from source to destination
      bearing = bearing = math.atan2(math.sin(lon2 - lon1) * math.cos(lat2), math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
      # Move 35 km from the source point towards the destination
      new_point = geodesic(source_point, destination_point).destination(destination_point,bearing, distance=35)
      src_waypoint_Pos = Common.format_coordinates(new_point.latitude, new_point.longitude,float(crusing_alt))
      src_waypoint_id = "USERWP"
      src_waypoint_reg = "USER"
      first_way_point = 2

    RW_Head_way_Pos = "None"
    try:    
      with Common.engine_approach_db.connect() as conn:
        qry_str = '''SELECT "_rowid_", * FROM "main"."approach" WHERE "airport_ident" LIKE '%'''+des+'''%' ESCAPE '\\'  AND "runway_name" LIKE '%'''+RW+'''%' AND "heading" IS NOT NULL'''
        Way_RW_Heading = pd.read_sql(sql=qry_str, con=conn.connection)
      
      with Common.engine_waypoint_db.connect() as conn:
        qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+Way_RW_Heading.iloc[-1]["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+Way_RW_Heading.iloc[-1]["fix_region"]+'''%' '''
        RW_Head_way_df = pd.read_sql(sql=qry_str, con=conn.connection)
  
      RW_Head_way_Pos = Common.format_coordinates(float(RW_Head_way_df.iloc[-1]["laty"]),float(RW_Head_way_df.iloc[-1]["lonx"]),Way_RW_Heading.iloc[-1]["altitude"])
      RW_Head_way_id = RW_Head_way_df.iloc[-1]["ident"]
      RW_Head_way_reg = RW_Head_way_df.iloc[-1]["region"]
    except:
      print("No waypoint on Runway Heading " + RW)

    fln_plan = """<?xml version="1.0" encoding="UTF-8"?> \
   
<SimBase.Document Type="AceXML" version="1,0">
    <Descr>AceXML Document</Descr>
    <FlightPlan.FlightPlan>
        <Title>"""+src + """ to """+ des +"""</Title>
        <FPType>IFR</FPType>
        <CruisingAlt>""" + str(crusing_alt) + """</CruisingAlt>
        <DepartureID>""" + src + """</DepartureID>
        <DepartureLLA>""" + src_Pos +"""</DepartureLLA>
        <DestinationID>""" + des + """</DestinationID>
        <DestinationLLA>"""+des_Pos+"""</DestinationLLA>
        <Descr>""" + src + """, """ + des + """</Descr>
        <DepartureName>""" + src_name + """</DepartureName>
        <DestinationName>""" + des_name + """</DestinationName>
        <AppVersion>
            <AppVersionMajor>10</AppVersionMajor>
            <AppVersionBuild>60327</AppVersionBuild>
        </AppVersion>
        <ATCWaypoint id=\""""+src + """\">
            <ATCWaypointType>Airport</ATCWaypointType>
            <WorldPosition>"""+src_Pos+"""</WorldPosition>
            <ICAO>
                <ICAOIdent>"""+src + """</ICAOIdent>
            </ICAO>
        </ATCWaypoint>\n"""
    if first_way_point == 2:
        fln_plan +="""        <ATCWaypoint id=\""""+src_waypoint_id+"""\">
            <ATCWaypointType>Intersection</ATCWaypointType>
            <WorldPosition>"""+src_waypoint_Pos+"""</WorldPosition>
            <ICAO>
                <ICAORegion>"""+src_waypoint_reg+"""</ICAORegion>
            <ICAOIdent>"""+src_waypoint_id+"""</ICAOIdent>
            </ICAO>
        </ATCWaypoint>\n"""
    if RW_Head_way_Pos != "None":  
      fln_plan += approach_string + """        <ATCWaypoint id=\""""+RW_Head_way_id+"""\">
            <ATCWaypointType>Intersection</ATCWaypointType>
            <WorldPosition>"""+RW_Head_way_Pos+"""</WorldPosition>
            <ICAO>
                <ICAORegion>"""+RW_Head_way_reg+"""</ICAORegion>
                <ICAOIdent>"""+RW_Head_way_id + """</ICAOIdent>
            </ICAO>
        </ATCWaypoint>"""
      
    fln_plan +="""      <ATCWaypoint id=\""""+ des +"""\">
            <ATCWaypointType>Airport</ATCWaypointType>
            <WorldPosition>"""+des_Pos+"""</WorldPosition>\n"""
    if RW_Head_way_Pos != "None": 
      fln_plan +="""  <RunwayNumberFP>"""+RW_num+"""</RunwayNumberFP>\n"""
      if len(RW_des) > 0:
        fln_plan +="""            <RunwayDesignatorFP>"""+RW_designa+"""</RunwayDesignatorFP>\n"""
    fln_plan +="""            <ICAO>
                <ICAOIdent>"""+ des +"""</ICAOIdent>        
          </ICAO>
        </ATCWaypoint>
    </FlightPlan.FlightPlan>
</SimBase.Document>
  """
    with open("fln_plan_arr.pln", "w", encoding="utf-8-sig") as file:
      file.write(fln_plan)
    
    inject_index = 1
    for index,waypoint in Injection_Waypoint.iterrows():
      if (len(Injection_Waypoint) - (Arrival.Arrival_Index + 1)) == index and waypoint["dis"] > 25:
        inject_index = index + 1
        #print(waypoint["waypoint"])
  
    return inject_index

  def inject_Traffic_Arrival(RW):
    global current_dir
    if len(Arrival.FR24_Arrival_Traffic) > 0:
      if Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Call"] in SimConnect.MSFS_AI_Arrival_Traffic['Call'].values:
        return
      if Arrival.Arrival_Index < len(Arrival.FR24_Arrival_Traffic):
        last_element = len(SimConnect.MSFS_AI_Arrival_Traffic)
        Estimate_time = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Estimate_time"]
        Call = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Call"]
        Type = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Type"]
        Src  = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Src_ICAO"]
        Des = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Des_ICAO"]
        Reg = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Reg"]
        try:
          Cur_Lat = Arrival.ADBS_Arrival_Traffic.loc[Arrival.ADBS_Arrival_Traffic["Reg"] == Reg, "Lat"].values[0]
        except:
          Cur_Lat = 0.0
        try:  
          Cur_Log = Arrival.ADBS_Arrival_Traffic.loc[Arrival.ADBS_Arrival_Traffic["Reg"] == Reg, "Lon"].values[0]
        except:
          Cur_Log = 0.0
        
        try:
          altitude = Arrival.ADBS_Arrival_Traffic.loc[Arrival.ADBS_Arrival_Traffic["Reg"] == Reg, "Altitude"].values[0]
        except:
          altitude = 0
        
        Prv_Lat = 0.0
        Prv_Log = 0.0
        Par_log = 0.0
        Par_lat = 0.0
        Stuck = 0
        Req_Id = Common.Global_req_id
        Obj_Id = 0
        Airspeed = 0.0
        Landing_light = 0.0
        ON_Ground = 0.0
        Heading = 0.0
        Gear = 0.0
        Landed = 0
        SimConnect.MSFS_AI_Arrival_Traffic.loc[last_element] = [Estimate_time, Call,Type,Src, Des,Par_lat,Par_log,Cur_Lat,Cur_Log,altitude,Prv_Lat,Prv_Log,Stuck,Airspeed,Landing_light,ON_Ground,Landed,Heading,Gear,Req_Id,Obj_Id]
        try:
          inject_index = Arrival.Create_flight_plan_arr(Src,Des,RW)
          Livery_name , callsign = Common.Get_flight_match(Call,Type)
          print("Arrival----" + callsign + " " + Type + " " + str(Livery_name))
          result = sm.AICreateEnrouteATCAircraft(Livery_name,callsign,int(Call[2:]),current_dir + "/fln_plan_arr",float(inject_index),False,Req_Id)
          Common.Global_req_id+=1
          time.sleep(2)
          if SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Obj_Id"].values[0] > 1:
              sm.AIAircraftAirspeed(SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Obj_Id"].values[0],600)
        except:
          print("Cannot create Arrival flight plan")
        #print(flt_plan)
        #print(SimConnect.MSFS_AI_Arrival_Traffic)
      Arrival.Arrival_Index += 1

  def Check_Traffic_Arrival():

    point1  = (SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Lat"] ,SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Log"])
    Altitude1 = SimConnect.MSFS_User_Aircraft.iloc[-1]["Altitude"]
    for index, flight in SimConnect.MSFS_AI_Arrival_Traffic.iterrows():
      try:
        if flight["Cur_Lat"] != 0.0 and flight["Cur_Log"] != 0.0:
          #Check Dist
          point2 = (flight["Cur_Lat"] ,flight["Cur_Log"])
          dis = geodesic(point1, point2).km
    
          Altitude2 = flight["Altitude"]
          Alt = abs(Altitude1 - Altitude2)
          if dis > SPWAN_DIST or Alt > SPWAN_ALTITUDE:
            print("Arrival Remove----" + flight["Call"] + " " + flight["Type"] + " Distance " + str(dis) + " Altitude diff" + str(Alt))
            sm.AIRemoveObject(flight["Obj_Id"],flight["Req_Id"])
            SimConnect.MSFS_AI_Arrival_Traffic = SimConnect.MSFS_AI_Arrival_Traffic[SimConnect.MSFS_AI_Arrival_Traffic['Obj_Id'] != flight["Obj_Id"]]
      except:
        print("Error: Arrival " + str(flight))
    SimConnect.MSFS_AI_Arrival_Traffic = SimConnect.MSFS_AI_Arrival_Traffic.reset_index(drop=True)
    #print(SimConnect.MSFS_AI_Arrival_Traffic)

  def Check_Traffic_onRunway_Arrival(RW):
    for index, flight in SimConnect.MSFS_AI_Arrival_Traffic.iterrows():
      sm.AIAircraft_GetPosition(flight["Req_Id"],flight["Obj_Id"])
      Call = flight["Call"]
      if SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Gear"].values[0] == 0 or \
      SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Landing_light"].values[0] == 0 or \
      SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Landed"].values[0] == 1:
        continue
      time.sleep(1)
      Airspeed = SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Airspeed"].values[0]
      Landing_light = SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Landing_light"].values[0]
      ON_Ground = SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "ON_Ground"].values[0]
      
      try:
        if float(Airspeed) < 200.0 and int(Landing_light) == 1 and int(ON_Ground) == 1:
          if float(Airspeed) < 100:
            final_speed = float(Airspeed) - 20
          else:
            final_speed = float(Airspeed) - 30
          if final_speed < 50:
            final_speed = 50
            SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Landed"] = 1
          if flight['Obj_Id'] > 1:
            sm.AIAircraftAirspeed(flight["Obj_Id"],final_speed)

      except:
        print("Unable to set speed of aircraft on runway")


  def Check_Traffic_MinSeparation():
    df = SimConnect.MSFS_AI_Arrival_Traffic
    for i in range(len(df)):
      for j in range(i + 1, len(df)):  # Avoid double calculation
        heading1 = int(df.iloc[i]['Heading'])
        heading2 = int(df.iloc[j]['Heading'])
        # Use a tolerance to compare headings
        if abs(heading1 - heading2) < 45:  # 45 degrees tolerance for heading comparison
            if df.iloc[i]["ON_Ground"] == 0 and df.iloc[j]["ON_Ground"] == 0 and df.iloc[i]["Landed"] == 0 and df.iloc[j]["Landed"] == 0:
                lat1, lon1 = df.iloc[i][['Cur_Lat', 'Cur_Log']]
                lat2, lon2 = df.iloc[j][['Cur_Lat', 'Cur_Log']]
                speed1, speed2 = df.iloc[i]['Airspeed'], df.iloc[j]['Airspeed']
                
                # Calculate horizontal separation (distance) between the two aircraft
                separation = haversine((lat1, lon1), (lat2, lon2))
                
                # Calculate the bearing from aircraft 1 to aircraft 2
                lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
                bearing = math.atan2(math.sin(lon2 - lon1) * math.cos(lat2), math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
                bearing1_to_2 = (math.degrees(bearing) + 360) % 360
                
                # Calculate the bearing from aircraft 2 to aircraft 1
                lat1, lon1, lat2, lon2 = map(math.radians, [lat2, lon2, lat1, lon1])
                bearing = math.atan2(math.sin(lon2 - lon1) * math.cos(lat2), math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
                bearing2_to_1 = (math.degrees(bearing) + 360) % 360
                
                required_relative_speed = (MIN_SEPARATION - separation) * 36  # Increase the reduction factor
                # Example of speed adjustment if separation is too small (adjust as needed)
                if separation < MIN_SEPARATION:
                  if abs(bearing1_to_2 - heading1) < 45:  # Aircraft 2 is ahead of Aircraft 1 if bearing matches heading
                      speed_required = max(50,int(speed2 - required_relative_speed))
                      if df.iloc[i]['Obj_Id'] > 1:
                        sm.AIAircraftAirspeed(df.iloc[i]['Obj_Id'],speed_required)
                        #print(f"Aircraft {df.iloc[j]['Call']} is ahead of Aircraft {df.iloc[i]['Call']} required airspeed adjustment: {speed_required} km/h  separation: {separation} km")
                  
                  elif abs(bearing2_to_1 - heading2) < 45:  # Aircraft 1 is ahead of Aircraft 2 if bearing matches heading
                      speed_required = max(50,int(speed1 - required_relative_speed))
                      if df.iloc[i]['Obj_Id'] > 1:
                        sm.AIAircraftAirspeed(df.iloc[j]['Obj_Id'],speed_required)
                        #print(f"Aircraft {df.iloc[i]['Call']} is ahead of Aircraft {df.iloc[j]['Call']} required airspeed adjustment: {speed_required} km/h  separation: {separation} km")
                    

class Departure:
  
  FR24_Departure_Traffic = pd.DataFrame(columns=['Estimate_time', 'Scheduled_time', "Call","des", "Type","Reg",'Ocio',"Src_ICAO","Des_ICAO","Local_depart_time"])

  Departure_Index = 0

  def Get_Departure(airport,max_departure):
   
    # Set up the WebDriver (this assumes you have ChromeDriver installed)
    driver = uc.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    
    print("------------Get Departure FR24 Traffic---------------------")
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "icao" LIKE '%"""+airport+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      src_air = pd.read_sql(sql=qry_str, con=conn.connection)
    airport_iata = src_air["iata"].iloc[-1]
    Max_Gate = int(src_air["num_parking_gate"].iloc[-1]) + int(src_air["num_parking_ga_ramp"].iloc[-1])
  
    #print(airport_iata)
    
    try:
      url = "https://www.flightradar24.com/data/airports/" + airport_iata +"/departures"
      driver.get(url)
      time.sleep(10)
    except:
      print("Check internet connection = " + url)
      return
    

    # Get current date and time 
    current_datetime = datetime.now()

    # Get the next day's date and time
    next_day_datetime = current_datetime + timedelta(days=1)

    flight_elements = driver.find_elements(By.XPATH, "//td")  # Example XPath
    
    prev_lin = ""
    index = 0
    Check_New_Day = False
    prev_time = current_datetime.strftime('%H')
    for flight in flight_elements:
      flight_info = flight.text 
      if  prev_lin != flight_info:
        flight_info_list = flight_info.split("\n")
        if flight_info_list[0].split(" ")[0] == "Estimated" or flight_info_list[0].split(" ")[0] == "Delayed" or flight_info_list[0].split(" ")[0] == "Departed":
          if flight_info_list[2] in Departure.FR24_Departure_Traffic['Call'].values:
            continue
          last_element = len(Departure.FR24_Departure_Traffic)
          if last_element < max_departure and last_element < Max_Gate:
            try:
              last_element = len(Departure.FR24_Departure_Traffic)
              #print(flight_info_list)
              Estimate_time_list = flight_info_list[0].split(" ")
              if len(Estimate_time_list) == 4:
                Estimate_time = (datetime.strptime(str(Estimate_time_list[2] +" "+ Estimate_time_list[3]), '%I:%M %p')).strftime('%H:%M')
                Scheduled_time  =  (datetime.strptime(str(flight_info_list[1]), '%I:%M %p')).strftime('%H:%M')
              else:
                Estimate_time = datetime.strptime(Estimate_time_list[2],'%H:%M').strftime('%H:%M')
                Scheduled_time  = datetime.strptime(str(flight_info_list[1]),'%H:%M').strftime('%H:%M')

              Call =  flight_info_list[2]
              Des =  flight_info_list[3]
              Type =  flight_info_list[4]
              Reg = flight_info_list[-2]
              Ocio =  flight_info_list[-1]

              
              qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+re.search(r'\((.*?)\)', Des).group(1).upper()+"""%'"""
              with Common.engine_airport_db.connect() as conn:
                  des_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              Src_ICAO = airport
              Des_ICAO = des_air["icao"].iloc[-1]

              if int(prev_time) - int(Estimate_time.split(":")[0]) > 2 :
                Check_New_Day = True
              if Check_New_Day == True:
                day = next_day_datetime.day
                month = next_day_datetime.month
                year = next_day_datetime.year
              else:
                day = current_datetime.day
                month = current_datetime.month
                year = current_datetime.year
              Specific_Time = str(year)+"-"+str(month)+"-"+str(day)+ " " + Estimate_time.split(":")[0] + ":" + Estimate_time.split(":")[1] + ":00" 
              Local_depart_time =  Common.Get_Timezone(Src_ICAO,Specific_Time)
              Departure.FR24_Departure_Traffic.loc[last_element] = [Estimate_time, Scheduled_time, Call, Des, Type,Reg,Ocio,Src_ICAO,Des_ICAO,Local_depart_time]
              prev_time = Estimate_time.split(":")[0]
            except:
                print(str(flight_info_list) + " not found")

      index+=1  
      prev_lin = flight_info
    Departure.FR24_Departure_Traffic = Departure.FR24_Departure_Traffic.sort_values(by='Local_depart_time',ascending=True).reset_index(drop=True)
    print(Departure.FR24_Departure_Traffic)
    # Close the browser
    driver.quit()
    #time.sleep(5)

  def Create_flight_plan_Dep(src,des,RW):
    global ACTIVE_RUNWAY_TAKEOFF
  
    crusing_alt = 30000
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+src+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    src_name = src_df.iloc[-1]["name"]
    src_Pos = Common.format_coordinates(float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]),float(src_df.iloc[-1]["altitude"]))
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+des+"""%'"""
    with Common.engine_airport_db.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    des_name = des_df.iloc[-1]["name"] 
    des_Pos =  Common.format_coordinates(float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]),float(des_df.iloc[-1]["altitude"]))
  
    
    with Common.engine_approach_db.connect() as conn:
      qry_str = '''SELECT "_rowid_", * FROM "main"."approach" WHERE "airport_ident" LIKE '%'''+src+'''%' ESCAPE '\\' AND "type" LIKE '%GPS%' ESCAPE '\\' AND "suffix" LIKE '%D%' ESCAPE '\\' AND "runway_name" LIKE '%'''+RW+'''%' ESCAPE '\\'LIMIT 0, 49999;'''
      SID_df = pd.read_sql(sql=qry_str, con=conn.connection)

    if ACTIVE_RUNWAY_TAKEOFF != "":
      RW = ACTIVE_RUNWAY_TAKEOFF
    
    RW_num =  str(int((re.findall(r'\d+', RW))[0]))
    RW_des = re.findall(r'[A-Za-z]', RW)
    
    if len(RW_des) > 0: 
      if RW_des[0] == "C":
        RW_designa = "CENTER"
      if RW_des[0] == "L":
        RW_designa = "LEFT"
      if RW_des[0] == "R":
        RW_designa = "RIGHT"
    
    
    departure_string = ""
    prev_dis = 9999999999999999
    Cur_dep = pd.DataFrame()
    point1 = (float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]))
    if len(SID_df) > 1:
      for index,dep in SID_df.iterrows():
        dep_id = dep["approach_id"].iloc[-1]
        with Common.engine_approach_db.connect() as conn:
          qry_str = '''SELECT "_rowid_", * FROM "main"."approach_leg" WHERE "approach_id" = "'''+str(dep_id) + '''" '''
          Cur_dep_leg = pd.read_sql(sql=qry_str, con=conn.connection)
          if len(Cur_dep_leg) > 0 and Cur_dep_leg.iloc[-1]["fix_ident"] != None and Cur_dep_leg.iloc[-1]["fix_region"] != None:
            with Common.engine_waypoint_db.connect() as conn:
              qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+Cur_dep_leg.iloc[-1]["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+Cur_dep_leg.iloc[-1]["fix_region"]+'''%' '''
              way_df = pd.read_sql(sql=qry_str, con=conn.connection)
              if len(way_df) > 0:
                point2 = (float(way_df["laty"].iloc[-1]),float(way_df["lonx"].iloc[-1]))
                distance = geodesic(point1, point2).km
                if distance < prev_dis:
                  prev_dis = distance
                  Cur_dep = Cur_dep_leg
                  Dep_Name = dep["fix_ident"]
          
    if len(Cur_dep) > 0:
      Cur_dep.drop(['is_missed', 'type' ,'arinc_descr_code','approach_fix_type','turn_direction','recommended_fix_type', 'rnp',\
                       'time','theta','recommended_fix_laty','is_true_course','speed_limit_type','recommended_fix_ident','recommended_fix_region','recommended_fix_lonx','is_flyover','course'], axis=1,inplace=True)

      for index, dep_leg in Cur_dep.iterrows():
        if dep_leg["fix_ident"] == None or dep_leg["fix_region"] == None:
          continue
        with Common.engine_waypoint_db.connect() as conn:
          qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+dep_leg["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+dep_leg["fix_region"]+'''%' '''
          way_df = pd.read_sql(sql=qry_str, con=conn.connection)
        
        if len(way_df) > 0:
          if dep_leg["altitude1"] > 0:
            altitude = dep_leg["altitude1"]
          else:
            altitude = 10000
          waypoint_Pos = Common.format_coordinates(float(way_df["laty"].iloc[-1]),float(way_df["lonx"].iloc[-1]),float(altitude))
          departure_string += """        <ATCWaypoint id=\"""" + dep_leg["fix_ident"] + """\">
                <ATCWaypointType>Intersection</ATCWaypointType>
                <WorldPosition>"""+waypoint_Pos+"""</WorldPosition>
                <SpeedMaxFP>400</SpeedMaxFP>
                <DepartureFP>"""+Dep_Name+"""</DepartureFP>
                <RunwayNumberFP>"""+RW_num+"""</RunwayNumberFP>\n"""
      
          if len(RW_des) > 0:
              departure_string +="""            <RunwayDesignatorFP>"""+RW_designa+"""</RunwayDesignatorFP>\n"""
          
          departure_string += """            <ICAO>
                    <ICAORegion>""" + dep_leg["fix_region"] + """</ICAORegion>
                    <ICAOIdent>""" + dep_leg["fix_ident"] + """</ICAOIdent>
                    <ICAOAirport>""" +src + """</ICAOAirport>
                </ICAO>
            </ATCWaypoint>\n"""
    
  
    fln_plan = """<?xml version="1.0" encoding="UTF-8"?> \
 
<SimBase.Document Type="AceXML" version="1,0">
    <Descr>AceXML Document</Descr>
    <FlightPlan.FlightPlan>
        <Title>"""+src + """ to """+ des +"""</Title>
        <FPType>IFR</FPType>
        <CruisingAlt>""" + str(crusing_alt) + """</CruisingAlt>
        <DepartureID>""" + src + """</DepartureID>
        <DepartureLLA>""" + src_Pos +"""</DepartureLLA>
        <DestinationID>""" + des + """</DestinationID>
        <DestinationLLA>"""+des_Pos+"""</DestinationLLA>
        <Descr>""" + src + """, """ + des + """</Descr>
        <DepartureName>""" + src_name + """</DepartureName>
        <DestinationName>""" + des_name + """</DestinationName>
        <AppVersion>
            <AppVersionMajor>10</AppVersionMajor>
            <AppVersionBuild>60327</AppVersionBuild>
        </AppVersion>
        <ATCWaypoint id=\""""+src + """\">
            <ATCWaypointType>Airport</ATCWaypointType>
            <WorldPosition>"""+src_Pos+"""</WorldPosition>
            <ICAO>
                <ICAOIdent>"""+src + """</ICAOIdent>
            </ICAO>
        </ATCWaypoint>\n""" + departure_string + """       <ATCWaypoint id=\""""+ des +"""\">
            <ATCWaypointType>Airport</ATCWaypointType>
            <WorldPosition>"""+des_Pos+"""</WorldPosition>
            <ICAO>
                <ICAOIdent>"""+ des +"""</ICAOIdent>
            </ICAO>
        </ATCWaypoint>
    </FlightPlan.FlightPlan>
</SimBase.Document>
"""

    with open("fln_plan_dep.pln", "w", encoding="utf-8-sig") as file:
      file.write(fln_plan)
    return fln_plan

  def Inject_Parked_Traffic():

    for index, row in Departure.FR24_Departure_Traffic.iterrows():
      if row["Call"] in SimConnect.MSFS_AI_Departure_Traffic['Call'].values or len(SimConnect.MSFS_AI_Departure_Traffic) > MAX_PARKED_AI_FLIGHTS :
        continue
      last_element = len(SimConnect.MSFS_AI_Departure_Traffic)
      if last_element < len(Departure.FR24_Departure_Traffic):
        Estimate_time = row["Estimate_time"]
        Call = row["Call"]
        Type = row["Type"]
        Src  = row["Src_ICAO"]
        Des = row["Des_ICAO"]
        Cur_Lat = 0.0
        Cur_Log = 0.0
        Prv_Lat = 0.0
        Prv_Log = 0.0
        Par_log = 0.0
        Par_lat = 0.0
        Stuck = 0
        altitude = 0
        Req_Id = Common.Global_req_id
        Obj_Id = 0
        Local_depart_time = row["Local_depart_time"]
        SimConnect.MSFS_AI_Departure_Traffic.loc[last_element] = [Estimate_time, Call,Type,Src, Des,Par_lat,Par_log,Cur_Lat,Cur_Log,altitude,Prv_Lat,Prv_Log,Stuck,Req_Id,Obj_Id,Local_depart_time]  
        try:
          Livery_name , callsign = Common.Get_flight_match(Call,Type)
          sm.AICreateParkedATCAircraft(Livery_name,callsign,Src,Req_Id)
          print("Parked----" + callsign + " " + Type + " " + str(Livery_name))
          Common.Global_req_id+=1
          time.sleep(1)
        except:
          print("Cannot create flight plan")

    #Check if Aircraft is injected     
    for index, flight in SimConnect.MSFS_AI_Departure_Traffic.iterrows():
      sm.AIAircraft_GetPosition(flight["Req_Id"],flight["Obj_Id"])
      time.sleep(1)

    #print(SimConnect.MSFS_AI_Departure_Traffic)
    
    #Remove ai traffic which is not spawned
    for index, flight in SimConnect.MSFS_AI_Departure_Traffic.iterrows():
      if flight["Cur_Lat"] == 0.0 and flight["Cur_Log"] == 0.0 and flight["Altitude"] == 0.0:
        print("Remove from database index " + str(flight["Call"]))
        SimConnect.MSFS_AI_Departure_Traffic = SimConnect.MSFS_AI_Departure_Traffic[SimConnect.MSFS_AI_Departure_Traffic['Obj_Id'] != flight["Obj_Id"]]

    SimConnect.MSFS_AI_Departure_Traffic = SimConnect.MSFS_AI_Departure_Traffic.reset_index(drop=True)
    #print(SimConnect.MSFS_AI_Departure_Traffic)     

  def Assign_Flt_plan(RW):
    global current_dir,DEPART_REALTIME
    Assign_flt = True
    if Departure.Departure_Index < len(SimConnect.MSFS_AI_Departure_Traffic) and len(SimConnect.MSFS_AI_Departure_Traffic) > 0:
      if DEPART_REALTIME == True:
        current_local_time = datetime.now().astimezone()
        depart_time = datetime.fromisoformat(str(SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Local_depart_time"]))
        if current_local_time > depart_time:
          Assign_flt = True
        else:
          Assign_flt = False       

      if Assign_flt == True:
        try:
          Src = SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Src"]
          Des =  SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Des"]
          Call = SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Call"]
          Type = SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Type"]
          Obj_Id =  SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Obj_Id"]
          Req_Id = Common.Global_req_id
          flt_plan = Departure.Create_flight_plan_Dep(Src,Des,RW)
          print("Depart----" +Call + " " + Type)
          sm.AISetAircraftFlightPlan(Obj_Id, current_dir + "/fln_plan_dep",Req_Id)
          Common.Global_req_id+=1
        except:
          print("Cannot create Departure flight plan")
        Departure.Departure_Index += 1 

  def Check_Traffic_Departure():

    point1  = (SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Lat"] ,SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Log"])
    Altitude1 = SimConnect.MSFS_User_Aircraft.iloc[-1]["Altitude"]
    for index, flight in SimConnect.MSFS_AI_Departure_Traffic.iterrows():
      sm.AIAircraft_GetPosition(flight["Req_Id"],flight["Obj_Id"])
      time.sleep(1)
      try:
        if flight["Cur_Lat"] != 0.0 and flight["Cur_Log"] != 0.0:
          #Check Dist
          point2 = (flight["Cur_Lat"] ,flight["Cur_Log"])
          dis = geodesic(point1, point2).km
    
          Altitude2 = flight["Altitude"]
          Alt = abs(Altitude1 - Altitude2)
          if dis > SPWAN_DIST or Alt > SPWAN_ALTITUDE:
            print("Departure Remove----" + flight["Call"] + " " + flight["Type"] + " Distance " + str(dis) + " Altitude diff " + str(Alt))
            sm.AIRemoveObject(flight["Obj_Id"],flight["Req_Id"])
            SimConnect.MSFS_AI_Departure_Traffic = SimConnect.MSFS_AI_Departure_Traffic[SimConnect.MSFS_AI_Departure_Traffic['Obj_Id'] != flight["Obj_Id"]]
            time.sleep(2)
      except:
        print("Error: Departure " + str(flight["Call"]))
    SimConnect.MSFS_AI_Departure_Traffic = SimConnect.MSFS_AI_Departure_Traffic.reset_index(drop=True)
    #print(SimConnect.MSFS_AI_Departure_Traffic)


sm = SimConnect(library_path=".\Sim_Connect_Custom\SimConnect.dll")
Common.Run()

#Arrival.Create_flight_plan_arr("VARP","LEMD","36R")
#Arrival.Create_flight_plan_arr("LEMD","SAEZ","11")
#Departure.Create_flight_plan_Dep("NZAA","SCIP","05R")
#Cruise.Create_flt_Plan("NZAA","SCIP",float(-35.173808),float(-161.3815),float(400),float(5000))
#Common.Get_flight_match("H2322","32N")


#Arrival.Get_Arrival("VHHH",100)