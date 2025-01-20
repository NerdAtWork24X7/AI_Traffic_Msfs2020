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


warnings.filterwarnings('ignore')



SRC_AIRPORT_IATA = "BOM"
SRC_AIRPORT_IACO = "VABB"
ACTIVE_RUNWAY = "27"
MAX_ARRIVAL = 40
MAX_DEPARTURE = 40
MAX_SPAWN_DIST = 200
MAX_THRESOLD_ALTITUDE = 10000
INJECTION_TIME = 2


sm = SimConnect(library_path=".\Sim_Connect_Custom\SimConnect.dll")

class Common:
   
  chrome_options = Options()
  chrome_options.add_argument("--headless")  # Run in headless mode
  chrome_options.add_argument("--no-sandbox")  # Disable sandboxing (sometimes required)
  chrome_options.add_argument("--disable-dev-shm-usage")  # Disable /dev/shm usage (optional)
  chrome_options.add_argument('--disable-gpu')
  chrome_options.add_argument('--enable-unsafe-swiftshader')
   
  engine_fldatabase = create_engine('sqlite:///little_navmap_msfs.sqlite')

  Global_req_id = 0
  

  def Get_Timezone(src,specific_time_str):
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+src+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      src_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    
    lon = src_df.iloc[-1]["lonx"]
    lat = src_df.iloc[-1]["laty"]
    tf = TimezoneFinder()
    timezone = tf.timezone_at(lng=lon, lat=lat)
    
    # Define the timezone object for the local timezone
    from_zone = pytz.timezone(timezone)
    to_zone = get_localzone()
    
    specific_time = datetime.strptime(specific_time_str, '%Y-%m-%d %H:%M:%S')
    localized_time = from_zone.localize(specific_time)
   
    converted_time = localized_time.astimezone(to_zone)
        
    return converted_time


  def decimal_to_dms(degrees, is_latitude=True):
    # Get the absolute value of the degrees
    abs_deg = abs(degrees)
    
    # Calculate the degrees
    d = int(abs_deg)
    
    # Calculate the minutes
    minutes = (abs_deg - d) * 60
    m = int(minutes)
    
    # Calculate the seconds
    seconds = (minutes - m) * 60
    s = round(seconds, 2)  # Round to 2 decimal places for better readability
    
    # Determine the direction (N/S for latitude, E/W for longitude)
    if is_latitude:
        direction = "N" if degrees >= 0 else "S"
    else:
        direction = "E" if degrees >= 0 else "W"
    
    return f"{direction}{d}° {m}' {s}\""


  def format_coordinates(lat, lon, altitude):
    # Convert latitude and longitude to DMS format
    lat_dms = Common.decimal_to_dms(lat, is_latitude=True)
    lon_dms = Common.decimal_to_dms(lon, is_latitude=False)
    
    # Format the altitude (if any) with a sign and 2 decimal places
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
      point2 = (waypoint["laty"], waypoint["lonx"])   #Cordinates of ai
      Cur_Dis = geodesic(point_src, point2).km
      Des_Dis = geodesic(point_des, point2).km
      if Cur_Dis < pre_dis and Des_Dis < max_dis:
        df_close_waypoint = waypoint
        pre_dis = Cur_Dis
  
    return df_close_waypoint
 

  def Get_flight_match(callsign,typecode):
    
    #Default Livaery
    model_name = "FSLTL_FSPXAI_B788_Airindia"
  
    try: 
      tree = ET.parse('FSLTL_Rules.vmr')
      root = tree.getroot()
      IATA_call = callsign[:2]
      engine_airline_icao = create_engine('sqlite:///airline_icao.sqlite')
      with engine_airline_icao.connect() as conn:
        qry_str = '''SELECT "_rowid_",* FROM "main"."mytable" WHERE "iata" LIKE '%'''+IATA_call+'''%' '''
        src_df = pd.read_sql(sql=qry_str, con=conn.connection)
        icao = src_df.iloc[0]["icao"]
      #print(icao)
      # Iterate over all ModelMatchRule elements
      for model_match_rule in root.findall('ModelMatchRule'):
        # Check if the TypeCode matches
        if typecode == model_match_rule.get('TypeCode') and icao == model_match_rule.get('CallsignPrefix'):
            model_name_cur = (model_match_rule.get('ModelName')).split("//")
            break
      #print(model_name[0])
      model_name = model_name_cur[0]
    except:
      print("Error in flight matching")
  
  
    return model_name


  def Run():
        
    Departure.Get_Departure(SRC_AIRPORT_IATA)
    Departure.Inject_Parked_Traffic()
    Departure.Get_SID(SRC_AIRPORT_IACO,ACTIVE_RUNWAY)
   
    
    Arrival.Get_Arrival(SRC_AIRPORT_IATA)
    #Arrival.Get_STAR(SRC_AIRPORT_IACO,ACTIVE_RUNWAY)

    prev_min = 0
    while(False):
      
      if Departure.Departure_Index < 20 :
        Departure.Assign_Flt_plan()
        Arrival.inject_Traffic_Arrival()
        Arrival.Arrival_Index += 1
        Departure.Departure_Index += 1
      
      time.sleep(10)
    
    while (True):
      now = datetime.now()
      min = now.minute

      #if min % 1 == 0:
      #  sm.AIAircraft_GetPosition(4, sm.air_1_obj)
    
      #if min % 5 == 0:
      #  Arrival.Check_Arrived_Flights()
      #  Departure.Check_Departed_aircraft()


      if min % INJECTION_TIME == 0 and prev_min != min:
        #print(sm.running)
        #print(sm.paused)
        if Departure.Departure_Index < MAX_DEPARTURE :
          Departure.Assign_Flt_plan()
          Departure.Departure_Index += 1
        else:
          print("Departure injection Completed")
        
        if Arrival.Arrival_Index < MAX_ARRIVAL :
          Arrival.inject_Traffic_Arrival()
          Arrival.Arrival_Index += 1
        else:
          print("Arrival injection Completed")
       
       
        #if Departure.Departure_Index >= len(Departure.FR24_Departure_Traffic):
        #  Departure.Departure_Index = 0
        #  Departure.Get_Departure(SRC_AIRPORT_IATA)
        #  Departure.Inject_Parked_Traffic()
        #  Departure.Get_SID(SRC_AIRPORT_IACO,ACTIVE_RUNWAY)

        #
        #if Arrival.Arrival_Index >= len(Arrival.FR24_Arrival_Traffic):
        #  Arrival.Arrival_Index = 0
        #  Arrival.Get_Arrival(SRC_AIRPORT_IATA)
        #  #Arrival.Get_STAR(SRC_AIRPORT_IACO,ACTIVE_RUNWAY)
        
        prev_min = min
        print("injecting")
      time.sleep(50)





