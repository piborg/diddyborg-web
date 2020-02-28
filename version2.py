#!/usr/bin/env python
# coding: Latin-1

# Creates a web-page interface for DiddyBorg Metal Edition
# v2 by wingers999 - with /touch interface, /hold interface now also works with keyboard control (arrow keys), and also now shows Ultraborg sensor values
# thanks to gt213296's post on http://forum.piborg.org/comment/4090 for Ultraborg information and for Semi-Auto and Auto mode additions
# thanks to WS at http://forum.piborg.org/thunderborg/examples/users for /touch mode, keyboard control for /hold mode and jpeg quality settings

# Import library functions we need
import PicoBorgRev
import time
import sys
import threading
import SocketServer
import picamera
import picamera.array
import cv2
import UltraBorg
import datetime

# Settings for the web-page
webPort = 80                            # Port number for the web-page, 80 is what web-pages normally use
imageWidth = 240                        # Width of the captured image in pixels
imageHeight = 180                       # Height of the captured image in pixels
frameRate = 10                          # Number of images to capture per second
displayRate = 2                         # Number of images to request per second
photoDirectory = '/home/pi'             # Directory to save photos to
jpegQuality = 80                        # JPEG quality level, smaller is faster, higher looks better (0 to 100)

# Movement mode constants
MANUAL_MODE = 0                         # User controlled movement
SEMI_AUTO_MODE = 1                      # Semi-automatic movement
AUTO_MODE = 2                           # Fully automatic movement

# Global values
global PBR
global lastFrame
global lockFrame
global camera
global processor
global running
global watchdog
global movementMode
running = True
movementMode = MANUAL_MODE

# Setup the UltraBorg
global UB
UB = UltraBorg.UltraBorg()              # Create a new UltraBorg object
UB.Init()                               # Set the board up (checks the board is connected)

# Setup the PicoBorg Reverse
PBR = PicoBorgRev.PicoBorgRev()
#PBR.i2cAddress = 0x44                  # Uncomment and change the value if you have changed the board address
PBR.Init()
if not PBR.foundChip:
    boards = PicoBorgRev.ScanForPicoBorgReverse()
    if len(boards) == 0:
        print 'No PicoBorg Reverse found, check you are attached :)'
    else:
        print 'No PicoBorg Reverse at address %02X, but we did find boards:' % (PBR.i2cAddress)
        for board in boards:
            print '    %02X (%d)' % (board, board)
        print 'If you need to change the IÂ²C address change the setup line so it is correct, e.g.'
        print 'PBR.i2cAddress = 0x%02X' % (boards[0])
    sys.exit()
#PBR.SetEpoIgnore(True)                 # Uncomment to disable EPO latch, needed if you do not have a switch / jumper
PBR.SetCommsFailsafe(False)             # Disable the communications failsafe
PBR.ResetEpo()

# Power settings
voltageIn = 1.2 * 12                    # Total battery voltage to the PicoBorg Reverse
voltageOut = 12.0                       # Maximum motor voltage

# Setup the power limits
if voltageOut > voltageIn:
    maxPower = 1.0
else:
    maxPower = voltageOut / float(voltageIn)

# Timeout thread
class Watchdog(threading.Thread):
    def __init__(self):
        super(Watchdog, self).__init__()
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.timestamp = time.time()
        
    def run(self):
        timedOut = True
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for a network event to be flagged for up to one second
            if timedOut:
                if self.event.wait(1):
                    # Connection
                    print 'Reconnected...'
                    timedOut = False
                    self.event.clear()
            else:
                if self.event.wait(1):
                    self.event.clear()
                else:
                    # Timed out
                    print 'Timed out...'
                    timedOut = True
                    PBR.MotorsOff()

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self):
        super(StreamProcessor, self).__init__()
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.begin = 0

    def run(self):
        global lastFrame
        global lockFrame
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and save globally
                    self.stream.seek(0)
                    flippedArray = cv2.flip(self.stream.array, -1) # Flips X and Y
                    retval, thisFrame = cv2.imencode('.jpg', flippedArray, [cv2.IMWRITE_JPEG_QUALITY, jpegQuality])
                    del flippedArray
                    lockFrame.acquire()
                    lastFrame = thisFrame
                    lockFrame.release()
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

