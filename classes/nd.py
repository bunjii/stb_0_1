import math

class Nd: 

    def __init__(self, _id, _x, _y, _z):

        self.id = _id
        self.x  = _x
        self.y  = _y
        self.z  = _z

        self.cid    = None
        self.cons   = None
        self.reacts = None      # [lc][vals]
        self.disps  = None

        self.plt2d_arr = None

    def DistanceTo(self, _other):

        dist = math.sqrt((self.x-_other.x)**2 + (self.y-_other.y)**2 + (self.z-_other.z)**2) 
        
        return dist
    
    def OutputNdInfo(self):

        props = ["NODE",
                 "{0: >6}".format(self.id), 
                 "{0: >9}".format(self.x), 
                 "{0: >9}".format(self.y), 
                 "{0: >9}".format(self.z)
        ]

        if self.cons != None:
            props.append("{0: >6}".format('*'))
        else:
            props.append("")

        lns = ', '.join(props) + "\n"

        return lns
    
