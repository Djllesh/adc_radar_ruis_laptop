#!/usr/bin/env python3



import serial
import math

class Arduino( object ):
    def __init__(self, port ):
        self.com = serial.Serial( port, 115200, timeout = 1.0 )
    
    # Two SMA connectors, 16bit differential, both are configured to ±2.048V range
    def read_adc( self, channel ):
        msg = "read adc%i\n" % channel 

        self.com.write( bytes( msg, "utf-8" ) )

        response = self.com.readline()
        return float( response ) * 1e-3
    
    # Supply voltage monitoring, ch0 = 15V, ch1 = 12V, ch2 = 5V
    def read_vmon( self, channel ):
        msg = "read vmon%i\n" % channel 
        self.com.write( bytes( msg, "utf-8" ) )
        response = self.com.readline()
        return float( response )

    # IO pins, ch0 = sync pulse, ch1 = free, ch2 = RF relay
    def set_io( self, channel, state ):
        msg = "set io%i %i\n"

        if state:
            msg = msg % (channel, 1)
        else:
            msg = msg % (channel, 0)
        
        self.com.write( bytes( msg, "utf-8" ) )
    
    # Period is in microseconds
    def set_sync_period( self, period ):
        msg = "set sync_period %i\n" % period
        self.com.write( bytes( msg, "utf-8" ) )

    def read_sync_period( self ):
        msg = "read sync_period\n" 
        self.com.write( bytes( msg, "utf-8" ) )
        response = self.com.readline()
        return int( response )


    # Convinience function, set sync pulse frequency (in Hz)
    def set_sync_frequency( self, freq ):
        period = int( 1e6 / freq )
        self.set_sync_period( period )


    # Convinience function, set RF relay state
    def set_rf_relay( self, state ):
        self.set_io( 2, state )
    
    # Return measured power in dBm
    def read_rf_power( self ):
        voltage = self.read_adc( 1 )

        try:
            power = 10*math.log10( -voltage/0.5 )
        except ValueError:
            power = -100
        
        return power


