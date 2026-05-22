#!/usr/bin/env python3


from re import T
import sys
import numpy as np

import matplotlib.pyplot as plt
from multiprocessing import shared_memory
import time

import cv2, math
import scipy
import scipy.signal

plt.style.use('dark_background')
######################### Synthwave colour palette ####################################
def color_palette_map_synth( value ):
    colours = [(140,30,255), (242,34,255), (255,41,117), (255,144,31), (255,211,25)]
    q = value/255.0

    z = q * (len(colours)-1)
    idx0 = int(math.floor(z))
    p = z - idx0

    c0 = colours[idx0]
    if idx0 < len(colours) - 1:
        c1 = colours[idx0+1]
    else:
        c1 = colours[idx0]
    
    r = c0[0] * (1-p) + c1[0]*p
    g = c0[1] * (1-p) + c1[1]*p
    b = c0[2] * (1-p) + c1[2]*p
    return np.uint8((b,g,r))

# Map values to palette
def map_row( row ):
    out = np.zeros((row.shape[0], 3), dtype=np.uint8)
    for i in range( row.shape[0]):
        out[i, :] = color_palette_map( row[i] )
    return out

# Standard grayscale colour palette
def color_palette_map_normal( value ):
    colours = [(0,0,0), (255,255,255)]
    q = value/255.0

    z = q * (len(colours)-1)
    idx0 = int(math.floor(z))
    p = z - idx0

    c0 = colours[idx0]
    if idx0 < len(colours) - 1:
        c1 = colours[idx0+1]
    else:
        c1 = colours[idx0]
    
    r = c0[0] * (1-p) + c1[0]*p
    g = c0[1] * (1-p) + c1[1]*p
    b = c0[2] * (1-p) + c1[2]*p
    return np.uint8((b,g,r))
####################################################################################


# How much data is coming from Alazartech
samplesPerBuffer = 1792

# Sampling frequency:
f_samp = 3.5e9/48

# Select the signal from the data
startSample = 25
stopSample = 1735
Nsamples = stopSample-startSample

# Highpass IIR filter
filtteri = scipy.signal.iirdesign( wp = 0.02, ws = 0.01, gpass = 1.0, gstop = 30.0, output = 'sos')


# Initialise waterfall chart
#waterfall_chart = np.zeros( (1000, 856, 3), dtype = np.uint8 )

# Connect to shared memory for radar time-domain data
shm = shared_memory.SharedMemory(name = "milliscan-shm-1" )

# Map shared memory to their respective numpy arrays
shm_meta = np.ndarray((16,), dtype=np.uint32, buffer=shm.buf )
shm_data = np.ndarray((1, samplesPerBuffer), dtype=np.uint16, buffer=shm.buf, offset = shm_meta.nbytes)

# Parameters for the voltage conversion
old_cnt = -1
bitShift = 2
bitsPerSample = 14
inputRange_volts = 0.1 # same as in read-alazartech-coherent.py!

# Read data from shared memory (Alazartech outputs unipolar data)
channelA = (shm_data[0, :] >> bitShift).astype(np.float32)

# Convert samples to volts
codeZero = float((1 << (bitsPerSample - 1)) - 0.5)
codeRange = float((1 << (bitsPerSample - 1)) -0.5)
channelA = (inputRange_volts * (channelA - codeZero)/codeRange).astype(np.float32)

# First frame as offset..
#static_channelA = channelA.copy()

# Which is then removed from signal
#channelA -= static_channelA

# Select only data that is within the actual sweep, empirical range!
channelA = channelA[startSample:stopSample]

# Time domain window
#window = np.hanning(len(channelA))
window = scipy.signal.windows.tukey(len(channelA ), 0.25)

# Create time axis for the time-domain signal
X = np.linspace( 0, len(channelA)/f_samp * 1e6, len(channelA) )

# Initialize plots

