# import the necessary packages
from __future__ import print_function
from imutils.object_detection import non_max_suppression
from imutils import paths
import numpy as np
import argparse
import imutils
import cv2
import time
import threading
import Queue
import multiprocessing
from multiprocessing import Manager
import requests
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2
from urllib2 import Request, urlopen, URLError
import Queue
import urllib
import traceback
import os
import psutil
import subprocess, signal, sys
from socket import timeout
import errno
import paho.mqtt.client as mqtt
import atexit
import logging
import dlib

# Change DEVICE ID HERE for cv2.videoCapture , you can add 1 for webcam, 2 for anyother source and for video it's path.
DEVICE_ID = '/home/irum/Desktop/read_paths/VID_20180801_130116.mp4'
# Threshold for motion 
threshold = 1

# initialize the HOG descriptor/person detector
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
# initiallize dlib detector
detector = dlib.get_frontal_face_detector()

#path to file where all paths are saved
read_path = '/home/irum/Desktop/7-AUG-pedistrianDetectionNEWWWWW/read_paths.txt'

# ======================== READ PATHS FROM FILE  ===============================
def get_paths(read_path):
    with open(read_path) as f:
        all_paths = []
        for x in f.readlines():
            all_paths.append(x.strip('\n'))
    
    return all_paths

all_paths = get_paths(read_path)

userpass_path = all_paths[0] # path to file where user id and password is located
output_file_path = all_paths[1] # path to write logs
save_body_path = all_paths[2] # path to the folder to save detected bodies
save_faces_path = all_paths[3] # path to the folder to save detected faces
        
#======================= GET USERNAME PASSWORD ================================
def get_username_pwd():
    with open(userpass_path) as f:
        usrpas = []
        for x in f.readlines():
            usrpas.append(x.strip('\n'))
    return usrpas
#================================================================================
last_upload = 'none'
last_server_resp = 'none'
time_lastResponse = 'none'

t=time.time()

webcam , ret, frame , image , orig , rects , weights , body_big = None , None , None , None , None , None , None , None
cur_date , cur_time , new_pin , filename1 , filename2 , sampleFile = None , None , None , None , None , None
check , head ,tail = None , None , None
thread_list = []
thread_count = 0
offline_thread_list = []
offline_thread_count = 0
rectangleColor = (0,165,255)
frame_hist = 0
frameCounter = 0
tracker_count = 0
curr_rect = 0
first = 0
status = None
prev_frame, frame2gray , result_frame, frame1gray = None , None , None , None
grab = 0

# Any big enough random values just to make the condition false
t_x = 10001
t_y = 10001
t_w = 10031
t_h = 10031
t_x_bar = 100021
t_y_bar = 100011

# Setup the termination criteria, either 10 iteration or move by atleast 1 pt
term_crit = ( cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 1 )

#Queues to store data
manager=Manager()
queue_BODIES = manager.Queue()
queue_Check = manager.Queue()
queue_LOG_LastUpload = manager.Queue()
queue_LOG_ServerResp = manager.Queue()
queue_OFF_line = manager.Queue()

# Capture Camera Stream
try:
    #webcam = cv2.VideoCapture(DEVICE_ID)
    webcam = cv2.VideoCapture('/home/irum/Desktop/read_paths/VID_20180801_130116.mp4')

except Exception as e:
    #print ('Problem in Video Capture',e)
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
    logging.debug('Problem in Video Capture')
    logging.info(traceback.format_exc())
           
# Set Camera Resolution

# webcam.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 1280)
# webcam.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 720)

# Get Camera Resolution
print('CURRENT_WIDTH: ',webcam.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
print ('CURRENT_HEIGHT: ',webcam.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))

# Grab  one frame for motion analysis
try:
    if webcam.isOpened() and grab == 0:
        ret1 , prev_frame = webcam.read()
        prev_frame = imutils.resize(prev_frame, width=min(300, prev_frame.shape[1]))
        frame1gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY )
        grab = 1
except:
    logging.basicConfig(filename='errorLogs.txt',level=logging.DEBUG)
    logging.info('could not grabe frame for motion detection' )

