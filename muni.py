import requests
from pprint import pprint
import json
import calendar
from datetime import datetime, timedelta
from dateutil import parser
import time
from gpiozero import LED, RGBLED
import threading
import itertools



token_2 =  '''ENTER TOKEN'''


def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

def get_stop_direction_info(stopCode):
	url = "http://api.511.org/transit/StopMonitoring"
	querystring = {"api_key":token_2,"agency":"SF","stopCode":"{}".format(stopCode)}
	headers = {
	    'cache-control': "no-cache",
	    'Postman-Token': "8faab107-d18d-4217-9d35-bb4962d3e698"
	    }

	response = requests.request("GET", url, headers=headers, params=querystring)
	print response.text
	try: 
		json_data = json.loads(response.text)
	except ValueError as e:
		'''bug in nextmuni api response sends invalid character in position 0'''
		json_data = json.loads(response.text[1:])
	times = [ datetime.now() - utc_to_local(parser.parse(x['MonitoredVehicleJourney']['MonitoredCall']['AimedArrivalTime'])) for x in json_data['ServiceDelivery']['StopMonitoringDelivery']['MonitoredStopVisit']]
	parsed_times = [divmod(c.days * 86400 + c.seconds, 60)[0] for c in times]
	return parsed_times

class Stop:
	''' Create a object to store a stop with relation to its rgb pin mappings'''
	def __init__(self, name, arrival_time, red, green, blue):
		self.name = name
		self.arrival_time = arrival_time
		self.light = RGBLED(red, green, blue)
		self.colors = {
			'red': (1,0,0),
			'blue': (0,0,1),
			'green': (0,1,0),
			'yellow': (1,1,0),
		}
	def pulse(self, color):  
		self.light.pulse(
			fade_in_time=.7, fade_out_time=.3, on_color=color, off_color=(0,0,0), background=True)
		return

	def color_decider(self):
		''' Set light to be color/pulse depending on how long until the muni is coming'''
		self.light.on();
		if self.arrival_time in (0,1,2):
			self.pulse(self.colors['red'])	
		elif self.arrival_time in (3,4):
			self.pulse(self.colors['green'])		
		elif self.arrival_time in (5,6,7,8):
			self.light.color = self.colors['green']
		elif self.arrival_time in (9,10,11,12,13,14,15):
			self.light.color = self.colors['yellow']
		elif self.arrival_time > 15:
			self.light.color = self.colors['blue']
		else:
			raise Exception('Unexpected else in color decider on arrival_time value: {}'.format(self.arriva_time))
		return
	def cycle_colors(self):
		'''
		 	Cycling colors indicates to users that the lights are updating 
		'''
		self.light.on();
		self.light.color =self.colors['red']
		time.sleep(.5)
		self.light.color =self.colors['green']
		time.sleep(.5)
		self.light.color =self.colors['blue']
		time.sleep(.5)
		self.light.color =self.colors['yellow']
		time.sleep(.5)
		self.light.off()

def StopFactory():

	''' Create the stop/pin mappings here so we only do it once before main program loop'''
	stops = []
	NinboundPayload = ['NINB',0, 2, 3, 4]
	NoutboundPayload= ['NOUT',0, 9, 10, 11]
	for t in [NinboundPayload, NoutboundPayload]:
		S = Stop(t[0],t[1], t[2], t[3] ,t[4])
		stops.append(S)
	return stops

def StopWorker(S, t):
	''' Run the update/light action in separate thread ''' 
	S.arrival_time = t
	S.cycle_colors()
	S.color_decider()

def main():
	stops = StopFactory()
	while True:

		results = []
		stops_mapping = {
			'N': [
				(15201, 'inbound'), 
				(15202, 'outbound')
			]
		}
		for s, directions in stops_mapping.items():
			times = [ (s, d[1], get_stop_direction_info(d[0])) for d in directions ]
			results.append(times)
		print 'Results:'
		print results

		N_Stops = results[0]

		if len (N_Stops[0][2]):
			inb = N_Stops[0][2][0] *-1
		else:
			inb=100
		if len (N_Stops[1][2]):
			out = N_Stops[1][2][0] *-1
		else:
			out=100
		inbound_and_outbound_times = [inb, out]


		threads = []
		for StopObject, StopTime in zip(stops, inbound_and_outbound_times):
			print 'Updateing class and running decider...'
			print StopObject.name, StopTime
			t = threading.Thread(target=StopWorker, args=(StopObject, StopTime))
			threads.append(t)
			t.start()
		time.sleep(120)







if __name__ == "__main__":
	main()
