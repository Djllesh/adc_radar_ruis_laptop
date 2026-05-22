#!/usr/bin/env python3


import tkinter as tki
import tkinter.ttk as ttk

import tkinter.filedialog
import tkinter.messagebox

from PIL import Image, ImageTk

import time

import libs.DDS2

import ctypes

import pyvisa

import numpy as np

import h5py

import os

# Make all camera windows map pixels 1:1 to screen resolution
awareness = ctypes.c_int()
errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
#print( "Process DPI awareness:", awareness.value)
errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)




class App( object ):
    def __init__(self, root):
        self.root = root

        self.rm = pyvisa.ResourceManager()
        self.speccis = self.rm.open_resource( 'GPIB0::18::INSTR' )

        self.root.option_add( "*Font", "B612" )
        self.root.title("MilliScan Spectrum Analyzer Controller")
        self.mainmenubar = tki.Menu(self.root)
        self.root.config(menu=self.mainmenubar)

        self.filemenu = tki.Menu(self.mainmenubar, tearoff=0)
        self.filemenu.add_command(label="Exit", command=self.root.quit)
        self.mainmenubar.add_cascade(label="File",menu=self.filemenu)

        self.actionmenu = tki.Menu( self.mainmenubar, tearoff=0)
        self.actionmenu.add_command(label = "Init DDS", command=self.handle_init_dds )
        
        self.mainmenubar.add_cascade(label="Action",menu=self.actionmenu)



        self.frame = tki.Frame( self.root )
        self.frame.pack()

        logo = Image.open("assets/milliscan.png")
        #logo = logo.resize((122,52), Image.ANTIALIAS)
        logo_render = ImageTk.PhotoImage(logo)

        img = tki.Label(self.frame, image=logo_render)
        img.image = logo_render
        img.pack(padx = 10, pady = 10 )
        
        self.onoff_frame = tki.LabelFrame( self.frame, text="DDS output control" )
        #self.onoff_frame.pack( padx = 10, pady = 10, expand="yes", fill = "both" )
        self.btn0 = tki.Button( self.onoff_frame, text= "Power on", command=self.handle_power_on )
        self.btn0.grid( row = 0, column = 0, padx = 5, pady = 5)
        self.btn1 = tki.Button( self.onoff_frame, text= "Power off", command=self.handle_power_off )
        self.btn1.grid( row = 0, column = 1, padx = 5, pady = 5)

        
        self.sweep_frame = tki.LabelFrame( self.frame, text="Sweep control" )
        self.sweep_frame.pack( padx = 10, pady = 10, expand="yes", fill = "both" )
        
        tki.Label( self.sweep_frame, text = "Start freq. [MHz]:").grid( row = 0, column = 0, padx = 5, pady = 5, sticky="e" )
        
        self.start_freq_var = tki.StringVar( self.root )
        self.start_freq_entry = tki.Entry( self.sweep_frame, textvariable=self.start_freq_var)
        self.start_freq_entry.grid( row = 0, column = 1, padx = 5, pady = 5, sticky="w" )
        
        
        tki.Label( self.sweep_frame, text = "Stop freq. [MHz]:").grid( row = 0, column = 2, padx = 5, pady = 5, sticky="e" )
        
        self.stop_freq_var = tki.StringVar( self.root )
        self.stop_freq_entry = tki.Entry( self.sweep_frame, textvariable=self.stop_freq_var)
        self.stop_freq_entry.grid( row = 0, column = 3, padx = 5, pady = 5, sticky="w"  )
        

        tki.Label( self.sweep_frame, text = "Points [#]:").grid( row = 1, column = 0, padx = 5, pady = 5, sticky="e" )
        
        self.n_points_var = tki.StringVar( self.root )
        self.n_points_entry = tki.Entry( self.sweep_frame, textvariable=self.n_points_var)
        self.n_points_entry.grid( row = 1, column = 1, padx = 5, pady = 5, sticky="w"  )

        tki.Label( self.sweep_frame, text = "Dwell time [s]:").grid( row = 1, column = 2, padx = 5, pady = 5, sticky="e" )
        
        self.dwell_time_var = tki.StringVar( self.root )
        self.dwell_time_entry = tki.Entry( self.sweep_frame, textvariable=self.dwell_time_var)
        self.dwell_time_entry.grid( row = 1, column = 3, padx = 5, pady = 5, sticky="w"  )

        tki.Label( self.sweep_frame, text = "Output file:").grid( row = 2, column = 0, padx = 5, pady = 5, sticky="e" )

        self.output_file_var = tki.StringVar( self.root )
        self.output_file_entry = tki.Entry( self.sweep_frame, textvariable=self.output_file_var, width=40)
        self.output_file_entry.grid( row = 2, column = 1, columnspan=2, padx = 5, pady = 5, sticky="w" )

        self.btn2 = tki.Button( self.sweep_frame, text = "Select file", command=self.select_file )
        self.btn2.grid( row = 2, column = 3, padx = 5, pady = 5)


        self.btn3 = tki.Button( self.sweep_frame, text = "Start sweep", command=self.run_sweep )
        self.btn3.grid( row = 3, column=3, padx = 10, pady = 10 )


        self.progess_var = tki.StringVar( self.root )
        tki.Label( self.sweep_frame, textvariable=self.progess_var).grid( row = 3, column = 1, padx = 5, pady = 5)
        self.progess_var.set("")



        self.dds = libs.DDS2.DDS( "COM4" )


    def select_file( self ):
        fn = tki.filedialog.asksaveasfilename( filetypes = [("HDF5 file", "*.hdf5"), ("All files", "*.*")], defaultextension = ".hdf5" )
        if fn is not None:
            if len(fn) > 1:
                self.output_file_var.set( fn )
                self.output_file_entry.xview_moveto(1)

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


    def set_single_tone( self ):
        freq = float( self.cw_tone_var.get().replace(",", "." ) )

        self.dds.single_tone( freq )
        self.dds.update()

    def run_sweep( self ):
        start_freq = float( self.start_freq_var.get().replace(",", "." ) )
        stop_freq = float( self.stop_freq_var.get().replace(",", "." ) )
        n_points = int( self.n_points_var.get().replace(",", "." ) )


        fn = self.output_file_var.get()

        if os.path.exists( fn ):            
            response = tki.messagebox.askokcancel(title="File exists", message="File already exists, overwrite?" )
            if not response:
                return
        
        try:
            dwell_time = float( self.dwell_time_var.get().replace(",", "." ) )
        except:
            dwell_time = 0


        self.progess_var.set("Initialising DDS...")
        self.root.update_idletasks()
        self.handle_init_dds()        
        self.dds.single_tone( start_freq )
        self.dds.update()
        self.dds.powerup()
        time.sleep(0.25)
        
        self.progess_var.set("                    ")
        self.root.update_idletasks()
        

        dataset = None
        fn_handle = None


        for i in range( n_points ):
            q = i / ( n_points - 1)
            f = start_freq*(1-q) + stop_freq*(q)

            self.progess_var.set("Progress: %i / %i" %(i+1, n_points))
            self.root.update_idletasks()
        

            self.dds.single_tone( f )
            self.dds.update()
            self.dds.powerup()
        
            time.sleep( dwell_time )

            sp_centre_freq = float( self.speccis.query("CF?;").strip() )
            sp_freq_span = float( self.speccis.query("SP?;").strip() )

            trace = self.speccis.query("TDF P;TRA?")
            values = [float(p) for p in trace.split(",")]
            
            
            freqs = np.linspace(sp_centre_freq - sp_freq_span/2, sp_centre_freq + sp_freq_span/2, len(values) )


            if len(fn) > 0:
                if dataset is None:
                    fn_handle =  h5py.File(fn, "w")
                    dataset = fn_handle.create_dataset("spectra", (n_points, 2, len(values)), dtype='f')
                
                dataset[i, 0, :] = freqs
                dataset[i, 1, :] = values
            


            #print( freqs )
            #print( values )
        self.dds.powerdown()

        # Closing file
        del fn_handle

        self.progess_var.set("Done.")




        






root = tki.Tk()
app = App( root )

root.mainloop()
