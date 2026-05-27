
from common import Plane, Vec, Pnt

class Axis:

    def __init__(self, _id, _name, _isHorizontal, _nid, _xdir = None):
        
        self.id = _id
        self.name = _name
        self.isHorizontal = _isHorizontal
        self.nid = _nid
        self.xdir = _xdir

        self.pln = None # is assigned in mdl

        return
    
    @staticmethod
    def CalcPln(axis, mdl):

        pln = None

        n = list(filter(lambda n: n.id == axis.nid, mdl.nds))[0]
        if axis.isHorizontal == True:
            pln = Plane(n, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
            
        elif axis.xdir == 0:
            pln = Plane(n, (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0,-1.0, 0.0))

        elif axis.xdir == 1:
            pln = Plane(n, (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        
        else:
            print(f"something is wrong: {axis.id}")

        return pln
    
    def OutputAxisInfo(self): 

        if self.xdir is None:
            xdir = ""
        else:
            xdir = self.xdir

        props = ["AXIS",
            "{0: >6}".format(self.id),
            "{0:>10}".format(self.name),
            "{0: >6}".format(int(self.isHorizontal)),
            "{0: >6}".format(self.nid),
            "{0: >6}".format(xdir)
            ]
        
        lns = ', '.join(props) + "\n"

        return lns
    