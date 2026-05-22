#!/usr/bin/env python3


import tkinter as tki
import tkinter.ttk as ttk


from PIL import Image, ImageTk

import time

import libs.DDS2
import libs.libHousekeeping

import ctypes

# Make all camera windows map pixels 1:1 to screen resolution
awareness = ctypes.c_int()
errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
#print( "Process DPI awareness:", awareness.value)
errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)




class App( object ):
    def __init__(self, root):
        self.root = root

        self.root.option_add( "*Font", "B612" )
        self.root.title("MilliScan DDS Controller")
        self.mainmenubar = tki.Menu(self.root)
        self.root.config(menu=self.mainmenubar)

        self.filemenu = tki.Menu(self.mainmenubar, tearoff=0)
        self.filemenu.add_command(label="Exit", command=self.root.quit)
        self.mainmenubar.add_cascade(label="File",menu=self.filemenu)

        self.actionmenu = tki.Menu( self.mainmenubar, tearoff=0)
        self.actionmenu.add_command(label = "Init DDS", command=self.handle_init_dds )
        self.actionmenu.add_command(label = "Get Temp", command=self.get_temp)
        self.actionmenu.add_command(label = "Read", command=self.read)
        self.mainmenubar.add_cascade(label="Action",menu=self.actionmenu)


        self.root.configure( bg = 'black' )

        self.frame = tki.Frame( self.root )
        self.frame.pack()

        self.frame.configure( bg = 'black'  )
        logo = Image.open("assets/dds-logo.png")
        #logo = logo.resize((122,52), Image.ANTIALIAS)
        logo_render = ImageTk.PhotoImage(logo)

        img = tki.Label(self.frame, image=logo_render, bg = 'black')
        img.image = logo_render
        img.pack(padx = 10, pady = 10 )
        
        self.onoff_frame = tki.LabelFrame( self.frame, text="DDS output control", fg = "white", bg = "black" )
        self.onoff_frame.pack( padx = 10, pady = 10, expand="yes", fill = "both" )
        self.btn0 = tki.Button( self.onoff_frame, text= "Power on", bg="#F920FB", command=self.handle_power_on )
        self.btn0.grid( row = 0, column = 0, padx = 5, pady = 5)
        self.btn1 = tki.Button( self.onoff_frame, text= "Power off", fg="white", bg="#2669F4", command=self.handle_power_off )
        self.btn1.grid( row = 0, column = 1, padx = 5, pady = 5)

        self.cw_frame = tki.LabelFrame( self.frame, text="DDS CW control", fg = "white", bg = "black" )
        self.cw_frame.pack( padx = 10, pady = 10, expand="yes", fill = "both" )
        tki.Label( self.cw_frame, text = "Frequency [MHz]:", fg = "white", bg = "black").grid( row = 0, column = 0, padx = 5, pady = 5 )
        self.cw_tone_var = tki.StringVar( self.root )
        self.cw_tone_entry = tki.Entry( self.cw_frame, textvariable=self.cw_tone_var)
        self.cw_tone_entry.grid( row = 0, column = 1, padx = 5, pady = 5 )
        self.btn2 = tki.Button( self.cw_frame, text = "Set", bg="#F920FB", command=self.set_single_tone )
        self.btn2.grid( row = 0, column=2, padx = 5, pady = 5 )


        self.sweep_frame = tki.LabelFrame( self.frame, text="DDS sweep control", fg = "white", bg = "black" )
        self.sweep_frame.pack( padx = 10, pady = 10, expand="yes", fill = "both" )

        self.div_frame = tki.LabelFrame( self.frame, text="Housekeeping board trigger control", fg = "white", bg = "black" )
        self.div_frame.pack( padx = 10, pady = 10, expand="yes", fill = "both" )
        
        tki.Label( self.sweep_frame, text = "Start freq. [MHz]:", fg = "white", bg = "black").grid( row = 0, column = 0, padx = 5, pady = 5, sticky="e" )
        
        self.start_freq_var = tki.StringVar( self.root )
        self.start_freq_entry = tki.Entry( self.sweep_frame, textvariable=self.start_freq_var)
        self.start_freq_entry.grid( row = 0, column = 1, padx = 5, pady = 5, sticky="w" )
        self.start_freq_var.set( "901.25")
        
        tki.Label( self.sweep_frame, text = "Stop freq. [MHz]:", fg = "white", bg = "black").grid( row = 0, column = 2, padx = 5, pady = 5, sticky="e" )
        
        self.stop_freq_var = tki.StringVar( self.root )
        self.stop_freq_entry = tki.Entry( self.sweep_frame, textvariable=self.stop_freq_var)
        self.stop_freq_entry.grid( row = 0, column = 3, padx = 5, pady = 5, sticky="w"  )
        self.stop_freq_var.set( "1370" )

        tki.Label( self.sweep_frame, text = "Chirp rate [GHz / s]:", fg = "white", bg = "black").grid( row = 1, column = 0, padx = 5, pady = 5, sticky="e" )
        
        self.chirp_rate_var = tki.StringVar( self.root )
        self.chirp_rate_entry = tki.Entry( self.sweep_frame, textvariable=self.chirp_rate_var)
        self.chirp_rate_entry.grid( row = 1, column = 1, padx = 5, pady = 5, sticky="w"  )
        self.chirp_rate_var.set("20000")

        tki.Label( self.sweep_frame, text = "Chirp mode:", fg = "white", bg = "black").grid( row = 1, column = 2, padx = 5, pady = 5, sticky="e" )
        
        self.chirp_mode = ttk.Combobox(self.sweep_frame, values = ["Continuous", "Burst"], width=18 )
        self.chirp_mode.grid( row = 1, column = 3, padx = 5, pady = 5, sticky="w" )
        self.chirp_mode.current(0)
        self.chirp_mode.bind("<<ComboboxSelected>>", self.chirp_mode_handle )


        tki.Label( self.sweep_frame, text = "Trigger mode:", fg = "white", bg = "black").grid( row = 2, column = 0, padx = 5, pady = 5, sticky="e" )
        
        self.trigger_mode = ttk.Combobox(self.sweep_frame, values = ["Internal", "External"], width=18 )
        self.trigger_mode.grid( row = 2, column = 1, padx = 5, pady = 5, sticky="w" )
        self.trigger_mode.current(1)

        tki.Label( self.sweep_frame, text = "Burst duration [s]:", fg = "white", bg = "black").grid( row = 2, column = 2, padx = 5, pady = 5, sticky="e" )
        
        self.burst_duration_var = tki.StringVar( self.root )
        self.burst_duration_entry = tki.Entry( self.sweep_frame, textvariable=self.burst_duration_var)
        self.burst_duration_entry.grid( row = 2, column = 3, padx = 5, pady = 5, sticky="w"  )
        self.burst_duration_entry.configure(state = "disabled")
        


        self.btn3 = tki.Button( self.sweep_frame, text = "Start sweep", bg="#F920FB", command=self.set_ramp )
        self.btn3.grid( row = 3, column=3, padx = 10, pady = 10 )

        # divider selections

        tki.Label( self.div_frame, text = "Select trigger source:", fg = "white", bg = "black").grid( row = 0, column = 0, padx = 5, pady = 5, sticky="e" )
        
        self.clk_source = ttk.Combobox(self.div_frame, values = ["Internal CLK", "External CLK"], width=12 )
        self.clk_source.grid( row = 0, column = 1, padx = 5, pady = 5, sticky="w" )
        self.clk_source.current(1)
        self.clk_source.bind("<<ComboboxSelected>>", self.clk_source_handle )

        tki.Label( self.div_frame, text = "Int CLK freq. [Hz]:", fg = "white", bg = "black").grid( row = 1, column = 2, padx = 5, pady = 5, sticky="e" )
        
        self.int_clk_freq = tki.StringVar( self.root )
        self.int_clk_freq_entry = tki.Entry( self.div_frame, textvariable=self.int_clk_freq, width=12)
        self.int_clk_freq_entry.grid( row = 1, column = 3, padx = 5, pady = 5, sticky="w" )
        self.int_clk_freq.set( "40")
        self.btn3 = tki.Button( self.div_frame, text = "Set", bg="#F920FB", command=self.set_int_clk_freq )
        self.btn3.grid( row = 1, column=4, padx = 5, pady = 5 )

        tki.Label( self.div_frame, text = "Ext CLK freq. [MHz]:", fg = "white", bg = "black").grid( row = 1, column = 0, padx = 5, pady = 5, sticky="e" )
        
        self.ext_clk_freq = tki.StringVar( self.root )
        self.ext_clk_freq_entry = tki.Entry( self.div_frame, textvariable=self.ext_clk_freq, width=12)
        self.ext_clk_freq_entry.grid( row = 1, column = 1, padx = 5, pady = 5, sticky="w" )
        self.ext_clk_freq.set( "9.11458333")

        tki.Label( self.div_frame, text = "Trigger divider:", fg = "white", bg = "black").grid( row = 2, column = 0, padx = 5, pady = 5, sticky="e" )
        
        self.trig_div = ttk.Combobox(self.div_frame, values = ["x32", "x64", "x128", "x256", "x512", "x1024", "x2048", "x4096"], width=10 )
        self.trig_div.grid( row = 2, column = 1, padx = 5, pady = 5, sticky="w" )
        self.trig_div.current(3)
        self.trig_div.bind("<<ComboboxSelected>>", self.trig_div_handle )


        tki.Label( self.div_frame, text = "Camera divider:", fg = "white", bg = "black").grid( row = 3, column = 0, padx = 5, pady = 5, sticky="e" )
        
        self.cam_div = ttk.Combobox(self.div_frame, values = ["x4", "x8", "x16", "x32", "x64", "x128", "x256", "x512"], width=10 )
        self.cam_div.grid( row = 3, column = 1, padx = 5, pady = 5, sticky="w" )
        self.cam_div.current(6)
        self.cam_div.bind("<<ComboboxSelected>>", self.cam_div_handle )


        self.dds = libs.DDS2.DDS( "COM4" )


        self.root.protocol( "WM_DELETE_WINDOW", self.handle_shutdown )

    def handle_shutdown( self ):
        #self.handle_power_off()
        self.root.quit()

    def get_temp(self):
        temp = self.dds.board.get_temperature()
        print("Housekeeping board temperature:", temp)

    def read(self):
        self.dds.board.write(3,1) # ext clock enable = 1, disable = 0
        self.dds.board.write(1,3) # set ext clock division state ----> 0 = x32, 1 = x64, 2 = x128, 3 = x256, 4 = x512, 5 = 1024
        self.dds.board.write(2,0) # set cam clock division state ----> 0 = x4, 1 = x8, 2 = x16, 3 = x32, 4 = x64, 5 = x128, 6 = x256, 7 = x512
        val1 = self.dds.board.read(1)
        val2 = self.dds.board.read(2)
        val3 = self.dds.board.read(3)
        val4 = self.dds.board.read(4)
        val5 = self.dds.board.read(5)
        print("Ext clock division ratio:", 2**(5+val1))
        print("Cam clock division ratio:", 2**(2+val2))
        print("Ext clock enabled:", val3)
        print("Firmware version:", val4)
        print("Int trigger period (us):", val5)

        
    def handle_power_off( self ):
        self.dds.powerdown()

    def handle_power_on( self ):
        self.dds.powerup()
    
    def handle_init_dds( self ):
        self.dds.powerdown()
        self.dds.reset()
        self.dds.powerup()
        self.dds.reset()

        self.dds.calibrate_dac()
        time.sleep(1)
        self.dds.tmp()

    def set_single_tone( self ):
        freq = float( self.cw_tone_var.get().replace(",", "." ) )

        self.dds.single_tone( freq )
        #self.dds.update()

    def set_ramp( self ):
        start_freq = float( self.start_freq_var.get().replace(",", "." ) )
        stop_freq = float( self.stop_freq_var.get().replace(",", "." ) )
        chirp_rate = float( self.chirp_rate_var.get().replace(",", "." ) )
        
        try:
            burst_duration = float( self.burst_duration_var.get().replace(",", "." ) )
        except ValueError:
            burst_duration = 1

        flags = 0
        if self.trigger_mode.get() == "Internal":
            flags = libs.DDS2.DRG_NO_DWELL_HIGH |  libs.DDS2.DRG_NO_DWELL_LOW
        
        if self.chirp_mode.get() == "Continuous":
            period = (stop_freq-start_freq)/(1000*chirp_rate) * 1e6
            print( "PERIOD:", period)
            flags = libs.DDS2.DRG_NO_DWELL_HIGH
            self.dds.ramp( start_freq, stop_freq, period, flags )
            self.dds.update()
            self.dds.powerup()
        else:
            period = (stop_freq-start_freq)/(1000*chirp_rate) * 1e6
            self.dds.ramp( start_freq, stop_freq, period, flags )
            #self.dds.update()
            #self.dds.powerup()
            time.sleep( burst_duration )
            self.dds.powerdown()


    def chirp_mode_handle( self, *args ):
        if self.chirp_mode.get() == "Continuous":
            self.burst_duration_entry.configure(state = "disabled")
        else:
            self.burst_duration_entry.configure(state = "active")

    def trig_div_handle(self, *args ):
        if self.trig_div.get() == "x32":
            self.dds.board.write(1,0)
        elif self.trig_div.get() == "x64":
            self.dds.board.write(1,1)
        elif self.trig_div.get() == "x128":
            self.dds.board.write(1,2)
        elif self.trig_div.get() == "x256":
            self.dds.board.write(1,3)
        elif self.trig_div.get() == "x512":
            self.dds.board.write(1,4)
        elif self.trig_div.get() == "x1024":
            self.dds.board.write(1,5)
        elif self.trig_div.get() == "x2048":
            self.dds.board.write(1,6)
        elif self.trig_div.get() == "x4096":
            self.dds.board.write(1,7)
        div = self.dds.board.read(1)
        print("Trigger frequency division ratio:", 2**(5+div))
        tf, _ = self.calc_div_freqs()
        print("Radar trigger frequency: %.3f kHz" % tf)

    def cam_div_handle(self, *args ):
        if self.cam_div.get() == "x4":
            self.dds.board.write(2,0)
        elif self.cam_div.get() == "x8":
            self.dds.board.write(2,1)
        elif self.cam_div.get() == "x16":
            self.dds.board.write(2,2)
        elif self.cam_div.get() == "x32":
            self.dds.board.write(2,3)
        elif self.cam_div.get() == "x64":
            self.dds.board.write(2,4)
        elif self.cam_div.get() == "x128":
            self.dds.board.write(2,5)
        elif self.cam_div.get() == "x256":
            self.dds.board.write(2,6)
        elif self.cam_div.get() == "x512":
            self.dds.board.write(2,7)
        div2 = self.dds.board.read(2)
        print("Camera trigger division ratio:", 2**(2+div2))
        _, cf = self.calc_div_freqs()
        print("Camera trigger frequency: %.3f Hz" % cf)

    def calc_div_freqs(self):
        ext_clk_freq = float( self.ext_clk_freq.get().replace(",", "." ) )
        div1 = self.dds.board.read(1)
        div2 = self.dds.board.read(2)
        trig_freq = ext_clk_freq*1e3/(2**(5+div1)) # kHz
        cam_freq = trig_freq*1e3/(2**(2+div2)) # Hz
        return trig_freq, cam_freq
    
    def clk_source_handle( self, *args ):
        if self.clk_source.get() == "Internal CLK":
            self.dds.board.write(3,0)
        else:
            self.dds.board.write(3,1)
        val = self.dds.board.read(3)
        if val == 0:
            print("Triggering from internal clock")
        else:
            print("Triggering from external clock")

    def set_int_clk_freq(self):
        int_clk_freq = float( self.int_clk_freq.get().replace(",","."))
        int_clk_period_us = int((1/int_clk_freq)*1e6)
        self.dds.board.write(5,int_clk_period_us)
        val = self.dds.board.read(5)
        str = "Internal trigger period {} microseconds => {} Hz"
        #print("Internal trigger period %d microseconds => %.2f Hz" % val , (1/val)*1e6)
        print(str.format(val, (1/val)*1e6))
        if self.clk_source.get() == "Internal CLK":
            print("Int trigger ON")
        else: 
            print("Internal clock source not selected!")



root = tki.Tk()
app = App( root )

root.mainloop()
