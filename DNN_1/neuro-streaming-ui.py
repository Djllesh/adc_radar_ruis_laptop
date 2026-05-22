#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  

import os
os.environ["TF_GPU_ALLOCATOR"] = "cuda_malloc_async"


import tensorflow as tf
from numpy import asarray
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2DTranspose
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Reshape
from tensorflow.keras.layers import Flatten
from tensorflow.keras.layers import Dropout

from tensorflow.keras.optimizers import SGD
from train_mymodel import Model, ssim_loss, PSNR

from keras.models import load_model

from scipy.io import loadmat
import numpy as np

from multiprocessing import shared_memory

import cv2
import time

import tkinter as tki
import tkinter.ttk as ttk

import tkinter.filedialog
import tkinter.messagebox

from PIL import Image, ImageTk

import h5py

import pymsgbox
import scipy
import scipy.signal



samplesPerBuffer = 5000


shm_radar = shared_memory.SharedMemory(name = "milliscan-shm-1" )

shm_radar_meta = np.ndarray((4,), dtype=np.uint32, buffer=shm_radar.buf )
shm_radar_data = np.ndarray((2, samplesPerBuffer), dtype=np.uint16, buffer=shm_radar.buf, offset = shm_radar_meta.nbytes)

#shm_viscam = shared_memory.SharedMemory(name = "milliscan-shm-2" )

#shm_viscam_meta = np.ndarray((4,), dtype=np.uint32, buffer=shm_viscam.buf )
#shm_viscam_data = np.ndarray((256, 256), dtype=np.uint8, buffer=shm_viscam.buf, offset = shm_viscam_meta.nbytes)


filtteri = scipy.signal.iirdesign( wp = 0.02, ws = 0.01, gpass = 1.0, gstop = 30.0, output = 'sos')

def fetch_data( N_train = 100, N_validate = 10 ):
    global filtteri
    
    channelA = shm_radar_data[0, :].astype( np.float32 ) - 0x8000
    channelA = channelA[20:2500].copy()


    #viscam_frame = shm_viscam_data[:, :].copy()
    viscam_frame = np.zeros(4096)


    inputsTrain = np.zeros((N_train, channelA.shape[0]*2))
    #labelsTrain = np.zeros((N_train, 256*256))
    labelsTrain = np.zeros((N_train, 64*64))

    inputsPred = np.zeros((N_validate, channelA.shape[0]*2))
    #labelsPred = np.zeros((N_validate, 256*256))
    labelsPred = np.zeros((N_validate, 64*64))


    #print( "Hoovering data in...")
    N = 0
    old_radar_cnt = -1
    old_viscam_cnt = -1
    
    has_radar = False

    print( "Fetching training samples..")
    while N < N_train:
        if not has_radar:
            if old_radar_cnt != shm_radar_meta[0]:
                old_radar_cnt = shm_radar_meta[0]
                channelA = shm_radar_data[0, :].astype( np.float32 ) - 0x8000
                channelA = channelA[20:4980].copy()
                channelA = scipy.signal.sosfilt( filtteri, channelA )
                hilbertA =  scipy.signal.hilbert( channelA )

                #channelA = np.hstack([np.real(hilbertA), np.imag(hilbertA)])

                maxA = np.max( channelA )
                minA = np.min( channelA )

                
                # Do not do this kind of normalization again!
                #inputsTrain[N, :] = ((channelA - minA) / ( maxA - minA) - 0.5) * 2 # normalized data for NN
                inputsTrain[N, :] = channelA # non-normalized data for IF spectrum analysis; # Normalization removed on 13.06.2023
                has_radar = True
        
        if has_radar:
            #if old_viscam_cnt != shm_viscam_meta[0]:
                #old_viscam_cnt = shm_viscam_meta[0]
                viscam_frame = np.zeros(4096)
                viscam_frame = cv2.resize(viscam_frame, (64, 64))

                #viscam_frame = cv2.GaussianBlur(viscam_frame,(5,5),0)
                #viscam_frame = cv2.GaussianBlur(viscam_frame,(5,5),0)

                labelsTrain[N, :] = 1 - viscam_frame.flatten().astype(np.float32) / 255

                N += 1
                has_radar = False
                #print( "Train, N = ", N)

    N = 0
    print( "Fetching validation samples..")
    while N < N_validate:
        if not has_radar:
            if old_radar_cnt != shm_radar_meta[0]:
                old_radar_cnt = shm_radar_meta[0]
                channelA = shm_radar_data[0, :].astype( np.float32 ) - 0x8000
                channelA = channelA[20:2500].copy()
                channelA = scipy.signal.sosfilt( filtteri, channelA )
                hilbertA = scipy.signal.hilbert( channelA )
                
                channelA = np.hstack([np.real(hilbertA), np.imag(hilbertA)])


                maxA = np.max( channelA )
                minA = np.min( channelA )

                
                #inputsPred[N, :] = ((channelA - minA) / ( maxA - minA) - 0.5) * 2
                inputsPred[N, :] = channelA # Normalization removed on 13.06.2023
                has_radar = True
        
        if has_radar:
            #if old_viscam_cnt != shm_viscam_meta[0]:
                #old_viscam_cnt = shm_viscam_meta[0]
                viscam_frame = np.zeros(4096)
                viscam_frame = cv2.resize(viscam_frame, (64, 64))
                
                #viscam_frame = cv2.GaussianBlur(viscam_frame,(5,5),0)
                #viscam_frame = cv2.GaussianBlur(viscam_frame,(5,5),0)

                
                labelsPred[N, :] = 1 - viscam_frame.flatten().astype(np.float32) / 255

                N += 1
                has_radar = False
                #print( "Pred, N = ", N)

    print( "Fetching data done")
    return inputsTrain, labelsTrain, inputsPred, labelsPred