# Image capture thread
class ImageCapture(threading.Thread):
    def __init__(self):
        super(ImageCapture, self).__init__()
        self.start()

    def run(self):
        global camera
        global processor
        print 'Start the stream using the video port'
        camera.capture_sequence(self.TriggerStream(), format='bgr', use_video_port=True)
        print 'Terminating camera processing...'
        processor.terminated = True
        processor.join()
        print 'Processing terminated.'

    # Stream delegation loop
    def TriggerStream(self):
        global running
        while running:
            if processor.event.is_set():
                time.sleep(0.01)
            else:
                yield processor.stream
                processor.event.set()

# Automatic movement thread
class AutoMovement(threading.Thread):
    def __init__(self):
        super(AutoMovement, self).__init__()
        self.terminated = False
        self.start()

    def run(self):
        global movementMode
        # This method runs in a separate thread
        while not self.terminated:
            # See which mode we are in
            if movementMode == MANUAL_MODE:
                # User movement, wait a second before checking again
                time.sleep(1.0)
            elif movementMode == SEMI_AUTO_MODE:
                # Semi-automatic movement mode, checks twice per second
                # Ultrasonic distance readings semi auto mode

                # Get the readings from ultra sensors
                distance1 = int(UB.GetDistance1())
                distance2 = int(UB.GetDistance2())
                distance3 = int(UB.GetDistance3())
                distance4 = int(UB.GetDistance4())
                
                # Set critical allowed distance to object in front
                if distance1 <= 50:
                    PBR.MotorsOff()
                elif distance1 <= 100:
                    driveRight = 0.3 * maxPower
                    driveLeft = 0.3 * maxPower
                    PBR.SetMotor1(driveRight)
                    PBR.SetMotor2(-driveLeft)

                #Set critical allowed distance to object right
                #if distance2 <= 50:
                #    PBR.MotorsOff()
                #else:

                #Set critical allowed distance to object left
                #if distance3 <= 50:
                #    PBR.MotorsOff() 
                #else:

                #Set critical allowed distance to object rear
                #if distance4 <= 50: 
                #    PBR.MotorsOff()
                #elif distance4 <= 100:
                #    driveRight = 0.3 * maxPower
                #    driveLeft = 0.3 * maxPower
                #    PBR.SetMotor1(-driveRight)
                #    PBR.SetMotor2(driveLeft) 

                # Wait for 1/2 of a second before reading again
                thread.sleep(0.5)
            elif movementMode == AUTO_MODE:
                # Automatic movement mode, updates five times per second

                # TODO: Fill in logic here

                # Wait for 1/5 of a second before reading again
                thread.sleep(0.2)
            else: 
                # Unexpected, print an error and wait a second before trying again
                print 'Unexpected movement mode %d' % (movementMode)
                time.sleep(1.0)

