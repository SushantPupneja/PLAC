from Tkinter import Label, Button , Frame
import datetime, time
from PIL import Image , ImageTk
import requests
import os
import urllib
from urllib2 import urlopen
import io
import socket  
import base64

#--------------------------

import numpy as np
import cv2
import datetime, time
import argparse
import json
import os
import picamera
from picamera.array import PiRGBArray
from PIL import Image , ImageTk
# import face_gui
import multiprocessing as mp
import threading

from scipy.misc import imread
from scipy.linalg import norm
from scipy import sum, average

from Tkinter import Tk, Label, Button , Frame

s = socket.socket()         # Create a socket object
host = "192.168.1.19"       # Get local machine name
port = 10000             # Reserve a port for your service.

try:
  s.connect((host, port))
  log("connection established to tcp server.....")
except:
  print("connection failed while connecting tcp server")


#globals for face_reko

app_init_flag = True
ConfigFilePath="../webcam/Config.json"
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')
debug = 0

start_time, max_face_count, img_name, img_to_save = datetime.datetime.now(), 0, "", 0

def tcp_server():
  global s, host, port
  try:
    log("sending tcp server..........")
    s.send("open")
    print s.recv(1024)
  except Exception, e:
    print ("tcp server error ")
    print e
                     
  return None

def log(s):
  global debug
  if debug:
    print(s)



def startMatching(img):
  try:
    msg_queue.get_nowait()
  except Exception, e:
    print (" msg queue is empty ")
        
    ret = img_disp.match_image(img)

    if ret == 1:
      tcp_server()
      time.sleep(5)
    elif ret ==2 or ret==3:
      time.sleep(3)

    msg_queue.put_nowait("open")
    print("process is free now")


def storeImage(img):
  global app_init_flag
  current_time = datetime.datetime.now()
  gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
  faces = face_cascade.detectMultiScale(gray, 1.3, 5)
  if len(faces):
    for (x, y, w, h) in faces:
      cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    t_start = datetime.datetime.now()
    start_time = datetime.datetime.now()
    log(start_time.strftime('%H:%M:%S - ') + "Face found....")

  #display image on gui
    log("img found alert !!!!!!!!!!!!!!!!!!!!!!!!!!! {}".format(type(img)))
  #initiate scanning thread
    if app_init_flag:
      # image_obj_queue.put(img)
      app_init_flag = False
      t1 = threading.Thread(name="image_queue_thread", target=img_disp._check_queue(img))
      t1.start()

      t2 = threading.Thread(name="face_reco_api", target=startMatching(img))
      t2.start()
    else:
      try:
        flag = msg_queue.get_nowait()
        print flag
      except Exception, e:
        flag = ""
    
      if flag == "open":
        # image_obj_queue.put(img)
        log("image added to the queue")
        t1 = threading.Thread(name="image_queue_thread", target=img_disp._check_queue(img))
        t1.start()
        t2 = threading.Thread(name="face_reco_api", target=startMatching(img))
        t2.start()
      else:
        log("ignoring image process is busy")

  # print ("queue length -------------------", image_obj_queue.qsize())     
  #save image
  #print "Image written to file........."
  #cv2.imwrite( img_name, img)

  #log(start_time.strftime('%H:%M:%S - ') + "Image Saved. going to sleep", sleep, "seconds.")
#log("--------------")
  # start_time = current_time
  # time.sleep(5)
  # t_end = datetime.datetime.now()
  # time_elaps = (t_end - t_start).total_seconds()
  # frame_count = fps * time_elaps
  # frame_ref = 1 / frame_count
  # log("changing frame")
  # cap.set(1,1)
  # log("frame updated")

