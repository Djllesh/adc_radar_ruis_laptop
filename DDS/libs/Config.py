#!/usr/bin/env python3

import redis

class Config( object ):
	def __init__( self ):
		self.r = redis.Redis( host = "127.0.0.1")
	

	@property
	def camera_threshold( self ):
		value = self.r.get( "camera_threshold" )
		return float( value )
	
	@camera_threshold.setter
	def camera_threshold( self, value ):
		self.r.set( "camera_threshold", "%.6f" % value  )


	@property
	def vmon_5v_limit( self ):
		value = self.r.get( "vmon_5v_limit" )
		return float( value )
	
	@vmon_5v_limit.setter
	def vmon_5v_limit( self, value ):
		self.r.set( "vmon_5v_limit", "%.6f" % value  )

	@property
	def vmon_12v_limit( self ):
		value = self.r.get( "vmon_12v_limit" )
		return float( value )
	
	@vmon_12v_limit.setter
	def vmon_12v_limit( self, value ):
		self.r.set( "vmon_12v_limit", "%.6f" % value  )

	@property
	def vmon_15v_limit( self ):
		value = self.r.get( "vmon_15v_limit" )
		return float( value )
	
	@vmon_15v_limit.setter
	def vmon_15v_limit( self, value ):
		self.r.set( "vmon_15v_limit", "%.6f" % value  )


	@property
	def sync_freq( self ):
		value = self.r.get( "sync_freq" )
		return float( value )

	@sync_freq.setter
	def sync_freq( self, value ):
		self.r.set( "sync_freq", "%.3f" % value  )

