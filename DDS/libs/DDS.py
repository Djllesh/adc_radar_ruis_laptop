#!/usr/bin/env python3


import serial
import struct
import time
import math

POWER_TWO_THIRTYTWO = 4294967296.0

DRG_NO_DWELL_LOW = 1
DRG_NO_DWELL_HIGH = 2
DRG_NO_DWELL = 3

DDS_CLOCK = 3500000000.0

class DDS( object ):
    def __init__( self, port ):
        self.com = serial.Serial( port, 125000, timeout = 2.0 )
        
    
    def _validate_response( self, msg ):
        print( "debug, msg:", msg )
        if b"okay" in msg:
            return True
        return False

    def hello( self ):
        self.com.write( b"hello\n" )
        response = self.com.read( 5 )
        return self._validate_response( response )

    def _write_bytes( self, address, count, data ):
        msg = "write,%02x,%x," % (address, count )
        for i in range( count ):
            msg += "%02x" % data[i]

        msg += "\n"
        print( "debug, ->msg", repr(msg), "len(msg)=", len(msg))
        msg = bytes( msg, "utf-8")
        if len(msg) < 20:
            msg = msg + b"\0" * (20- len(msg))
        print( "debug, len(msg)", len(msg))
        self.com.write( msg )
        response = self.com.read( 5 )
        return self._validate_response( response )


    def _write_uint8( self, address, param ):
        return self._write_bytes( address, 1, [param])
    
    def _write_uint16( self, address, param):
        return self._write_bytes( address, 2, struct.pack(">H", param ))

    def _write_uint16_pair( self, address, param0, param1):
        return self._write_bytes( address, 4, struct.pack(">HH", param0, param1 ))

    def _write_uint32( self, address, param):
        print( "write uint32, param:", hex(param), "in bytes", [hex(x) for x in struct.pack("<I", param )])

        return self._write_bytes( address, 4, struct.pack(">I", param ))

    def _write_uint32_pair( self, address, param0, param1):
        return self._write_bytes( address, 8, struct.pack(">II", param0, param1 ))
    
    def _write_uint64( self, address, param):
        return self._write_bytes( address, 8, struct.pack(">Q", param ))

    
    def _read_bytes( self, address, count ):
        msg = "read,%02x,%x\n" % (address, count)
        msg = bytes( msg, "utf-8" )
        self.com.write( msg )
        response = self.com.readline()
        response = str( response, "utf-8" ).strip()
        if "error" in response:
            return False
        
        print( "response", response)
        return [int("0x" + response[i:i+2], 16) for i in range( 0, len(response), 2)]

    def _read_uint8( self, address ):
        return self._read_bytes( address, 1)[0]
        
    def _read_uint16( self, address ):
        data = self._read_bytes( address, 2)
        return (data[0] << 8) + data[1]
    
    def _read_uint32( self, address ):
        data = self._read_bytes( address, 4)
        return (data[0] << 24) + (data[1] << 16) + (data[2] << 8) + data[3]


    def reset( self ):
        self.com.write( b"reset\n" )
        response = self.com.readline()
        return self._validate_response( response )
    
    def update( self ):
        self.com.write( b"update\n" )
        response = self.com.readline()
        print("update!")
        return self._validate_response( response )

    def powerup( self ):
        self.com.write( b"powerup\n" )
        response = self.com.readline()
        return self._validate_response( response )

    def powerdown( self ):
        self.com.write( b"powerdown\n" )
        response = self.com.readline()
        return self._validate_response( response )


    def single_tone( self, frequency ):
        word = int(0.5 + 1000000.0 * frequency * POWER_TWO_THIRTYTWO / DDS_CLOCK )

        print( "word", word, "hex(word)", hex(word) )

        #import sys
        #sys.exit(1)

        #self._write_uint32( 0x00, 0x00000308 )
        
        #self._write_uint32( 0x01, 0x00800900 )
        self._write_uint32( 0x01, 0x00800900 )
        self._write_uint32( 0x0b, word )
        self._write_uint32( 0x0c, 0x00000000 )
        #self._write_uint32( 0x0c, 0x01010101 )
        #self._write_uint32( 0x0c, 0xffffffff )

        self.set_amplitude_and_phase( 2048, 1000 )
        

        return (word*DDS_CLOCK) / ( 1000000.0 * POWER_TWO_THIRTYTWO )
    

    def set_amplitude_and_phase( self, amplitude, phase ):
        value = (int(amplitude) << 16 ) | int(phase)
        self._write_uint32( 0x0c, value )
        

    def tmp( self ):
        #rint( self._read_bytes( 0x01, 4 ) )
        #print( self._read_bytes( 0x0b, 4 ) )
        #print( self._read_bytes( 0x0c, 4 ) ) 
        print( "reg 0:", self._read_bytes( 0x0, 4 ) ) 
        print( "reg 1:", self._read_bytes( 0x1, 4 ) ) 
        print( "reg 2:", self._read_bytes( 0x2, 4 ) ) 
        print( "reg b:", self._read_bytes( 0x0b, 4 ) ) 
        print( "reg c:", self._read_bytes( 0x0c, 4 ) ) 


    def calibrate_dac( self ):
        # dds_write_uint32(0x03, 0x01052120)
        # dds_update
        # dds_write_uint32(0x03, 0x00052120)
        # dds_update()

        self._write_uint32( 0x03, 0x01052120 )
        self.update()
        time.sleep(1.0)
        self._write_uint32( 0x03, 0x00052120 )
        self.update()
    
    def ramp( self, start_freq, stop_freq, period, flags ):

        steps = period * DDS_CLOCK / (1000000.0 * 24.0)
        round_steps = int( math.ceil(steps) )
        bandwidth = stop_freq * round_steps / steps - start_freq

        start_word = int(0.5 + 1000000.0 * start_freq * POWER_TWO_THIRTYTWO / DDS_CLOCK)
        step_size = int(0.5 + (1000000.0 * bandwidth * POWER_TWO_THIRTYTWO / DDS_CLOCK) / round_steps)
        stop_word = int( start_word + step_size * (round_steps) )
        cfr2 = 0x00082900

        if (flags & DRG_NO_DWELL_LOW) != 0:
            cfr2 |= (1 << 17)

        if (flags & DRG_NO_DWELL_HIGH) != 0:
            cfr2 |= (1 << 18)
        
        cfr2 |= (1<<13)

        self._write_uint32( 0x01, cfr2 )
        self._write_uint32( 0x04, start_word )
        self._write_uint32( 0x05, stop_word )
        self._write_uint32( 0x06, step_size )
        self._write_uint32( 0x07, step_size )
        self._write_uint16_pair( 0x08, 1, 1 )
        self._write_uint32( 0x09, 0 )
        self._write_uint32( 0x0a, 0 )
        

        