class Arrival:

  FR24_Arrival_Traffic = pd.DataFrame(columns=['Estimate_time', 'Scheduled_time', "Call","Src", "Type",'Ocio',"Src_ICAO","Dest_ICAO","Local_arrival_time"])
 
  Arrival_Index = 0
  approach_string = ""


  # Extract and print flight information
  def Get_Arrival(airport):
    # Set up the WebDriver (this assumes you have ChromeDriver installed)
    driver = webdriver.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    #window_size = driver.get_window_size()
    #print(window_size)
    url = "https://www.flightradar24.com/data/airports/" + airport +"/arrivals"
    driver.get(url)
    time.sleep(10)

    # Get current date and time 
    current_datetime = datetime.now()

    # Get the next day's date and time
    next_day_datetime = current_datetime + timedelta(days=1)

    flight_elements = driver.find_elements(By.XPATH, "//td")  # Example XPath
  
    prev_lin = ""
    Check_New_Day = False
    prev_AM_PM = ""
    for flight in flight_elements:
      flight_info = flight.text 
      if  prev_lin != flight_info:
        #print(flight_info)
        flight_info_list = flight_info.split("\n") 
        #print(flight_info_list)
        if flight_info_list[0].split(" ")[0] == "Estimated" or flight_info_list[0].split(" ")[0] == "Delayed":
          if flight_info_list[2] in Arrival.FR24_Arrival_Traffic['Call'].values:
            continue
          last_element = len(Arrival.FR24_Arrival_Traffic)
          if last_element < MAX_ARRIVAL:
            try:
              last_element = len(Arrival.FR24_Arrival_Traffic)
              Estimate_time = (datetime.strptime(str(flight_info_list[0].split(" ")[1] +" "+ flight_info_list[0].split(" ")[2]), '%I:%M %p')).strftime('%H:%M')
              Scheduled_time  =  (datetime.strptime(str(flight_info_list[1]), '%I:%M %p')).strftime('%H:%M')
              Call =  flight_info_list[2]
              Src =  flight_info_list[3]
              Type =  flight_info_list[4]
              Ocio =  flight_info_list[-1]
              qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+airport+"""%'"""
              with Common.engine_fldatabase.connect() as conn:
                  des_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+re.search(r'\((.*?)\)', Src).group(1).upper()+"""%'"""
              with Common.engine_fldatabase.connect() as conn:
                  src_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              Src_ICAO = src_air["icao"].iloc[-1]
              Dest_ICAO = des_air["icao"].iloc[-1]

              if flight_info_list[0].split(" ")[2] == "AM" and prev_AM_PM == "PM":
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
              Local_arrival_time =  Common.Get_Timezone(Dest_ICAO,Specific_Time)
              Arrival.FR24_Arrival_Traffic.loc[last_element] = [Estimate_time, Scheduled_time, Call, Src, Type,Ocio,Src_ICAO,Dest_ICAO,Local_arrival_time]
              prev_AM_PM = flight_info_list[0].split(" ")[2]
            except:
              print(str(flight_info_list) + " not found")
      
      prev_lin = flight_info
    
    Arrival.FR24_Arrival_Traffic = Arrival.FR24_Arrival_Traffic.sort_values(by='Local_arrival_time',ascending=True).reset_index(drop=True)
    print(Arrival.FR24_Arrival_Traffic)
    # Close the browser
    driver.quit()
    time.sleep(5)

  def Get_STAR(airport,RW):
  
    with Common.engine_fldatabase.connect() as conn:
      qry_str = '''SELECT "_rowid_", * FROM "main"."approach" WHERE "airport_ident" LIKE '%'''+airport+'''%' ESCAPE '\\' AND "type" LIKE '%GPS%' ESCAPE '\\' AND "suffix" LIKE '%A%' ESCAPE '\\' AND "runway_name" LIKE '%'''+RW+'''%' ESCAPE '\\'LIMIT 0, 49999;'''
      src_df = pd.read_sql(sql=qry_str, con=conn.connection)
      #print(src_df)
    
    qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "ident" LIKE '%"""+airport+"""%'"""
    with Common.engine_fldatabase.connect() as conn:
      des_df = pd.read_sql(sql=qry_str, con=conn.connection) 
    

    Max_app_df = pd.DataFrame()
    prev_distance = 99999999
    if len(src_df) > 2:
      for index,app in src_df.iterrows():
        app_id = app["approach_id"].iloc[-1]
        
        with Common.engine_fldatabase.connect() as conn:
          qry_str = '''SELECT "_rowid_", * FROM "main"."approach_leg" WHERE "approach_id" LIKE '%'''+str(app_id)+'''%' '''
          Cur_app = pd.read_sql(sql=qry_str, con=conn.connection)
          with Common.engine_fldatabase.connect() as conn:
            qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+Cur_app.iloc[0]["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+Cur_app.iloc[0]["fix_region"]+'''%' '''
            way_df = pd.read_sql(sql=qry_str, con=conn.connection)
            point1 = (float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]))
            point2 = (way_df.iloc[-1]["laty"], way_df.iloc[-1]["lonx"]) 
            distance = geodesic(point1, point2).km
            #print(distance)
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
    RW_num =  ACTIVE_RUNWAY[:2]
    
    if len(ACTIVE_RUNWAY) > 2:
      if ACTIVE_RUNWAY[-1] == "C":
        RW_designa = "CENTER"
      if ACTIVE_RUNWAY[-1] == "L":
        RW_designa = "LEFT"
      if ACTIVE_RUNWAY[-1] == "R":
        RW_designa = "RIGHT"
  
    
    for index, app_leg in Max_app_df.iterrows():
      with Common.engine_fldatabase.connect() as conn:
        qry_str = '''SELECT "_rowid_", * FROM "main"."waypoint" WHERE "ident" LIKE '%'''+app_leg["fix_ident"] +'''%' ESCAPE '\\' AND "region" LIKE '%'''+app_leg["fix_region"]+'''%' '''
        way_df = pd.read_sql(sql=qry_str, con=conn.connection)
      if len(way_df) > 0:
        Max_app_df.loc[index,"fix_lonx"] = way_df["lonx"].iloc[-1]
        Max_app_df.loc[index,"fix_laty"] = way_df["laty"].iloc[-1]
        point1 = (float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]))
        #point1 = (float(df_close_waypoint["laty"]),float(df_close_waypoint["lonx"]))
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
        if len(ACTIVE_RUNWAY) > 2:
          Arrival.approach_string +="""            <RunwayDesignatorFP>"""+RW_designa+"""</RunwayDesignatorFP>\n"""
        
        Arrival.approach_string += """            <ICAO>
                  <ICAORegion>""" + app_leg["fix_region"] + """</ICAORegion>
                  <ICAOIdent>""" + app_leg["fix_ident"] + """</ICAOIdent>
                  <ICAOAirport>""" + airport + """</ICAOAirport>
              </ICAO>
          </ATCWaypoint>\n"""
        

    print(Max_app_df)
    
    

  def Create_flight_plan_arr(src,des):
  
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
    
    #if Arrival.Arrival_Index < 10:
    #    max_dist = 40 + (Arrival.Arrival_Index * 3)
    #else :
    #  max_dist = 60
    max_dist = 50
    df_close_waypoint = Common.get_close_waypoint(float(src_df.iloc[-1]["laty"]),float(src_df.iloc[-1]["lonx"]),des,float(des_df.iloc[-1]["laty"]),float(des_df.iloc[-1]["lonx"]),max_dist)
  
    src_waypoint_Pos = Common.format_coordinates(float(df_close_waypoint["laty"]),float(df_close_waypoint["lonx"]),float(des_df.iloc[-1]["altitude"]))
    src_waypoint_id = df_close_waypoint["ident"]
    src_waypoint_reg = df_close_waypoint["region"]
    
    if Arrival.Arrival_Index < 10:
        crusing_alt = str(4000 + (500 * Arrival.Arrival_Index))
    else :
       crusing_alt = str(15000)
    

    #fill lat and log
    RW_num =  ACTIVE_RUNWAY[:2]
    
    if len(ACTIVE_RUNWAY) > 2:
      if ACTIVE_RUNWAY[-1] == "C":
        RW_designa = "CENTER"
      if ACTIVE_RUNWAY[-1] == "L":
        RW_designa = "LEFT"
      if ACTIVE_RUNWAY[-1] == "R":
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
            <ApproachTypeFP>ILS</ApproachTypeFP>
            <RunwayNumberFP>"""+RW_num+"""</RunwayNumberFP>\n"""
    if len(ACTIVE_RUNWAY) > 2:
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

 
  def inject_Traffic_Arrival():
      
    if Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Call"] in SimConnect.MSFS_AI_Arrival_Traffic['Call'].values:
      return
    if Arrival.Arrival_Index < MAX_ARRIVAL:
      last_element = len(SimConnect.MSFS_AI_Arrival_Traffic)
      Estimate_time = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Estimate_time"]
      Call = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Call"]
      Type = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Type"]
      Src  = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Src_ICAO"]
      Dest = Arrival.FR24_Arrival_Traffic.loc[Arrival.Arrival_Index,"Dest_ICAO"]
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
      SimConnect.MSFS_AI_Arrival_Traffic.loc[last_element] = [Estimate_time, Call,Type,Src, Dest,Par_lat,Par_log,Cur_Lat,Cur_Log,altitude,Prv_Lat,Prv_Log,Stuck,Req_Id,Obj_Id]
      try:
        flt_plan = Arrival.Create_flight_plan_arr(Src,Dest)
        Livery_name = Common.Get_flight_match(Call,Type)
        print("Arrival----" + Call + " " + Type + " " + str(Livery_name))
        result = sm.AICreateEnrouteATCAircraft(Livery_name,Call,int(Call[2:]),"E:/workspace/pyhton/aiTraffic/fln_plan_arr",float(1),False,Req_Id)
        Common.Global_req_id+=1
      except:
        print("Cannot create flight plan")
      #print(flt_plan)
      #print(SimConnect.MSFS_AI_Arrival_Traffic)

  def Check_Arrived_Flights():
    
    sm.AIAircraft_GetPosition(0, 1)
    time.sleep(1)
    #point1= (SimConnect.MSFS_User_Aircraft["Cur_Lat"],SimConnect.MSFS_User_Aircraft["Cur_Log"])
    print(SimConnect.MSFS_User_Aircraft)
    
    #User_altitude = SimConnect.MSFS_User_Aircraft["altitude"]

    #for index ,flight in SimConnect.MSFS_AI_Arrival_Traffic.iterrows():
    #  sm.AIAircraft_GetPosition(0, flight["Obj_Id"])
    #  time.sleep(1)

    #  #Ai flight
    #  point2= (flight["Cur_Lat"], flight["Cur_Log"])
    #  Cur_Dis = geodesic(point1, point2).km
    #  Cur_altitude = flight["altitude"]
    #  if Cur_Dis > MAX_SPAWN_DIST:
    #    sm.AIRemoveObject(flight["Obj_Id"],Common.Global_req_id)
    #    SimConnect.MSFS_AI_Arrival_Traffic.loc[SimConnect.MSFS_AI_Arrival_Traffic["Obj_Id"] == flight["Obj_Id"], "Req_Id"] = Common.Global_req_id
    #    Common.Global_req_id += 1


