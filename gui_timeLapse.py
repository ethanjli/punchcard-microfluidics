import tkinter as tk
import datetime
from picamera import PiCamera
#from scipy import misc


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        #self.pack()
        self.grid()
        self.create_widgets()

    ### define methods ###
    def toggle_LED(self,tog=[0]):
        tog[0] = not tog[0]
        if tog[0]:
            self.btn_LED.config(relief='sunken')
            ledON();
        else:
            self.btn_LED.config(relief='raised')
            ledOFF();

    def toggle_laser(self,tog=[0]):
        tog[0] = not tog[0]
        if tog[0]:
            self.btn_laser.config(relief='sunken')
            laserON();
        else:
            self.btn_laser.config(relief='raised')
            laserOFF();

    def toggle_bf(self,tog=[0]):
        tog[0] = not tog[0]
        if tog[0]:
            laserOFF();
            self.btn_laser.config(relief='raised')
            self.btn_fluorescence.config(relief='raised')
            self.var_ss.set(self.var_ss_bf.get())
            self.btn_LED.config(relief='sunken')
            self.btn_bf.config(relief='sunken')
            ledON();
        else:
            self.btn_LED.config(relief='raised')
            self.btn_bf.config(relief='raised')
            ledOFF();

    def toggle_fluorescence(self,tog=[0]):
        tog[0] = not tog[0]
        if tog[0]:
            ledOFF();
            self.btn_LED.config(relief='raised')
            self.btn_bf.config(relief='raised')
            self.var_ss.set(self.var_ss_fluorescence.get())
            self.btn_laser.config(relief='sunken')
            self.btn_fluorescence.config(relief='sunken')
            laserON();
        else:
            self.btn_laser.config(relief='raised')
            self.btn_fluorescence.config(relief='raised')
            laserOFF();

    ### create widgets ###
    def create_widgets(self):        

        # x #
        self.label_x = tk.Label(self,text='x')
        self.entry_x_step = tk.Entry(self,width = 5)
        self.entry_x_delay = tk.Entry(self,width = 5)
        self.entry_x_step.insert(0,"512")
        self.entry_x_delay.insert(0,"0.001")
        self.btn_x_forward = tk.Button(self, text="Forward",
                              command=lambda:x_move('f',int(self.entry_x_step.get()),float(self.entry_x_delay.get())))
        self.btn_x_backward = tk.Button(self, text="Backward",
                              command=lambda:x_move('b',int(self.entry_x_step.get()),float(self.entry_x_delay.get())))

        # y #
        self.label_y = tk.Label(self,text='y')
        self.entry_y_step = tk.Entry(self,width = 5)
        self.entry_y_delay = tk.Entry(self,width = 5)
        self.entry_y_step.insert(0,"512")
        self.entry_y_delay.insert(0,"0.001")
        self.btn_y_forward = tk.Button(self, text="Forward",
                              command=lambda:y_move('f',int(self.entry_y_step.get()),float(self.entry_y_delay.get())))
        self.btn_y_backward = tk.Button(self, text="Backward",
                              command=lambda:y_move('b',int(self.entry_y_step.get()),float(self.entry_y_delay.get())))

        # z #
        self.label_z = tk.Label(self,text='z')
        self.entry_z_step = tk.Entry(self,width = 5)
        self.entry_z_delay = tk.Entry(self,width = 5)
        self.entry_z_step.insert(0,"32")
        self.entry_z_delay.insert(0,"0.001")
        self.btn_z_forward = tk.Button(self, text="Forward",
                              command=lambda:z_move('f',int(self.entry_z_step.get()),float(self.entry_z_delay.get())))
        self.btn_z_backward = tk.Button(self, text="Backward",
                              command=lambda:z_move('b',int(self.entry_z_step.get()),float(self.entry_z_delay.get())))

        
        # quit
        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=root.destroy)
        self.label_x.grid(row=1,column=0)
        self.entry_x_step.grid(row=1,column=1)
        self.entry_x_delay.grid(row=1,column=2)
        self.btn_x_forward.grid(row=1,column=3)
        self.btn_x_backward.grid(row=1,column=4)
        
        self.label_y.grid(row=2,column=0)
        self.entry_y_step.grid(row=2,column=1)
        self.entry_y_delay.grid(row=2,column=2)
        self.btn_y_forward.grid(row=2,column=3)
        self.btn_y_backward.grid(row=2,column=4)
        
        self.label_z.grid(row=3,column=0)
        self.entry_z_step.grid(row=3,column=1)
        self.entry_z_delay.grid(row=3,column=2)
        self.btn_z_forward.grid(row=3,column=3)
        self.btn_z_backward.grid(row=3,column=4)

        # seperation
        self.label_seperator = tk.Label(self,text='  ')
        self.label_seperator.grid(row=4,column=0)
        
        # shutter speed
        self.label_ss = tk.Label(self,text='SS (ms)')
        self.var_ss = tk.StringVar()
        self.var_ss.trace("w", lambda name, index, mode, var_ss=self.var_ss:ss_update(var_ss))
        self.entry_ss = tk.Entry(self,width = 6,textvariable=self.var_ss)
        self.entry_ss.insert(0,"2")
        self.label_ss.grid(row=5,column=0,sticky=tk.W)
        self.entry_ss.grid(row=5,column=1,sticky=tk.W)

        # LED and laser
        self.btn_LED = tk.Button(self, text="LED", fg="black",
                              command=self.toggle_LED)
        self.btn_laser = tk.Button(self, text="laser", fg="blue",
                              command=self.toggle_laser)
        self.btn_LED.grid(row=5,column=3)
        self.btn_laser.grid(row=5,column=4)

        # seperation
        self.label_seperator = tk.Label(self,text='  ')
        self.label_seperator.grid(row=6,column=0)

        # preset modes - bf
        self.label_ss_bf = tk.Label(self,text='SS (ms)')
        self.var_ss_bf = tk.StringVar()
        self.var_ss_bf.trace("w", lambda name, index, mode, var_ss=self.var_ss:ss_update(var_ss))
        self.entry_ss_bf = tk.Entry(self,width = 6,textvariable=self.var_ss_bf)
        self.entry_ss_bf.insert(0,"2")
        self.btn_bf = tk.Button(self, text="Bright Field", fg="black",
                              command=self.toggle_bf)
        self.label_ss_bf.grid(row=7,column=0,sticky=tk.W)
        self.entry_ss_bf.grid(row=7,column=1,sticky=tk.W)
        self.btn_bf.grid(row=7,column=3,columnspan=2)

        # preset modes - fluorescence
        self.label_ss_fluorescence = tk.Label(self,text='SS (ms)')
        self.var_ss_fluorescence = tk.StringVar()
        self.var_ss_fluorescence.trace("w", lambda name, index, mode, var_ss=self.var_ss:ss_update(var_ss))
        self.entry_ss_fluorescence = tk.Entry(self,width = 6,textvariable=self.var_ss_fluorescence)
        self.entry_ss_fluorescence.insert(0,"200")
        self.btn_fluorescence = tk.Button(self, text="Fluorescence", fg="black",
                              command=self.toggle_fluorescence)
        self.label_ss_fluorescence.grid(row=8,column=0,sticky=tk.W)
        self.entry_ss_fluorescence.grid(row=8,column=1,sticky=tk.W)
        self.btn_fluorescence.grid(row=8,column=3,columnspan=2)

        # seperation
        self.label_seperator = tk.Label(self,text='  ')
        self.label_seperator.grid(row=9,column=0)
        
        # zoom
        self.label_zoom = tk.Label(self,text='Zoom')
        self.scale_zoom = tk.Scale(self,from_=1, to = 10,
                                  resolution=1,
                                  orient=tk.HORIZONTAL,
                                  length = 275,
                                  command=lambda value:setROI(float(value)))
        self.scale_zoom.set(1)
        self.label_zoom.grid(row=10,column=0,sticky=tk.W)
        self.scale_zoom.grid(row=10,column=1,columnspan=4,sticky=tk.W)

        # seperation
        self.label_seperator = tk.Label(self,text='  ')
        self.label_seperator.grid(row=11,column=0)

        # autofocus
        self.label_N = tk.Label(self,text='N')
        self.entry_N = tk.Entry(self,width = 5)
        self.label_step = tk.Label(self,text='step')
        self.entry_step = tk.Entry(self,width = 5)
        self.btn_autoFocus = tk.Button(self, text="Autofocus", fg="black",
                                     command=lambda:autofocus(int(self.entry_N.get()),
                                                            int(self.entry_step.get())))
        self.entry_N.insert(0,'15')
        self.entry_step.insert(0,'16')                                                      
        self.label_N.grid(row=12,column=0,sticky=tk.W)
        self.entry_N.grid(row=12,column=1,sticky=tk.W)
        self.label_step.grid(row=12,column=2,sticky=tk.W)
        self.entry_step.grid(row=12,column=3,sticky=tk.W)
        self.btn_autoFocus.grid(row=12,column=4,sticky=tk.W)

        # seperation
        self.label_seperator = tk.Label(self,text='  ')
        self.label_seperator.grid(row=13,column=0)

        # filename
        self.label_filename = tk.Label(self,text='Prefix')
        self.entry_filename = tk.Entry(self,width = 31)
        
        self.label_filename.grid(row=14,column=0,sticky=tk.W)
        self.entry_filename.grid(row=14,column=1,columnspan=4,sticky=tk.W)

        # capture
        self.btn_capture = tk.Button(self, text="Capture", fg="black", bg = "yellow",
                                     width = 32, height = 2,
                                     command=lambda:capture(self.entry_filename.get(),
                                                            self.entry_ss.get(),
                                                            self.scale_zoom.get()))
        self.btn_capture.grid(row=15,column=0,columnspan=5,rowspan=2)

