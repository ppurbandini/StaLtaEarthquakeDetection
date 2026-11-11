from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.geodetics.base import gps2dist_azimuth
import pandas as pd
import os
import math

#Download earthquake catalog
client = Client("USGS")

starttime = UTCDateTime("2024-01-01")
endtime = UTCDateTime("2024-03-31")

catalog = client.get_events(starttime = starttime,
                            endtime = endtime,
                            minlatitude = -11.379,
                            maxlatitude = -3.98,
                            minlongitude = 115.269,
                            maxlongitude = 128.188,
                            minmagnitude = 4.0)

print("Number of events:", len(catalog))

#Set up FDSN clients
client_gfz = Client("GFZ")
client_earthscope = Client("EARTHSCOPE")

#Station lists
stations = [('GE', 'MMRI'),
            ('GE', 'SOEI'),
            ('II', 'KAPI')]

#Get station coordinates
print("Getting station coordinates...")

station_coordinates = {}
for net, sta in stations:

    if net == "GE":
        station_client = client_gfz
    elif net == "II":
        station_client = client_earthscope
    else:
        continue

    try:
        inventory = station_client.get_stations(network=net, station=sta, level="station")
        station = inventory[0][0]
        station_coordinates[(net, sta)] = {"latitude": station.latitude, "longitude": station.longitude,
                                           "elevation_m": station.elevation}

    except Exception as e:
        None

#Download waveforms event by event
os.makedirs("data/waveforms", exist_ok=True)
st_bulk = []

for i, event in enumerate(catalog):

    event_id = f"EQ{i+1:03d}"
    print("Get earthquake origin...")
    origin_time = event.preferred_origin().time #get the earthquake origin time
    event_lat = event.preferred_origin().latitude
    event_lon = event.preferred_origin().longitude
    event_depth_km = event.preferred_origin().depth / 1000
    
    print("Get magnitude...")
    magnitude = None
    magnitude_obj = event.preferred_magnitude()
    
    if magnitude_obj is not None:
        magnitude = magnitude_obj.mag
        
    
    print("Get waveforms...")
    for net, sta in stations:
        if net == 'GE':
            client = client_gfz
        elif net == 'II':
            client = client_earthscope
        else:
            continue
        
        #calculate distance
        station_info = station_coordinates.get((net, sta))
        if station_info is not None:
            station_lat = station_info["latitude"]
            station_lon = station_info["longitude"]

            distance_m, azimuth, back_azimuth = gps2dist_azimuth(event_lat, event_lon, station_lat, station_lon)
            epicentral_distance_km = distance_m / 1000
            
            station_elevation_km = (station_info["elevation_m"] / 1000)
            vertical_difference_km = (event_depth_km + station_elevation_km)

            hypocentral_distance_km = math.sqrt(epicentral_distance_km**2 + vertical_difference_km**2)

        else:
            station_lat = None
            station_lon = None
            epicentral_distance_km = None
            hypocentral_distance_km = None
        
        waveform_start_req = origin_time - 60
        waveform_end_req = origin_time + 300
        
        #initialize variables
        available = False
        n_traces = 0
        sampling_rate = None
        waveform_start = None
        waveform_end = None
        
        #download the waveforms
        try:
            st = client.get_waveforms(network = net, 
                                      station = sta,
                                      location = '',
                                      channel = 'BHZ',
                                      starttime = waveform_start_req,
                                      endtime = waveform_end_req)
            if len(st) > 0:
                available = True
                n_traces = len(st)
                sampling_rate = st[0].stats.sampling_rate
                waveform_start = st[0].stats.starttime
                waveform_end = st[0].stats.endtime
                
                #saving .mseed files
                filename = (f"data/waveforms/{event_id}_{net}_{sta}_BHZ.mseed")
                st.write(filename, format="MSEED")
                print("Saved:", filename)
                
            else:
                available = False
                n_traces = 0
                sampling_rate = None
                waveform_start = None
                waveform_end = None
                
        except Exception as e:
            available = False
            n_traces = 0
            sampling_rate = None
            waveform_start = None
            waveform_end = None
        
        #store result        
        st_bulk.append({"event_id": event_id,
                        "origin_time": str(origin_time),
                        "latitude": event_lat,
                        "longitude": event_lon,
                        "depth(km)": event_depth_km,
                        "magnitude": magnitude,
                        "network": net,
                        "station": sta,
                        "station_lat": station_lat,
                        "station_lon": station_lon,
                        "epicentral_distance_km": epicentral_distance_km,
                        "hypocentral_distance_km": hypocentral_distance_km,
                        "channel": "BHZ",
                        "start_time": str(waveform_start_req),
                        "end_time": str(waveform_end_req),
                        "waveform_availability": available,
                        "num_of_traces": n_traces,
                        "sampling_rate": sampling_rate,
                        "waveform_start": str(waveform_start),
                        "waveform_end": str(waveform_end)})
        
df = pd.DataFrame(st_bulk)
print(df.head())

#saving csv file
os.makedirs("data", exist_ok=True)
filename = "data/waveform_availability.csv"
df.to_csv(filename, index=False)

#Summary
print("\n---Data Availability Summary---")
number_of_traces = df["num_of_traces"].sum()
number_of_events = df.loc[df["waveform_availability"], "event_id"].nunique()
print("Total number of traces: ", number_of_traces)
print("Total number of events: ", number_of_events)

print("\n--- Station Availability Summary ---")
station_summary = (df.groupby(["network", "station"]).agg(
                requested=("event_id", "count"), available=("waveform_availability", "sum")).reset_index())
print(station_summary)

successful = df[df["waveform_availability"] == True]

print("\n--- Final Download Summary ---")
print("Total catalog events:", len(catalog))
print("Events with available waveforms:",
      successful["event_id"].nunique())
print("Total waveform traces:", successful["num_of_traces"].sum())
print("Stations with available waveforms:",
      successful[["network", "station"]].drop_duplicates().shape[0])