# Thread calling Upload function to upload data on sever
class myThread (threading.Thread):
    
   def __init__(self, name, filename2,sampleFile,curr_time,curr_day,username,password,user_id):
       
      threading.Thread.__init__(self)

      self.name = name
      self.filename2 = filename2
      self.sampleFile = sampleFile
      self.curr_time = curr_time
      self.curr_day = curr_day
      self.username = username
      self.password = password
      self.user_id = user_id
      
   def run(self):
       try:
           upload_via_thread(self.filename2,self.sampleFile,self.curr_time,self.curr_day,self.username,self.password,self.user_id)
       except Exception as e:
           #print ('Could not start thread', e)
           logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
           logging.debug('def run() thread')
           logging.info(traceback.format_exc())


# Funtion to upload data on server
def upload_via_thread(filename2,sampleFile,curr_time,curr_day,username,password,user_id):

    global output_file_path
    global last_upload 
    global last_server_resp
    global time_lastResponse
    attempt = 0
    flag = 0

    register_openers()

    try:
        datagen, headers = multipart_encode({"sampleFile": open(sampleFile), "name": filename2, "userID": user_id,'date': curr_day,'time': curr_time, 'username': username,'password': password})
    except Exception as e:
        #print ('Exception in Headers', e)
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
        logging.debug('datagen,headers')
        logging.info(traceback.format_exc())
        
    try:
        request = urllib2.Request("http://videoupload.hopto.org:5001/api/Synclog", datagen, headers)
    except Exception as e:
        #print ('Request Failed', e)
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
        logging.debug('urllib2.Request()')
        logging.info(traceback.format_exc())
        
    try:
        response = urllib2.urlopen(request, timeout = 20)
        html=response.read()
        print('response',html)

        # To Remove File On Successful Upload
        if html == 'success':
            # Delete file
            command = 'rm'+' '+ sampleFile
            os.system(command)
        else:
            pass

        queue_LOG_LastUpload.put(filename2)
        queue_LOG_ServerResp.put(html)                     

    except timeout , e:
        print ('Timeout Exception:',e)

        flag = 1

        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
        logging.debug('timeout')
        logging.info(traceback.format_exc())

    except URLError , e:
        if hasattr(e, 'reason'):
            print ('URL Error Exception: ', str(e.reason))

            flag = 1

            logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
            logging.debug('URLError')
            logging.info(traceback.format_exc())

        elif hasattr(e, 'code'):
            print ('URLError code Exception: ',str(e.code))

            flag = 1
   
            logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
            logging.debug('URLError')
            logging.info(traceback.format_exc())

    except Exception:
        print ('generic exception: ' + traceback.format_exc())

        flag = 1

        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
        logging.debug('generic exception')
        logging.info(traceback.format_exc())
  
    # If flaf is 1 it means there was an unsuccessful upload due to exception.
    # If there was an unsuccessful upload try to reupload it 3 times.
    # If after 3 attempts upload is still unsucessful add the upload to offline queue and upload later when system is sitting idle

    while (flag == 1):
        if (attempt < 3):
            try:
                response = urllib2.urlopen(request, timeout = 20)
                html=response.read()
                print('response',html)

                if html == 'success':
                    # Delete file after successful upload
                    command = 'rm'+' '+ sampleFile
                    os.system(command)
                else:
                    pass

            except URLError , e:
                print ('URL Error Exception: ', str(e.reason))

                logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
                logging.debug('URLError reuploading')
                logging.info(traceback.format_exc())
                
                if hasattr(e, 'reason'):
                    print ('Reason: ', str(e.reason))

                    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
                    logging.debug('URLError reuploading')
                    logging.info(traceback.format_exc())

                    # If exceptipn occurs during re uploading mark flag to 1 but add 1 to attempt
                    flag = 1
                    attempt += 1

                elif hasattr(e, 'code'):
                    print ('Error code: ', str(e.code))

                    # If exceptipn occurs during re uploading mark flag to 1 but add 1 to attempt
                    flag = 1
                    attempt += 1

            except timeout , e:
                print ('socket timed out - URL %s', str(e))

                logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
                logging.debug('timeout reupload')
                logging.info(traceback.format_exc())

            except Exception:

                    print ('generic exception: ' + traceback.format_exc())

                    # If exceptipn occurs during re uploading mark flag to 1 but add 1 to attempt
                    flag = 1
                    attempt += 1

                    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
                    logging.debug('generic exception reupload')
                    logging.info(traceback.format_exc())
            else:
                # If reuploading is successful mark flag as 0
                print ('Reuploading uccessful')
                flag = 0
                break
        else:
            # after 3 attempts put all the unsuccessful upload in OFF_line queue and upload latter
            queue_OFF_line.put(sampleFile)
            flag = 0
            break
    return

