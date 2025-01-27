#  Real-Time AI Injector for MSFS2020

## Description
This project reads real-time flight data from Flight Radar 24 and injects it into Microsoft Flight Simulator 2020 (MSFS2020).

## Features
- Real-time AI traffic injection based on Flight Radar 24 data
- Customizable parameters for traffic injection
- Integration with AIFlow and AIGround for managing AI landings and departures
- Inject Traffic based on location of user (Departure, Cruise, Destination)

## Prerequisites
- Python 3.x
- Required Python packages: pip3 install -r requirements.txt
- FSLT base package
- ADB-s api for tracking live flight at cruise https://rapidapi.com/adsbx/api/adsbx-flight-sim-traffic/pricing
- Make sure departure and destination airport has medium and large gate else Ai traffic will not be swapened if msfs is not able to detect the gates

## Installation
- git clone https://github.com/NerdAtWork24X7/AI_Traffic_Msfs2020.git
- Link for modified little_navmap_msfs.sqlite -- https://drive.google.com/file/d/1LRD1JWVqBQ1_btgYX5jagCKUEGadeKts/view?usp=sharing
- Create config.py

##Config
 - Create config.py file and add api keys from ADB-S account
   - config = {"key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx","host" : "adsbx-flight-sim-traffic.p.rapidapi.com"}


## Modify this Parameters to inject traffic at airport
    # Mandatory parameter before start
      - SRC_AIRPORT_IACO = "VABB"
      - DES_AIRPORT_IACO = "EDDF"
      - SRC_ACTIVE_RUNWAY = "27"
      - S_ACTIVE_RUNWAY = "25R"

    # Optional Parameter you can tweak it or keep it as they are
      - MAX_ARRIVAL = 20
      - MAX_DEPARTURE = 20
      - MAX_CRUISE_AI_FLIGHTS = 20
      - CRUISE_ALTITUDE = 10000
      - SRC_GROUND_RANGE = 50
      - DES_GROUND_RANGE = 100
      - GROUND_INJECTION_TIME = 2
      - CRUISE_INJECTION_TIME = 5
      - SPWAN_DIST = 200
      - SPWAN_ALTITUDE = 10000



## Running Script :
  python3 Real_Time_AiInjector.py


## Acknowledgements
Thanks to
 - LittleNavMap database
 - FSLT base package
 - SimConnectPython


## Note:
- Ensure you are at the departure airport before starting the script.
- Use the script with AIFlow and AIGround to manage AI landings and departures from specific runways.
- Use data from Flight Radar 24 responsibly to avoid connection issues.
- This project is for educational purposes.

## Contributions
Contributions are welcome. Feel free to open issues or submit pull requests.

I am just learning OPPS programming in python so created this fun project.
