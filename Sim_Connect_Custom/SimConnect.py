from ctypes import *
from ctypes.wintypes import *
import logging
import ctypes
import struct
import time
from .Enum import *
from .Constants import *
from .Attributes import *
import os
import threading
import pandas as pd
import math



_library_path = os.path.splitext(os.path.abspath(__file__))[0] + '.dll'

LOGGER = logging.getLogger(__name__)


def millis():
	return int(round(time.time() * 1000))

class AircraftData(ctypes.Structure):
    	_fields_  = [
        ("Altitude", ctypes.c_double),
        ("Latitude", ctypes.c_double),
        ("Longitude", ctypes.c_double),
        ("Airspeed", ctypes.c_double),
        ("Landing_light", ctypes.c_double),
        ("ON_Ground", ctypes.c_double),
        ("Heading", ctypes.c_double),
        ("Gear", ctypes.c_double),
    ]
		

class SimConnect:
	
	MSFS_AI_Arrival_Traffic =  pd.DataFrame(columns=['Estimate_time', "Call","Type","Src", "Des","Par_Lat","Par_Lon","Cur_Lat","Cur_Log","Altitude","Prv_Lat","Prv_Log","Stuck","Airspeed","Landing_light","ON_Ground","Landed","Heading","Gear","Req_Id","Obj_Id"])
	MSFS_AI_Departure_Traffic =  pd.DataFrame(columns=['Estimate_time', "Call","Type","Src", "Des","Par_Lat","Par_Lon","Cur_Lat","Cur_Log","Altitude","Prv_Lat","Prv_Log","Stuck","Req_Id","Obj_Id","Local_depart_time"])
	MSFS_User_Aircraft =  pd.DataFrame(columns=["Cur_Lat","Cur_Log","Altitude","Dis_Src", "Dis_Des","Req_Id","Obj_Id"])
	MSFS_Cruise_Traffic = pd.DataFrame(columns=["Call","Type","Src","Des","Cur_Lat","Cur_Log","Altitude","Heading","Speed","Flt_plan","Req_Id","Obj_Id"])
	MSFS_AI_Traffic = pd.DataFrame(columns=["Call","Cur_Lat","Cur_Log","Altitude","Heading","Speed","Req_Id","Obj_Id"])

	def IsHR(self, hr, value):
		_hr = ctypes.HRESULT(hr)
		return ctypes.c_ulong(_hr.value).value == value
	

	def handle_id_event(self, event):
		uEventID = event.uEventID
		if uEventID == self.dll.EventID.EVENT_SIM_START:
			LOGGER.info("SIM START")
			self.running = True
		if uEventID == self.dll.EventID.EVENT_SIM_STOP:
			LOGGER.info("SIM Stop")
			self.running = False
		# Unknow whay not reciving
		if uEventID == self.dll.EventID.EVENT_SIM_PAUSED:
			LOGGER.info("SIM Paused")
			self.paused = True
		if uEventID == self.dll.EventID.EVENT_SIM_UNPAUSED:
			LOGGER.info("SIM Unpaused")
			self.paused = False

	
	def handle_Remove_Exception(self,dwRequestID):
		pass
	
	def handle_addremove_event(self,pData):
		event_id = pData.uEventID
		#obj_type = SIMCONNECT_SIMOBJECT_TYPE(pData.eObjType).name
		Obj_Id = pData.dwData
		if event_id == 4:
			if len(self.MSFS_AI_Traffic) == 0:
				self.MSFS_AI_Traffic.loc[len(self.MSFS_AI_Traffic)] =["Call",0.0,0.0,0.0,0.0,0.0,999,Obj_Id]
			else:
				if not( Obj_Id in self.MSFS_AI_Traffic["Obj_Id"].values):
					self.MSFS_AI_Traffic.loc[len(self.MSFS_AI_Traffic)] =["Call",0.0,0.0,0.0,0.0,0.0,999,Obj_Id]
	
	
	def handle_addremove_simobject_event(self,pData):
	
		req_id = pData.dwRequestID
		obj_id = pData.dwObjectID
   
		if req_id in self.MSFS_AI_Arrival_Traffic["Req_Id"].values:
			if self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Req_Id"] == req_id, "Obj_Id"].values[0] == 0:
				self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Req_Id"] == req_id, "Obj_Id"] = obj_id
				#print(self.MSFS_AI_Arrival_Traffic.iloc[-1]["Call"] + "  Added")

		if req_id in self.MSFS_AI_Departure_Traffic["Req_Id"].values:
			if self.MSFS_AI_Departure_Traffic.loc[self.MSFS_AI_Departure_Traffic["Req_Id"] == req_id, "Obj_Id"].values[0] == 0:
				self.MSFS_AI_Departure_Traffic.loc[self.MSFS_AI_Departure_Traffic["Req_Id"] == req_id, "Obj_Id"] = obj_id
				#print(self.MSFS_AI_Departure_Traffic.iloc[-1]["Call"] + "  Added")


		if req_id in self.MSFS_Cruise_Traffic["Req_Id"].values:
			if self.MSFS_Cruise_Traffic.loc[self.MSFS_Cruise_Traffic["Req_Id"] == req_id, "Obj_Id"].values[0] == 0:
				self.MSFS_Cruise_Traffic.loc[self.MSFS_Cruise_Traffic["Req_Id"] == req_id, "Obj_Id"] = obj_id
				#print(self.MSFS_Cruise_Traffic.iloc[-1]["Call"] + "  Added")



	def handle_ai_aircraft(self,pObjData):
		req_id = pObjData.dwRequestID
		obj_id = pObjData.dwObjectID
        

		if obj_id in self.MSFS_AI_Arrival_Traffic["Obj_Id"].values:		
			addressof_dwData = ctypes.addressof(pObjData.dwData)
			pointer = ctypes.cast(addressof_dwData, ctypes.POINTER(ctypes.c_double))
			altitude = float(pointer[0])
			Latitude = float(pointer[1])
			longitude = float(pointer[2])
			Airspeed = float(pointer[3])
			Landing_light = float(pointer[4])
			ON_Ground = float(pointer[5])
			Heading = math.degrees(float(pointer[6]))
			Gear = float(pointer[7])

			self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Obj_Id"] == obj_id, "Cur_Lat"] = Latitude
			self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Obj_Id"] == obj_id, "Cur_Log"] = longitude
			self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Obj_Id"] == obj_id, "Altitude"] = altitude
			self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Obj_Id"] == obj_id, "Airspeed"] = Airspeed
			self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Obj_Id"] == obj_id, "Landing_light"] = Landing_light
			self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Obj_Id"] == obj_id, "ON_Ground"] = ON_Ground
			self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Obj_Id"] == obj_id, "Heading"] = Heading
			self.MSFS_AI_Arrival_Traffic.loc[self.MSFS_AI_Arrival_Traffic["Obj_Id"] == obj_id, "Gear"] = Gear
			


		if obj_id in self.MSFS_AI_Departure_Traffic["Obj_Id"].values:
			addressof_dwData = ctypes.addressof(pObjData.dwData)
			pointer = ctypes.cast(addressof_dwData, ctypes.POINTER(ctypes.c_double))
			altitude = float(pointer[0])
			Latitude = float(pointer[1])
			longitude = float(pointer[2])
			self.MSFS_AI_Departure_Traffic.loc[self.MSFS_AI_Departure_Traffic["Obj_Id"] == obj_id, "Cur_Lat"] = Latitude
			self.MSFS_AI_Departure_Traffic.loc[self.MSFS_AI_Departure_Traffic["Obj_Id"] == obj_id, "Cur_Log"] = longitude
			self.MSFS_AI_Departure_Traffic.loc[self.MSFS_AI_Departure_Traffic["Obj_Id"] == obj_id, "Altitude"] = altitude


		if obj_id in self.MSFS_Cruise_Traffic["Obj_Id"].values:
			addressof_dwData = ctypes.addressof(pObjData.dwData)
			pointer = ctypes.cast(addressof_dwData, ctypes.POINTER(ctypes.c_double))
			altitude = float(pointer[0])
			Latitude = float(pointer[1])
			longitude = float(pointer[2])
			self.MSFS_Cruise_Traffic.loc[self.MSFS_Cruise_Traffic["Obj_Id"] == obj_id, "Cur_Lat"] = Latitude
			self.MSFS_Cruise_Traffic.loc[self.MSFS_Cruise_Traffic["Obj_Id"] == obj_id, "Cur_Log"] = longitude
			self.MSFS_Cruise_Traffic.loc[self.MSFS_Cruise_Traffic["Obj_Id"] == obj_id, "Altitude"] = altitude

		if obj_id in self.MSFS_AI_Traffic["Obj_Id"].values:
			addressof_dwData = ctypes.addressof(pObjData.dwData)
			pointer = ctypes.cast(addressof_dwData, ctypes.POINTER(ctypes.c_double))
			altitude = float(pointer[0])
			Latitude = float(pointer[1])
			longitude = float(pointer[2])
			Airspeed = float(pointer[3])
			Landing_light = float(pointer[4])
			ON_Ground = float(pointer[5])
			Heading = math.degrees(float(pointer[6]))
			Gear = float(pointer[7])
			pointer_char = ctypes.cast(addressof_dwData, ctypes.POINTER(ctypes.c_char))
			Call_sign = (pointer_char[64:74].split(b'\x00')[0].decode('utf-8'))

			self.MSFS_AI_Traffic.loc[self.MSFS_AI_Traffic["Obj_Id"] == obj_id, "Call"] = Call_sign		
			self.MSFS_AI_Traffic.loc[self.MSFS_AI_Traffic["Obj_Id"] == obj_id, "Cur_Lat"] = Latitude
			self.MSFS_AI_Traffic.loc[self.MSFS_AI_Traffic["Obj_Id"] == obj_id, "Cur_Log"] = longitude
			self.MSFS_AI_Traffic.loc[self.MSFS_AI_Traffic["Obj_Id"] == obj_id, "Altitude"] = altitude
			self.MSFS_AI_Traffic.loc[self.MSFS_AI_Traffic["Obj_Id"] == obj_id, "Heading"] = Heading
			self.MSFS_AI_Traffic.loc[self.MSFS_AI_Traffic["Obj_Id"] == obj_id, "Speed"] = Airspeed
	  
		
		if obj_id == 1:
			addressof_dwData = ctypes.addressof(pObjData.dwData)
			pointer = ctypes.cast(addressof_dwData, ctypes.POINTER(ctypes.c_double))
			altitude = float(pointer[0])
			Latitude = float(pointer[1])
			longitude = float(pointer[2])
			self.MSFS_User_Aircraft.loc[1,"Cur_Lat"] = Latitude
			self.MSFS_User_Aircraft.loc[1,"Cur_Log"] = longitude
			self.MSFS_User_Aircraft.loc[1,"Altitude"] = altitude


	def handle_exception_event(self, exc):
		_exception = SIMCONNECT_EXCEPTION(exc.dwException).name
		_unsendid = exc.UNKNOWN_SENDID
		_sendid = exc.dwSendID
		_unindex = exc.UNKNOWN_INDEX
		_index = exc.dwIndex

		# request exceptions
		for _reqin in self.Requests:
			_request = self.Requests[_reqin]
			if _request.LastID == _unsendid:
				#LOGGER.warn("%s: in %s" % (_exception, _request.definitions[0]))
				return
			self.handle_Remove_Exception(_request.LastID)
		#LOGGER.warn(_exception)

	def handle_state_event(self, pData):
		print("I:", pData.dwInteger, "F:", pData.fFloat, "S:", pData.szString)

	# TODO: update callbackfunction to expand functions.
	def my_dispatch_proc(self, pData, cbData, pContext):
		
		dwID = pData.contents.dwID

		if dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_EVENT:
			evt = cast(pData, POINTER(SIMCONNECT_RECV_EVENT)).contents
			self.handle_id_event(evt)

		elif dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_SYSTEM_STATE:
			state = cast(pData, POINTER(SIMCONNECT_RECV_SYSTEM_STATE)).contents
			self.handle_state_event(state)

		elif dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_SIMOBJECT_DATA_BYTYPE:
			pObjData = cast(
				pData, POINTER(SIMCONNECT_RECV_SIMOBJECT_DATA_BYTYPE)
			).contents
			self.handle_simobject_event(pObjData)


		elif dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_SIMOBJECT_DATA:
			pObjData = cast(
				pData, POINTER(SIMCONNECT_RECV_SIMOBJECT_DATA)
			).contents
			self.handle_ai_aircraft(pObjData)

		
		elif dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_OPEN:
			LOGGER.info("SIM OPEN")
			self.ok = True

		elif dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_EXCEPTION:
			exc = cast(pData, POINTER(SIMCONNECT_RECV_EXCEPTION)).contents
			self.handle_exception_event(exc)
		
		elif dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_EVENT_OBJECT_ADDREMOVE:
			pObjData = cast(
				pData, POINTER(SIMCONNECT_RECV_EVENT_OBJECT_ADDREMOVE)
			).contents
			self.handle_addremove_event(pObjData)
			
		
		
		elif dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_ASSIGNED_OBJECT_ID:
			pObjData = cast(
				pData, POINTER(SIMCONNECT_RECV_ASSIGNED_OBJECT_ID)
			).contents
          
			objectId = pObjData.dwObjectID
			self.handle_addremove_simobject_event(pObjData)
			os.environ["SIMCONNECT_OBJECT_ID"] = str(objectId)
			

		elif (dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_AIRPORT_LIST) or (
			dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_WAYPOINT_LIST) or (
			dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_NDB_LIST) or (
			dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_VOR_LIST):
			pObjData = cast(
				pData, POINTER(SIMCONNECT_RECV_FACILITIES_LIST)
			).contents
			dwRequestID = pObjData.dwRequestID
			for _facilitie in self.Facilities:
				if dwRequestID == _facilitie.REQUEST_ID.value:
					_facilitie.parent.dump(pData)
					_facilitie.dump(pData)

		
		elif dwID == SIMCONNECT_RECV_ID.SIMCONNECT_RECV_ID_QUIT:
			self.quit = 1
		else:
			LOGGER.debug("Received:", SIMCONNECT_RECV_ID(dwID))
		return

	def __init__(self, auto_connect=True, library_path=_library_path):

		self.Requests = {}
		self.Facilities = []
		self.dll = SimConnectDll(library_path)
		self.hSimConnect = HANDLE()
		self.quit = 0
		self.ok = False
		self.running = False
		self.paused = False
		self.DEFINITION_POS = None
		self.DEFINITION_ATC_DATA = None
		self.DEFINITION_AIRSPEED = None
		self.my_dispatch_proc_rd = self.dll.DispatchProc(self.my_dispatch_proc)
		
		if auto_connect:
			self.connect()

	def connect(self):
		try:
			err = self.dll.Open(
				byref(self.hSimConnect), LPCSTR(b"AI_Injector"), None, 0, 0, 0
			)
			if self.IsHR(err, 0):
				LOGGER.debug("Connected to Flight Simulator!")
				#print("Connected to Flight Simulator!")
				# Request an event when the simulation starts

				# The user is in control of the aircraft
				self.dll.SubscribeToSystemEvent(
					self.hSimConnect, self.dll.EventID.EVENT_SIM_START, b"SimStart"
				)
				# The user is navigating the UI.
				self.dll.SubscribeToSystemEvent(
					self.hSimConnect, self.dll.EventID.EVENT_SIM_STOP, b"SimStop"
				)
				# Request a notification when the flight is paused
				self.dll.SubscribeToSystemEvent(
					self.hSimConnect, self.dll.EventID.EVENT_SIM_PAUSED, b"Paused"
				)
				# Request a notification when the flight is un-paused.
				self.dll.SubscribeToSystemEvent(
					self.hSimConnect, self.dll.EventID.EVENT_SIM_UNPAUSED, b"Unpaused"
				)

				self.dll.SubscribeToSystemEvent(
					self.hSimConnect, self.dll.EventID.EVENT_ADDED_AIRCRAFT, b"ObjectAdded"
				)
				
				self.dll.SubscribeToSystemEvent(
					self.hSimConnect, self.dll.EventID.EVENT_REMOVED_AIRCRAFT, b"ObjectRemoved"
				)
				

				self.timerThread = threading.Thread(target=self._run)
				self.timerThread.daemon = True
				self.timerThread.start()
				#while self.ok is False:
				#	pass
		except OSError:
			LOGGER.debug("Did not find Flight Simulator running.")
			raise ConnectionError("Did not find Flight Simulator running.")

	def _run(self):
		while self.quit == 0:
			try:
				self.dll.CallDispatch(self.hSimConnect, self.my_dispatch_proc_rd, None)
				time.sleep(1)
			except OSError as err:
				print("OS error: {0}".format(err))

	def exit(self):
		self.quit = 1
		self.timerThread.join()
		self.dll.Close(self.hSimConnect)


	def new_def_id(self):
		_name = "Definition" + str(len(list(self.dll.DATA_DEFINITION_ID)))
		names = [m.name for m in self.dll.DATA_DEFINITION_ID] + [_name]

		self.dll.DATA_DEFINITION_ID = Enum(self.dll.DATA_DEFINITION_ID.__name__, names)
		DEFINITION_ID = list(self.dll.DATA_DEFINITION_ID)[-1]
		return DEFINITION_ID
	
	def get_paused(self):
		hr = self.dll.RequestSystemState(
			self.hSimConnect,
			self.dll.EventID.EVENT_SIM_PAUSED,
			b"Sim"
		)

	
	def createSimulatedObject(self, name, lat, lon, rqst, hdg=0, gnd=1, alt=0, pitch=0, bank=0, speed=0):
		simInitPos = SIMCONNECT_DATA_INITPOSITION()
		simInitPos.Altitude = alt
		simInitPos.Latitude = lat
		simInitPos.Longitude = lon
		simInitPos.Pitch = pitch
		simInitPos.Bank = bank
		simInitPos.Heading = hdg
		simInitPos.OnGround = gnd
		simInitPos.Airspeed = speed
		self.dll.AICreateSimulatedObject(
		    self.hSimConnect,
		    name.encode(),
		    simInitPos,
		    rqst.value
		)


	def AICreateParkedATCAircraft(self, name, Tailnum, Airport,rqst):
		retval = self.dll.AICreateParkedATCAircraft(
		    self.hSimConnect,
		    name.encode(),
			Tailnum.encode(),
			Airport.encode(),
		    rqst
		)

		return retval
	


	def AISetAircraftFlightPlan(self, obj_Id, flight_pln_path,rqst):
		retval = self.dll.AISetAircraftFlightPlan(
		    self.hSimConnect,
		    obj_Id,
			flight_pln_path.encode(),
		    rqst
		)

		return retval
	
	
	def AICreateEnrouteATCAircraft(self, name, Tailnum, flightnum, flight_pln_path, flight_loc,touchNgo,rqst):
		retval = self.dll.AICreateEnrouteATCAircraft(
		    self.hSimConnect,
		    name.encode(),
			Tailnum.encode(),
			flightnum,
		    flight_pln_path.encode(),
			float(flight_loc),
			bool(touchNgo),
		    rqst
		)

		return retval


	def AICreateNonATCAircraft(self, name, Tailnum, alt, lat, lon,pitch,bank,hdg,gnd,speed,rqst):
		simInitPos = SIMCONNECT_DATA_INITPOSITION()
		simInitPos.Altitude = alt
		simInitPos.Latitude = lat
		simInitPos.Longitude = lon
		simInitPos.Pitch = pitch
		simInitPos.Bank = bank
		simInitPos.Heading = hdg
		simInitPos.OnGround = gnd
		simInitPos.Airspeed = speed
		retval = self.dll.AICreateNonATCAircraft(
			self.hSimConnect,
			name.encode(),
			Tailnum.encode(),
			simInitPos,
			rqst
		)
		return retval
 
	def AIRemoveObject(self, objid,rqst):
		retval = self.dll.AIRemoveObject(
		    self.hSimConnect,
			objid,
		    rqst
		)
		return retval
	
	def AIAircraft_GetPosition(self, req_id, object_id):
		
		if self.DEFINITION_POS is None:
			self.DEFINITION_POS = self.new_def_id()
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'Plane Altitude',b'feet',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'Plane Latitude',b'degrees',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'Plane Longitude',b'degrees',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			#self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'AIRSPEED INDICATED',b'knots',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'AIRSPEED TRUE',b'knots',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'LIGHT LANDING',b'bool',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'SIM ON GROUND',b'bool',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'HEADING INDICATOR',b'radians',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'GEAR HANDLE POSITION',b'bool',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_POS.value,b'ATC ID',b'',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_STRING8,0,SIMCONNECT_UNUSED)
				
		retval = self.dll.RequestDataOnSimObject(
		    self.hSimConnect,
			req_id,
			self.DEFINITION_POS.value,
			object_id,
			SIMCONNECT_PERIOD.SIMCONNECT_PERIOD_ONCE,
			0,
			0,
			0,
			0
		)
		return retval
	
	def AIAircraftAirspeed(self,object_id,airspeed):
		
		if self.DEFINITION_AIRSPEED is None:
			self.DEFINITION_AIRSPEED = self.new_def_id()
			#self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_AIRSPEED.value,b'AIRSPEED INDICATED',b'knots',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_AIRSPEED.value,b'AIRSPEED TRUE',b'knots',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_FLOAT64,0,SIMCONNECT_UNUSED)
		
		pyarr = list([airspeed])
		dataarray = (ctypes.c_double * len(pyarr))(*pyarr)

		pObjData = cast(
			dataarray, c_void_p
		)
				
		retval = self.dll.SetDataOnSimObject(
		    self.hSimConnect,
			self.DEFINITION_AIRSPEED.value,
			object_id,
			0,
			0,
			sizeof(ctypes.c_double) * len(pyarr),
			pObjData
		)
		return retval


	def Get_ATC_Data(self, req_id, object_id):
		
		if self.DEFINITION_ATC_DATA is None:
			self.DEFINITION_ATC_DATA = self.new_def_id()
			self.dll.AddToDataDefinition(self.hSimConnect,self.DEFINITION_ATC_DATA.value,b'ATC ID',b'',SIMCONNECT_DATATYPE.SIMCONNECT_DATATYPE_STRING8,0,SIMCONNECT_UNUSED)
				
		retval = self.dll.RequestDataOnSimObject(
		    self.hSimConnect,
			req_id,
			self.DEFINITION_ATC_DATA.value,
			object_id,
			SIMCONNECT_PERIOD.SIMCONNECT_PERIOD_ONCE,
			0,
			0,
			0,
			0
		)
		return retval
	