### LED, stepper control ###
import RPi.GPIO as GPIO
from time import sleep
import time

# pin def
ledPIN = 19
laserPIN = 26
x_stepPin = 23
x_dirPin = 24
x_enablePin = 27
y_stepPin = 14
y_dirPin = 15
y_enablePin = 3

z_stepPin = 16
z_dirPin = 20

def initDriver():
	GPIO.setmode(GPIO.BCM)  # set board mode to Broadcom
	
	GPIO.setup(ledPIN, GPIO.OUT)
	GPIO.setup(laserPIN, GPIO.OUT)
	
	GPIO.setup(x_stepPin, GPIO.OUT)
	GPIO.setup(x_dirPin, GPIO.OUT)
	GPIO.setup(x_enablePin, GPIO.OUT)
	GPIO.setup(y_stepPin, GPIO.OUT)
	GPIO.setup(y_dirPin, GPIO.OUT)
	GPIO.setup(y_enablePin, GPIO.OUT)
	GPIO.setup(z_stepPin, GPIO.OUT)
	GPIO.setup(z_dirPin, GPIO.OUT)

	
	
def ledON():
	GPIO.output(ledPIN,1)

def ledOFF():
	GPIO.output(ledPIN,0)

def laserON():
	GPIO.output(laserPIN,1)