def upload_internet():

    global thread_list 
    global thread_count
    global output_file_path

    #GETUSERNAME PASSWORD
    usrpas = get_username_pwd()
    username = usrpas[0]
    password = usrpas[1]
    user_id = usrpas[2]

    # Check queue , if it is empty no threads needed
    if queue_BODIES.empty():
        thread_count = 0  
    # If queue is not empty check queue size      
    else:
        # if queue size is greater than 5 , start 5 threads to upload 5 images simultaneously on server. 
        if (queue_BODIES.qsize() > 5):
            # Start only 5 threads
            while (thread_count < 5):
                try:
                    sampleFile = queue_BODIES.get() 
                    # append 5 uploads in thread_list
                    thread_list.append(sampleFile)
                    thread_count += 1
                except:
                    break
        else:
            # If queue size is less than 5, start threads equal to queue size to upload images simultaneously on server
            limit = queue_BODIES.qsize()
            while (thread_count < limit):
                try:
                    sampleFile = queue_BODIES.get()
                    thread_list.append(sampleFile)
                    thread_count += 1
                except:
                    break
                
##        print ('FINAL LENGTH of thread list: ',len(thread_list))

        # For every image in thread_list initiate a new thread
        if len(thread_list) > 0: 
            for img in thread_list:
                sampleFile = img
                head , tail = os.path.split(sampleFile)
                filename2 = tail
                name = filename2.split('-')

                # Date TIME
                curr_day = name[1]+'-'+name[2]+'-'+name[3]
                curr_time = name[4].split('.')
                curr_time = curr_time[0]
             
                name = filename2
                # Call myThread for every upload
                try:
                    upload_thread = myThread(name,filename2,sampleFile,curr_time,curr_day,username,password,user_id)
                    upload_thread.start()
                except:
                    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
                    logging.debug('upload_thread')
                    logging.info(traceback.format_exc())
                
        thread_count = 0
        thread_list = []
       
    return
################################

# Function to upload the images from OFF_line queue. This function is similar to upload_internet()
def upload_offline():

    global offline_thread_list 
    global offline_thread_count
    global offline_output_file_path

    #GETUSERNAME PASSWORD
    usrpas = get_username_pwd()
    username = usrpas[0]
    password = usrpas[1]
    user_id = usrpas[2]

    if queue_OFF_line.empty():
        offline_thread_count = 0    
    else:
        if (queue_OFF_line.qsize() > 5):
            while (offline_thread_count < 5):
                try:
                    sampleFile = queue_OFF_line.get() 
                    offline_thread_list.append(sampleFile)
                    offline_thread_count += 1        
                except:
                    # handel exception when queue gets empty before reaching terminating condition for while loop
                    break
        else:
            limit = queue_OFF_line.qsize()
            while (offline_thread_count < limit):
                try:
                    sampleFile = queue_OFF_line.get()
                    offline_thread_list.append(sampleFile)
                    offline_thread_count += 1
                except:
                    break

        # For every image in list initiate a new thread
        if len(offline_thread_list) > 0: 
            for img in offline_thread_list:
                sampleFile = img
                head , tail = os.path.split(sampleFile)
                filename2 = tail
                name = filename2.split('-')

                # Date TIME
                curr_day = name[1]+'-'+name[2]+'-'+name[3]
                curr_time = name[4].split('.')
                curr_time = curr_time[0]

                name = filename2

                upload_thread = myThread(name,filename2,sampleFile,curr_time,curr_day,username,password,user_id)
                upload_thread.start()
                
        offline_thread_count = 0
        offline_thread_list = []      
    return