class App( object ):
    def __init__(self, root):
        self.root = root

        self.root.option_add( "*Font", "B612" )
        self.root.title("MilliScan Neural net Controller")
        self.mainmenubar = tki.Menu(self.root)
        self.root.config(menu=self.mainmenubar)

        self.filemenu = tki.Menu(self.mainmenubar, tearoff=0)

        self.filemenu.add_command(label="Load model", command=self.load_model)
        self.filemenu.add_command(label="Save model", command=self.save_model)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.root.quit)
        self.mainmenubar.add_cascade(label="File",menu=self.filemenu)

        self.actionmenu = tki.Menu( self.mainmenubar, tearoff=0)
        self.actionmenu.add_command(label = "Dump data to disk", command=self.dump_to_disk )
        
        self.mainmenubar.add_cascade(label="Action",menu=self.actionmenu)




        self.frame = tki.Frame( self.root )
        self.frame.pack()

        logo = Image.open("assets/milliscan.png")
        #logo = logo.resize((122,52), Image.ANTIALIAS)
        logo_render = ImageTk.PhotoImage(logo)

        img = tki.Label(self.frame, image=logo_render)
        img.image = logo_render
        img.pack(padx = 10, pady = 10 )
        
        self.control_frame = tki.LabelFrame( self.frame, text="Neural net control" )

        self.btn0 = tki.Button( self.control_frame, text= "Train model", command=self.handle_train_model )
        self.btn0.grid( row = 0, column = 0, padx = 5, pady = 5)
        self.btn1 = tki.Button( self.control_frame, text= "Run model", command=self.handle_run_model )
        self.btn1.grid( row = 0, column = 1, padx = 5, pady = 5)

        self.is_training = False
        self.is_running = False

        self.control_frame.pack( padx = 10, pady = 10, expand="yes", fill = "both" )

        self.init_net()


    def handle_train_model( self ):
        if not self.is_training:
            self.btn0.config(text="Stop training")
            self.is_training = True
        else:
            self.btn0.config(text="Train model")
            self.is_training = False

        if self.is_training:
            self.root.after( 100, self.training_loop )

        
    def handle_run_model( self ):
        if not self.is_running:
            self.btn1.config(text="Stop running")
            self.is_running = True
        else:
            self.btn1.config(text="Run model")
            self.is_running = False

        if self.is_running:
            self.root.after( 100, self.running_loop )


    def training_loop( self ):
        if self.is_training:
            self.training_round()
            self.root.after( 100, self.training_loop )

    def running_loop( self ):
        if self.is_running:
            self.predict_round()
            self.root.after( 100, self.running_loop )

    def init_net( self ):
        
        inputsTrain, labelsTrain, inputsPred, labelsPred = fetch_data( N_train=1, N_validate=1)
        numInputs = inputsTrain.shape[1]    
        #model = Sequential()
        #model.add(Dense(1000*2*2, input_shape=(numInputs,), activation='relu'))#, kernel_initializer=initializers.RandomNormal(stddev=1), bias_initializer=initializers.RandomNormal(stddev=.01)))
        #model.add(Dropout(0.1))
        #model.add(Dense(500*2*2, activation='relu')) # Add starts
        #model.add(Dropout(0))
        #model.add(Dense(50*2*2, activation='relu')) 
        #model.add(Dropout(0))
        #model.add(Reshape((2,2,50))) # Add stops
        
        # Big
        #model.add(Conv2DTranspose(100,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(50,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(25,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(12,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(6,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(3,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(1,(3,3), strides = (2,2), padding='same',activation='sigmoid', kernel_initializer=initializers.RandomNormal(stddev=1), bias_initializer=initializers.RandomNormal(stddev=.01)))
        #model.add(Reshape((256*256,1)))
        
        # Smaller
        #model.add(Conv2DTranspose(25,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(12,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(6,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(3,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(1,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(3,(3,3), strides = (2,2), padding='same',activation='relu'))
        #model.add(Conv2DTranspose(1,(3,3), strides = (2,2), padding='same',activation='sigmoid', kernel_initializer=initializers.RandomNormal(stddev=1), bias_initializer=initializers.RandomNormal(stddev=.01)))
        
        #model.add(Reshape((64*64,1)))
        #model.add(Flatten())
        #model.summary()
        print( "Initing the model..")
        model = Model()

    
        self.model = model
        
        print( "Other keras stuff")
        
        opt = tf.keras.optimizers.Adam(learning_rate = 0.001)
        self.model.compile(optimizer=opt, loss='mean_squared_error', metrics=['mae'])
        #self.model.compile(optimizer=opt, loss='mean_squared_error', metrics=['mae'])
        #self.model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['mae'])

    
    def training_round( self ):
        print( "Training round, fetching data...")
        inputsTrain, labelsTrain, inputsPred, labelsPred = fetch_data( N_train = 100, N_validate = 10 )
        print( "Training round, fitting model...")

        # ----------------------------------------
        # CHANGE THE DIM OF lABEL
        labelsTrain = labelsTrain.reshape(-1, 64, 64, 1)
        labelsPred = labelsPred.reshape(-1, 64, 64, 1)
        # -----------------------------------------
        
        history = self.model.fit(inputsTrain, labelsTrain, steps_per_epoch = 1, epochs = 3, validation_data=(inputsPred, labelsPred), validation_steps = 1)
        prediction = self.model.predict(inputsPred)
        img = prediction[0, :]
        #img = img.reshape((256,256))
        #img = img.reshape((64,64))
        #cv2.imshow( "Prediction", img )
        #outimg = np.hstack([img, labelsPred[0].reshape((256,256))])
        print( "Training round, plotting results...")
        
        #outimg = np.hstack([img, labelsPred[0].reshape((64,64))])
        outimg = np.hstack([img, labelsPred[0]])
        outimg = cv2.resize(outimg, (0,0), fx = 4.0, fy = 4.0, interpolation=cv2.INTER_NEAREST)     
        cv2.imshow( "Prediction + ground truth", outimg )
        #cv2.imshow( "A", img )
        #cv2.imshow( "B", labelsPred[0] )

        print( "img min", np.min(img), "max", np.max(img))


        cv2.waitKey(1)

        #plt.plot(history.history['loss'])
        #plt.plot(history.history['val_loss'])
        #plt.show(block = False)
        #print( "Loss:", history )
    
    def predict_round( self ):
        inputsTrain, labelsTrain, inputsPred, labelsPred = fetch_data(N_train= 2, N_validate=2)

        # ----------------------------------------
        # CHANGE THE DIM OF lABEL
        labelsTrain = labelsTrain.reshape(-1, 64, 64, 1)
        labelsPred = labelsPred.reshape(-1, 64, 64, 1)
        # -----------------------------------------


        prediction = self.model.predict(inputsPred)
        img = prediction[0, :]
        #img = img.reshape((256,256))
        #img = img.reshape((64,64))
        #outimg = np.hstack([img, labelsPred[0].reshape((256,256))])
        outimg = np.hstack([img, labelsPred[0]])
        outimg = cv2.resize(outimg, (0,0), fx = 4.0, fy = 4.0, interpolation=cv2.INTER_NEAREST)     
        cv2.imshow( "Prediction + ground truth", outimg )
        cv2.waitKey(1)
    
    def load_model( self ):
        fn = tki.filedialog.askopenfilename( filetypes = [("Keras file", "*.keras"), ("All files", "*.*")], defaultextension = ".keras" )    
        if len(fn) > 0:
            self.model = load_model( fn )
    
    def save_model( self ):
        fn = tki.filedialog.asksaveasfilename( filetypes = [("Keras file", "*.keras"), ("All files", "*.*")], defaultextension = ".keras" )    
        if len(fn) > 0:
            #self.model = load_model( fn )
            self.model.save( fn )
    
    def dump_to_disk( self ):
        fn = tki.filedialog.asksaveasfilename( filetypes = [("HDF5 file", "*.hdf5"), ("All files", "*.*")], defaultextension = ".hdf5" )
        if len( fn ) > 0:
            Npoints = pymsgbox.prompt(text = "Number of frames", title = "Action required" )
            Npoints = int(Npoints)
            inputsTrain, labelsTrain, inputsPred, labelsPred = fetch_data( N_train = Npoints, N_validate=1 )
            fn_handle =  h5py.File(fn, "w")
            dataset_radar = fn_handle.create_dataset("radar", inputsTrain.shape, dtype='f')
            dataset_viscam = fn_handle.create_dataset("viscam", labelsTrain.shape, dtype='f')

            dataset_radar[:,:] = inputsTrain[:, :]
            dataset_viscam[:,:] = labelsTrain[:, :]

            del fn_handle
            pymsgbox.alert(text = "Data saved to disk.", title = "Success")

                



