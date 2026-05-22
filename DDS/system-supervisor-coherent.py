#!/usr/bin/env python3


import tkinter as tki
import tkinter.ttk as ttk

import tkinter.filedialog
import tkinter.messagebox

from PIL import Image, ImageTk

import time


import ctypes


import os
import pymsgbox

import serial

from threading import Thread

import subprocess

from multiprocessing import shared_memory


import numpy as np


import libs.Config


# Create shared memory blocks for radar time-domain data and viscam frames
#shm_viscam = shared_memory.SharedMemory(name = "milliscan-shm-2", create=True, size=256*256+100)
samplesPerBuffer =  1792
shm_alazar = shared_memory.SharedMemory(name = "milliscan-shm-1", create=True, size=64000)


shm_meta_alazar = np.ndarray((16,), dtype=np.uint32, buffer=shm_alazar.buf )


os.system("title MilliScan Supervisor")

PROCESS_TABLE = {}

PROCESS_TABLE["Alazartech"] = {"running": True, "path": ["python", r"C:\Users\taylorz1\OneDrive - Aalto University\Zach_Samu_Data_Dump\Run DDS\DDS\read-alazartech-coherent.py"]}
PROCESS_TABLE["Plotting"] = {"running": False, "path": ["python", r"C:\Users\taylorz1\OneDrive - Aalto University\Zach_Samu_Data_Dump\Run DDS\DDS\plot-alazar-stream-coherent.py"]}
#PROCESS_TABLE["Viscam"] = {"running": True, "path": ["py", r"C:\src\MilliScanSoftware\DDS\Development\Python\basler-view.py"]}
PROCESS_TABLE["Neural net"] = {"running": False, "path": ["python", r"C:\Users\taylorz1\OneDrive - Aalto University\Zach_Samu_Data_Dump\Run DDS\DNN\neuro-streaming-ui-coherent.py"]}
PROCESS_TABLE["Doppler"] = {"running": False, "path": ["python", r"C:\Users\taylorz1\OneDrive - Aalto University\Zach_Samu_Data_Dump\Run DDS\DDS\plot-doppler-coherent.py"]}



def run_process( pid ):
    global PROCESS_TABLE
    
    while True:
        while PROCESS_TABLE[pid]["running"]:
            subprocess.run( PROCESS_TABLE[pid]["path"], shell=True )
            if PROCESS_TABLE[pid]["running"]:
                pymsgbox.alert(title = "Restarting", text = "Restarting '%s'" % pid )
        time.sleep(1)


def run_singleshot_process( path ):
    subprocess.run( ["python"] + [path] , shell=True)



# Make all camera windows map pixels 1:1 to screen resolution
awareness = ctypes.c_int()
errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
#print( "Process DPI awareness:", awareness.value)
errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)




