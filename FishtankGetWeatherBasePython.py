'''
This workflow uses the ip address of the board to get the lat/lon, which is then used to get the
local weather condition.  This happends when the board first connects to Medium One.  A 
notification is generated based on the weather conditions.  Limit to 1 look-up hour unless the IP 
address changed.

Last Updated: Oct 2, 2016

Author: Medium One
'''
import Store
import M1Geolocation
import Weather
import json
import MQTT
import datetime
import DateConversion

# set the time between notification (unless IP changed) (default = 3600s = 1hr)
time_between_notifications = 3600

# This function returns the time different in seconds between two iso timestamps
def iso_time_delta(a,b):
    a_datetime = DateConversion.to_py_datetime(a)
    b_datetime = DateConversion.to_py_datetime(b)
    return (b_datetime - a_datetime).total_seconds()

# This function returns current time in iso format
def get_current_iso_time():
    dtnow = datetime.datetime.now()
    dtutcnow = datetime.datetime.utcnow()
    delta = dtnow - dtutcnow
    hh,mm = divmod((delta.days * 24*60*60 + delta.seconds + 30) // 60, 60)
    #log(hh)
    #log(mm)
    return "%s%+03d:%02d" % (dtnow.isoformat(), hh, mm)

# current wan ip address of the board
current_ip = IONode.get_input('in1')['event_data']['value']

# last saved ip address and geopoint of the board
last_ip = Store.get("ip_address")
gps_location = Store.get("gps_location_via_ip")

if last_ip == None:
    last_ip = ""
    
if gps_location == None:
    gps_location = ""
    
new_IP = False
# determine if a new ip to gps lookup is required
if current_ip != last_ip or gps_location == "":
    log("Setting ip address to Store: "+current_ip)
    Store.set_data("ip_address",current_ip,-1)
    geo_data = M1Geolocation.get_location_from_ip(current_ip)
    gps_location = str(geo_data['location']['latitude']) + " " + str(geo_data['location']['longitude'])
    Store.set_data("gps_location_via_ip",gps_location,-1)
    new_IP = True

# check if it has been over 1 hr since the last welcome alert
over_notification_limit = False
last_notification = Store.get("last_welcome_alert")
if last_notification is None:
    over_notification_limit = True
    Store.set_data("last_welcome_alert",get_current_iso_time(),-1)
else:
    log("last_notification: "+last_notification)
    last_notification = DateConversion.to_py_datetime(last_notification)
    now = DateConversion.to_py_datetime(get_current_iso_time())
    log("seconds since last notification: "+str(iso_time_delta(last_notification,now)))
    if iso_time_delta(last_notification,now) > time_between_notifications:
        Store.set_data("last_welcome_alert",get_current_iso_time(),-1)
        over_notification_limit = True
        log("over_notification_limit set to True")
        
# update weather only when new ip or > over_notification_limit
if new_IP or over_notification_limit:
    # get weather forcast based on geopoint
    current_weather = Weather.get_weather_by_coordinates(float(gps_location.split(' ')[0]), float(gps_location.split(' ')[1]))
    icon = current_weather['weather'][0]['icon']

    # map weather condition code
    weather_condition_map = {
    '01d':'clear skies',
    '01n':'night time', 
    '02d':'few clouds',
    '02n':'night time',
    '03d':'scattered clouds',
    '03n':'night time',
    '04d':'broken clouds',
    '04n':'night time',
    '09d':'shower rain',
    '09n':'night time',
    '10d':'rain',
    '10n':'night time',
    '11d':'thunderstorm',
    '11n':'night time',
    '13d':'snow',
    '13n':'night time',
    '50d':'mist',
    '50n':'night time'
    }
    current_weather['main']['condition'] = weather_condition_map.get(icon,"unknown")

    # prepare appropriate message based on weather condition
    if "01d" in icon or "02d" in icon:
        message = "It's a great day for fish in an aquarium!"
    elif "03d" in icon:
        message = "It's a nice day for a fish."
    elif "n" in icon:
        message = "It's getting dark. Turn on light?"
    else:
        message = "Fish are cold. Turn on heater."

    # prepare message for board display
    screen_msg = "Fish tank conditions: " + str(current_weather['main']['temp'] - 273.15) + "C " + str(current_weather['main']['humidity']) +"% Humidity " + current_weather['main']['condition']

    # send notification to board
    IONode.set_output('out3', {"message": screen_msg, "screen":True, "line":5})

    # send notification to user
    IONode.set_output('out1', {"message": message, "sms":True,"email":True,"push":True})

    # save weather condition
    IONode.set_output('out2', current_weather['main'])