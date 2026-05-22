import tensorflow as tf
from numpy import asarray
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2DTranspose
from tensorflow.keras.layers import Conv2D
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Reshape
from tensorflow.keras.layers import AveragePooling2D
from tensorflow.keras.layers import MaxPool2D
from tensorflow.keras.layers import UpSampling2D
from tensorflow.keras.layers import Concatenate
from tensorflow.keras.layers import Dropout
from tensorflow.keras.layers import Add
from tensorflow.keras.models import model_from_json
from tensorflow.keras.layers import BatchNormalization
from tensorflow.keras.activations import sigmoid

class Res_block(tf.keras.Model):
    '''
    Residual block w/o BN
    ---Conv-ReLU-Conv-+-
     |________________|
    '''
    def __init__(self, n_feat):
        super().__init__()
        self.conv1 = Conv2D(filters=n_feat, kernel_size=3, padding='same', strides=1, activation='relu')
        self.conv2 = Conv2D(filters=n_feat, kernel_size=3, padding='same', strides=1, activation='relu')
        self.conv3 = Conv2D(filters=n_feat, kernel_size=1, padding="same")
    def call(self, input):
        res = self.conv2(self.conv1(input))
        res += self.conv3(input)
        return res

class down_block(tf.keras.Model):
    def __init__(self, filters, kernel_size=(3, 3), padding="same", strides=1):
        super().__init__()
        self.conv = Res_block(n_feat=filters)
        self.pool = MaxPool2D((2, 2), (2, 2))
    def call(self, input):
        c = self.conv(input)
        p = self.pool(c)
        return c, p

class up_block(tf.keras.Model):
    def __init__(self, filters, kernel_size=(3, 3), padding="same", strides=1):
        super().__init__()
        self.us = UpSampling2D((2, 2))
        self.cat = Concatenate()
        self.conv = Res_block(n_feat=filters)
    def call(self, x, skip):
        us = self.us(x)
        concat = self.cat([us, skip])
        c = self.conv(concat)
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

class ResUNet(tf.keras.Model):
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

if __name__ == '__main__':
    #a = tf.random((1, 402, 1))
    #print(a.shape)
    input_layer = tf.keras.Input(shape=(512, 512, 1), batch_size=4)
    print(input_layer.shape)
    model = ResUNet()
    out = model(input_layer)
    print(out.shape)

    
        
        