################################
flag_set=True

# Function to decide when to start uploading and what function should be called
# Before Starting uploding check internet status 
# if connected , Start upload otherwise wait for connection
#  before uploading images first check the BODIES queue, if its empty check OFF_line queue and upload images from there
# if BODIES queue is not empty upload images from this queue
def start_upload ():
    global flag_set
    global output_file_path
    global status

    while True:
        if queue_BODIES.empty():
            if queue_OFF_line.empty():
                pass
            else: 
                # First read internet status
                with open('/home/odroid/Desktop/7-AUG-pedistrianDetection/internet_status.txt') as f:
                    status = f.readline()
                f.close()

                if status == 'connected':       
                    try:
                        #print ('Calling upload_offline ')
                        upload_offline()
                    except:

                        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
                        logging.debug('could not call upload_offline')
                        logging.info(traceback.format_exc())
                else:
                    print('internet disconnected')
                    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
                    logging.debug('internet disconnected')            
        else:
            '''try:
                if(flag_set==True):
                    #subprocess.call('/home/odroid/Desktop/FinalPython/timeset.sh')
                    flag_set=False
            except:
                logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
                logging.debug('timeset.sh')
                logging.info(traceback.format_exc())'''

            try:
                upload_internet()
            except:
                logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='errorLogs.txt', level=logging.DEBUG)
                logging.debug('Upload_internet')
                logging.info(traceback.format_exc())
 
# fuction to check motion       
def somethingHasMoved(result_frame1):
    global threshold
    global result_frame

    result_frame = result_frame1

    nb=0 #Will hold the number of black pixels
    shape = result_frame.shape
    height = shape[0]
    width = shape [1]
    # print('shape',shape)
    # print('width',width)
    # print('height', height)
    nb_pixels = (height*width)

    for x in range(height): #Iterate the hole image
        for y in range(width):
            if result_frame[x,y] == 0.0: #If the pixel is black keep it
                nb += 1
    #print ("black pixels: ", nb)
    #print ("total pixels: ", nb_pixels)
    avg = (nb*100.0)/nb_pixels #Calculate the average of black pixel in the image
    if avg > threshold:#If over the ceiling trigger the alert/ try to find human
        return True
    else:
        return False


# function to perform body detection, if system detects any motion it will try to find humans in the frame.
# if there are humans capture the bodies , save and upload them on server
# Keep tracking the detected humans to avoid repetitive detectiond and uploads.

