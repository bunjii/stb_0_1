import math

#
# type 0: Rectangle 
# type 1: Circular 
# type 2: I
# type 3: CHS
# type 4: RHS
#

class Sec:

    def __init__(self, _id, _name, _mat, _type, _dims: list):

        self.id   = _id
        self.name = _name
        self.mat  = _mat
        self.type = _type
        self.dims = _dims

        self.cid  =  None

        self.CalcSectionProps()
        # A, J, Iy, Iz, Wy, Wz, iy, iz
        # Asy, Asz
    
    def CalcSectionProps(self):

        # shape factor: see also Kassimali 1999 pp537-538 sec9.7 nshear deformations

        if self.type == 0:
            
            B = self.dims[0]
            H = self.dims[1]

            # Area
            self.A = B * H

            # J: Saint Venant's torsional constant
            # reference: Takemura p.129 
            N = 10
            a = max(B, H)
            b = min(B, H)
            k = 0
            for i in range(1, N):
                n = 1 + 2 * i
                k += 1.0 / n ** 5 * math.tanh( n * math.pi * a / (2.0 * b))
            self.J = 1.0 / 3.0 * a * b ** 3 * (1.0 - 192.0 / math.pi ** 5.0 * b / a * k) 

            # Iy, Iz
            self.Iy = 1.0 / 12.0 * B * H ** 3
            self.Iz = 1.0 / 12.0 * H * B ** 3 

            # Wy, Wz
            self.Wy = 1.0 / 6.0 * B * H ** 2
            self.Wz = 1.0 / 6.0 * H * B ** 2 

            # Asy, Asz
            # "Mechanics of materials, 2nd. Gere & Timoshenko"
            self.fs  = 1.2
            self.Asy = self.A / self.fs
            self.Asz = self.A / self.fs

        elif self.type == 1: 

            D = self.dims[0]

            # Area
            self.A = 0.25 * math.pi * (D ** 2) 

            # J: torsional constant
            # reference: Takemura p.127
            # Ip: Polar moment of inertia of area
            self.J = math.pi / 32.0 * D ** 4 

            # Iy, Iz
            self.Iy = 1.0 / 64.0 * math.pi * D ** 4 
            self.Iz = self.Iy

            # Wy, Wz
            self.Wy = 1.0 / 32.0 * math.pi * D ** 3 
            self.Wz = self.Wy

            # Asy, Asz
            # "Mechanics of materials, 2nd. Gere & Timoshenko"
            self.fs  = 10.0 / 9.0
            self.Asy = self.A / self.fs
            self.Asz = self.A / self.fs


        elif self.type == 2: 

            H  = self.dims[0]
            W  = self.dims[1]
            Tw = self.dims[2]
            Tf = self.dims[3]
            # Area
            self.A = H * W - (H - 2.0 * Tf) * (W - Tw)

            # J: torsional constant
            self.J = 1.0 / 3.0 * (2.0 * W * Tf ** 3 + (H - 2.0 * Tf) * Tw ** 3)

            # Iy, Iz
            self.Iy = 1.0 / 12.0 * (W * H ** 3- (W - Tw) * (H - 2.0 * Tf) ** 3)
            self.Iz = 1.0 / 12.0 * (2.0 * Tf * W ** 3 + (H - 2.0 * Tf) * Tw ** 3)

            # Wy, Wz
            self.Wy = 2.0 / H * self.Iy
            self.Wz = 2.0 / W * self.Iz

            # Asy, Asz
            # "Mechanics of materials, 2nd. Gere & Timoshenko"
            self.fs  = 1.0 
            self.Asy = 2.0 * Tf * W
            self.Asz = Tw * (H - 2.0 * Tf)

        elif self.type == 3: 

            D  = self.dims[0]
            t  = self.dims[1]

            # Area
            self.A = 0.25 * math.pi * ((D ** 2) - (D - 2.0 * t)**2)

            # J: torsional constant
            self.J = math.pi / 32.0 * (D ** 4 - (D - 2.0 * t) ** 4)

            # Iy, Iz
            self.Iy = math.pi / 64.0 * (D ** 4 - (D - 2.0 * t) ** 4)
            self.Iz = self.Iy

            # Wy, Wz
            self.Wy = 2.0 / D * self.Iy
            self.Wz = self.Wy

            # Asy, Asz
            # "Mechanics of materials, 2nd. Gere & Timoshenko"
            self.fs  = 2.0 
            self.Asy = self.A / self.fs
            self.Asz = self.A / self.fs
        
        elif self.type == 4: 

            H  = self.dims[0]
            W  = self.dims[1]
            Tw = self.dims[2]
            Tf = self.dims[3]

            # Area
            self.A = H * W - (H - 2.0 * Tf) * (W - 2.0 * Tw)

            # J: torsional constant
            h = H - Tf
            w = W - Tw
            self.J = 4.0 * (h * w) ** 2 / ( 2.0 * h / Tw + 2.0 * w / Tf)

            # Iy, Iz
            self.Iy = 1.0 / 12.0 * (W * H ** 3 - (W - 2.0 * Tw) * (H - 2.0 * Tf) ** 3)
            self.Iz = 1.0 / 12.0 * (H * W ** 3 - (H - 2.0 * Tf) * (W - 2.0 * Tw) ** 3)

            # Wy, Wz
            self.Wy = 2.0 / H * self.Iy
            self.Wz = 2.0 / W + self.Iz

            # Asy, Asz
            # "Mechanics of materials, 2nd. Gere & Timoshenko"
            self.fs  = 1.0 
            self.Asy = 2.0 * Tf * W
            self.Asz = 2.0 * Tw * (H - 2.0 * Tf)
            


        # iy, iz for all types
        self.iy = math.sqrt(self.Iy/self.A)
        self.iz = math.sqrt(self.Iz/self.A)
    
    def OutputSecInfo(self):

        props = ["SECT", 
                 "{0: >6}".format(self.id), 
                 "{0: >10}".format(self.name), 
                 "{0: >6}".format(self.mat.id), 
                 "{0: >6}".format(self.type)
                 ]
        
        for d in self.dims:
            props.append("{0: >6.1f}".format(d * 1e3)) # [m] -> [mm]

        lns = ', '.join(props) + "\n"
        
        return lns