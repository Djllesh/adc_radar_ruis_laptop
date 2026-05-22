#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  imagingLogos20210105_2
# Imaging logos where training data is located outside x = 0
# Testing data is located at x = 0
# Image size is 256 x 256 pixels
# 220-330 GHz
# 
## ####### #     # ###  #####     ###  #####     ####### ### #     #    #    #                   ######  #######    #     # ####### #######     #####  #     #    #    #     #  #####  ####### 
#   # #    #     #  #  #     #     #  #     #    #        #  ##    #   # #   #                   #     # #     #    ##    # #     #    #       #     # #     #   # #   ##    # #     # #       
#   # #    #     #  #  #           #  #          #        #  # #   #  #   #  #                   #     # #     #    # #   # #     #    #       #       #     #  #   #  # #   # #       #       
#   # #    #######  #   #####      #   #####     #####    #  #  #  # #     # #          #####    #     # #     #    #  #  # #     #    #       #       ####### #     # #  #  # #  #### #####   
#   # #    #     #  #        #     #        #    #        #  #   # # ####### #                   #     # #     #    #   # # #     #    #       #       #     # ####### #   # # #     # #       
#   # #    #     #  #  #     #     #  #     #    #        #  #    ## #     # #                   #     # #     #    #    ## #     #    #       #     # #     # #     # #    ## #     # #       
#   # #    #     # ###  #####     ###  #####     #       ### #     # #     # #######             ######  #######    #     # #######    #        #####  #     # #     # #     #  #####  ####### 
#
# Added FC layers to arrive to latent representations.  January 20 2021
#  
    
#  

import os
os.environ["TF_GPU_ALLOCATOR"] = "cuda_malloc_async"


import tensorflow as tf
from numpy import asarray
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2DTranspose
from tensorflow.keras.layers import Conv2D
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Reshape
from tensorflow.keras.layers import Flatten
from tensorflow.keras.layers import Dropout
from tensorflow.keras.models import model_from_json
from tensorflow.keras.layers import Activation
from tensorflow.keras.layers import BatchNormalization

from tensorflow.keras.optimizers import SGD
from scipy.io import loadmat
import numpy as np


def main(args):
	

	# 255-295 GHz
	
	data = loadmat(r'activations_USAF1951_noNorm_202206031620')
	
	# data = loadmat(r'activations_USAF1951_202205271428.mat') # All random activations
	
	# data = loadmat(r'activations_USAF1951_noNorm_202205271913.mat') # No normalization in data, predictions from i = 78...80 % of max, training from random.
	
	

	inputsTrain = np.array(data['inputsTrain']);
	labelsTrain = np.array(data['labelsTrain']);
	labelsTrain = labelsTrain/255.0;
	inputsPred = np.array(data['inputsPred']);
	labelsPred = np.array(data['labelsPred']);
	labelsPred = labelsPred/255.0;
	
	#np.savetxt('labels202200603.txt', labelsPred, delimiter=" ")
	
	numInputs = 2002
		
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
	
	#model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['mae'])
	# model.compile(optimizer=opt, loss='mean_squared_error', metrics=['mae']) # Changed back to MSE as the sigmoid at output makes it work again, 23rd February 2021, ATa
	model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['mae']) # Changed back to MSE as the sigmoid at output makes it work again, 23rd February 2021, ATa
	
	#history = model.fit(inputsTrain, labelsTrain, steps_per_epoch = 1000, epochs = 100, validation_data=(inputsPred, labelsPred), validation_steps = 1)
	history = model.fit(inputsTrain, labelsTrain, steps_per_epoch = 1000, epochs = 100, validation_data=(inputsPred, labelsPred), validation_steps = 1, batch_size = 64 )
	
	# model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['mae'])
	# history = model.fit(inputs, labels, steps_per_epoch = 1000, epochs=200, validation_data=(inputs, labels), validation_steps = 3)
	
	prediction = model.predict(inputsPred)
	
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
	import sys
	sys.exit(main(sys.argv))
