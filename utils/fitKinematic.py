import math, __init__ as utils,ROOT as r
try:
    import scipy.optimize as opt
except: pass
try:
    import numpy as np
except:
    pass

widthTop = 13.1/2
###########################
class leastsqLeptonicTop(object) :
    '''Fit jet, lepton, and missing energy to the hypothesis t-->blv.'''

    def __init__(self, b, bResolution, mu, nuXY, nuErr, 
                 massT = 172.0, widthT = widthTop, massW = 80.4, zPlus = True ) :

        for key,val in zip(['',                     'XY',   'Z',   'E',      'T2',    'T',   'Phi'],
                           [mu,np.array([mu.x(),mu.y()]),mu.z(),mu.e(),mu.Perp2(),mu.Pt(),mu.Phi()]) : setattr(self,"mu"+key,val)

        for key,val in zip(['massW2','massT','invT','bound','sign','rawB','nuXY','fitNu'],
                           [massW**2,massT,1./widthT,False,[-1,1][zPlus],b,nuXY,utils.LorentzV()]) : setattr(self,key,val)

        self.bXY = np.array([b.x(),b.y()])

        eig,self.Rinv = np.linalg.eig(nuErr)
        self.R = self.Rinv.transpose()
        self.inv = 1./np.append([bResolution],np.sqrt(np.maximum(1,eig)))

        self.setFittedNu(nuXY)
        _,self.rawW,self.rawT = np.cumsum([mu,self.fitNu,self.rawB])
        
        self.residualsBSLT = self.fit()
        self.chi2 = self.residualsBSLT.dot(self.residualsBSLT)
        _,self.fitW,self.fitT = np.cumsum([mu,self.fitNu,self.fitB])
        
    def setFittedNu(self,nuXY) :
        P = self.massW2 + 2* nuXY.dot(self.muXY)
        self.discriminant = 1 - 4 * self.muT2 * nuXY.dot(nuXY) / P**2
        nuZ = 0.5 * P / self.muT2 * (self.muZ + self.sign*self.muE*math.sqrt(max(0,self.discriminant)))
        self.fitNu.SetPxPyPzE(nuXY[0],nuXY[1],nuZ,0)
        self.fitNu.SetM(0)

    def setBoundaryFittedNu(self,phi) :
        nuT = 0.5 * self.massW2 / (self.muT * (1 - math.cos(self.muPhi-phi)))
        self.setFittedNu( nuT * np.array([math.cos(phi), math.sin(phi)]) )
        
    def fit(self) :
        def lepResiduals(d) : # deltaB, dS, dL
            self.fitB = self.rawB * (1+d[0])
            self.setFittedNu(self.nuXY - d[0]*self.bXY + self.Rinv.dot(d[1:]))
            return np.append( self.inv * d,
                              self.invT * (self.massT - (self.mu + self.fitNu + self.fitB ).M()) )
        
        def lepBoundResiduals(x) : # deltaB, phi
            self.fitB = self.rawB * (1+x[0])
            self.setBoundaryFittedNu(x[1])
            nuXY = [self.fitNu.x(),self.fitNu.y()]
            dS,dL = self.R.dot(nuXY - self.nuXY + x[0]*self.bXY)
            return np.append( self.inv * [x[0],dS,dL],
                              self.invT * (self.massT - (self.mu + self.fitNu + self.fitB).M()) )

        deltas,_ = opt.leastsq(lepResiduals, 3*[0], epsfcn=0.01, ftol=1e-3)
        if 0 <= self.discriminant : return lepResiduals(deltas)
        self.bound = True
        best,_ = opt.leastsq(lepBoundResiduals, [0, math.atan2(self.nuXY[1],self.nuXY[0])], epsfcn=0.01, ftol=1e-3)
        return lepBoundResiduals(best)
        