def main(args):
        

    inputsTrain, labelsTrain, inputsPred, labelsPred = fetch_data()


    # 255-295 GHz
    
    #data = loadmat(r'activations_USAF1951_noNorm_202206031620')
    
    # data = loadmat(r'activations_USAF1951_202205271428.mat') # All random activations
    
    # data = loadmat(r'activations_USAF1951_noNorm_202205271913.mat') # No normalization in data, predictions from i = 78...80 % of max, training from random.
    
    
    if False:
        inputsTrain = np.array(data['inputsTrain']);
        labelsTrain = np.array(data['labelsTrain']);
        labelsTrain = labelsTrain/255.0;
        inputsPred = np.array(data['inputsPred']);
        labelsPred = np.array(data['labelsPred']);
        labelsPred = labelsPred/255.0;
        
    #np.savetxt('labels202200603.txt', labelsPred, delimiter=" ")
    
    #numInputs = 2002
    #numInputs = channelA.shape[0]
    numInputs = inputsTrain.shape[1]
        
    train_dataset = tf.data.Dataset.from_tensor_slices((inputsTrain, labelsTrain))
    
    model = Sequential()
    model.add(Dense(1000*2*2, input_shape=(numInputs,), activation='relu'))
    model.add(Dropout(0.5))
    model.add(Reshape((2,2,1000)))
    model.add(Conv2DTranspose(100,(3,3), strides = (2,2), padding='same',activation='relu'))
    model.add(Conv2DTranspose(50,(3,3), strides = (2,2), padding='same',activation='relu'))
    model.add(Conv2DTranspose(25,(3,3), strides = (2,2), padding='same',activation='relu'))
    model.add(Conv2DTranspose(12,(3,3), strides = (2,2), padding='same',activation='relu'))
    model.add(Conv2DTranspose(6,(3,3), strides = (2,2), padding='same',activation='relu'))
    model.add(Conv2DTranspose(3,(3,3), strides = (2,2), padding='same',activation='relu'))
    model.add(Conv2DTranspose(1,(3,3), strides = (2,2), padding='same',activation='sigmoid'))
    model.add(Reshape((256*256,1)))
    model.add(Flatten())
    model.summary()
    #exit()
    
    # Changed the learning rate on 19th February 2021 for improved convergence of *both* training and validating sets
    opt = tf.keras.optimizers.Adam(learning_rate = 0.001)
    
    model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['mae'])
    #model.compile(optimizer=opt, loss='mean_squared_error', metrics=['mae']) # Changed back to MSE as the sigmoid at output makes it work again, 23rd February 2021, ATa
    #model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['mae']) # Changed back to MSE as the sigmoid at output makes it work again, 23rd February 2021, ATa
    
    #history = model.fit(inputsTrain, labelsTrain, steps_per_epoch = 1000, epochs = 100, validation_data=(inputsPred, labelsPred), validation_steps = 1)
    for i in range( 100 ):
        print( "Training loop: %i", i)
        fetch_t0 = time.time()

        inputsTrain, labelsTrain, inputsPred, labelsPred = fetch_data()
        fetch_t1 = time.time()
        print( "Fetching took: %.2f s" % (fetch_t1 - fetch_t0) )
        history = model.fit(inputsTrain, labelsTrain, steps_per_epoch = 1, epochs = 3, validation_data=(inputsPred, labelsPred), validation_steps = 1, batch_size = 64 )
        prediction = model.predict(inputsPred)
        img = prediction[0, :]
        img = img.reshape((256,256))
        cv2.imshow( "Prediction", img )
        cv2.waitKey(1)
    
    # model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['mae'])
    # history = model.fit(inputs, labels, steps_per_epoch = 1000, epochs=200, validation_data=(inputs, labels), validation_steps = 3)
    
    #prediction = model.predict(inputsPred)
    
    #summarize history for accuracy, 19th February 2021
    # plt.figure(1)
    # plt.plot(history.history['mae'])
    # plt.plot(history.history['val_mae'])
    # plt.title('model accuracy')
    # plt.ylabel('mae')
    # plt.xlabel('epoch')
    # plt.legend(['train', 'test'], loc='upper left')
    
    # summarize history for loss, 19th FEbruary 2021
    # plt.figure(2)
    # plt.plot(history.history['loss'])
    # plt.plot(history.history['val_loss'])
    # plt.title('model loss')
    # plt.ylabel('loss')
    # plt.xlabel('epoch')
    # plt.legend(['train', 'test'], loc='upper left')
    # plt.show()
    
    
    # 19th February 2021
    if False:
        np.savetxt('prediction20220603.txt', prediction, delimiter=" ")
        np.savetxt('loss20220603.txt', history.history['loss'])
        np.savetxt('valLoss20220603.txt', history.history['val_loss'])
        np.savetxt('mae20220603.txt', history.history['mae'])
        np.savetxt('valMae20220603.txt', history.history['val_mae'])
        
        model_json = model.to_json()
        with open("model20220603.json", "w") as json_file:
            json_file.write(model_json)
        model.save_weights("model20220603.h5")
        print("Saved model to disk!")
        
    # plt.title('Loss')
    # plt.plot(history.history['loss'], label='train')
    # plt.show()
    
    return 0
    
if __name__ == '__main__':
    #import sys
    #sys.exit(main(sys.argv))
    root = tki.Tk()
    app = App( root )

    root.mainloop()
