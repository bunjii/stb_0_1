import numpy as np
import math

import common
#from elm import Elm1D

class EJnt:

    def __init__(self, 
                 _eid, 
                 _jnts):
    
        self.eid = _eid
        
        # self.Txi = _jnts[0]
        # self.Tyi = _jnts[1]
        # self.Tzi = _jnts[2]
        # self.Rxi = _jnts[3]
        # self.Ryi = _jnts[4]
        # self.Rzi = _jnts[5]

        # self.Txj = _jnts[ 6]
        # self.Tyj = _jnts[ 7]
        # self.Tzj = _jnts[ 8]
        # self.Rxj = _jnts[ 9]
        # self.Ryj = _jnts[10]
        # self.Rzj = _jnts[11]

        self.ryi = _jnts[0]
        self.rzi = _jnts[1]
        self.ryj = _jnts[2]
        self.rzj = _jnts[3]

        self.Ryi = None #_jnts[0]
        self.Rzi = None #_jnts[1]
        self.Ryj = None #_jnts[2]
        self.Rzj = None #_jnts[3]
        self.auto_generated = False

    def OutputElmJntInfo(self):

        props = ["EJNT", "{0: >6}".format(self.eid)] 

        # jnts = [self.Txi, self.Tyi, self.Tzi, self.Rxi, self.Ryi, self.Rzi, 
        #           self.Txj, self.Tyj, self.Tzj, self.Rxj, self.Ryj, self.Rzj]

        jnts = [self.ryi, self.rzi, self.ryj, self.rzj]

        for j in jnts:

            # if j >= 1e20:
            #     val = ""
            # elif j <= 1e-20:
            #     val = 0
            if j == None:
                val = ""
            else: 
                val = j * 1e-3

            props.append("{0: >8}".format(val))

        lns = ', '.join(props) + "\n"

        return lns