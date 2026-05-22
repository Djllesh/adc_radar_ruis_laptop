#!/usr/bin/env python3


import serial
import struct
import time
import math

from . import libHousekeeping

POWER_TWO_THIRTYTWO = 4294967296.0

DRG_NO_DWELL_LOW = 1
DRG_NO_DWELL_HIGH = 2
DRG_NO_DWELL = 3

DDS_CLOCK = 3500000000.0

class DDS( object ):
    def __init__( self, port ):
        self.com = serial.Serial( port, 115200, timeout = 2.0 )
        
        self.board = libHousekeeping.HousekeepingBoard( self.com )

    
    def reset( self ):
        #self.com.write( b"reset\n" )
        #response = self.com.readline()
        #return self._validate_response( response )
        self.board.dds_reset()

    
    
    def powerup( self ):
        #self.com.write( b"powerup\n" )
        #response = self.com.readline()
        #return self._validate_response( response )
        #self.board.dds_powerup()
        #self.board.dds_reset()
        pass

    def update( self ):
        pass
    
    def powerdown( self ):
        #self.com.write( b"powerdown\n" )
        #response = self.com.readline()
        #return self._validate_response( response )
        #self.board.dds_powerdown()
        self.board.dds_reset()


    def single_tone( self, frequency ):
        word = int(0.5 + 1000000.0 * frequency * POWER_TWO_THIRTYTWO / DDS_CLOCK )

        print( "word", word, "hex(word)", hex(word) )

        #import sys
        #sys.exit(1)

        #self._write_uint32( 0x00, 0x00000308 )
        
        #self._write_uint32( 0x01, 0x00800900 )
        #self._write_uint32( 0x01, 0x00800900 )
        #self._write_uint32( 0x0b, word )
        #self._write_uint32( 0x0c, 0x00000000 )
        #self._write_uint32( 0x0c, 0x01010101 )
        #self._write_uint32( 0x0c, 0xffffffff )

        print( "debug: 0x01=", hex(self.board.dds_read( 0x01 )) )
        self.board.dds_write( 0x01, 0x00800900 )
        print( "debug: 0x01=", hex(self.board.dds_read( 0x01 )) )
        self.board.dds_write( 0x0b, word )
        self.board.dds_write( 0x0c, 0x00000000 )
        
        
        
        self.set_amplitude_and_phase( 2048, 1000 )
        

        print( "reg b: 0x%08x" % self.board.dds_read( 0x0b ) ) 
        print( "reg c: 0x%08x" % self.board.dds_read( 0x0c ) ) 



        return (word*DDS_CLOCK) / ( 1000000.0 * POWER_TWO_THIRTYTWO )
    

    def set_amplitude_and_phase( self, amplitude, phase ):
        value = (int(amplitude) << 16 ) | int(phase)
        #self._write_uint32( 0x0c, value )
        self.board.dds_write( 0x0C, value )


    def tmp( self ):
        #rint( self._read_bytes( 0x01, 4 ) )
        #print( self._read_bytes( 0x0b, 4 ) )
        #print( self._read_bytes( 0x0c, 4 ) ) 
        print( "reg 0: 0x%08x" % self.board.dds_read( 0x00 ) ) 
        print( "reg 1: 0x%08x" % self.board.dds_read( 0x01 ) ) 
        print( "reg 2: 0x%08x" % self.board.dds_read( 0x02 ) ) 
        print( "reg b: 0x%08x" % self.board.dds_read( 0x0b ) ) 
        print( "reg c: 0x%08x" % self.board.dds_read( 0x0c ) ) 


    def calibrate_dac( self ):
        # dds_write_uint32(0x03, 0x01052120)
        # dds_update
        # dds_write_uint32(0x03, 0x00052120)
        # dds_update()


        #self._write_uint32( 0x03, 0x01052120 )
        #self.update()
        #time.sleep(1.0)
        #self._write_uint32( 0x03, 0x00052120 )
        #self.update()

        print( "reg 3: 0x%08x" % self.board.dds_read( 0x03 ) ) 
        self.board.dds_write( 0x03, 0x01052120 )
        print( "reg 3: 0x%08x" % self.board.dds_read( 0x03 ) ) 
        time.sleep(1.0)
        self.board.dds_write( 0x03, 0x00052120 )
        

    
    def ramp( self, start_freq, stop_freq, period, flags ):

        steps = period * DDS_CLOCK / (1000000.0 * 24.0)
        round_steps = int( math.ceil(steps) )
        bandwidth = stop_freq * round_steps / steps - start_freq

        start_word = int(0.5 + 1000000.0 * start_freq * POWER_TWO_THIRTYTWO / DDS_CLOCK)
        step_size = int(0.5 + (1000000.0 * bandwidth * POWER_TWO_THIRTYTWO / DDS_CLOCK) / round_steps)
        stop_word = int( start_word + step_size * (round_steps) )
        #low_jump = int(0.5 + 1.0 * POWER_TWO_THIRTYTWO / DDS_CLOCK) # 1 Hz
        #high_jump = int(0.5 + 1000000.0 * 1.0 * POWER_TWO_THIRTYTWO / DDS_CLOCK) # 1 MHz
        cfr2 = 0x00082900
        cfr1 = 0x00010008

        if (flags & DRG_NO_DWELL_LOW) != 0:
            cfr2 |= (1 << 17)

        if (flags & DRG_NO_DWELL_HIGH) != 0:
            cfr2 |= (1 << 18)
        
        cfr2 |= (1<<13) # DROVER output on
        cfr2 |= (1<<15) # Matched latency on
        #cfr2 |= (1<<9) # sync out on??
        
        cfr1 |= (1<<8) # osk enabled
        cfr1 |= (1<<9) # external osk enabled
        cfr1 |= (1<<14) # autoclear digital ramp accumulator
        #cfr1 |= (1<<13) # autoclear phase accumulator
        print("cfr1 = 0x%08x" % cfr1)
        

        #self._write_uint32( 0x01, cfr2 )
        #self._write_uint32( 0x04, start_word )
        #self._write_uint32( 0x05, stop_word )
        #self._write_uint32( 0x06, step_size )
        #self._write_uint32( 0x07, step_size )
        #self._write_uint16_pair( 0x08, 1, 1 )
        #self._write_uint32( 0x09, 0 )
        #self._write_uint32( 0x0a, 0 )

        self.board.dds_write( 0x00, cfr1 )
        self.board.dds_write( 0x01, cfr2 )        
        self.board.dds_write( 0x04, start_word )        
        self.board.dds_write( 0x05, stop_word )        
        self.board.dds_write( 0x06, step_size )        
        self.board.dds_write( 0x07, step_size )        
        self.board.dds_write( 0x08, 0x00010001 )        
        self.board.dds_write( 0x09, 0 )        
        self.board.dds_write( 0x0a, 0 ) 
        self.board.dds_write( 0x0C, 0x0FFF0000 )       
        print( "reg 8: 0x%08x" % self.board.dds_read( 0x08 ) ) 
        print( "reg 1: 0x%08x" % self.board.dds_read( 0x01 ) ) 
        print( "reg 0: 0x%08x" % self.board.dds_read( 0x00 ) )


        
        