fig = plt.figure()
ax_time = fig.add_subplot(1,1,1)
ax_time.set_xlabel("Time [µs]")
ax_time.set_ylabel("Amplitude [mV]")
ax_time.set_xlim(0, 23)
ax_time.set_ylim(-100, 100)
plt.grid(True, which='major', axis='both')

fig2 = plt.figure()
ax_spectrum = fig2.add_subplot(1,1,1)
ax_spectrum.set_xlabel( "Frequency [MHz]" )
ax_spectrum.set_ylabel( "Amplitude [dB]" )
ax_spectrum.set_xlim(0, 35)
ax_spectrum.set_ylim(-120, -30)
plt.grid(True, which='major', axis='both')

# Compute power spectrum
fftA = np.fft.rfft(window * channelA, norm="forward" )
pwrA = np.abs( fftA )**2 
X2 = np.fft.fftfreq(fftA.size * 2, 1/f_samp)[ :len(pwrA) ]
#print( "X2.shape", X2.shape )

# Freq domain windowing
f_c = 13e6
sigma = 3e6
fwindow = np.exp(-((X2) - f_c)**2/sigma**2) + 0*np.exp(-((X2) + f_c)**2/sigma**2)
wFspectrum = fwindow * pwrA
wFifft = np.fft.ifftshift(np.fft.irfft(wFspectrum, n=Nsamples, norm='backward'))

# Plot
plot_chA, = ax_time.plot( X, window * channelA * 1000 ,'m')
plot_spectrum, = ax_spectrum.plot( X2 / 1e6, np.log10(pwrA) * 10 ,'m')

plt.show(block = False)


# Select colour palette
color_palette_map = color_palette_map_normal

if len(sys.argv) > 1:
    if sys.argv[1] == "synthwave":
        color_palette_map = color_palette_map_synth



done = False
try:
    while not done:
        if shm_meta[1] == 0:
            done = True

        # Wait until new data has been written to shared memory by Alazartech
        if shm_meta[0] != old_cnt:
            #print( shm_meta[0] )
            old_cnt = shm_meta[0]
            channelA = (shm_data[0, :] >> bitShift).astype(np.float32)

            # Convert samples to volts
            channelA = (inputRange_volts * (channelA - codeZero)/codeRange).astype(np.float32)

            #channelA -= static_channelA

            channelA = channelA[startSample:stopSample]

            # Filtering
            channelA = scipy.signal.sosfilt( filtteri, channelA )

            # Update plots (faster than replotting)
            plot_chA.set_ydata(window * channelA * 1000)
            
            fftAb = np.fft.rfft( window * channelA * 1000 , norm="forward" )
            pwrAb = np.abs( fftAb )**2 

            #wFspectrum = fwindow * pwrAb
            #wFifft = np.fft.ifftshift(np.fft.irfft(wFspectrum, n=Nsamples, norm='backward'))

            # Show band-pass filter range
            #plt.axvline(x = 9, color = 'r' )
            #plt.axvline(x = 15, color = 'r' )

            plot_spectrum.set_ydata( np.log10( pwrAb /1e6) * 10 )
            #plotwFspectrum.set_ydata( np.log10(wFspectrum / 1e6) * 10)
            #plot_ifft.set_ydata( wFifft * 1000)

            fig.canvas.draw()
            fig.canvas.flush_events()

            fig2.canvas.draw()
            fig2.canvas.flush_events()

            time.sleep(0.02)
            # Update waterfall chart
            #log_pwr = np.log10( pwrA )
            #log_pwr[ np.where( log_pwr < 0) ] = 0
            #waterfall_chart[:-1, :] =  waterfall_chart[1:, :]
            #waterfall_chart[-1, :] = map_row( np.uint8( np.clip( (log_pwr-5)*35, 0, 255) ) )
            #cv2.imshow( "Waterfall", waterfall_chart )

        else:
            time.sleep(0.001)
except KeyboardInterrupt:
    pass

shm.close()