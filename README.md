# AI_Traffic_Msfs2020
Real time Ai traffic from Flight Radar 24

Read Flights from Flight Radar 24 


Modify this Parameters to inject traffic at airport
SRC_AIRPORT_IATA = "BOM"
SRC_AIRPORT_IACO = "VABB"
ACTIVE_RUNWAY = "27"
MAX_ARRIVAL = 40
MAX_DEPARTURE = 40

Link for little_navmap_msfs.sqlite -- https://drive.google.com/file/d/1hyI_WuTPm7Hwv2sD9qQ14Ij9zBXahC0L/view?usp=sharing

Start :

  python3 Real_Time_AiInjector.py


Any contribution are welcome.

Thanks to
 - LittleNavMap database
 - FSLT base package


Note:
  MAke sure Sim you are at destination airport before you start.
  Use it with AIFlow and AIGround to Force Landing and Departures from specific RW
  Use data from Flight Radar 24 . so donot request too much data else connection to Flight Radar 24 will be refused.
  Not liable for any license issues Use at your own risk

I am just learning OPPS programming in python so created this fun project.