def body_detection():

    global frame_hist
    global first
    global tracker_count
    global t_x
    global t_y
    global t_w
    global t_h 
    global t_x_bar 
    global t_y_bar
    global output_file_path
    global finalLOG_file_path
    global last_server_resp
    global last_upload
    global save_body_path
    global t
    global prev_frame
    global frame2gray
    global frame1gray
    global result_frame


    while True: 

        # read each frame
        ret, frame = webcam.read()
        if ret is False:
            print('NO FRAME COMING, Return value is ',ret)


        # Un comment the below part iff you want to log system status every minute 

        # ######### LOG THIS INFO IN FINAL LOG VERY MINUTE #################
        # if time.time()-t > 60:

        #     with open(finalLOG_file_path ,"a") as output:
        #         output.write("_________ WRITING LOG AT "+time.strftime("%H:%M:%S")+" DATE "+time.strftime("%Y-%m-%d")+"_________ \n\n"+"CAMERA DEVICE ID: cv2.VideoCapture(1)\n")
        #         #CHECK CAMERA
        #         if webcam.isOpened():
        #             output.write("CAMERA FEED STATUS AT "+time.strftime("%H:%M:%S")+"  AVAILABLE\n")
        #         else:
        #             output.write("CAMERA FEED STATUS AT " +time.strftime("%H:%M:%S")+ "  NOT AVAILABLE \n")

        #         #CHECK FRAME CAPTURE
        #         if ret==True:
        #             output.write("CURRENT FRAME STATUS AT " +time.strftime("%H:%M:%S")+" YES\n")       
        #         else:
        #             output.write("CURRENT FRAME STATUS AT "+time.strftime("%H:%M:%S")+" NO\n")
        #         # WRITE LAST UPLOAD AND SERVER RESPONSE TO FILE
        #         try:
        #             if not queue_LOG_LastUpload.empty():
        #                 last_upload = queue_LOG_LastUpload.get()
        #             if not queue_LOG_ServerResp.empty():
        #                 last_server_resp = queue_LOG_ServerResp.get()
        #         except:
        #             logging.basicConfig(filename='errorLogs.txt',level=logging.DEBUG)
        #             logging.info('problem getting values from diagonistcs queue')

        #         # ADD LAST UPLOAD AND SERVER RESPONSE TO FILE
        #         output.write("LAST UPLOADING FILE NAME: "+ last_upload + "\n"+"LAST SERVER RESPONSE: "+ last_server_resp +"\n\n")
        #         output.write("_______________END OF LOG SEGMENT___________________\n\n\n")
        #     output.close()
        #     t=time.time()
        # ##########################

        # Pre process every frame for motion analysis
        if frame_hist == 0:
            hsv_roi =  cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv_roi, np.array((0., 60.,32.)), np.array((180.,255.,255.)))
            roi_hist = cv2.calcHist([hsv_roi],[0],mask,[180],[0,180])
            cv2.normalize(roi_hist,roi_hist,0,255,cv2.NORM_MINMAX)
            frame_hist = 1

        # resize every frame to reduce computational power 
        image = imutils.resize(frame, width=min(300, frame.shape[1]))
        orig = image.copy()

        # Process every frame for motion analysis
        # convert frame to gray
        frame2gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY )
        #Absdiff to get the difference between the frames
        result_frame = cv2.absdiff(frame1gray,frame2gray)
        # Pre process every result frame for motion analysis
        result_frame = cv2.blur(result_frame,(5,5))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT,(5,5))
        result_frame = cv2.morphologyEx(result_frame, cv2.MORPH_OPEN, kernel)
        result_frame = cv2.morphologyEx(result_frame, cv2.MORPH_CLOSE, kernel)
        val , result_frame = cv2.threshold(result_frame, 13, 255, cv2.THRESH_BINARY_INV)

        # Check for motion. If there is any motion try to detect humans.
        if somethingHasMoved(result_frame):
    
            # detect people in the frame using our hog classifier
            (rects, weights) = hog.detectMultiScale(image, winStride=(4, 4),
                padding=(0, 0), scale=1.1)

            # If no detection reset these values to any random large values
            if len(rects) == 0:
                t_x = 10001
                t_y = 10001
                t_w = 10031
                t_h = 10031
                t_x_bar = 100021
                t_y_bar = 100011

            # Iterate through all of the detected human bodies
            for i in range(len(rects)):

                body_i = rects[i]
                (x, y, w, h) = [v * 1 for v in body_i]

                # draw the bounding boxes for every detection
                cv2.rectangle(orig, (x, y), (x + w, y + h), (0, 0, 255), 2)

                # apply non-maxima suppression to reduce overlapping
                rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
                pick = non_max_suppression(rects, probs=None, overlapThresh=0.65)

                # # Iterate through all of the detected human bodies after NON NAXIMA 
                for i in range(len(pick)):

                    body_i = pick[i]
                    (xA, yA, xB, yB) = [int(v * 1) for v in body_i]

                    # draw the final bounding boxes after NON MAXIMA
                    #cv2.rectangle(image, (xA, yA), (xB, yB), (0, 255, 0), 2)

                    # Now draw bounding boxes on original full resolution frame
                    # First map the final bounding boxes to the original frame 
                    # Calculated multiplication factor varries with camera resolution
                    # (4.28 for 1280x720) (6.4 for 1920x1080)

                    (x1, y1, w1, h1) = [int(v * 4.28) for v in body_i]
                    cv2.rectangle(frame, (x1, y1), (w1, h1), (0, 255, 55), 2)

                    # for tracking , every time current rectangle is the new rectangle/bounding box
                    curr_rect = (x1, y1, w1, h1)

                    # for first run, set tracking window here
                    if first == 0:
                        track_window = curr_rect
                        first = 1

                    #calculate the centerpoint of NEW rectangle/bounding boxes
                    x_bar = x1 + 0.5 * w1
                    y_bar = y1 + 0.5 * h1

                    # CHECK IF CURRENT RECTANGLES LIES SOMWHERE IN THE PREVIOUS RECTANGLES
                    if ((t_x <= x_bar <= (t_x + t_w)) and (t_y <= y_bar <= (t_y + t_h)) and (x1 <= t_x_bar <= (x1 + w1 )) and ( y1 <= t_y_bar <= (y1 + h1  ))):
                        
                        # If it lies somewhere in the previous rectangle do not reset the tracker, keep tracking the previous one
                        #print ('RECT MATCHED - KEEP TRACKING - DONT RESET')
                        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                        dst = cv2.calcBackProject([hsv],[0],roi_hist,[0,180],1)
                        # apply meanshift to get the new location
                        ret, track_window = cv2.meanShift(dst, track_window, term_crit)

                        x3,y3,w3,h3 = track_window

                        x3 = ((x1-x3)+x3)
                        y3 = ((y1-y3)+y3)
                        w3 = ((w1-w3)+w3)
                        h3 = ((h1-h3)+h3)

                        # draw tracking rectangles
                        cv2.rectangle(frame, (x3, y3),(w3, h3),rectangleColor ,2)
                        # copy current rects in tracking rects
                        (t_x , t_y , t_w , t_h) = curr_rect
                        #calculate the centerpoints
                        t_x_bar = t_x + 0.5 * t_w
                        t_y_bar = t_y + 0.5 * t_h
                       
                    else:
                        # If it does not lie in the previous rectangles , update the tracked and track the current/new one
                        #print('NO MATCHING RECTS - UPDATE TRACKER - UPDATE RECTS') 
                        track_window = curr_rect

                        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                        dst = cv2.calcBackProject([hsv],[0],roi_hist,[0,180],1)
                        # apply meanshift to get the new location
                        ret, track_window = cv2.meanShift(dst, track_window, term_crit)

                        x3,y3,w3,h3 = track_window

                        x3 = ((x1-x3)+x3)
                        y3 = ((y1-y3)+y3)
                        w3 = ((w1-w3)+w3)
                        h3 = ((h1-h3)+h3)

                        # draw tracking rectangles
                        cv2.rectangle(frame, (x3, y3),(w3, h3),rectangleColor ,2)
                        
                        # copy current rects in tracking rects
                        (t_x , t_y , t_w , t_h) = curr_rect
                        #calculate the centerpoints
                        t_x_bar = t_x + 0.5 * t_w
                        t_y_bar = t_y + 0.5 * t_h 

                        # Every time we hav new detection or bounding box save it to upload on server
                        # Crop body from Original full resolution frame
                        body_big = frame[y1:h1, x1:w1]

                        # Uncomment this if you want your every detection on same aspect ratio i-e 1:2

                        '''
                        ####################################

                        im_shape = body_big.shape
                        #print('ORIGINAl Width: ',im_shape[0])
                        #print('ORIGINAL Height: ',im_shape[1])
                        aspect_ratio = float(float(im_shape[0]) / float(im_shape[1]))
                        #print('ORIGINAL Aspect Ratio: ',aspect_ratio)
                        ratio_check = float(1 / 1.67)
                        #print ('Aspect Ratio Threshold: ', ratio_check)

                        if aspect_ratio < (ratio_check) or aspect_ratio > (ratio_check):
                            new_width = ratio_check * float(im_shape[1])
                            #print('NEW width: ', new_width)
                            aspect_ratio = float(float(new_width) / float(im_shape[1]))
                            #print('NEW aspect ratio: ', aspect_ratio)
                            body_big = imutils.resize(body_big, width=int(new_width))
                            
                        ####################################
                        '''
                        # before saving the detected image first get current date and time to append it with name
                        cur_date = (time.strftime("%Y-%m-%d"))
                        cur_time = (time.strftime("%H:%M:%S"))
                        # Append date and time
                        new_pin =cur_date+"-"+cur_time
                        # any hardcoded name you want
                        filename1 = 'UNKNOWN'
                        # Append new_pin and hardcoded name to make final name 
                        filename2 = str(filename1)+'-'+str(new_pin)
                        # this is your final image with the path to where it is located
                        sampleFile = ('%s/%s.png' % (save_body_path, filename2))

                        #Save image in a folder, save_body_path has the full path to the folder where we want to save images
                        cv2.imwrite('%s/%s.png' % (save_body_path, filename2), body_big)

                        # For Face Detection read each image from the location where we saved it
                        person = cv2.imread(sampleFile)
                        # Pass the image to face detector, we are using dlib's face detector 
                        dets = detector(person, 1)

                        print("Number of faces detected: {}".format(len(dets)))

                        # Iterate through all of detected bounding boxes/faces
                        for i, d in enumerate(dets):
                            print("Detection {}: Left: {} Top: {} Right: {} Bottom: {}".format(
                                i, d.left(), d.top(), d.right(), d.bottom()))

                            # Crop the faces/bounding boxes and save in a seperate folder for later use
                            crop = person[d.top():d.bottom(), d.left():d.right()]
                            # before saving the detected image first get current date and time to append it with name
                            cur_date = (time.strftime("%Y-%m-%d"))
                            cur_time = (time.strftime("%H:%M:%S"))
                            new_pin =cur_date+"-"+cur_time
                            facename1 = 'FACE'
                            facename2 = str(facename1)+'-'+str(new_pin)
                            sampleFace = ('%s/%s.png' % (save_faces_path, facename2))
                            #Save Image Here
                            cv2.imwrite('%s/%s.png' % (save_faces_path, facename2), crop)

                        # Put detected bodies in Queue... un comment below line if you have upload process running
                        # queue_BODIES.put(sampleFile)  
                    
        # show the output images
        cv2.imshow("Before NMS", orig)
        #cv2.imshow("After NMS", image)
        #cv2.imshow("ANZEN", frame)
        #cv2.imshow("thres", result_frame)

        # Always copy current frame to prev frame to consider it as a background for motion analysis
        frame1gray = frame2gray.copy()
            

        key = cv2.waitKey(10)
        if key == 27:
            break
        
