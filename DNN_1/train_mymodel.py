#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  

import tensorflow as tf
from numpy import asarray
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2DTranspose
from tensorflow.keras.layers import Conv2D
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Reshape
from tensorflow.keras.layers import MaxPool2D
from tensorflow.keras.layers import Dropout
from tensorflow.keras.layers import Flatten
from tensorflow.keras.models import model_from_json
from tensorflow.keras.layers import UpSampling2D
from tensorflow.keras.layers import Concatenate
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.callbacks import TensorBoard
from tensorflow.keras.callbacks import LearningRateScheduler
from tensorflow.keras.optimizers import SGD
from scipy.io import loadmat
import numpy as np
import os
from Mymodel import ResUNet

def ssim_loss(y_true, y_pred):
    ssim = 1 - tf.reduce_mean(tf.image.ssim(y_true, y_pred, 1.0))
    L2 = tf.losses.mean_squared_error(y_true, y_pred)
    return L2 + ssim

def PSNR(y_true, y_pred):
    return tf.image.psnr(y_true, y_pred, max_val=1.0, name=None)




class MLP(tf.keras.Model):
    # obtain features in the spectrum latent space.
    def __init__(self):
        super().__init__(self)
        # Multilayer Perceptron for real part
        self.rdense = Dense(units=64, activation='sigmoid')
        # Multilayer perceptron for imaginary part
        self.idense = Dense(units=64, activation='sigmoid')
        
        # Multilayer perceptron for feature fusion
        self.fdense = Dense(units=64, activation='sigmoid')
        self.reshape = Reshape((8, 8))
        self.drop = Dropout(0.5)
        
    def call(self, input):
        re, im = tf.split(input, num_or_size_splits=2, axis=1)
        r_out = self.rdense(re)
        
        i_out = self.idense(im)
        
        f_out = tf.concat([r_out, i_out], axis=1)
        f_out = self.drop(f_out)
        out = self.fdense(f_out)
        out = self.reshape(out)
        
        return out

class TransformSD(tf.keras.Model):
    # transform the spectrum latent space features to feature maps in the spatial domain
    def __init__(self):
        super().__init__(self)
        self.head_conv = Conv2D(filters=64, kernel_size=3, padding='same', activation='relu')
        self.dconv1 = Conv2DTranspose(32, (3 ,3), strides = (2,2), padding='same', activation='relu')
        self.dconv2 = Conv2DTranspose(16, (3 ,3), strides = (2,2), padding='same', activation='relu')
        self.dconv3 = Conv2DTranspose(8, (3 ,3), strides = (2,2), padding='same', activation='relu')
        #self.dconv4 = Conv2DTranspose(4, (3 ,3), strides = (2,2), padding='same', activation='relu')
        #self.dconv5 = Conv2DTranspose(2, (3 ,3), strides = (2,2), padding='same', activation='relu')
        self.end_conv = Conv2D(filters=1, kernel_size=3, padding='same')
    
    def call(self, input):
        input = tf.expand_dims(input, axis=-1)
        out = self.head_conv(input)
        out = self.dconv1(out)
        out = self.dconv2(out)
        out = self.dconv3(out)
        #out = self.dconv4(out)
        #out = self.dconv5(out)
        out = self.end_conv(out)
        
        return out
    
class Res_block(tf.keras.Model):
    '''
    Residual block w/o BN
    ---Conv-ReLU-Conv-+-
     |________________|
    '''
    def __init__(self, out_ch=1, n_feat=32):
        super().__init__()
        self.conv1 = Conv2D(filters=n_feat, kernel_size=3, padding='same', activation='relu')
        self.conv2 = Conv2D(filters=out_ch, kernel_size=3, padding='same')
    def call(self, input):
        res = self.conv2(self.conv1(input))
        res += input
        return res

class down_block(tf.keras.Model):
    def __init__(self, filters, kernel_size=(3, 3), padding="same", strides=1):
        super().__init__()
        self.conv1 = Conv2D(filters, kernel_size, padding=padding, strides=strides, activation="relu")
        self.conv2 = Conv2D(filters, kernel_size, padding=padding, strides=strides, activation="relu")
        self.pool = MaxPool2D((2, 2), (2, 2))
    def call(self, input):
        c = self.conv1(input)
        c = self.conv2(c)
        p = self.pool(c)
        return c, p

class up_block(tf.keras.Model):
    def __init__(self, filters, kernel_size=(3, 3), padding="same", strides=1):
        super().__init__()
        self.us = UpSampling2D((2, 2))
        self.cat = Concatenate()
        self.conv1 = Conv2D(filters, kernel_size, padding=padding, strides=strides, activation="relu")
        self.conv2 = Conv2D(filters, kernel_size, padding=padding, strides=strides, activation="relu")
    def call(self, x, skip):
        us = self.us(x)
        concat = self.cat([us, skip])
        c = self.conv1(concat)
        c = self.conv2(c)
        return c

class bottleneck(tf.keras.Model):
    def __init__(self, filters, kernel_size=(3, 3), padding="same", strides=1):
        super().__init__()
        self.conv1 = Conv2D(filters, kernel_size, padding=padding, strides=strides, activation="relu")
        self.conv2 = Conv2D(filters, kernel_size, padding=padding, strides=strides, activation="relu")
    def call(self, x):
        c = self.conv1(x)
        c = self.conv2(c)
        return c