# # face reco process
def faceReko():
  log("starting face reKo")
  global start_time, max_face_count, img_name, img_to_save, app_init_flag, ConfigFilePath, face_cascade, eye_cascade, debug
  global DeviceId, url, token, camResolutionWidth, camResolutionHeight, camFramerate, camShutterSpeed, camISO
  #Read JSON config file
  try:
        #print "itry"
        json_data1 = json.loads(open(ConfigFilePath).read())
        #print json_data1
        DeviceId=json_data1['DeviceId']
        log("Device Id = " + json_data1['DeviceId'])
        camResolutionWidth = json_data1['cameraSettings']['resolution']['width']
        camResolutionHeight = json_data1['cameraSettings']['resolution']['height']
        camFramerate = json_data1['cameraSettings']['framerate']
        camShutterSpeed = json_data1['cameraSettings']['shutterSpeed']
        camISO = json_data1['cameraSettings']['iso']
  except Exception as e:
        log("error reading config file, setting deviceId, UploadUrl, Token to default...", str(e))

  parser = argparse.ArgumentParser()
  parser.add_argument('--threshhold', type=int, help="frame threshhold default 5 frames", default=5)
  parser.add_argument('--sleep', type=int, help="sleep seconds default 5 seconds", default=5)
  parser.add_argument('--method', type=int, help="0:frame from opencv; 1:frame from picamera", default=0)
  parser.add_argument('--W', type=int, help="", default=640)
  parser.add_argument('--H', type=int, help="", default=480)
  parser.add_argument('--framerate', type=int, help="", default=5)
  parser.add_argument('--shutterSpeed', type=int, help="8323,10000,16588", default=16588)
  parser.add_argument('--iso', type=int, help="400,800,1600", default=1600)
  parser.add_argument('--debug', type=int, help="", default=0)
  
  args = parser.parse_args()

  prev_faces, prev_img = [], 0
  threshhold = args.threshhold
  sleep = args.sleep
  method = args.method
  camResolutionWidth = args.W
  camResolutionHeight = args.H
  camFramerate = args.framerate
  camShutterSpeed = args.shutterSpeed
  camISO = args.iso
  debug = args.debug
  counter = 0

  log("threshhold {} , Sleep {}".format(threshhold,sleep))
  if debug:
    print ("process will work in debug mode")
  else:
    print("process will work in non debug mode")
  if method == 0:
    log("using opencv frames method")
    cap = cv2.VideoCapture(0)
    cap.set(3, camResolutionWidth)
    cap.set(4, camResolutionHeight)
    # frame_count = 120
    #######use below code to check the fps for connected webcam using open cv#####
    # start_time = datetime.datetime.now()
    # for i in range(frame_count):
    #  ret, img = cap.read()
    # end_time = datetime.datetime.now()

    # time_taken = (end_time - start_time).total_seconds()
    # print time_taken
    # fps = frame_count / time_taken
    # print "fps raprint start_time.strftime('%H:%M:%S - ') + "Face found...., counter = " + str(counter)te is {}".format(fps)
    ################################################################################
    while 1:
      ret, img = cap.read()     
      # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
      #faces = face_cascade.detectMultiScale(gray, 1.3, 5)
     
      
      #if len(faces):
      cv2.imshow('Live Face',img)
      k = cv2.waitKey(30) & 0xff
      if k == 27:
        break

      try:
         if not image_processing_thread.isAlive():
          image_processing_thread = threading.Thread(name="image_store_thread", target=storeImage, args=(img,))
          image_processing_thread.start()
         else:
          pass
          #log('Image Ignored')
      except:
        image_processing_thread = threading.Thread(name="image_store_thread", target=storeImage, args=(img,))
        image_processing_thread.start()

    #else:
     #   prev_faces, prev_img, counter = [], 0, 0
      #  log("no faces found")
      #  k = cv2.waitKey(30) & 0xff
      #  if k == 27:
      #    break


    cap.release()
    cv2.destroyAllWindows()

  elif method == 1:
    print "using picamera frames method"
    print ("starting face reKo")
    print "threshhold", threshhold, ", Sleep ", sleep

    camera = picamera.PiCamera()

    camera.resolution = (camResolutionWidth,camResolutionHeight)
    camera.shutter_speed = camShutterSpeed
    camera.framerate = camFramerate
    camera.ISO = camISO
    camera.video_stabilization = True

    rawCapture = PiRGBArray(camera)
    time.sleep(sleep)

    for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
      img = frame.array
      gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
      faces = face_cascade.detectMultiScale(gray, 1.3, 2)

      current_time = datetime.datetime.now()
      if len(faces):
        print "Face found...."
        image_name = 'images/' + DeviceId + 'Grp_' + start_time.strftime('%Y-%m-%d_%H:%M:%S.%f') + ".jpg"
        # print image_name
        # cv2.imwrite( image_name, image)
        #display image on gui
        print "img found alert !!!!!!!!!!!!!!!!!!!!!!!!!!!", type(img)
        #initiate scanning thread
        if app_init_flag:
            # image_obj_queue.put(img)
            app_init_flag = False
            t1 = threading.Thread(name="image_queue_thread", target=img_disp._check_queue(img))
            t1.start()

            t2 = threading.Thread(name="face_reco_api", target=startMatching(img))
            t2.start()
        else:
          try:
            flag = msg_queue.get_nowait()
            print flag
          except Exception, e:
            flag = ""
          
          if flag == "open":
            # image_obj_queue.put(img)
            print ("image added to the queue")
            t1 = threading.Thread(name="image_queue_thread", target=img_disp._check_queue(img))
            t1.start()
            t2 = threading.Thread(name="face_reco_api", target=startMatching(img))
            t2.start()
          else:
            print("ignoring image process is busy")
        start_time = current_time
        print start_time.strftime('%H:%M:%S - ') + "Image Saved"

      else:
        print "no faces found"

      rawCapture.truncate(0)




