#!/usr/bin/env python

import serial
import struct
from typing import Tuple

__version__ = '1.0.0'

OP_ERROR = 0x7f

OP_WRITE = 0x01
OP_READ = 0x02


OP_I2C_MEM_W = 0x19
OP_I2C_MEM_R = 0x20

OP_SET_RELAY = 0x09
OP_GET_INPUTS = 0x10

OP_DDS_READ	= 0x11
OP_DDS_WRITE = 0x12
OP_DDS_RESET = 0x13

OP_GET_TEMPERATURE = 0x14

### Params


PARAM_EXT_CLOCK_DIVIDER =    (1)
PARAM_CAMERA_CLOCK_DIVIDER = (2)
PARAM_TRIGGER_SELECT =       (3)
PARAM_FIRMWARE_VER =         (4)
PARAM_INT_TRIGGER_PERIOD =   (5)

# Functions to encode messages

def gen_write_msg( addr: int, key: int, value: int ) -> bytes:
	return struct.pack( ">BBIi", addr, OP_WRITE, key, value )

def gen_write_float_msg( addr: int, key: int, value: float ) -> bytes:
	return struct.pack( ">BBIf", addr, OP_WRITE, key, value )

def gen_read_msg( addr: int, key: int) -> bytes:
	return struct.pack( ">BBIi", addr, OP_READ, key, 0 )

def gen_action_msg( addr: int, action: int, key: int, value: int ) -> bytes:
	return struct.pack( ">BBII", addr, action, key, value )

def gen_action_msg_float( addr: int, action: int, key: int, value: int ) -> bytes:
	return struct.pack( ">BBIf", addr, action, key, value )


def gen_action_msg( addr: int, action: int, key: int, value: int ) -> bytes:
	return struct.pack( ">BBII", addr, action, key, value )

def	gen_dds_action_msg( addr: int, action: int, key: int, value: int ) -> bytes:
	return struct.pack( ">BBI", addr, action, key ) + struct.pack( "<I", value)
	

def gen_action_msg_mem( addr: int, action: int, key: int, value: int ) -> bytes:
	return struct.pack( ">BBII", addr, action, key, value )

def gen_action_msg_mem_float( addr: int, action: int, key: int, value: int ) -> bytes:
	return struct.pack( ">BBIf", addr, action, key, value )


# Functions to decode message

def decode_error( msg: bytes ) -> Tuple[int, int]:
	(addr, op, error, extra) = struct.unpack( ">BBIi", msg )
	return error, extra

def decode_read( msg: bytes ) -> Tuple[int, int]:
	(addr, op, key, value) = struct.unpack( ">BBIi", msg )
	return key, value

def decode_read_float( msg: bytes ) -> Tuple[int, float]:
	(addr, op, key, value) = struct.unpack( ">BBIf", msg )
	return key, value

def decode_action( msg: bytes ) -> Tuple[int, int]:
	(addr, op, key, value) = struct.unpack( ">BBIi", msg )
	return key, value

def decode_dds_action( msg: bytes ) -> Tuple[int, int]:
	(addr, op, key, value) = struct.unpack( "<BBII", msg )
	return key, value


def decode_action_mem( msg: bytes ) -> Tuple[int, int]:
	(addr, op, key, value) = struct.unpack( ">BBII", msg )
	return key, value

def decode_action_mem_float( msg: bytes ) -> Tuple[int, float]:
	(addr, op, key, value) = struct.unpack( ">BBIf", msg )
	return key, value


def decode_header( msg: bytes ) -> Tuple[int, int]:
	(addr, op) = struct.unpack_from( ">BB", msg )
	
	return addr, op 

def decode_measure( msg: bytes ) -> Tuple[float, float]:
	(addr, op, voltage, current) = struct.unpack( ">BBff", msg )
	return voltage, current