class App( object ):
    def __init__(self, root):
        self.root = root
        
        self.config = libs.Config.Config()


        self.root.option_add( "*Font", "B612" )
        self.root.title("MilliScan System Supervisor")
        self.mainmenubar = tki.Menu(self.root)
        self.root.config(menu=self.mainmenubar)

        self.filemenu = tki.Menu(self.mainmenubar, tearoff=0)
        self.filemenu.add_command(label="Exit", command=self.handle_shutdown)
        self.mainmenubar.add_cascade(label="File",menu=self.filemenu)


        self.actionmenu = tki.Menu( self.mainmenubar, tearoff=0)

        
        self.settingsmenu = tki.Menu( self.mainmenubar, tearoff=0)

        


        self.mainmenubar.add_cascade(label="Action",menu=self.actionmenu)
        self.mainmenubar.add_cascade(label="Settings",menu=self.settingsmenu)

        self.frame = tki.Frame( self.root )
        self.frame.pack()

        logo = Image.open("assets/milliscan.png")
        #logo = logo.resize((122,52), Image.ANTIALIAS)
        logo_render = ImageTk.PhotoImage(logo)

        img = tki.Label(self.frame, image=logo_render)
        img.image = logo_render
        img.pack(padx = 10, pady = 10 )
        
        self.onoff_frame = tki.LabelFrame( self.frame, text="Software control" )
        self.btn0 = tki.Button( self.onoff_frame, text= "Start plotting", command=self.handle_plotting )
        self.btn0.grid( row = 0, column = 0, padx = 5, pady = 5)
        self.btn1 = tki.Button( self.onoff_frame, text= "Start neural net", command=self.handle_neuralnet )
        self.btn1.grid( row = 0, column = 1, padx = 5, pady = 5)
        self.btn5 = tki.Button( self.onoff_frame, text= "Start Doppler", command=self.handle_doppler)
        self.btn5.grid( row = 0, column = 2, padx = 5, pady = 5)
        
        self.btn2 = tki.Button( self.onoff_frame, text= "Run DDS UI", command=self.handle_run_dds_ui )
        self.btn2.grid( row = 1, column = 0, padx = 5, pady = 5)
        
        self.btn3 = tki.Button( self.onoff_frame, text= "Run Spectrum analyzer UI", command=self.handle_run_speccis_ui )
        self.btn3.grid( row = 1, column = 1, padx = 5, pady = 5)
        
        self.btn4 = tki.Button( self.onoff_frame, text= "Run Power meter UI", command=self.handle_run_powermeter_ui )
        self.btn4.grid( row = 1, column = 2, padx = 5, pady = 5)
        

        self.onoff_frame.pack( padx = 10, pady = 10, expand="yes", fill = "both" )


        self.statusframe = tki.LabelFrame( self.frame, text = "System status" )
        


        self.statusframe.pack( padx = 10, pady = 10, expand="yes", fill = "both" )


        


        for key in PROCESS_TABLE:
            th = Thread( target = run_process, args=(key,), daemon=True)
            th.start()



        
        self.root.protocol( "WM_DELETE_WINDOW", self.handle_shutdown )
        self.bias_error_flag = True



    def handle_shutdown( self ):
        self.root.quit()

    
    def handle_plotting( self ):
        global PROCESS_TABLE
        if PROCESS_TABLE["Plotting"]["running"]:
            shm_meta_alazar[1] = 0 # Flag alazar plotting process to shutdown
            PROCESS_TABLE["Plotting"]["running"] = False
            self.btn0.config(text = "Start plotting")
        else:
            shm_meta_alazar[1] = 1 # Flag alazar plotting process to keep running
            PROCESS_TABLE["Plotting"]["running"] = True
            self.btn0.config(text = "Stop plotting")

    def handle_neuralnet( self ):
        global PROCESS_TABLE
        if PROCESS_TABLE["Neural net"]["running"]:
            PROCESS_TABLE["Neural net"]["running"] = False
            self.btn1.config(text = "Start neural net")
        else:
            PROCESS_TABLE["Neural net"]["running"] = True
            self.btn1.config(text = "Stop neural net")

    def handle_doppler( self ):
        global PROCESS_TABLE
        if PROCESS_TABLE["Doppler"]["running"]:
            shm_meta_alazar[1] = 0 # Flag Doppler plotting process to shutdown
            PROCESS_TABLE["Doppler"]["running"] = False
            self.btn5.config(text = "Start Doppler")
        else:
            shm_meta_alazar[1] = 1 # Flag Doppler plotting process to shutdown
            PROCESS_TABLE["Doppler"]["running"] = True
            self.btn5.config(text = "Stop Doppler")

    def handle_run_dds_ui(self):
        th = Thread( target = run_singleshot_process, args=(r"C:\Users\taylorz1\OneDrive - Aalto University\Zach_Samu_Data_Dump\Run DDS\DDS\dds-ui-coherent.py",), daemon=True)
        th.start()

    def handle_run_speccis_ui(self):
        th = Thread( target = run_singleshot_process, args=(r"C:\Users\taylorz1\OneDrive - Aalto University\Zach_Samu_Data_Dump\Run DDS\DDS\speccis-ui.py",), daemon=True)
        th.start()
        
    def handle_run_powermeter_ui(self):
        th = Thread( target = run_singleshot_process, args=(r"C:\Users\taylorz1\OneDrive - Aalto University\Zach_Samu_Data_Dump\Run DDS\DDS\tehomittari-ui.py",), daemon=True)
        th.start()


root = tki.Tk()
app = App( root )

root.mainloop()


import signal

os.kill(os.getpid(), signal.CTRL_C_EVENT  )