class FaceWindow:
    """docstring for FaceWindow"""

    def __init__(self, window,msg_queue):

        #create global variable for root
        self.window = window

        self.window.configure(background='white')

        #create global variable for root
        self.msg_queue = msg_queue

        # #create a global list of label
        self.label_list = {}
    
        

    def _check_queue(self,img_ref):
        try:
            log("time for queue check")
            # print ("queue length is now", self.image_obj_queue.qsize())
            self.paint_list(img_ref)
            log("image printed")
        except Exception:
            print(">>>>>>>> no new image")
            pass


    def paint_list(self,image_ref):
        
        try:
            log("-----clearing frame----------")
            try:
                for key in self.label_list.keys():
                    log(key)
                    panel = self.label_list[key]
                    panel.destroy()
                    del self.label_list[key]

            except Exception, e:
              print ("exeption in clearing labels",e)

            log("------------------------------------------------------------------------------------")
            image = Image.fromarray(image_ref)
            log("1")

            # image.save("saved_img_from_pil_img_obj.jpg")
            
            #resize the image
            im = image.resize((400, 400), Image.ANTIALIAS)
            log("2")

            #Creates a Tkinter-compatible photo image, which can be used everywhere Tkinter expects an image object.
            img = ImageTk.PhotoImage(im)
            log("3")

            main_frame = Frame(self.window)
            main_frame.pack()
            

            # #The Label widget is a standard Tkinter widget used to display a text or image on the screen.
            panel = Label(main_frame, image = img, bg="white")
            log("4")
            

            #keep the refrence of the image
            panel.image = img
            log("5")

            #The Pack geometry manager packs widgets in rows or columns.
            panel.pack(side = "left", fill = "both", expand = "yes")



            load = Image.open("loading.jpg")
            load_im = load.resize((400, 400), Image.ANTIALIAS)
            load_img = ImageTk.PhotoImage(load_im)

            panel1 = Label(main_frame, image=load_img, bg = "white", )
            panel1.image = load_img
            panel1.pack(side = "left", fill = "both", expand = "yes")


            api_result_frame = Frame(self.window, bg="white")
            api_result_frame.pack(side="bottom")

            lab = Label(api_result_frame, text="Matching Image .......... ", bg="white", font="Verdana 30 bold italic", fg="LightSkyBlue1", width=50, height=50)
            lab.pack(fill = "both", expand = "yes")

            #append label in label list
            self.label_list["mainFrame"] = main_frame
            self.label_list["panel"] = panel
            self.label_list["panel1"] = panel1
            self.label_list["api_result_frame"] = api_result_frame
            self.label_list["lab"] = lab

            log(self.label_list)
        
            log("------------------------------------------------------------------------------------")
        except Exception,e :
            print e

    def fetch_image(self,img_link):
      # img = io.BytesIO()
      # # img =Image.open(urlopen(img_link))
      # im = Image.open(img)
      log("displaying....... image in thread")
      img_b64 = base64.b64decode(img_link)
      img = io.BytesIO(img_b64)
      im = Image.open(img)
      im = im.resize((400, 400), Image.ANTIALIAS)
      image = ImageTk.PhotoImage(im)

      #delete loading label
      panel1 = self.label_list["panel1"]
      panel1.destroy()

      #paste image
      main_frame = self.label_list["mainFrame"] 

      panel1 = Label(main_frame, image=image, bg = "white")
      panel1.image = image
      panel1.pack(side = "left", fill = "both", expand = "yes", padx = 5, pady = 5)

      #append label in label list
      self.label_list["panel1"] = panel1




    def match_image(self,image_ref):
        #hit the api
        image = Image.fromarray(image_ref)
        img_name = str(datetime.datetime.now().date()) + "T" + str(datetime.datetime.now().time()) + "_im.jpg"
        image.save(img_name)


        
        log("sending............ {}".format(img_name))

        try:
            log(" matching....... image on cloud")
            re = requests.post("http://192.168.1.10:9092/vehicle/v1.0/self_check_in", data={'type': "match"}, files={"file":open(img_name,"rb")})
            log("image sent")
        except Exception as e:
            print ("Network Error.....")
            os.remove(img_name)
            return None

        os.remove(img_name)
        res_code = re.status_code

        if res_code != 200:
            return None
        resp = re.json()
        log("received image result")

        if resp["message"] == "success":

            try:
                log("fetching matched image")
                img_link = resp["result"]["fields"]["imageUrl"]

                log("initiating thread for image ........")
                
                image_thread = threading.Thread(name="image_thread", target=img_disp.fetch_image(img_link))
                image_thread.start()  

                log("thread initiated")           

                #delete matching label
                lab = self.label_list["lab"]
                lab.destroy()

                api_result_frame = self.label_list["api_result_frame"] 


                #label for display msg
                msg = "Congratulations " + resp["result"]["fields"]["passengerName"] + " ..... !!!! You have been " + str(int(resp["result"]["fields"]["Similarity"])) + "'%' recognized by ZESTIOT"
                namePanel = Label(api_result_frame, text=msg, bg = "white", fg="Green", font="Helvetica 10 bold", height=50)
                namePanel.pack(fill = "both", expand = "yes")

                #append label in label list
                self.label_list["namePanel"] = namePanel

                return 1
                
            except Exception, e:
                print ("error in fetching matched image",e)
            

        if resp["message"] == "noFaceFound":
          #delete loading label
          panel1 = self.label_list["panel1"]
          panel1.destroy()

          #delete matching label
          lab = self.label_list["lab"]
          lab.destroy()

          api_result_frame = self.label_list["api_result_frame"] 


          #label for display msg
          msg = "Face Not Found ......."
          namePanel = Label(api_result_frame, text=msg, bg = "white", fg="black", font="Helvetica 14 bold", height=50)
          namePanel.pack(fill = "both", expand = "yes")

          #append label in label list
          self.label_list["namePanel"] = namePanel

          return 2

        if resp["message"] == "failed":
          #delete loading label
          panel1 = self.label_list["panel1"]
          panel1.destroy()

          #paste image
          main_frame = self.label_list["mainFrame"] 

          im = Image.open("cancel.jpg")
          failed_im = im.resize((400, 400), Image.ANTIALIAS)

          failed_image = ImageTk.PhotoImage(failed_im)


          panel1 = Label(main_frame, image=failed_image, bg = "white")
          panel1.image = failed_image
          panel1.pack(side = "left", fill = "both", expand = "yes", padx = 5, pady = 5)


          #delete matching label
          lab = self.label_list["lab"]
          lab.destroy()

          api_result_frame = self.label_list["api_result_frame"] 


          #label for display msg
          msg = "Recognition Failed"
          namePanel = Label(api_result_frame, text=msg, bg = "white", fg="red", font="Helvetica 14 bold", height=50)
          namePanel.pack(fill = "both", expand = "yes")

          #append label in label list
          self.label_list["namePanel"] = namePanel

          return 2

        return None

#initate shared memory between sub processes
log('not running')
msg_queue = mp.Queue()

#initate face traking thread
t1 = threading.Thread(name="faceReko_scan", target=faceReko)
t1.setDaemon(True)
t1.start()

#prepare window
window = Tk()
window.title("Face Reco Application")
window.geometry("850x600")
img_disp = FaceWindow(window,msg_queue)
window.mainloop()



#use below func for picamera

