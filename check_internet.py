import paho.mqtt.client as mqtt
import time
from reconnect import *
while 1:
    if len(all_interfaces()) > 1:
        matching = [s for s in all_interfaces() if get_ip_address() in s]
        if matching == []:
            print ("not found")            
        else:
            print ("network is up")
            break
                       
    else:
        print ("network down")
    time.sleep(2)
time.sleep(2)

def on_connect(client, userdata, rc):
    print("Connected with result code "+str(rc))
    with open('/home/odroid/Desktop/7-AUG-pedistrianDetection/internet_status.txt','w') as m:
        m.write('connected')
    #print("Connection returned result: "+connack_string(rc))

    subs=client.subscribe("/camera/connect/nic")
    print"subscriber",subs
def on_message(client, userdata, msg):
    print str(msg.payload)
    
    if msg.retain == 0:
        pass
    else:
        client.publish(msg.topic, None, 1, True)
    
def on_subscribe(client, userdata, mid, granted_qos):
    print "topic subscribed"
    #create function for callback
def on_disconnect(client, userdata, rc):
    print "on disconnect"
    with open('/home/odroid/Desktop/7-AUG-pedistrianDetection/internet_status.txt','w') as m:
        m.write('disconnected')
    if rc != 0:
        print "Unexpected MQTT disconnection. Will auto-reconnect"

client = mqtt.Client(client_id="foo123", clean_session=False)
client.username_pw_set(username="nic", password="abcd1234")
connection = client.connect("videoupload.hopto.org",1234,10)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_subscribe = on_subscribe

client.loop_forever()







##def on_connect(client, userdata, rc):
##    print("Connected with result code "+str(rc))
##    #print("Connection returned result: "+connack_string(rc))
##
##    subs=client.subscribe("/update/MAC")
##    print"subscriber",subs
##
##def on_log(client, userdata, level, buf):
##    print("log: ",buf)
##
##def on_subscribe(client, userdata, mid, granted_qos):   #create function for callback
##    print("subscribed with qos",granted_qos, "\n")
##    print "userdata : " +str(userdata)
##    pass
##
##def on_message(client, userdata, msg):
##    print(msg.topic+" "+str(msg.payload))
##    print "new mac", msg.payload
##    print "retain" , msg.retain
##    print "userdata : " +str(userdata)
##    with open("mac2.json", "wb") as code:
##                mac = []
##                mac_len = len(resp['list'])
##                print "mac length",mac_len
##                i = 0
##                for i in range(mac_len):
##                    if (i < mac_len):
##                        mac_add = resp['list'][i]['Mac_Address']
##                        i +=1
##                        code.write(mac_add)
##    if msg.retain == 0:
##        pass
##    else:
##        print("Clearing topic "+msg.topic)
##        (rc, final_mid) = client.publish(msg.topic, None, 1, True)
##
##def on_log(client, userdata, level, buf):
##    print("log: ",buf)
##
##client = mqtt.Client()
##client.username_pw_set(username="nic", password="abcd1234")
##client.on_connect = on_connect
##client.on_message = on_message
##client.on_subscribe = on_subscribe  
##client.on_log=on_log
##
##connection = client.connect("videoupload.hopto.org",1234,60)
##print"connection",connection 
##client.loop_forever()
