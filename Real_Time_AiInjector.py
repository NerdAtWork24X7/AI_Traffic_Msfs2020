import os
import pandas as pd
import time
from selenium import webdriver
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
import random
import xml.etree.ElementTree as ET
import time
from Sim_Connect_Custom.SimConnect import SimConnect 
#import SimConnect
import json
import requests
import config


warnings.filterwarnings('ignore')


flt_plan = "IFR Frankfurt Main (EDDF) to Munich Airport (EDDM).pln"


SRC_AIRPORT_IACO = ""
DES_AIRPORT_IACO = ""
SRC_ACTIVE_RUNWAY = ""
DES_ACTIVE_RUNWAY = ""

USE_FSTRAFFIC_LIVERY = True
MAX_ARRIVAL_AI_FLIGHTS = 20
MAX_DEPARTURE_AI_FLIGHTS = 20
MAX_CRUISE_AI_FLIGHTS = 20
MAX_PARKED_AI_FLIGHTS = 40
CRUISE_ALTITUDE = 10000
SRC_GROUND_RANGE = 50
DES_GROUND_RANGE = 100
GROUND_INJECTION_TIME_ARR = 3
GROUND_INJECTION_TIME_DEP = 2
CRUISE_INJECTION_TIME = 5
SPWAN_DIST = 200
SPWAN_ALTITUDE = 20000

current_dir = os.getcwd()


sm = SimConnect(library_path=".\Sim_Connect_Custom\SimConnect.dll")

