from obspy.clients.fdsn import Client
from obspy import UTCDateTime

#Get the stations

client = Client("EARTHSCOPE")

starttime = UTCDateTime("2024-01-01")
endtime = UTCDateTime("2024-03-31")

inventory = client.get_stations(
    minlatitude=-11.379,
    maxlatitude=-3.98,
    minlongitude=115.269,
    maxlongitude=128.188,
    starttime=starttime,
    endtime=endtime,
    level="station"
)

print(inventory)

# #Check channels
# stations = [("GE", "MMRI"),
#             ("GE", "SOEI"),
#             ("II", "KAPI")]

# for net, sta in stations:
#     print("=" * 60)
#     print(f"{net}.{sta}")

#     inventory = client_earthscope.get_stations(network=net, station=sta, level="channel")
#     print(inventory)