class UNet(tf.keras.Model):
    def __init__(self):
        super().__init__()
        f = [16, 32, 64, 128, 256]
        
        self.down_block1 = down_block(filters=f[0])
        self.down_block2 = down_block(filters=f[1])
        self.down_block3 = down_block(filters=f[2])
        self.down_block4 = down_block(filters=f[3])
        
        self.bn = bottleneck(filters=f[4])
        
        self.up_block1 = up_block(filters=f[3])
        self.up_block2 = up_block(filters=f[2])
        self.up_block3 = up_block(filters=f[1])
        self.up_block4 = up_block(filters=f[0])
        
        self.tail = Conv2D(1, (1, 1), padding="same", activation="sigmoid")
    
    def call(self, x):
        c1, p1 = self.down_block1(x)
        c2, p2 = self.down_block2(p1)
        c3, p3 = self.down_block3(p2)
        c4, p4 = self.down_block4(p3)
        
        bn = self.bn(p4)
        
        u1 = self.up_block1(bn, c4) #8 -> 16
        u2 = self.up_block2(u1, c3) #16 -> 32
        u3 = self.up_block3(u2, c2) #32 -> 64
        u4 = self.up_block4(u3, c1)
        
        out = self.tail(u4)

        return out    



class DUN(tf.keras.Model):
    def __init__(self, in_ch=1, out_ch=1, n_feat=32):
        super().__init__()
        # Flexible Gradient Descent Module
        self.phi_1 = Res_block(out_ch=in_ch, n_feat=n_feat)
        self.phi_2 = Res_block(out_ch=in_ch, n_feat=n_feat)
        self.r = tf.Variable(0.1, trainable=True,dtype=tf.float32)
        
        # Informative Proximal Mapping Module
        self.ipmm = ResUNet()#UNet()
    
    def call(self, x):
        # Flexible Gradient Descent Module
        phixsy = self.phi_1(x) - x
        v = x - self.r * self.phi_2(phixsy)
        
        # Informative Proximal Mapping Module
        out = self.ipmm(v)
        return out    
        

class Model(tf.keras.Model):
    def __init__(self):
        super().__init__()
        self.mlp = MLP()
        self.transformsd = TransformSD()
        #self.basic_block1 = DUN()
    
    def call(self, input):
        out = self.mlp(input)
        out = self.transformsd(out)
        #out = self.basic_block1(out)
        return out
    
def scheduler(epoch, lr):
  if epoch < 250:
    return lr
  else:
    return lr * tf.math.exp(-0.1)


def main(args):

	data = loadmat(r'data/activations_USAF1951202301111510.mat')

	inputsTrain = np.array(data['inputsTrain'])
	labelsTrain = np.array(data['labelsTrain']).reshape(-1, 256, 256, 1)
	labelsTrain = labelsTrain/255.0
	inputsPred = np.array(data['inputsPred'])
	labelsPred = np.array(data['labelsPred'])
	labelsPred = labelsPred/255.0
 
    
	np.savetxt('labels20220801.txt', labelsPred, delimiter = " ")
	labelsPred = labelsPred.reshape(-1, 256, 256, 1)
	
	numInputs = 402
		
	#train_dataset = tf.data.Dataset.from_tensor_slices((inputsTrain, labelsTrain))
 
	# build a tensorboard class for visualizing some parameters
	tbCallBack = TensorBoard(log_dir="./logs", write_images=True)
	#reduce_lr_loss = LearningRateScheduler(scheduler)
	
	model = Model()
	#model.summary()
	# exit()
	
	# Changed the learning rate on 19th February 2021 for improved convergence of *both* training and validating sets
	opt = tf.keras.optimizers.Adam(learning_rate = 0.0001)
	
	# model.compile(optimizer=opt, loss='mean_squared_error' or 'mean_absolute_error', metrics=['mae']) # Changed back to MSE as the sigmoid at output makes it work again, 23rd February 2021, ATa
	
	model.compile(optimizer=opt, loss=ssim_loss, metrics=[PSNR]) # Changed back to MSE as the sigmoid at output makes it work again, 23rd February 2021, ATa
	
	history = model.fit(inputsTrain, labelsTrain, steps_per_epoch = 1000, epochs = 500, validation_data=(inputsPred, labelsPred), validation_steps = 2, callbacks=[tbCallBack])
	
	# model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['mae'])
	# history = model.fit(inputs, labels, steps_per_epoch = 1000, epochs=200, validation_data=(inputs, labels), validation_steps = 3)

	prediction = model.predict(inputsPred).reshape(-1, 256*256*1)
	
	np.savetxt('ResUnet_prediction.txt', prediction, delimiter=" ")
	np.savetxt('loss.txt', history.history['loss'])
	np.savetxt('valLoss.txt', history.history['val_loss'])
	#np.savetxt('PSNR.txt', history.history['PSNR'])
	#np.savetxt('valPSNR.txt', history.history['val_PSNR'])
	
	model_json = model.to_json()
	with open("model.json", "w") as json_file:
		json_file.write(model_json)
	model.save_weights("model.h5")
	print("Saved model to disk!")
	
	return 0
	
if __name__ == '__main__':
	import sys
	sys.exit(main(sys.argv))