class Departure:
  
  FR24_Departure_Traffic = pd.DataFrame(columns=['Estimate_time', 'Scheduled_time', "Call","des", "Type",'Ocio',"Src_ICAO","Dest_ICAO","Local_depart_time"])

  departure_string = ""
  Departure_Index = 0

  def Get_Departure(airport):
   
    # Set up the WebDriver (this assumes you have ChromeDriver installed)
    driver = webdriver.Chrome(options=Common.chrome_options)
    driver.set_window_size(945, 1012)
    url = "https://www.flightradar24.com/data/airports/" + airport +"/departures"
    driver.get(url)
    time.sleep(10)

    # Get current date and time 
    current_datetime = datetime.now()

    # Get the next day's date and time
    next_day_datetime = current_datetime + timedelta(days=1)

    flight_elements = driver.find_elements(By.XPATH, "//td")  # Example XPath
    
    prev_lin = ""
    index = 0
    Check_New_Day = False
    prev_AM_PM = ""
    for flight in flight_elements:
      flight_info = flight.text 
      if  prev_lin != flight_info:
        #print(flight_info)
        flight_info_list = flight_info.split("\n")
        #print(flight_info_list)
        if flight_info_list[0].split(" ")[0] == "Estimated" or flight_info_list[0].split(" ")[0] == "Delayed":
          if flight_info_list[2] in Departure.FR24_Departure_Traffic['Call'].values:
            continue
          last_element = len(Departure.FR24_Departure_Traffic)
          if last_element < MAX_DEPARTURE:
            try:
              last_element = len(Departure.FR24_Departure_Traffic)
              Estimate_time = (datetime.strptime(str(flight_info_list[0].split(" ")[2] +" "+ flight_info_list[0].split(" ")[3]), '%I:%M %p')).strftime('%H:%M')
              Scheduled_time  =  (datetime.strptime(str(flight_info_list[1]), '%I:%M %p')).strftime('%H:%M')
              Call =  flight_info_list[2]
              Des =  flight_info_list[3]
              Type =  flight_info_list[4]
              Ocio =  flight_info_list[-1]
              qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+airport+"""%'"""
              with Common.engine_fldatabase.connect() as conn:
                  src_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              qry_str = f"""SELECT "_rowid_",* FROM "main"."airport" WHERE "iata" LIKE '%"""+re.search(r'\((.*?)\)', Des).group(1).upper()+"""%'"""
              with Common.engine_fldatabase.connect() as conn:
                  des_air = pd.read_sql(sql=qry_str, con=conn.connection)
              
              Src_ICAO = src_air["icao"].iloc[-1]
              Dest_ICAO = des_air["icao"].iloc[-1]

              if flight_info_list[0].split(" ")[3] == "AM" and prev_AM_PM == "PM":
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
              Departure.FR24_Departure_Traffic.loc[last_element] = [Estimate_time, Scheduled_time, Call, Des, Type,Ocio,Src_ICAO,Dest_ICAO,Local_depart_time]
              prev_AM_PM = flight_info_list[0].split(" ")[3]
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
  
    if len(src_df) > 1:
      max_leg_dep = 0
      for index,dep in src_df.iterrows():
        dep_id = dep["approach_id"].iloc[-1]
        with Common.engine_fldatabase.connect() as conn:
          qry_str = '''SELECT "_rowid_", * FROM "main"."approach_leg" WHERE "approach_id" LIKE '%'''+str(dep_id)+'''%' '''
          Cur_dep = pd.read_sql(sql=qry_str, con=conn.connection)
          cur_len = len(Cur_dep)
          if cur_len > max_leg_dep:
            Max_dep_df = Cur_dep
            max_leg_dep = cur_len
            Dep_Name = dep["fix_ident"]
  
  
      Max_dep_df.drop(['is_missed', 'type' ,'arinc_descr_code','approach_fix_type','turn_direction','recommended_fix_type', 'rnp',\
                       'time','theta','recommended_fix_laty','is_true_course','speed_limit_type','recommended_fix_ident','recommended_fix_region','recommended_fix_lonx','is_flyover','course'], axis=1,inplace=True)
     
    
    #fill lat and log
    RW_num =  RW[:2]
    
    if len(RW) > 2:
      if RW[-1] == "C":
        RW_designa = "CENTER"
      if RW[-1] == "L":
        RW_designa = "LEFT"
      if RW[-1] == "R":
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
          altitude = 5000
        src_waypoint_Pos = Common.format_coordinates(float(way_df["laty"].iloc[-1]),float(way_df["lonx"].iloc[-1]),float(altitude))
        Departure.departure_string += """        <ATCWaypoint id=\"""" + dep_leg["fix_ident"] + """\">
              <ATCWaypointType>Intersection</ATCWaypointType>
              <WorldPosition>"""+src_waypoint_Pos+"""</WorldPosition>
              <SpeedMaxFP>240</SpeedMaxFP>
              <DepartureFP>"""+Dep_Name+"""</DepartureFP>
              <RunwayNumberFP>"""+RW_num+"""</RunwayNumberFP>\n"""
    
        if len(RW) > 2:
            Departure.departure_string +="""            <RunwayDesignatorFP>"""+RW_designa+"""</RunwayDesignatorFP>\n"""
        
        Departure.departure_string += """            <ICAO>
                  <ICAORegion>""" + dep_leg["fix_region"] + """</ICAORegion>
                  <ICAOIdent>""" + dep_leg["fix_ident"] + """</ICAOIdent>
                  <ICAOAirport>""" +airport + """</ICAOAirport>
              </ICAO>
          </ATCWaypoint>\n"""
        
  
    print(Max_dep_df)


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
      if row["Call"] in SimConnect.MSFS_AI_Departure_Traffic['Call'].values:
        continue
      last_element = len(SimConnect.MSFS_AI_Departure_Traffic)
      if last_element < MAX_DEPARTURE:
        Estimate_time = row["Estimate_time"]
        Call = row["Call"]
        Type = row["Type"]
        Src  = row["Src_ICAO"]
        Dest = row["Dest_ICAO"]
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
        SimConnect.MSFS_AI_Departure_Traffic.loc[last_element] = [Estimate_time, Call,Type,Src, Dest,Par_lat,Par_log,Cur_Lat,Cur_Log,altitude,Prv_Lat,Prv_Log,Stuck,Req_Id,Obj_Id]  
        try:
          Livery_name = Common.Get_flight_match(Call,Type)
          result = sm.AICreateParkedATCAircraft(Livery_name,Call,Src,Req_Id)
          print("Parked----" + Call + " " + Type + " " + str(Livery_name))
          Common.Global_req_id+=1
        except:
          print("Cannot create flight plan")
        
        time.sleep(1)
    
    print(SimConnect.MSFS_AI_Departure_Traffic)     

  def Assign_Flt_plan():
  
    if Departure.Departure_Index < MAX_DEPARTURE:
      try:
        Src = SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Src"]
        Dest =  SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Dest"]
        Call = SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Call"]
        Type = SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Type"]
        Obj_Id =  SimConnect.MSFS_AI_Departure_Traffic.loc[Departure.Departure_Index,"Obj_Id"]
        Req_Id = Common.Global_req_id
        flt_plan = Departure.Create_flight_plan_Dep(Src,Dest)
        print("Depart----" +Call + " " + Type)
        result = sm.AISetAircraftFlightPlan(Obj_Id, "E:/workspace/pyhton/aiTraffic/fln_plan_dep",Req_Id)
        Common.Global_req_id+=1
      except:
        print("Cannot create flight plan")


  def Check_Departed_aircraft():
    
    sm.AIAircraft_GetPosition(0, 0)
    time.sleep(1)
    point1= (SimConnect.MSFS_User_Aircraft["Cur_Lat"],SimConnect.MSFS_User_Aircraft["Cur_Log"])
    User_altitude = SimConnect.MSFS_User_Aircraft["altitude"]


    for index ,flight in SimConnect.MSFS_AI_Departure_Traffic.iterrows():
      sm.AIAircraft_GetPosition(0, flight["Obj_Id"])
      time.sleep(1)
      
      #Ai flight
      point2= (flight["Cur_Lat"], flight["Cur_Log"])
      Cur_Dis = geodesic(point1, point2).km
      Cur_altitude = flight["altitude"]
      if Cur_Dis > MAX_SPAWN_DIST:
        sm.AIRemoveObject(flight["Obj_Id"],Common.Global_req_id)
        SimConnect.MSFS_AI_Departure_Traffic.loc[SimConnect.MSFS_AI_Departure_Traffic["Obj_Id"] == flight["Obj_Id"], "Req_Id"] = Common.Global_req_id
        Common.Global_req_id += 1


Common.Run()



#For Testing
#Arrival.Get_Arrival("BOM")
#Departure.Get_Departure("BOM")

#Arrival.Get_STAR("VABB","27")
#Arrival.Create_flight_plan_arr("VOBL","VABB")