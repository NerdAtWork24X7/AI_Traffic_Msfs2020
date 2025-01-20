# AI_Traffic_Msfs2020
Real time Ai traffic from Flight Radar 24

Read Flights from Flight Radar 24 and injects it in MSFS2020


Modify this Parameters to inject traffic at airport
1) SRC_AIRPORT_IATA = "BOM"
2) SRC_AIRPORT_IACO = "VABB"
3) ACTIVE_RUNWAY = "27"
4) MAX_ARRIVAL = 40
5) MAX_DEPARTURE = 40
6) INJECTION_TIME = 2 //Default 2 mins


Script inject Traffic every 3 mins but this can modified . Ideal is 1 min. < 1 min can create Traffic congestion


Link for little_navmap_msfs.sqlite -- https://drive.google.com/file/d/1hyI_WuTPm7Hwv2sD9qQ14Ij9zBXahC0L/view?usp=sharing

Running Script :
  python3 Real_Time_AiInjector.py


Any contribution are welcome.

Thanks to
 - LittleNavMap database
 - FSLT base package
 - SimConnect


Note:
  1) Make sure you are at destination airport before you start.
  2) Use it with AIFlow and AIGround to Force Landing and Departures from specific RW
  3) Use data from Flight Radar 24 . so donot request too much data else connection to Flight Radar 24 will be refused.
  4) Not liable for any license issues Use at your own risk

I am just learning OPPS programming in python so created this fun project.