class Common:
   
  chrome_options = Options()
  chrome_options.add_argument("--headless")  # Run in headless mode
  chrome_options.add_argument("--no-sandbox")  # Disable sandboxing (sometimes required)
  chrome_options.add_argument("--disable-dev-shm-usage")  # Disable /dev/shm usage (optional)
  chrome_options.add_argument('--disable-gpu')
  chrome_options.add_argument('--enable-unsafe-swiftshader')
  chrome_options.add_argument('log-level=3')
   
  engine_fldatabase = create_engine('sqlite:///little_navmap_msfs.sqlite')

  Global_req_id = 1000
  
  Retry_SRC = 0
  Retry_DES = 0

  Prev_Callsign = ""
  
  Src_Airport = pd.DataFrame(columns=['Src', 'Lat', "Lon","Altitude"])
  Des_Airport = pd.DataFrame(columns=['Src', 'Lat', "Lon","Altitude"]) 

  Shift_Src_Cruise = False
  Shift_Cruise_Des = False

  Skip_injection = 1 # For Flight spacing
  

  def Get_Flight_plan():
    global SRC_AIRPORT_IACO,DES_AIRPORT_IACO,SRC_ACTIVE_RUNWAY,DES_ACTIVE_RUNWAY

    response = requests.get("https://www.simbrief.com/api/xml.fetcher.php?username=" + config.config["simbrief_username"])

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
    with Common.engine_fldatabase.connect() as conn:
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

   
  def get_close_waypoint(src_lat,src_lon,des,des_lat,des_lon,max_dis):

    qry_str = f"""SELECT "_rowid_",* FROM "main"."waypoint" WHERE "airport_ident" LIKE '%""" + des +"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      des_waypoint_df = pd.read_sql(sql=qry_str, con=conn.connection)
  
    point_src = (src_lat,src_lon) 
    point_des = (des_lat,des_lon) 
    df_close_waypoint = pd.DataFrame()
    pre_dis = 99999999.0
    for index, waypoint in des_waypoint_df.iterrows():
      point2 = (waypoint["laty"], waypoint["lonx"])
      Cur_Dis = geodesic(point_src, point2).km
      Des_Dis = geodesic(point_des, point2).km
      if Cur_Dis < pre_dis and Des_Dis < max_dis and Des_Dis > 50:
        df_close_waypoint = waypoint
        pre_dis = Cur_Dis
  
    return df_close_waypoint
 

  def Get_flight_match(callsign,typecode):
    
    #Default Livaery
    model_name = "FSLTL_FSPXAI_B788_Airindia"
    
    livery_found = False
    try: 
      IATA_call = callsign[:2]
      engine_airline_icao = create_engine('sqlite:///airline_icao.sqlite')
      with engine_airline_icao.connect() as conn:
        qry_str = '''SELECT "_rowid_",* FROM "main"."mytable" WHERE "iata" LIKE '%'''+IATA_call+'''%' '''
        src_df = pd.read_sql(sql=qry_str, con=conn.connection)
        icao = src_df.iloc[0]["icao"]


      tree = ET.parse('FSLTL_Rules.vmr')
      root_Fsltl = tree.getroot()
      # Iterate over all ModelMatchRule elements
      for model_match_rule in root_Fsltl.findall('ModelMatchRule'):
        # Check if the TypeCode matches
        if typecode == model_match_rule.get('TypeCode') and icao == model_match_rule.get('CallsignPrefix'):
            model_name_cur = (model_match_rule.get('ModelName')).split("//")
            Common.Prev_Callsign = icao
            livery_found = True
            break

      if livery_found == False and USE_FSTRAFFIC_LIVERY == True:  
        tree = ET.parse('FSTraffic.vmr')
        root_FSTraffic = tree.getroot()
        for model_match_rule in root_FSTraffic.findall('ModelMatchRule'):
          # Check if the TypeCode matches
          if typecode == model_match_rule.get('TypeCode') and icao == model_match_rule.get('CallsignPrefix'):
              model_name_cur = (model_match_rule.get('ModelName')).split("//")
              Common.Prev_Callsign = icao
              livery_found = True
              break
      
      
      
      if livery_found == False:
        # Iterate over all ModelMatchRule elements
        for model_match_rule in root_Fsltl.findall('ModelMatchRule'):
          # Check if the TypeCode matches
          if typecode == model_match_rule.get('TypeCode') and Common.Prev_Callsign == model_match_rule.get('CallsignPrefix'):
              model_name_cur = (model_match_rule.get('ModelName')).split("//")
              livery_found = True
              break
          
      if livery_found == False and USE_FSTRAFFIC_LIVERY == True:
        # Iterate over all ModelMatchRule elements
        for model_match_rule in root_FSTraffic.findall('ModelMatchRule'):
          # Check if the TypeCode matches
          if typecode == model_match_rule.get('TypeCode') and Common.Prev_Callsign == model_match_rule.get('CallsignPrefix'):
              model_name_cur = (model_match_rule.get('ModelName')).split("//")
              livery_found = True
              break   

      model_name = model_name_cur[0]
    except:
      print("Error in flight matching")
  
  
    return model_name

      
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

  def Run():
        
    Common.Get_Flight_plan()

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+SRC_AIRPORT_IACO+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    Lat = src_df.iloc[-1]["laty"]
    Lon = src_df.iloc[-1]["lonx"]
    Altitude = src_df.iloc[-1]["altitude"]
    Common.Src_Airport.loc[-1] = [SRC_AIRPORT_IACO,Lat,Lon,Altitude] 
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+DES_AIRPORT_IACO+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
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
        if SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Src"] < SRC_GROUND_RANGE:
          Fr24_Dep_len = len(Departure.FR24_Departure_Traffic)
          Fr24_Arr_len = len(Arrival.FR24_Arrival_Traffic)    
          
          if (Fr24_Dep_len == 0 or Fr24_Arr_len == 0) and Common.Retry_SRC < 2:
            print("--------------At Departure Airport-------------------") 
            Departure.Get_Departure(SRC_AIRPORT_IACO,100)
            Departure.Inject_Parked_Traffic()
            Departure.Get_SID(SRC_AIRPORT_IACO,SRC_ACTIVE_RUNWAY)
            
            Arrival.Get_Arrival(SRC_AIRPORT_IACO,100)
            #Arrival.Get_STAR(SRC_AIRPORT_IACO,SRC_ACTIVE_RUNWAY)

            Common.Retry_SRC += 1             #Retry only once if Flight Radar data is available
            
          else:
            if min % GROUND_INJECTION_TIME_DEP == 0 and Departure.Departure_Index < MAX_DEPARTURE_AI_FLIGHTS:   
              if Departure.Departure_Index < Fr24_Dep_len:
                  Departure.Assign_Flt_plan()
                  Departure.Departure_Index += 1
              else:
                print("Departure injection Completed at Departure airport")

            if min % GROUND_INJECTION_TIME_ARR == 0 and len(SimConnect.MSFS_AI_Arrival_Traffic) < MAX_ARRIVAL_AI_FLIGHTS:
              if Arrival.Arrival_Index < len(Arrival.FR24_Arrival_Traffic) :
                if Common.Skip_injection % 4 != 0:
                  Arrival.inject_Traffic_Arrival(SRC_ACTIVE_RUNWAY)
                  Arrival.Arrival_Index += 1
              else:
                print("Arrival injection Completed at Departure airport")
              Common.Skip_injection += 1 

        # if User aircraft within 100KM of Arrival airport  
        if SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Src"] > SRC_GROUND_RANGE  and SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Des"] < DES_GROUND_RANGE:
          Fr24_Dep_len = len(Departure.FR24_Departure_Traffic)
          Fr24_Arr_len = len(Arrival.FR24_Arrival_Traffic)  
          
          if ((Fr24_Dep_len == 0 or Fr24_Arr_len == 0) or (Common.Shift_Cruise_Des == False and Common.Shift_Src_Cruise == True)) and Common.Retry_DES < 2:
            print("--------------At Destination Airport-------------------")   
            #Clear Arrival and Departure FR24 dataframe
            Common.Shift_Cruise_Des = True 
            Arrival.FR24_Arrival_Traffic = pd.DataFrame(columns=['Estimate_time', 'Scheduled_time', "Call","Src", "Type","Reg",'Ocio',"Src_ICAO","Des_ICAO","Local_arrival_time"])
            Arrival.Arrival_Index = 0
            Departure.FR24_Departure_Traffic = pd.DataFrame(columns=['Estimate_time', 'Scheduled_time', "Call","des", "Type","Reg",'Ocio',"Src_ICAO","Des_ICAO","Local_depart_time"])
            Departure.Departure_Index = 0
            Departure.departure_string = ""
            Arrival.approach_string = ""
            
            Departure.Get_Departure(DES_AIRPORT_IACO,100)
            Departure.Inject_Parked_Traffic()
            Departure.Get_SID(DES_AIRPORT_IACO,DES_ACTIVE_RUNWAY)
          
            Arrival.Get_Arrival(DES_AIRPORT_IACO,100)
            #Arrival.Get_STAR(DES_AIRPORT_IACO,DES_ACTIVE_RUNWAY)
          
            Common.Retry_DES += 1             #Retry only once if Flight Radar data is available
          
          else:
            if min % GROUND_INJECTION_TIME_DEP == 0 and Departure.Departure_Index < MAX_DEPARTURE_AI_FLIGHTS:
              if Departure.Departure_Index < Fr24_Dep_len:
                  Departure.Assign_Flt_plan()
                  Departure.Departure_Index += 1
              else:
                print("Departure injection Completed at destination airport")

            if min % GROUND_INJECTION_TIME_ARR == 0 and len(SimConnect.MSFS_AI_Arrival_Traffic) < MAX_ARRIVAL_AI_FLIGHTS:
              if Arrival.Arrival_Index < len(Arrival.FR24_Arrival_Traffic) :
                if Common.Skip_injection % 4 != 0:
                  Arrival.inject_Traffic_Arrival(DES_ACTIVE_RUNWAY)
                  Arrival.Arrival_Index += 1
              else:
                print("Arrival injection Completed at destination airport")  
              Common.Skip_injection += 1
            
        # if User aircraft is Crusing
        if SimConnect.MSFS_User_Aircraft.iloc[-1]["Altitude"] > CRUISE_ALTITUDE and SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Src"] > SRC_GROUND_RANGE  and SimConnect.MSFS_User_Aircraft.iloc[-1]["Dis_Des"] > DES_GROUND_RANGE:   
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

      time.sleep(50)