try:
      if __name__ == '__main__':

        #print ('Starting body_detection')
        body_det = multiprocessing.Process(target=body_detection)
        body_det.start()
         
        # Uncomment it if you want to enable uploading   
        # print('Starting start_upload')  
        # upload_body_process = multiprocessing.Process(target=start_upload)
        # upload_body_process.start()
        # upload_body_process.join()

except BaseException as e:
    #print ('BaseException %s',e)
    logging.basicConfig(filename='errorLogs.txt',level=logging.DEBUG)
    logging.debug('BaseException')
    logging.info(traceback.format_exc())
               
except GeneratorExit as e:
    #print ('GeneratorExit',e)
    logging.basicConfig(filename='errorLogs.txt',level=logging.DEBUG)
    logging.debug('GeneratorExit')
    logging.info(traceback.format_exc())

except MemoryError as e:
    #print ('MemoryError',e)     
    logging.basicConfig(filename='errorLogs.txt',level=logging.DEBUG)
    logging.debug('MemoryError')
    logging.info(traceback.format_exc()) 

except OSError as e:
    #print ('OSError',e)
    logging.basicConfig(filename='errorLogs.txt',level=logging.DEBUG)
    logging.debug('OSError')
    logging.info(traceback.format_exc())

except SystemExit as e:
    logging.basicConfig(filename='errorLogs.txt',level=logging.DEBUG)
    logging.debug('SystemExit')
    logging.info(traceback.format_exc())

except Exception as e:
    #print ('Exception',e)
    logging.basicConfig(filename='errorLogs.txt',level=logging.DEBUG)
    logging.debug('Exception')
    logging.info(traceback.format_exc())
    


    

    
    
    





