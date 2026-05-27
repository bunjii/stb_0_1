
class Plt:

    def __init__(self, _id, _name, _axis_id, _type, _lc, _scale, _deffac):

        self.id      = _id
        self.name    = _name
        self.axis_id = _axis_id
        self.type    = _type
        self.lc      = _lc
        self.scale   = _scale
        self.deffac  = _deffac

        return
    
    def OutputPltInfo(self): 

        if self.lc is None:
            lc = ""
        else:
            lc = self.lc

        props = ["PLOT",
            "{0: >6}".format(self.id),
            "{0:>10}".format(self.name),
            "{0: >6}".format(self.axis_id),
            "{0: >6}".format(self.type),
            "{0: >6}".format(lc),
            "{0: >6}".format(self.scale),
            "{0: >6}".format(self.deffac)
            ]

        lns = ', '.join(props) + "\n"

        return lns