class Cruise:
  Cruise_Traffic_ADB = pd.DataFrame(columns=["Call", "Type","Src_ICAO","Des_ICAO","Lat","Lon","Altitude","Heading","Speed"])
  FR24_Cruise_Arrival_des_Traffic = pd.DataFrame(columns=["Call", "Type","Src_ICAO","Des_ICAO"])
  FR24_Cruise_Arrival_src_Traffic = pd.DataFrame(columns=["Call", "Type","Src_ICAO","Des_ICAO"])
  Cruise_Arr_des_Index = 0
  Cruise_Arr_src_Index = 0

  def Create_Cruise_Traffic_database_Arrival_des(airport,max_cruise):
    driver = webdriver.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    print("------------Get Cruise Arrival FR24 Traffic---------------------")

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "icao" LIKE '%"""+airport+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
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
              with Common.engine_fldatabase.connect() as conn:
                  src_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              Src_ICAO = src_air["icao"].iloc[-1]
              Des_ICAO = airport
              Cruise.FR24_Cruise_Arrival_des_Traffic.loc[last_element] = [Call,Type,Src_ICAO,Des_ICAO]
            except:
              print(str(flight_info_list) + " FR24 Arrival not found")
      
      prev_lin = flight_info
    
    print(Cruise.FR24_Cruise_Arrival_des_Traffic)

    driver.quit()
    time.sleep(5)


  def Create_Cruise_Traffic_database_Arrival_src(airport,max_cruise):
    driver = webdriver.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    print("------------Get Cruise Arrival FR24 Traffic---------------------")

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "icao" LIKE '%"""+airport+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
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
              with Common.engine_fldatabase.connect() as conn:
                  src_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              Src_ICAO = src_air["icao"].iloc[-1]
              Des_ICAO = airport
              Cruise.FR24_Cruise_Arrival_src_Traffic.loc[last_element] = [Call,Type,Src_ICAO,Des_ICAO]
            except:
              print(str(flight_info_list) + " FR24 Cruise Arrival not found")
      
      prev_lin = flight_info
    
    print(Cruise.FR24_Cruise_Arrival_src_Traffic)

    driver.quit()
    time.sleep(5)

  
  def Get_Cruise_Traffic_ADS_S(lat,lon,dist):
    
    url = "https://adsbx-flight-sim-traffic.p.rapidapi.com/api/aircraft/json/lat/" + str(lat) + "/lon/" + str(lon) +"/dist/" + str(dist) +"/"
    headers = {
    	"x-rapidapi-key": config.config["key"],
    	"x-rapidapi-host": config.config["host"]
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
            with Common.engine_fldatabase.connect() as conn:
              src_air = pd.read_sql(sql=qry_str, con=conn.connection)
            Src_ICAO = src_air["icao"].iloc[-1]
            
            qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+flight["to"].split(" ")[0]+"""%'"""
            with Common.engine_fldatabase.connect() as conn:
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
        Livery_name = Common.Get_flight_match(Call,Type)
        flt_plan = Cruise.Create_flt_Plan(Src,Des,float(Cur_Lat),float(Cur_Log),float(Speed),float(Altitude))
        print("Crusing----" + Call + " " + Type + " " + str(Livery_name))
        result = sm.AICreateEnrouteATCAircraft(Livery_name,Call,int(re.findall(r'\d+', Call)[0]),current_dir + "/fln_plan_cruise",float(1),False,Req_Id)
        Common.Global_req_id+=1
        time.sleep(2)
        if SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0] != 0:
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
          Livery_name = Common.Get_flight_match(Call,Type)
          Altitude_offset = random.choice([-1000,-2000,-3000,-4000,-5000,1000,2000,3000])
          flt_plan = Cruise.Create_flt_Plan(Src,Des,float(Cur_Lat), float(Cur_Log) ,Speed,float(int(Altitude) + int(Altitude_offset)))
          print("Crusing----" + Call + " " + Type + " " + str(Livery_name))
          result = sm.AICreateEnrouteATCAircraft(Livery_name,Call,int(re.findall(r'\d+', Call)[0]),current_dir + "/fln_plan_cruise",float(1),False,Req_Id)
          Common.Global_req_id+=1
          time.sleep(2)
          if SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0] != 0:
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
          Livery_name = Common.Get_flight_match(Call,Type)
          Altitude_offset = random.choice([-1000,-2000,-3000,-4000,-5000,1000,2000,3000])
          flt_plan = Cruise.Create_flt_Plan(Src,Des,float(Cur_Lat), float(Cur_Log) ,Speed,float(int(Altitude) + int(Altitude_offset)))
          print("Crusing----" + Call + " " + Type + " " + str(Livery_name))
          result = sm.AICreateEnrouteATCAircraft(Livery_name,Call,int(re.findall(r'\d+', Call)[0]),current_dir + "/fln_plan_cruise",float(1),False,Req_Id)
          Common.Global_req_id+=1
          time.sleep(2)
          if SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0] != 0:
            sm.AIAircraftAirspeed(SimConnect.MSFS_Cruise_Traffic.loc[SimConnect.MSFS_Cruise_Traffic["Call"] == Call, "Obj_Id"].values[0],500)
        except:
          print("Cannot create Arrival Des Cruise flight plan")  

    #print(SimConnect.MSFS_Cruise_Traffic)

  def Create_flt_Plan(Src,Des,Lat,Lon,Speed,crusing_alt):

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+Src+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    src_name = src_df.iloc[-1]["name"]
    src_Pos = Common.format_coordinates(float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]),float(src_df.iloc[-1]["altitude"]))
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+Des+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    des_name = des_df.iloc[-1]["name"] 
    des_Pos =  Common.format_coordinates(float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]),float(des_df.iloc[-1]["altitude"]))
    
    with Common.engine_fldatabase.connect() as conn:
      qry_str = '''SELECT"_rowid_",* FROM "main"."waypoint" WHERE "laty" > '''  + str(int(Lat)-3) + ''' AND "laty" < '''  + str(int(Lat) + 3) + ''' AND "lonx" > '''  + str(int(Lon)-3) + '''  AND "lonx" < '''  + str(int(Lon) + 3) + ''' '''
      way_df = pd.read_sql(sql=qry_str, con=conn.connection)


    point1 = (Lat,Lon)
    df_nearest_waypoint = pd.DataFrame()
    df_nearest_waypoint_list = []
    for waypoint in way_df.iterrows():
        point2 = (float(waypoint[1]["laty"]),float(waypoint[1]["lonx"]))
        Dis = geodesic(point1, point2).km
        if Dis > 2 and Dis < 100:
          df_nearest_waypoint_list.append(waypoint)
    
    df_nearest_waypoint = random.choice(df_nearest_waypoint_list) 
    waypoint_Pos = Common.format_coordinates(float(df_nearest_waypoint[1]["laty"]),float(df_nearest_waypoint[1]["lonx"]),float(crusing_alt))
    waypoint_id = df_nearest_waypoint[1]["ident"]
    waypoint_reg = df_nearest_waypoint[1]["region"]
    
    
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
  approach_string = ""

  def Get_Arrival_ADB_S(lat,lon,dist):
    
    print("------------Get Arrival ADB-S Traffic---------------------")

    url = "https://adsbx-flight-sim-traffic.p.rapidapi.com/api/aircraft/json/lat/" + str(lat) + "/lon/" + str(lon) +"/dist/" + str(dist) +"/"
    
    headers = {
    	"x-rapidapi-key": config.config["key"],
    	"x-rapidapi-host": config.config["host"]
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

    driver = webdriver.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    print("------------Get Arrival FR24 Traffic---------------------")

    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "icao" LIKE '%"""+airport+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
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

    current_datetime = datetime.now()
    next_day_datetime = current_datetime + timedelta(days=1)

    flight_elements = driver.find_elements(By.XPATH, "//td")
  
    prev_lin = ""
    Check_New_Day = False
    prev_time = current_datetime.strftime('%H')
    for flight in flight_elements:
      flight_info = flight.text 
      if  prev_lin != flight_info:
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
              with Common.engine_fldatabase.connect() as conn:
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

    driver.quit()
    time.sleep(5)

  def Get_STAR(airport,RW):
  
    with Common.engine_fldatabase.connect() as conn:
      qry_str = '''SELECT "_rowid_", * FROM "main"."approach" WHERE "airport_ident" LIKE '%'''+airport+'''%' ESCAPE '\\' AND "type" LIKE '%GPS%' ESCAPE '\\' AND "suffix" LIKE '%A%' ESCAPE '\\' AND "runway_name" LIKE '%'''+RW+'''%' ESCAPE '\\'LIMIT 0, 49999;'''
      src_df = pd.read_sql(sql=qry_str, con=conn.connection)

    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+airport+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    

    Max_app_df = pd.DataFrame()
    prev_distance = 99999999
    if len(src_df) > 2:
      for index,app in src_df.iterrows():
        app_id = app["approach_id"].iloc[-1]
        
        with Common.engine_fldatabase.connect() as conn:
          qry_str = '''SELECT "_rowid_", * FROM "main"."approach_leg" WHERE "approach_id" = "'''+str(app_id) + '''" '''
          Cur_app = pd.read_sql(sql=qry_str, con=conn.connection)
          with Common.engine_fldatabase.connect() as conn:
            qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+Cur_app.iloc[0]["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+Cur_app.iloc[0]["fix_region"]+'''%' '''
            way_df = pd.read_sql(sql=qry_str, con=conn.connection)
            point1 = (float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]))
            point2 = (way_df.iloc[-1]["laty"], way_df.iloc[-1]["lonx"]) 
            distance = geodesic(point1, point2).km
            if distance > 25 and distance < prev_distance:
              Max_app_df = Cur_app
              App_Name = app["fix_ident"]
              prev_distance = distance 
  
      try:          
        Max_app_df.drop(['is_missed', 'type' ,'arinc_descr_code','approach_fix_type','turn_direction','recommended_fix_type', 'rnp',\
                       'time','theta','recommended_fix_laty','is_true_course','speed_limit_type','recommended_fix_ident','recommended_fix_region','recommended_fix_lonx','is_flyover','course'], axis=1,inplace=True)
      except:
        pass       
    
    
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
  
    
    for index, app_leg in Max_app_df.iterrows():
      with Common.engine_fldatabase.connect() as conn:
        qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+app_leg["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+app_leg["fix_region"]+'''%' '''
        way_df = pd.read_sql(sql=qry_str, con=conn.connection)
      if len(way_df) > 0:
        Max_app_df.loc[index,"fix_lonx"] = way_df["lonx"].iloc[-1]
        Max_app_df.loc[index,"fix_laty"] = way_df["laty"].iloc[-1]
        point1 = (float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]))
        point2 = (way_df["laty"].iloc[-1], way_df["lonx"].iloc[-1]) 
        distance = geodesic(point1, point2).km
        Max_app_df.loc[index,"distance"] = distance
      
        app_waypoint_Pos = Common.format_coordinates(float(way_df["laty"].iloc[-1]),float(way_df["lonx"].iloc[-1]),float(5000))  
        Arrival.approach_string += """        <ATCWaypoint id=\"""" + app_leg["fix_ident"] + """\">
              <ATCWaypointType>Intersection</ATCWaypointType>
              <WorldPosition>"""+app_waypoint_Pos+"""</WorldPosition>
              <SpeedMaxFP>-1</SpeedMaxFP>\n"""
                 
        Arrival.approach_string +="""            <ArrivalFP>"""+App_Name+"""</ArrivalFP>
          <RunwayNumberFP>"""+RW_num+"""</RunwayNumberFP>\n"""
        if len(RW_des) > 0:
          Arrival.approach_string +="""            <RunwayDesignatorFP>"""+RW_designa+"""</RunwayDesignatorFP>\n"""
        
        Arrival.approach_string += """            <ICAO>
                  <ICAORegion>""" + app_leg["fix_region"] + """</ICAORegion>
                  <ICAOIdent>""" + app_leg["fix_ident"] + """</ICAOIdent>
                  <ICAOAirport>""" + airport + """</ICAOAirport>
              </ICAO>
          </ATCWaypoint>\n"""
        

    #print(Max_app_df)
    
  def Create_flight_plan_arr(src,des,RW):
  
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+src+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    src_name = src_df.iloc[-1]["name"]
    src_Pos = Common.format_coordinates(float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]),float(src_df.iloc[-1]["altitude"]))
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+des+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    des_name = des_df.iloc[-1]["name"] 
    des_Pos =  Common.format_coordinates(float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]),float(des_df.iloc[-1]["altitude"]))
    
    max_dist = 100
    df_close_waypoint = Common.get_close_waypoint(float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]),des,float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]),max_dist)
  
    src_waypoint_Pos = Common.format_coordinates(float(df_close_waypoint["laty"]),float(df_close_waypoint["lonx"]),7000)
    src_waypoint_id = df_close_waypoint["ident"]
    src_waypoint_reg = df_close_waypoint["region"]
    
    #if Arrival.Arrival_Index < 10:
    #    crusing_alt = str(4000 + (500 * Arrival.Arrival_Index))
    #else :
    crusing_alt = str(7000)
    

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
        </ATCWaypoint>
        <ATCWaypoint id=\"""" + src_waypoint_id + """\">
            <ATCWaypointType>Intersection</ATCWaypointType>
            <WorldPosition>"""+src_waypoint_Pos+"""</WorldPosition>
            <SpeedMaxFP>400</SpeedMaxFP>
            <ICAO>
                <ICAORegion>""" + src_waypoint_reg + """</ICAORegion>
                <ICAOIdent>""" + src_waypoint_id + """</ICAOIdent>
            </ICAO>
        </ATCWaypoint>\n""" +  Arrival.approach_string + """        <ATCWaypoint id=\""""+ des +"""\">
            <ATCWaypointType>Airport</ATCWaypointType>
            <WorldPosition>"""+des_Pos+"""</WorldPosition>
            <RunwayNumberFP>"""+RW_num+"""</RunwayNumberFP>\n"""
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
    return fln_plan

  def inject_Traffic_Arrival(RW):
    global current_dir
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
      SimConnect.MSFS_AI_Arrival_Traffic.loc[last_element] = [Estimate_time, Call,Type,Src, Des,Par_lat,Par_log,Cur_Lat,Cur_Log,altitude,Prv_Lat,Prv_Log,Stuck,Req_Id,Obj_Id]
      try:
        flt_plan = Arrival.Create_flight_plan_arr(Src,Des,RW)
        Livery_name = Common.Get_flight_match(Call,Type)
        print("Arrival----" + Call + " " + Type + " " + str(Livery_name))
        result = sm.AICreateEnrouteATCAircraft(Livery_name,Call,int(Call[2:]),current_dir + "/fln_plan_arr",float(1),False,Req_Id)
        Common.Global_req_id+=1
        time.sleep(2)
        if SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Obj_Id"].values[0] != 0:
            sm.AIAircraftAirspeed(SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Call"] == Call, "Obj_Id"].values[0],400)
      except:
        print("Cannot create Arrival flight plan")
      #print(flt_plan)
      #print(SimConnect.MSFS_AI_Arrival_Traffic)

  def Check_Traffic_Arrival():

    point1  = (SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Lat"] ,SimConnect.MSFS_User_Aircraft.iloc[-1]["Cur_Log"])
    Altitude1 = SimConnect.MSFS_User_Aircraft.iloc[-1]["Altitude"]
    for index, flight in SimConnect.MSFS_AI_Arrival_Traffic.iterrows():
      #print(flight)
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
            print("Arrival Remove----" + flight["Call"] + " " + flight["Type"] + " Distance " + str(dis) + " Altitude diff" + str(Alt))
            sm.AIRemoveObject(flight["Obj_Id"],flight["Req_Id"])
            SimConnect.MSFS_AI_Arrival_Traffic = SimConnect.MSFS_AI_Arrival_Traffic[SimConnect.MSFS_AI_Arrival_Traffic['Obj_Id'] != flight["Obj_Id"]]
            time.sleep(2)
      except:
        print("Error: Arrival " + str(flight))
    SimConnect.MSFS_AI_Arrival_Traffic = SimConnect.MSFS_AI_Arrival_Traffic.reset_index(drop=True)
    #print(SimConnect.MSFS_AI_Arrival_Traffic)

class Departure:
  
  FR24_Departure_Traffic = pd.DataFrame(columns=['Estimate_time', 'Scheduled_time', "Call","des", "Type","Reg",'Ocio',"Src_ICAO","Des_ICAO","Local_depart_time"])

  departure_string = ""
  Departure_Index = 0

  def Get_Departure(airport,max_departure):
   
    # Set up the WebDriver (this assumes you have ChromeDriver installed)
    driver = webdriver.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    
    print("------------Get Departure FR24 Traffic---------------------")
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "icao" LIKE '%"""+airport+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
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
        if flight_info_list[0].split(" ")[0] == "Estimated" or flight_info_list[0].split(" ")[0] == "Delayed":
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
              with Common.engine_fldatabase.connect() as conn:
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
    time.sleep(5)

  def Get_SID(airport,RW):

    with Common.engine_fldatabase.connect() as conn:
      qry_str = '''SELECT "_rowid_", * FROM "main"."approach" WHERE "airport_ident" LIKE '%'''+airport+'''%' ESCAPE '\\' AND "type" LIKE '%GPS%' ESCAPE '\\' AND "suffix" LIKE '%D%' ESCAPE '\\' AND "runway_name" LIKE '%'''+RW+'''%' ESCAPE '\\'LIMIT 0, 49999;'''
      src_df = pd.read_sql(sql=qry_str, con=conn.connection)
    
    Max_dep_df = pd.DataFrame()
    if len(src_df) > 1:
      max_leg_dep = 0
      for index,dep in src_df.iterrows():
        dep_id = dep["approach_id"].iloc[-1]
        with Common.engine_fldatabase.connect() as conn:
          qry_str = '''SELECT "_rowid_", * FROM "main"."approach_leg" WHERE "approach_id" = "'''+str(dep_id) + '''" '''
          Cur_dep = pd.read_sql(sql=qry_str, con=conn.connection)
          cur_len = len(Cur_dep)
          if cur_len > max_leg_dep:
            Max_dep_df = Cur_dep
            max_leg_dep = cur_len
            Dep_Name = dep["fix_ident"]
          
      try:
        Max_dep_df.drop(['is_missed', 'type' ,'arinc_descr_code','approach_fix_type','turn_direction','recommended_fix_type', 'rnp',\
                       'time','theta','recommended_fix_laty','is_true_course','speed_limit_type','recommended_fix_ident','recommended_fix_region','recommended_fix_lonx','is_flyover','course'], axis=1,inplace=True)
      except:
        pass
    
    #fill lat and log
  
    RW_num =  str(int((re.findall(r'\d+', RW))[0]))
    RW_des = re.findall(r'[A-Za-z]', RW)
    
    if len(RW_des) > 0: 
      if RW_des[0] == "C":
        RW_designa = "CENTER"
      if RW_des[0] == "L":
        RW_designa = "LEFT"
      if RW_des[0] == "R":
        RW_designa = "RIGHT"
  
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+airport+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
  
    for index, dep_leg in Max_dep_df.iterrows():
      if dep_leg["fix_ident"] == None or dep_leg["fix_region"] == None:
        continue
      with Common.engine_fldatabase.connect() as conn:
        qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+dep_leg["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+dep_leg["fix_region"]+'''%' '''
        way_df = pd.read_sql(sql=qry_str, con=conn.connection)
      if len(way_df) > 0:
        Max_dep_df.loc[index,"fix_lonx"] = way_df["lonx"].iloc[-1]
        Max_dep_df.loc[index,"fix_laty"] = way_df["laty"].iloc[-1]
        point1 = (float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]))
        point2 = (way_df["laty"].iloc[-1], way_df["lonx"].iloc[-1]) 
        distance = geodesic(point1, point2).km
        Max_dep_df.loc[index,"distance"] = distance
        
        if Max_dep_df.loc[index,"altitude1"] > 0:
          altitude = Max_dep_df.loc[index,"altitude1"]
        else:
          altitude = 10000
        src_waypoint_Pos = Common.format_coordinates(float(way_df["laty"].iloc[-1]),float(way_df["lonx"].iloc[-1]),float(altitude))
        Departure.departure_string += """        <ATCWaypoint id=\"""" + dep_leg["fix_ident"] + """\">
              <ATCWaypointType>Intersection</ATCWaypointType>
              <WorldPosition>"""+src_waypoint_Pos+"""</WorldPosition>
              <SpeedMaxFP>400</SpeedMaxFP>
              <DepartureFP>"""+Dep_Name+"""</DepartureFP>
              <RunwayNumberFP>"""+RW_num+"""</RunwayNumberFP>\n"""
    
        if len(RW_des) > 0:
            Departure.departure_string +="""            <RunwayDesignatorFP>"""+RW_designa+"""</RunwayDesignatorFP>\n"""
        
        Departure.departure_string += """            <ICAO>
                  <ICAORegion>""" + dep_leg["fix_region"] + """</ICAORegion>
                  <ICAOIdent>""" + dep_leg["fix_ident"] + """</ICAOIdent>
                  <ICAOAirport>""" +airport + """</ICAOAirport>
              </ICAO>
          </ATCWaypoint>\n"""
        
  
    #print(Max_dep_df)

  def Create_flight_plan_Dep(src,des):
  
    crusing_alt = 30000
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+src+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    src_name = src_df.iloc[-1]["name"]
    src_Pos = Common.format_coordinates(float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]),float(src_df.iloc[-1]["altitude"]))
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+des+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    des_name = des_df.iloc[-1]["name"] 
    des_Pos =  Common.format_coordinates(float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]),float(des_df.iloc[-1]["altitude"]))
  
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
        </ATCWaypoint>\n""" + Departure.departure_string + """       <ATCWaypoint id=\""""+ des +"""\">
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
        SimConnect.MSFS_AI_Departure_Traffic.loc[last_element] = [Estimate_time, Call,Type,Src, Des,Par_lat,Par_log,Cur_Lat,Cur_Log,altitude,Prv_Lat,Prv_Log,Stuck,Req_Id,Obj_Id]  
        try:
          Livery_name = Common.Get_flight_match(Call,Type)
          sm.AICreateParkedATCAircraft(Livery_name,Call,Src,Req_Id)
          print("Parked----" + Call + " " + Type + " " + str(Livery_name))
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

  def Assign_Flt_plan():
    global current_dir
    if Departure.Departure_Index < len(SimConnect.MSFS_AI_Departure_Traffic):
      try:
        Src = SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Src"]
        Des =  SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Des"]
        Call = SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Call"]
        Type = SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Type"]
        Obj_Id =  SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Obj_Id"]
        Req_Id = Common.Global_req_id
        flt_plan = Departure.Create_flight_plan_Dep(Src,Des)
        print("Depart----" +Call + " " + Type)
        sm.AISetAircraftFlightPlan(Obj_Id, current_dir + "/fln_plan_dep",Req_Id)
        Common.Global_req_id+=1
      except:
        print("Cannot create Departure flight plan")

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


Common.Run()
