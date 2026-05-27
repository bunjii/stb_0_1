class Cons:

    def __init__(self, _nid: int, _tx: bool, _ty: bool, _tz: bool, _rx: bool, _ry: bool, _rz: bool):

        self.nid    = _nid 
        self.csts   = [_tx, _ty, _tz, _rx, _ry, _rz] 

        self.nd     = None

    def FindNd(self, _nds):

        self.nd = list(filter(lambda n: n.id == self.nid, _nds))[0]
        self.nd.cons = self

    def OutputConstInfo(self):
        
        props = ["CONS", 
                 "{0: >6}".format(self.nid)]

        for c in self.csts:
            props.append("{0: >4}".format(int(c))) 

        lns = ', '.join(props) + "\n"

        return lns