# Class used to implement the web server
class WebServer(SocketServer.BaseRequestHandler):
    def handle(self):
        global PBR
        global lastFrame
        global watchdog
        global movementMode
        # Get the HTTP request data
        reqData = self.request.recv(1024).strip()
        reqData = reqData.split('\n')
        # Get the URL requested
        getPath = ''
        for line in reqData:
            if line.startswith('GET'):
                parts = line.split(' ')
                getPath = parts[1]
                break

        watchdog.event.set()

        if getPath.startswith('/distances-once'):
            # Ultrasonic distance readings
            # Get the readings
            distance1 = int(UB.GetDistance1())
            distance2 = int(UB.GetDistance2())
            distance3 = int(UB.GetDistance3())
            distance4 = int(UB.GetDistance4())
            
            # Build a table for the values
            httpText = '<html><body><center><table border="0" style="width:50%"><tr>'
            if distance1 == 0:
                httpText += '<td width="25%"><center>None</center></td>'
            else:
                httpText += '<td width="25%%"><center>%04d</center></td>' % (distance1)
            if distance2 == 0:
                httpText += '<td width="25%"><center>None</center></td>'
            else:
                httpText += '<td width="25%%"><center>%04d</center></td>' % (distance2)
            if distance3 == 0:
                httpText += '<td width="25%"><center>None</center></td>'
            else:
                httpText += '<td width="25%%"><center>%04d</center></td>' % (distance3)
            if distance4 == 0:
                httpText += '<td width="25%"><center>None</center></td>'
            else:
                httpText += '<td width="25%%"><center>%04d</center></td>' % (distance4)
            httpText += '</tr></table></body></html>'
            self.send(httpText) 

        elif getPath.startswith('/semiAuto'):
              # Toggle Auto mode
              if movementMode == SEMI_AUTO_MODE:
                  # We are in semi-auto mode, turn it off
                  movementMode = MANUAL_MODE
                  httpText = '<html><body><center>'
                  httpText += 'Speeds: 0 %, 0 %'
                  httpText += '</center></body></html>'
                  self.send(httpText)
                  PBR.MotorsOff()
              else:
                  # We are not in semi-auto mode, turn it on
                  movementMode = SEMI_AUTO_MODE
                  httpText = '<html><body><center>'
                  httpText += 'Semi Mode'
                  httpText += '</center></body></html>'
                  self.send(httpText)

        elif getPath.startswith('/Auto'):
              # Toggle Auto mode
              if movementMode == AUTO_MODE:
                  # We are in auto mode, turn it off
                  movementMode = MANUAL_MODE
                  httpText = '<html><body><center>'
                  httpText += 'Speeds: 0 %, 0 %'
                  httpText += '</center></body></html>'
                  self.send(httpText)
                  PBR.MotorsOff()
              else:
                  # We are not in auto mode, turn it on
                  movementMode = AUTO_MODE
                  httpText = '<html><body><center>'
                  httpText += 'Auto Mode'
                  httpText += '</center></body></html>'
                  self.send(httpText)

        elif getPath.startswith('/cam.jpg'):
            # Camera snapshot
            lockFrame.acquire()
            sendFrame = lastFrame
            lockFrame.release()
            if sendFrame is not None:
                self.send(sendFrame.tostring())

        elif getPath.startswith('/off'):
            # Turn the drives off and switch to manual mode
            movementMode = MANUAL_MODE
            httpText = '<html><body><center>'
            httpText += 'Speeds: 0 %, 0 %'
            httpText += '</center></body></html>'
            self.send(httpText)
            PBR.MotorsOff()

        elif getPath.startswith('/set/'):
            # Motor power setting: /set/driveLeft/driveRight
            parts = getPath.split('/')
            # Get the power levels
            if len(parts) >= 4:
                try:
                    driveLeft = float(parts[2])
                    driveRight = float(parts[3])
                except:
                    # Bad values
                    driveRight = 0.0
                    driveLeft = 0.0
            else:
                # Bad request
                driveRight = 0.0
                driveLeft = 0.0
            # Ensure settings are within limits
            if driveRight < -1:
                driveRight = -1
            elif driveRight > 1:
                driveRight = 1
            if driveLeft < -1:
                driveLeft = -1
            elif driveLeft > 1:
                driveLeft = 1
                
            # Report the current settings
            percentLeft = driveLeft * 100.0;
            percentRight = driveRight * 100.0;
            httpText = '<html><body><center>'
            if movementMode == MANUAL_MODE:
                httpText += 'Speeds: %.0f %%, %.0f %%' % (percentLeft, percentRight)
            elif movementMode == SEMI_AUTO_MODE:
                httpText += 'Semi: %.0f %%, %.0f %%' % (percentLeft, percentRight)
            elif movementMode == AUTO_MODE:
                percentLeft = PBR.GetMotor2() * 100.0;
                percentRight = PBR.GetMotor1() * 100.0;
                httpText += 'Auto: %.0f %%, %.0f %%' % (percentLeft, percentRight)
            httpText += '</center></body></html>'
            self.send(httpText)
            
            # Set the outputs as long as we are not in auto mode
            if movementMode != AUTO_MODE:
                driveLeft *= maxPower
                driveRight *= maxPower
                PBR.SetMotor1(driveRight)
                PBR.SetMotor2(-driveLeft)

        elif getPath.startswith('/photo'):
            # Save camera photo
            lockFrame.acquire()
            captureFrame = lastFrame
            lockFrame.release()
            httpText = '<html><body><center>'
            if captureFrame != None:
                photoName = '%s/Photo %s.jpg' % (photoDirectory, datetime.datetime.utcnow())
                try:
                    photoFile = open(photoName, 'wb')
                    photoFile.write(captureFrame)
                    photoFile.close()
                    httpText += 'Photo saved to %s' % (photoName)
                except:
                    httpText += 'Failed to take photo!'
            else:
                httpText += 'Failed to take photo!'
            httpText += '</center></body></html>'
            self.send(httpText)                    

        elif getPath == '/':
            # Main page, click buttons to move and to stop
            httpText = '<html>\n'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function Drive(left, right) {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' var slider = document.getElementById("speed");\n'
            httpText += ' left *= speed.value / 100.0;'
            httpText += ' right *= speed.value / 100.0;'
            httpText += ' iframe.src = "/set/" + left + "/" + right;\n'
            httpText += '}\n'
            httpText += 'function Off() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/off";\n'
            httpText += '}\n'
            httpText += 'function Photo() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/photo";\n'
            httpText += '}\n'
            httpText += 'function semiAuto() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/semiAuto";\n'
            httpText += '}\n'
            httpText += 'function Auto() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/Auto";\n'
            httpText += '}\n'
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body>\n'
            httpText += '<iframe src="/stream" width="100%" height="500" frameborder="0"></iframe>\n'
            httpText += '<iframe id="setDrive" src="/off" width="100%" height="50" frameborder="0"></iframe>\n'
            httpText += '<center>\n'
            httpText += '<button onclick="Drive(-1,1)" style="width:200px;height:50px;"><b>Spin Left</b></button>\n'
            httpText += '<button onclick="Drive(1,1)" style="width:200px;height:50px;"><b>Forward</b></button>\n'
            httpText += '<button onclick="Drive(1,-1)" style="width:200px;height:50px;"><b>Spin Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="Drive(0,1)" style="width:200px;height:50px;"><b>Turn Left</b></button>\n'
            httpText += '<button onclick="Drive(-1,-1)" style="width:200px;height:50px;"><b>Reverse</b></button>\n'
            httpText += '<button onclick="Drive(1,0)" style="width:200px;height:50px;"><b>Turn Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="semiAuto(1)" style="width:200px;height:50px;"><b>Semi Auto</b></button>\n'
            httpText += '<button onclick="Off()" style="width:200px;height:50px;"><b>Stop</b></button>\n'
            httpText += '<button onclick="Auto(1)" style="width:200px;height:50px;"><b>Auto Mode</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="Photo()" style="width:200px;height:50px;"><b>Save Photo</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<input id="speed" type="range" min="0" max="100" value="50" style="width:600px" />\n'
            httpText += '</center>\n'
            httpText += '<br /><center>Distances (mm)</centre><br />\n'
            httpText += '<iframe src="/distances" width="100%" height="200" frameborder="0"></iframe>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)
            
        elif getPath == '/hold':
            # Alternate page, hold buttons to move (does not work with all devices)	
            httpText = '<html>\n'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function Drive(left, right) {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' var slider = document.getElementById("speed");\n'
            httpText += ' left *= speed.value / 100.0;'
            httpText += ' right *= speed.value / 100.0;'
            httpText += ' iframe.src = "/set/" + left + "/" + right;\n'
            httpText += '}\n'
            httpText += 'function Off() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/off";\n'
            httpText += '}\n'
            httpText += 'function Photo() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/photo";\n'
            httpText += '}\n'
            httpText += 'function semiAuto() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/semiAuto";\n'
            httpText += '}\n'
            httpText += 'function Auto() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/Auto";\n'
            httpText += '}\n'
            # key management ------------------------------------------------
            # 38=UP 40=DOWN 37=LEFT 39=RIGHT
            httpText += 'var valLeft = 0;\n'
            httpText += 'var valRight = 0;\n'
            httpText += 'function checkKey() {\n'
            httpText += 'valLeft = 0;\n'
            httpText += 'valRight = 0;\n'
            #UP
            httpText += '  if (map[38]) {\n'
            httpText += '      valLeft = 1;\n'
            httpText += '      valRight = 1;\n'
            httpText += '  }\n'
            #DOWN
            httpText += '  if (map[40]) {\n'
            httpText += '      valLeft = -1;\n'
            httpText += '      valRight = -1;\n'
            httpText += '  }\n'
            #LEFT
            httpText += '  if (map[37]) {\n'
            httpText += '      valLeft = -1;\n'
            httpText += '      valRight = 1;\n'
            httpText += '  }\n'
            #RIGHT
            httpText += '  if (map[39]) {\n'
            httpText += '      valLeft = 1;\n'
            httpText += '      valRight = -1;\n'
            httpText += '  }\n'
            #UP LEFT
            httpText += '  if (map[38] && map[37] ) {\n'
            httpText += '      valLeft = 0.1;\n'
            httpText += '      valRight = 1;\n'
            httpText += '  }\n'
            #UP RIGHT
            httpText += '  if (map[38] && map[39] ) {\n'
            httpText += '      valLeft = 1;\n'
            httpText += '      valRight = 0.1;\n'
            httpText += '  }\n'
            #UP DOWN
            httpText += '  if (map[38] && map[40] ) {\n'
            httpText += '      valLeft = 0;\n'
            httpText += '      valRight = 0;\n'
            httpText += '  }\n'
            #DOWN LEFT
            httpText += '  if (map[40] && map[37] ) {\n'
            httpText += '      valLeft = -0.1;\n'
            httpText += '      valRight = -1;\n'
            httpText += '  }\n'
            #DOWN RIGHT
            httpText += '  if (map[40] && map[39] ) {\n'
            httpText += '      valLeft = -1;\n'
            httpText += '      valRight = -0.1;\n'
            httpText += '  }\n'
            #ACTION
            httpText += '  if (valLeft == 0 && valRight == 0) {\n'
            httpText += '      Off();\n'
            httpText += '  }\n'
            httpText += '  else {\n'
            httpText += '      Drive(valLeft,valRight);\n'
            httpText += '  }\n'
            httpText += '}\n'
            httpText += 'var map = {38: false, 40: false, 37: false, 39: false};\n'
            httpText += 'onkeydown = (function(e) {\n'
            httpText += ' if (e.keyCode in map) {\n'
            httpText += '  map[e.keyCode] = true;\n'
            httpText += ' checkKey()\n'
            httpText += ' }\n'
            httpText += '})\n'
            httpText += 'onkeyup = (function(e) {\n'
            httpText += ' if (e.keyCode in map) {\n'
            httpText += '  map[e.keyCode] = false;\n'
            httpText += ' checkKey()\n'
            httpText += ' }\n'
            httpText += '});\n'
            # ---------------------------------------------------------------
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body>\n'
            httpText += '<iframe src="/stream" width="100%" height="500" frameborder="0"></iframe>\n'
            httpText += '<iframe id="setDrive" src="/off" width="100%" height="50" frameborder="0"></iframe>\n'
            httpText += '<center>\n'
            httpText += '<button onmousedown="Drive(-1,1)" onmouseup="Off()" style="width:200px;height:50px;"><b>Spin Left</b></button>\n'
            httpText += '<button onmousedown="Drive(1,1)" onmouseup="Off()" style="width:200px;height:50px;"><b>Forward</b></button>\n'
            httpText += '<button onmousedown="Drive(1,-1)" onmouseup="Off()" style="width:200px;height:50px;"><b>Spin Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onmousedown="Drive(0,1)" onmouseup="Off()" style="width:200px;height:50px;"><b>Turn Left</b></button>\n'
            httpText += '<button onmousedown="Drive(-1,-1)" onmouseup="Off()" style="width:200px;height:50px;"><b>Reverse</b></button>\n'
            httpText += '<button onmousedown="Drive(1,0)" onmouseup="Off()" style="width:200px;height:50px;"><b>Turn Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="semiAuto(1)" style="width:200px;height:50px;"><b>Semi Auto</b></button>\n'
            httpText += '<button onclick="Auto(1)" style="width:200px;height:50px;"><b>Auto Mode</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="Photo()" style="width:200px;height:50px;"><b>Save Photo</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<input id="speed" type="range" min="0" max="100" value="50" style="width:600px" />\n'
            httpText += '</center>\n'
            httpText += '<br /><center>Distances (mm)</centre><br />\n'
            httpText += '<iframe src="/distances" width="100%" height="200" frameborder="0"></iframe>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)
			
        elif getPath == '/touch':
            # Alternate page, touch hold buttons to move (does not work with all devices)
            httpText = '<html>\n'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function Drive(left, right) {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' var slider = document.getElementById("speed");\n'
            httpText += ' left *= speed.value / 100.0;'
            httpText += ' right *= speed.value / 100.0;'
            httpText += ' iframe.src = "/set/" + left + "/" + right;\n'
            httpText += '}\n'
            httpText += 'function Off() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/off";\n'
            httpText += '}\n'
            httpText += 'function Photo() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/photo";\n'
            httpText += '}\n'
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body>\n'
            httpText += '<iframe src="/stream" width="100%" height="500" frameborder="0"></iframe>\n'
            httpText += '<iframe id="setDrive" src="/off" width="100%" height="50" frameborder="0"></iframe>\n'
            httpText += '<center>\n'
            httpText += '<button ontouchstart="Drive(-1,1)" ontouchend="Off()" style="width:200px;height:100px;"><b>Spin Left</b></button>\n'
            httpText += '<button ontouchstart="Drive(1,1)" ontouchend="Off()" style="width:200px;height:100px;"><b>Forward</b></button>\n'
            httpText += '<button ontouchstart="Drive(1,-1)" ontouchend="Off()" style="width:200px;height:100px;"><b>Spin Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button ontouchstart="Drive(0,1)" ontouchend="Off()" style="width:200px;height:100px;"><b>Turn Left</b></button>\n'
            httpText += '<button ontouchstart="Drive(-1,-1)" ontouchend="Off()" style="width:200px;height:100px;"><b>Reverse</b></button>\n'
            httpText += '<button ontouchstart="Drive(1,0)" ontouchend="Off()" style="width:200px;height:100px;"><b>Turn Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="Photo()" style="width:200px;height:100px;"><b>Save Photo</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<input id="speed" type="range" min="0" max="100" value="100" style="width:600px" />\n'
            httpText += '</center>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)	
			
        elif getPath == '/stream':
            # Streaming frame, set a delayed refresh
            displayDelay = int(1000 / displayRate)
            httpText = '<html>\n'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function refreshImage() {\n'
            httpText += ' if (!document.images) return;\n'
            httpText += ' document.images["rpicam"].src = "cam.jpg?" + Math.random();\n'
            httpText += ' setTimeout("refreshImage()", %d);\n' % (displayDelay)
            httpText += '}\n'
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body onLoad="setTimeout(\'refreshImage()\', %d)">\n' % (displayDelay)
            httpText += '<center><img src="/cam.jpg" style="width:640;height:480;" name="rpicam" /></center>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)
            
        elif getPath == '/distances':
            # Repeated reading of the ultrasonic distances, set a delayed refresh
            # We use AJAX to avoid screen refreshes caused by refreshing a frame
            displayDelay = int(1000 / displayRate)
            httpText = '<html>\n'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function readDistances() {\n'
            httpText += ' var xmlhttp;\n'
            httpText += ' if (window.XMLHttpRequest) {\n'
            httpText += '  // code for IE7+, Firefox, Chrome, Opera, Safari\n'
            httpText += '  xmlhttp = new XMLHttpRequest();\n'
            httpText += ' } else {\n'
            httpText += '  // code for IE6, IE5\n'
            httpText += '  xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");\n'
            httpText += ' }\n'
            httpText += ' xmlhttp.onreadystatechange = function() {\n'
            httpText += '  var div = document.getElementById("readDistances");\n'
            httpText += '  var DONE = 4;\n'
            httpText += '  var OK = 200;\n'
            httpText += '  if (xmlhttp.readyState == DONE) {\n'
            httpText += '   if (xmlhttp.status == OK) {\n'
            httpText += '    div.innerHTML = xmlhttp.responseText;\n'
            httpText += '   } else {\n'
            httpText += '    div.innerHTML = "<center>Failed reading distances (not running?)</center>";\n'
            httpText += '   }\n'
            httpText += '  }\n'
            httpText += ' }\n'
            httpText += ' xmlhttp.open("GET","distances-once",true);\n'
            httpText += ' xmlhttp.send();\n'
            httpText += ' setTimeout("readDistances()", %d);\n' % (displayDelay)
            httpText += '}\n'
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body>\n'
            httpText += '<body onLoad="setTimeout(\'readDistances()\', %d)">\n' % (displayDelay)
            httpText += '<div id="readDistances"><center>Waiting for first distance reading...</center></div>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)

        else:
            # Unexpected page
            self.send('Path : "%s"' % (getPath))

    def send(self, content):
        self.request.sendall('HTTP/1.0 200 OK\n\n%s' % (content))


# Create the image buffer frame
lastFrame = None
lockFrame = threading.Lock()

# Startup sequence
print 'Setup camera'
camera = picamera.PiCamera()
camera.resolution = (imageWidth, imageHeight)
camera.framerate = frameRate

print 'Setup the stream processing thread'
processor = StreamProcessor()

print 'Wait ...'
time.sleep(2)
captureThread = ImageCapture()

print 'Setup the watchdog'
watchdog = Watchdog()

print 'Setup the automatic movement'
autoMovement = AutoMovement()

# Run the web server until we are told to close
try:
    httpServer = None
    httpServer = SocketServer.TCPServer(("0.0.0.0", webPort), WebServer)
except:
    # Failed to open the port, report common issues
    print
    print 'Failed to open port %d' % (webPort)
    print 'Make sure you are running the script with sudo permissions'
    print 'Other problems include running another script with the same port'
    print 'If the script was just working recently try waiting a minute first'
    print
    # Flag the script to exit
    running = False
try:
    print 'Press CTRL+C to terminate the web-server'
    while running:
        httpServer.handle_request()
except KeyboardInterrupt:
    # CTRL+C exit
    print '\nUser shutdown'
finally:
    # Turn the motors off under all scenarios
    PBR.MotorsOff()
    print 'Motors off'
# Tell each thread to stop, and wait for them to end
running = False
captureThread.join()
processor.terminated = True
watchdog.terminated = True
autoMovement.terminated = True
processor.join()
watchdog.join()
autoMovement.join()
del camera
PBR.SetLed(True)
print 'Web-server terminated.'
