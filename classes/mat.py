class Mat:

    def __init__(self, 
                 _id: int, 
                 _name: str, 
                 _E: float, 
                 _G: float, 
                 _gamma: float, 
                 _alpha: float, 
                 _fy: float
                 ):

        self.id    = _id
        self.name  = _name
        self.E     = _E 
        self.G     = _G 
        self.gamma = _gamma
        self.alpha = _alpha
        self.fy    = _fy

        self.cid   =  None
        self.auto_generated = False

    def OutputMatInfo(self):

        props = ["MATE", 
                 "{0: >6}".format(self.id), 
                 "{0: >10}".format(self.name), 
                 "{0: >8}".format(int(self.E * 1e-6)), 
                 "{0: >8}".format(int(self.G * 1e-6)), 
                 "{0: >8.1f}".format(self.gamma * 1e-3), 
                 "{0: 8.1e}".format(self.alpha), 
                 "{0: >8}".format(int(self.fy * 1e-6))
                 ]
        
        lns  = ', '.join(props) + "\n"

        return lns