class HousekeepingBoard( object ):
	def __init__( self, com: object) -> None:
		self.com = com
		self.address = 1
	

	def _clear_buffer( self ) -> None:
		if self.com.in_waiting > 0:
			self.com.read( self.com.in_waiting )

	def write( self, key: int, value: int ) -> None:
		self._clear_buffer()

		self.com.write( gen_write_msg( self.address, int(key), int(value) ) )
		response = self.com.read( 10 )
		addr, op = decode_header( response )
		if op == OP_ERROR:
			raise IndexError

	def write_float( self, key: int, value: float ) -> None:
		self._clear_buffer()
		
		self.com.write( gen_write_float_msg( self.address, int(key), value ) )
		response = self.com.read( 10 )
		addr, op = decode_header( response )
		if op == OP_ERROR:
			raise IndexError



	def read( self, key: int ) -> int:
		self._clear_buffer()
		
		self.com.write( gen_read_msg( self.address, int( key ) ) )
		response = self.com.read( 10 )
		
		addr, op = decode_header( response )
		if op == OP_ERROR:
			raise IndexError
		
		key, value = decode_read( response )
		return value

	def read_float( self, key: int ) -> float:
		self._clear_buffer()
		
		self.com.write( gen_read_msg( self.address, int( key ) ) )
		response = self.com.read( 10 )
		
		addr, op = decode_header( response )
		if op == OP_ERROR:
			raise IndexError
		
		key, value = decode_read_float( response )
		return value

	def mem_write( self, addr: int, value: int ) -> int:
		self._clear_buffer()
		
		self.com.write( gen_action_msg_mem( self.address, OP_I2C_MEM_W, addr, value ) )
		response = self.com.read( 10 )
		key, value = decode_action( response )
		return value 
	
	def mem_read( self, addr: int ) -> int:
		self._clear_buffer()
		
		self.com.write( gen_action_msg( self.address, OP_I2C_MEM_R, addr, 0 ) )
		response = self.com.read( 10 )
		key, value = decode_action_mem( response )
		return value 


	def mem_write_float( self, addr: int, value: float ) -> float:
		self._clear_buffer()
		
		self.com.write( gen_action_msg_mem_float( self.address, OP_I2C_MEM_W, addr, value ) )
		response = self.com.read( 10 )
		key, value = decode_action( response )
		return value 
	
	def mem_read_float( self, addr: int ) -> float:
		self._clear_buffer()
		
		self.com.write( gen_action_msg( self.address, OP_I2C_MEM_R, addr, 0 ) )
		response = self.com.read( 10 )
		key, value = decode_action_mem_float( response )
		return value 


	def get_temperature( self ) -> float:
		self._clear_buffer()
		
		self.com.write( gen_action_msg_float( self.address, OP_GET_TEMPERATURE, 0, 0 ) )
		response = self.com.read( 10 )
		key, value = decode_action( response )
		temp = value / 256.0
		return temp
	
	def get_inputs( self ) -> Tuple[int, int]:
		self._clear_buffer()
		
		self.com.write( gen_action_msg( self.address, OP_GET_INPUTS, 0, 0 ) )
		response = self.com.read( 10 )
		key, value = decode_action( response )
		return key, value

	def set_relay( self, key: int, value: int ) -> None:
		self._clear_buffer()

		self.com.write( gen_action_msg( self.address, OP_SET_RELAY, int(key), int(value) ) )
		response = self.com.read( 10 )
		addr, op = decode_header( response )
		if op == OP_ERROR:
			raise IndexError

	def dds_read( self, key: int ) -> int:
		self._clear_buffer()

		self.com.write( gen_action_msg( self.address, OP_DDS_READ, int(key), 0 ) )
		response = self.com.read( 10 )
		addr, op = decode_header( response )
		if op == OP_ERROR:
			raise IndexError
		_, value = decode_dds_action( response )
		return value

	def dds_write( self, key: int, value: int ) -> None:
		self._clear_buffer()

		self.com.write( gen_dds_action_msg( self.address, OP_DDS_WRITE, int(key), int(value) ) )
		response = self.com.read( 10 )
		addr, op = decode_header( response )
		if op == OP_ERROR:
			raise IndexError

	def dds_reset( self ) -> None:
		self._clear_buffer()

		self.com.write( gen_dds_action_msg( self.address, OP_DDS_RESET, 0, 0 ) )
		response = self.com.read( 10 )
		addr, op = decode_header( response )
		if op == OP_ERROR:
			raise IndexError