def laserOFF():
	GPIO.output(laserPIN,0)

def x_move(direction,steps,dt):
    if 'f' == direction:
        GPIO.output(x_dirPin, 0)
    else:
        GPIO.output(x_dirPin, 1)
    GPIO.output(x_enablePin, 0)
    for i in range(steps):
        GPIO.output(x_stepPin,0)
        sleep(dt/2)
        GPIO.output(x_stepPin,1)
        sleep(dt/2)
    GPIO.output(x_enablePin, 1)
		
def y_move(direction,steps,dt):
    if 'f' == direction:
        GPIO.output(y_dirPin, 0)
    else:
        GPIO.output(y_dirPin, 1)
    GPIO.output(y_enablePin, 0)
    for i in range(steps):
        GPIO.output(y_stepPin,0)
        sleep(dt/2)
        GPIO.output(y_stepPin,1)
        sleep(dt/2)
    GPIO.output(y_enablePin, 1)
		
def z_move(direction,steps,dt):
    if 'f' == direction:
        GPIO.output(z_dirPin, 0)
    else:
        GPIO.output(z_dirPin, 1)
    for i in range(steps):
        GPIO.output(z_stepPin,0)
        sleep(dt/2)
        GPIO.output(z_stepPin,1)
        sleep(dt/2)