###########################
class leastsqHadronicTop(object) :
    '''Fit three jets to the hypothesis t-->bqq.

    Index 2 is the b-jet.
    Resolutions are expected in units of sigma(pT)/pT.'''

    def __init__(self, jetP4s, jetResolutions, massT = 172.0, widthT = widthTop, massW = 80.4, widthW = 2.085/2 ) :
        for key,val in zip(['massT','massW','invT','invW'],
                           [massT,massW,1./widthT,1./widthW]) : setattr(self,key,val)
        
        self.rawJ = jetP4s;
        self.invJ = 1./np.array(jetResolutions)
        self.fit()
        _,self.fitW,self.fitT = np.cumsum(self.fitJ)
        _,self.rawW,self.rawT = np.cumsum(self.rawJ)

    def fit(self) :
        def hadResiduals(d) :
            _,W,T = np.cumsum(self.rawJ * (1+d))
            return np.append((d*self.invJ), [ (self.massW-W.M())*self.invW,
                                              (self.massT-T.M())*self.invT])

        self.deltaJ,_ = opt.leastsq(hadResiduals,3*[0],epsfcn=0.01, ftol=1e-3)
        self.fitJ = self.rawJ * (1+self.deltaJ)
        self.residualsPQBWT = hadResiduals(self.deltaJ)
        self.chi2 = self.residualsPQBWT.dot(self.residualsPQBWT)
###########################
class leastsqLeptonicTop2(object) :
    '''Fit jet, lepton, and missing energy to the hypothesis t-->blv.'''

    def __init__(self, b, bResolution, mu, nuXY, nuErr, 
                 massT = 172.0, massW = 80.4) :

        Wm2 = massW**2

        x0 = Wm2 / (2*mu.P())
        A_munu = np.array([[  0, 0,              -x0],
                           [  0, 1,                0],
                           [-x0, 0, Wm2 - x0**2]])
        
        c = r.Math.VectorUtil.CosTheta(mu,b)
        s = math.sqrt(1-c*c)
        R = np.array([[c, -s, 0],
                      [s,  c, 0],
                      [0,  0, 1]])

        b_m2 = b.M2()
        b_e2 = b_m2 + b.P2()
        b_p = b.P()
        Q = 0.5 * (massT**2 - Wm2 - b_m2)

        A_b = R.dot(np.array([[  b_m2/b_e2, 0,          -Q*b_p/b_e2],
                              [          0, 1,                    0],
                              [-Q*b_p/b_e2, 0, Wm2 - Q**2/b_e2]])).dot(R.transpose())


        self.evals,v = np.linalg.eig( np.linalg.inv(A_munu).dot(A_b) )

        #self.valid = any(e.imag for e in self.evals) 
        #if not self.valid : return

        degenerate = np.array([[b_m2/b_p**2 +s**2,  -c*s],
                               [             -c*s, -s**2]])
        _,rot = np.linalg.eig(degenerate)
        diag = rot.transpose().dot(degenerate).dot(rot)
        print rot
        print diag/diag[1,1]
        print

        base = math.atan2(rot[1,0],rot[0,0])
        pm = math.atan(math.sqrt(-diag[0,0]/diag[1,1]))
        slopes = [math.tan(ang) for ang in [base+pm, base-pm, -base+pm, -base-pm, base+1/pm, base-1/pm, -base+1/pm, -base-1/pm]]

        x1 = x0
        y1= ( Q/b_p - x1*c ) / s

        #T = np.array([[1,0,-x0],[0,1,(c*x0 - Q/b_p)/s],[0,0,1]])
        #print T.transpose().dot(A_b-A_munu).dot(T)
        #print degenerate
        
        print "point: (%.2f,%.2f)"%(x1,y1)
        #print "slopes: [ %.2f  %.2f]"%slopes

        def coord_pm(m) :
            def coord(y) : return np.array([0.5*(y*y + Wm2) / x0 - 0.5*x0, y, 1]).transpose()
            disc = math.sqrt( 1 -2*m*y1/x0 +  m**2 * (2*x1/x0 +1 - massW**2/x0**2 ) )
            return tuple( coord(y) for y in  x0/m*np.array([1+disc,1-disc]) )

        for slope in slopes :
            try :
                for coord in coord_pm(slope) :
                    #print coord.transpose().dot(A_munu).dot(coord)
                    print coord.transpose().dot(A_b).dot(coord)
            except ValueError :
                print "Invalid"
