#  Real-Time AI Injector for MSFS2020

## Description
This project reads real-time flight data from Flight Radar 24 and injects it into Microsoft Flight Simulator 2020 (MSFS2020).

## Features
- Real-time AI traffic injection based on Flight Radar 24 data
- Arrivals and departures based on STAR and SID
- Min separation of 5 NM during approach reducing go arounds 
- Quick roll off during landing by adjusting speed when airplane on runway
- Customizable parameters for traffic injection
- Inject Traffic based on location of user (Departure, Cruise, Destination)
- Injects Traffic only at user location to reduce CPU load
- ATC always active 
- Uses simbrief to get active runway based on headwind
- Model matching with FSLTL and FSTraffic 
- Remove traffic which is outside user visible distance to reduce CPU Load


## Prerequisites
- Python 3.x
- Required Python packages: pip3 install -r requirements.txt
- FSLT base package
- ADB-s api for tracking live flight at cruise https://rapidapi.com/adsbx/api/adsbx-flight-sim-traffic/pricing
- Make sure departure and destination airport has medium and large gate else Ai traffic will not be swapened if msfs is not able to detect the gates
- Prefiled sim brief plan

## Installation
- git clone https://github.com/NerdAtWork24X7/AI_Traffic_Msfs2020.git
- Create config.py

##Config
 - Create config_user.json file and add api keys from ADB-S account
   - {"key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx","host" : "adsbx-flight-sim-traffic.p.rapidapi.com", "simbrief_username" : "abc"}


## Optional Parameter you can tweak it or keep it as they are in config_msfs.json
    - USE_FSTRAFFIC_LIVERY = True
    - MAX_ARRIVAL_AI_FLIGHTS = 20
    - MAX_DEPARTURE_AI_FLIGHTS = 20
    - MAX_CRUISE_AI_FLIGHTS = 20
    - MAX_PARKED_AI_FLIGHTS = 40
    - CRUISE_ALTITUDE = 10000
    - SRC_GROUND_RANGE = 50
    - DES_GROUND_RANGE = 100
    - GROUND_INJECTION_TIME_ARR = 2
    - GROUND_INJECTION_TIME_DEP = 2
    - CRUISE_INJECTION_TIME = 5
    - SPWAN_DIST = 200
    - SPWAN_ALTITUDE = 20000
    - MIN_SEPARATION = 10 #KM



## Running Script :
  - File simbrief plan
  - Start MSFS 2020 and wait untill flight is loaded
  - python3 Real_Time_AiInjector.py


## Acknowledgements
Thanks to
 - LittleNavMap database
 - FSLT base package
 - FSTraffic liveries
 - SimConnectPython


## Note:
- Ensure you are at the departure airport before starting the script with flight generated in simbrief
- Use data from Flight Radar 24 responsibly to avoid connection issues.
- This project is for educational purposes.

## Contributions
Contributions are welcome. Feel free to open issues or submit pull requests.

I am just learning OPPS programming in python so created this fun project.