# camera control

def setROI(zoom):
  x_start = 0.5 - 1/(2*zoom)
  y_start = 0.5 - 1/(2*zoom)
  width = 1/zoom
  height = 1/zoom
  print(1/zoom)
  camera.zoom = (x_start,y_start,width,height)

def ss_update(var_ss):
  tmp = var_ss.get()
  if tmp == '':
    print(0)
  else:
    ss = int(float(tmp)*1000)
    framerate_current = camera.framerate
    framerate_new = int(1000000/float(ss))  
    camera.framerate = min(framerate_new,30)
    camera.shutter_speed = ss

def capture(prefix,ss,zoom):
  filename = (prefix +
        '_' + str(int(zoom)) + 'x' +
        '_' + str(ss) + 'us' +
        '_' + '{:%Y-%m-%d %H-%M-%S-%f}'.format(datetime.datetime.now())[:-3]
              )
  print(filename)
  camera.resolution = (3280, 2464)
  camera.capture(filename + '.jpeg')

# import matplotlib.pyplot as plt

def autofocus(N,step):
  FM = [0]*N
  use_video_port = True
  splitter_port=0
  resize=None
  dt = 0.003
  FM_max = 0
  j = 0
  
  # start_time = time.time()
  prefix = 'Z autofocus, 1080p'

  timestamp = time.time()
  camera.resolution = '1920x1080'
  for i in range(N):
    j = j + 1
    # actuate
    z_move('f',step,0.001)
    sleep(0.005)
    img = np.empty((1920 * 1088 * 3,), dtype=np.uint8)
    #camera.capture(img,'rgb',use_video_port=True)
    ledON();
    camera.capture(img,'rgb',use_video_port=False)
    sleep(0.005)
    ledOFF();
    # img = misc.imread(filename)
    img = img.reshape(1088,1920,3)
    ROI = img[540-256+1:540+256,960-256+1:960+256,1]
    lap = laplace(ROI)
    fm = mean(square(lap))
    print(fm)
    FM[i] = fm
    #filename = prefix + '_bf_' + str(0).zfill(2) + '_' + str(i).zfill(2) + '_' + str(0).zfill(2) + '.png' 
    #misc.imsave(filename,img)
    FM_max = max(fm,FM_max)
    if fm < FM_max*0.85:
      break

  print('time:')
  print(time.time()-timestamp)
  idx = FM.index(max(FM))
  print(idx)
  # plt.plot(FM)
  z_move('b',step*j,dt)
  z_move('f',step*(idx+1),dt)
  camera.resolution = '1920x1080'
  ledON();
#======================================================================#
#======================================================================#
#======================================================================#

# init.
initDriver()
#ledOFF();
#laserOFF();

# set up camera
camera = PiCamera(resolution='3280x2464',sensor_mode=2,framerate=15)
# camera = PiCamera(resolution='1920x1080',sensor_mode=2,framerate=15)
# camera = PiCamera(resolution='1920x1080',sensor_mode=1,framerate = 30)
camera.iso = 60
camera.exposure_mode = 'off'
camera.shutter_speed = 500
camera.awb_mode = 'off'
camera.awb_gains = (2,1)
camera.start_preview(resolution=(1640, 1232),fullscreen=False, window=(800, 0, 820, 616))

# create GUI
root = tk.Tk()
app = Application(master=root)
app.mainloop()

# exit routine
GPIO.cleanup()
