#!/usr/bin/env python3

from unittest.mock import AsyncMagicMixin
import numpy as np
import matplotlib.pyplot as plt
from multiprocessing import shared_memory
import time

import scipy
import scipy.signal

plt.style.use('dark_background')
### Data stream ###

# How much data is coming from Alazartech
samplesPerBuffer = 1792
startSample = 25
stopSample = 1735

# Connect to shared memory for radar time-domain data
shm = shared_memory.SharedMemory(name = "milliscan-shm-1" )

# Map shared memory to their respective numpy arrays
shm_meta = np.ndarray((16,), dtype=np.uint32, buffer=shm.buf )
shm_data = np.ndarray((1, samplesPerBuffer), dtype=np.uint16, buffer=shm.buf, offset = shm_meta.nbytes)


old_cnt = -1
bitShift = 2
# Read data from shared memory and remove offset (Alazartech outputs unipolar data)
channelA = (shm_data[0, :] >> bitShift).astype( np.float32 ) - 0x2000
#channelB = shm_data[1, :].astype( np.float32 ) - 0x8000

# Select only data that is within the actual sweep, empirical range!
channelA = channelA[startSample:stopSample]

####################

### Doppler processing ###

##### Variables #########################
# Number of coherent chirps processed   #
n_CRI = 128                            #
                                        #
# Decimation factor in range dimension  #
dec = 3                                 #
#########################################

# Speed of light
c0 = 299792458

# Full radar bandwidth
BW = 30e9

# Radar center frequency
f_c = 340e9

# Radar range resolution
dR = c0/(2*BW)

# Housekeeping board EXT CLK frequency
f_hkin = 9.1145833e6

# Chirp repetition frequency (trigger frequency)
CRF = f_hkin/256

# Chirp repetition interval
CRI = 1/CRF 

# Max unambiguous velocity
v_max = c0/(4*CRI*f_c)

# Number of range bins
n_Rbin = len(channelA)

# Range axis 
rng = np.linspace(0, dR*(n_Rbin/(2*dec)), int(n_Rbin/(2*dec)+1))

# Velocity axis
vel = np.linspace(-v_max, v_max, n_CRI-1)

# Initialize frame
decHdata = np.zeros( (n_CRI-1, int(n_Rbin/dec)) )

# Initialize window functions
w_range = np.hanning(n_Rbin/dec)
w_dopp = np.hanning(n_CRI-1)

# Initialize Doppler-plot
DD_dB = np.zeros( (n_CRI-1, int(n_Rbin/(2*dec)+1)) )

# Initialize figure
fig, ax = plt.subplots()
plot_doppler = ax.pcolormesh(rng,vel,DD_dB[:-1, :-1], vmin=-100, vmax= -60, cmap='gnuplot2')
ax.set_xlabel("Range (m)")
ax.set_ylabel("Velocity (m/s)")
fig.colorbar(plot_doppler)
plt.show(block = False)
plt.grid(True, which='major')

# AlazarTech value scaling
bitsPerSample = 14
inputRange_volts = 0.1
codeZero = float((1 << (bitsPerSample - 1)) - 0.5)
codeRange = float((1 << (bitsPerSample - 1)) -0.5)

# Initialize dataframe
dataFrame = np.zeros((n_CRI-1, len(channelA)))
done = False
N = 0
# Loop over coherent chirps #
try:
    while not done:
        if shm_meta[1] == 0:
            done = True

        while N < n_CRI-1:
        # Wait until new data has been written to shared memory by Alazartech
            if shm_meta[0] != old_cnt:
                channelA = (shm_data[0, :] >> bitShift).astype( np.float32 )
                channelA = (inputRange_volts * (channelA - codeZero)/codeRange).astype(np.float32)
                dataFrame[N, :] = channelA[startSample:stopSample].copy()
                N += 1

        # Hilbert transform to each chirp to get I/Q-formatted complex data
        Hdata = scipy.signal.hilbert(dataFrame, axis=-1)

        # decimate the data in range dimension
        decHdata = scipy.signal.decimate(Hdata, dec, ftype='fir', axis=-1)

        # range processing using FFT
        rangeData = np.fft.fft(w_range*decHdata, norm = 'forward')
        rangeData = rangeData[:,0:int(np.size(rangeData,1)/2+1)]
        rangeData[:, 1:-2] = 2*rangeData[:, 1:-2]

        # Doppler processing using FFT
        DoppData = np.fft.fftshift(np.fft.fft(w_dopp*np.transpose(rangeData), norm = 'forward'),-1)
        DD_dB = 10*np.log10(np.abs(np.real(DoppData))**2 + np.abs(np.imag(DoppData))**2)
        DD_dB = np.transpose(DD_dB)

        # Update plot
        plot_doppler.update({'array': DD_dB[:-1,:-1]})
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.03)
        N = 0

except KeyboardInterrupt:
    pass

shm.close()