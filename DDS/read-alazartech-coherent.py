#!/usr/bin/env python3
# read-alazartech-coherent.py, unified with read-alazartech-incoherent.py on PC for comparison measurements, 20240129, SVP

from __future__ import division
import ctypes
import numpy as np
import os
import signal
import sys
import time
from multiprocessing import shared_memory

import libs.atsapi as ats

# Sample rate, is filled later 
samplesPerSec = None


samplesPerBuffer =  1792 # buffer size is equal to the amount of points sampled in each chirp

# Connect to shared memory for time-domain radar data
shm = shared_memory.SharedMemory(name = "milliscan-shm-1")

# Map shared memory to their respective numpy arrays

shm_meta = np.ndarray((16,), dtype=np.uint32, buffer=shm.buf ) # Metadata

shm_data = np.ndarray((1, samplesPerBuffer), dtype=np.uint16, buffer=shm.buf, offset = shm_meta.nbytes) # Actual contents
shm_meta[0] = 0 # Set buffer counter to zero


# Configures a board for acquisition
def ConfigureBoard(board):

    global samplesPerSec
    samplesPerSec = 3.5e9/48

    
    # COHERENT RADAR USES EXTERNAL CLOCK
    board.setCaptureClock(ats.FAST_EXTERNAL_CLOCK,
                          ats.SAMPLE_RATE_USER_DEF,
                          ats.CLOCK_EDGE_RISING,
                          0)
    
    # Select channel A input parameters as required.
    board.inputControlEx(ats.CHANNEL_A,
                         ats.AC_COUPLING,
                         ats.INPUT_RANGE_PM_100_MV,
                         ats.IMPEDANCE_50_OHM)
    
    # Select channel A bandwidth limit as required.
    board.setBWLimit(ats.CHANNEL_A, 0)
    
    
    # Select channel B input parameters as required.
    board.inputControlEx(ats.CHANNEL_B,
                         ats.DC_COUPLING,
                         ats.INPUT_RANGE_PM_4_V,
                         ats.IMPEDANCE_50_OHM)
    
    # Select channel B bandwidth limit as required.
    board.setBWLimit(ats.CHANNEL_B, 0)
    
    # Select trigger inputs and levels as required.
    board.setTriggerOperation(ats.TRIG_ENGINE_OP_J,
                              ats.TRIG_ENGINE_J,
                              ats.TRIG_EXTERNAL,
                              ats.TRIGGER_SLOPE_POSITIVE,
                              240,
                              ats.TRIG_ENGINE_K,
                              ats.TRIG_DISABLE,
                              ats.TRIGGER_SLOPE_POSITIVE,
                              128)

    # Select external trigger parameters as required.
    board.setExternalTrigger(ats.DC_COUPLING, ats.ETR_2V5)

    # Set trigger delay as required.
    triggerDelay_sec = 0
    triggerDelay_samples = int(triggerDelay_sec * samplesPerSec + 0.5)
    board.setTriggerDelay(triggerDelay_samples)

    # Set trigger timeout as required.
    board.setTriggerTimeOut(0)

    # Configure AUX I/O connector as required
    board.configureAuxIO(ats.AUX_OUT_TRIGGER,
                         0)
    

def AcquireData(board):
    global shm_meta, shm_data
    # Select the total acquisition length in seconds
    acquisitionLength_sec = 1 
    
    # Select the active channels.
    channels = ats.CHANNEL_A
    channelCount = 0
    for c in ats.channels:
        channelCount += (c & channels == c)
    print("Number of channels: ",channelCount)

    # Compute the number of bytes per record and per buffer
    memorySize_samples, bitsPerSample = board.getChannelInfo()
    bytesPerSample = (bitsPerSample.value + 7) // 8
    bytesPerBuffer = bytesPerSample * samplesPerBuffer * channelCount
    # Calculate the number of buffers in the acquisition
    samplesPerAcquisition = int(samplesPerSec * acquisitionLength_sec + 0.5);
    buffersPerAcquisition = ((samplesPerAcquisition + samplesPerBuffer - 1) //
                             samplesPerBuffer)

    bufferCount = 16

    # debug
    print("bitsPerSample", bitsPerSample)
    print("bytesPerSample:", bytesPerSample)
    print("bytesPerBuffer:", bytesPerBuffer)
    print("samplesPerAcquisition:", samplesPerAcquisition)
    print("buffersPerAcquisition:", buffersPerAcquisition)

    # Allocate DMA buffers

    sample_type = ctypes.c_uint8
    if bytesPerSample > 1:
        sample_type = ctypes.c_uint16

    buffers = []
    for i in range(bufferCount):
        buffers.append(ats.DMABuffer(board.handle, sample_type, bytesPerBuffer))
    

    board.setRecordSize(0, samplesPerBuffer)


    board.beforeAsyncRead(channels,
                          0,                 # Must be 0
                          samplesPerBuffer,
                          1,                 # Must be 1
                          0x7FFFFFFF,        # Ignored
                          ats.ADMA_EXTERNAL_STARTCAPTURE | ats.ADMA_NPT )#ats.ADMA_TRIGGERED_STREAMING )
    


    # Post DMA buffers to board
    for buffer in buffers:
        print("buffer size:",buffer.size_bytes)
        board.postAsyncBuffer(buffer.addr, buffer.size_bytes)

    start = time.time() # Keep track of when acquisition started
    try:
        board.startCapture() # Start the acquisition
        print("Capturing %d buffers. Press <enter> to abort" %
              buffersPerAcquisition)
        buffersCompleted = 0
        bytesTransferred = 0
        while True:
            # Wait for the buffer at the head of the list of available
            # buffers to be filled by the board.
            buffer = buffers[buffersCompleted % len(buffers)]
            try:
                board.waitAsyncBufferComplete(buffer.addr, timeout_ms=5000)
                buffersCompleted += 1
                bytesTransferred += buffer.size_bytes

                # Read channel A from the data stream
                tmp = buffer.buffer.copy()
                channelA = tmp[:len(tmp)//1]
                
                # Write them to shared memory
                shm_data[0, :] = channelA
                shm_meta[0] += 1 # Update buffer counter to signal others that the data has been updated

                # Add the buffer to the end of the list of available buffers.
                board.postAsyncBuffer(buffer.addr, buffer.size_bytes)
            except Exception as err:
                print( err )
    finally:
        board.abortAsyncRead()
        # Compute the total transfer time, and display performance information.
        transferTime_sec = time.time() - start
        print("Capture completed in %f sec" % transferTime_sec)
        buffersPerSec = 0
        bytesPerSec = 0
        if transferTime_sec > 0:
            buffersPerSec = buffersCompleted / transferTime_sec
            bytesPerSec = bytesTransferred / transferTime_sec
        print("Captured %d buffers (%f buffers per sec)" %
            (buffersCompleted, buffersPerSec))
        print("Transferred %d bytes (%f bytes per sec)" %
            (bytesTransferred, bytesPerSec))

if __name__ == "__main__":
    board = ats.Board(systemId = 1, boardId = 1)

    #th = Thread( target = plotter_thread, args = (1, ) )
    #th.daemon = True
    #th.start()


    ConfigureBoard(board)
    try:
        AcquireData(board)
    except KeyboardInterrupt:
        pass
    finally:
        shm.close()
        shm.unlink()