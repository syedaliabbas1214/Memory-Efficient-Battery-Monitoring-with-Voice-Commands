from datetime import datetime
import psutil
import uuid, time
import redis
import argparse

parser = argparse.ArgumentParser()        # default arguments are credentials of our redis account
parser.add_argument('--host', type=str, default="redis-19958.c246.us-east-1-4.ec2.cloud.redislabs.com")
parser.add_argument('--port', type=int, default=19958)
parser.add_argument('--user', type=str, default="default")
parser.add_argument('--password', type=str, default="ixQZhyT2TmuE12NAxb7MyQINpRiFYVYx")
parser.add_argument('--delete', type=int, default=0)  # debug
parser.add_argument('--verbose', type=int, default=0)  # debug

args = parser.parse_args()

REDIS_HOST = args.host
REDIS_PORT = args.port
REDIS_USER = args.user
REDIS_PASSWORD = args.password

redis_client = redis.Redis(host = REDIS_HOST, port = REDIS_PORT, username = REDIS_USER, password = REDIS_PASSWORD)

is_connected = redis_client.ping()
print('Redis Connected:', is_connected)

mac_address = hex(uuid.getnode())
mac_battery = f'{mac_address}:battery'
mac_power = f'{mac_address}:power'
mac_pluged_seconds = f'{mac_address}:pluged_seconds'

# bucket size duration for the plugged_seconds timeseries
bucket_duration_in_ms = 24 * 60 * 60 * 1000  # 24h

# delete previous timeseries, for debugging 
if args.delete == 1:
    redis_client.delete(mac_battery)
    redis_client.delete(mac_power)
    redis_client.delete(mac_pluged_seconds)




# Create a timeseries named 'integers'
# mac_battery = str(hex(uuid.getnode())) + ":battery"   # creating time series mac:battery
print("Name of mac battery time series: ", mac_battery)
try:
    redis_client.ts().create(mac_battery)
except redis.ResponseError:
    # Ignore error if the timeseries already exists
    pass


# mac_power = str(hex(uuid.getnode())) + ":power"   # creating time series mac:power
print("Name of mac power time series: ", mac_power)
try:
    redis_client.ts().create(mac_power)
except redis.ResponseError:
    # Ignore error if the timeseries already exists
    pass


# mac_pluged_seconds = str(hex(uuid.getnode())) + ":pluged_seconds"   # creating time series mac:pluged_seconds
print("Name of mac pluged_seconds time series: ", mac_pluged_seconds)
try:
    redis_client.ts().create(mac_pluged_seconds)
    redis_client.ts().createrule(mac_power, mac_pluged_seconds, aggregation_type='sum', bucket_size_msec=bucket_duration_in_ms)   # laying out rule to compute aggregation
except redis.ResponseError:
    # Ignore error if the timeseries already exists
    pass

battery_retention = int(5 * (2**20 / 1.6) * 1000)  # 3276800000 ms
# print(battery_retention)
power_retention = int(5 * (2**20 / 1.6) * 1000)
power_plugged_seconds_retention = int((2**20 / 1.6) * 24 * 60 * 60 * 1000)  # 5.6623104e13 ms

#create retention window
redis_client.ts().alter(mac_battery, retention_msec=battery_retention)
redis_client.ts().alter(mac_power, retention_msec=power_retention)
redis_client.ts().alter(mac_pluged_seconds, retention_msec=power_plugged_seconds_retention)



while True:
    timestamp_ms = int(time.time() * 1000) 
    report = psutil.sensors_battery()
    battery = report.percent
    power = int(report.power_plugged)
    redis_client.ts().add(mac_battery, timestamp_ms, battery)
    redis_client.ts().add(mac_power, timestamp_ms, power)
    time.sleep(1)



