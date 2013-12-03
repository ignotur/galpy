#The DF of a tidal stream
import numpy
import multiprocessing
from scipy import special
from galpy.orbit import Orbit
from galpy.util import bovy_coords, stable_cholesky, bovy_conversion, multi
class streamdf:
    """The DF of a tidal stream"""
    def __init__(self,sigv,progenitor=None,pot=None,aA=None,
                 tdisrupt=None,sigMeanOffset=6.,deltaAngle=0.3,leading=True,
                 sigangle=None,
                 deltaAngleTrack=1.5,nTrackChunks=11,
                 Vnorm=220.,Rnorm=8.,
                 R0=8.,Zsun=0.025,vsun=[-11.1,8.*30.24,7.25],
                 multi=None):
        """
        NAME:
           __init__
        PURPOSE:
           Initialize a quasi-isothermal DF
        INPUT:
           sigv - radial velocity dispersion of the progenitor
           tdisrupt= (5 Gyr) time since start of disruption (natural units)
           leading= (True) if True, model the leading part of the stream
                           if False, model the trailing part
           progenitor= progenitor orbit as Orbit instance 
           pot= Potential instance or list thereof
           aA= actionAngle instance used to convert (x,v) to actions
           sigMeanOffset= (6.) offset between the mean of the frequencies
                          and the progenitor, in units of the largest 
                          eigenvalue of the frequency covariance matrix 
                          (along the largest eigenvector), should be positive;
                          to model the trailing part, set leading=False
           deltaAngle= (0.3) estimate of 'dispersion' in largest angle
           sigangle= (sigv/100) estimate of the angle spread of the debris 
                     initially
           deltaAngleTrack= (1.5) angle to estimate the stream track over (rad)
           nTrackChunks= (11) number of chunks to divide the progenitor track in
           multi= (None) if set, use multi-processing

           Coordinate transformation inputs:
              Vnorm= (220) circular velocity to normalize velocities with
              Rnorm= (8) Galactocentric radius to normalize positions with
              R0= (8) Galactocentric radius of the Sun (kpc)
              Zsun= (0.025) Sun's height above the plane (kpc)
              vsun= ([-11.1,241.92,7.25]) Sun's motion in cylindrical coordinates (vR positive away from center)

        OUTPUT:
           object
        HISTORY:
           2013-09-16 - Started - Bovy (IAS)
           2013-11-25 - Started over - Bovy (IAS)
        """
        self._sigv= sigv
        if tdisrupt is None:
            self._tdisrupt= 5./bovy_conversion.time_in_Gyr(Vnorm,Rnorm)
        else:
            self._tdisrupt= tdisrupt
        self._sigMeanOffset= sigMeanOffset
        self._deltaAngle= deltaAngle
        if pot is None:
            raise IOError("pot= must be set")
        self._pot= pot
        self._aA= aA
        self._progenitor= progenitor
        self._multi= multi
        #Progenitor orbit: Calculate actions, frequencies, and angles for the progenitor
        acfs= aA.actionsFreqsAngles(self._progenitor,maxn=3)
        self._progenitor_jr= acfs[0][0]
        self._progenitor_lz= acfs[1][0]
        self._progenitor_jz= acfs[2][0]
        self._progenitor_Omegar= acfs[3]
        self._progenitor_Omegaphi= acfs[4]
        self._progenitor_Omegaz= acfs[5]
        self._progenitor_Omega= numpy.array([acfs[3],acfs[4],acfs[5]]).reshape(3)
        self._progenitor_angler= acfs[6]
        self._progenitor_anglephi= acfs[7]
        self._progenitor_anglez= acfs[8]
        self._progenitor_angle= numpy.array([acfs[6],acfs[7],acfs[8]]).reshape(3)
        #Calculate dO/dJ Jacobian at the progenitor
        self._dOdJp= calcaAJac(self._progenitor._orb.vxvv,
                               self._aA,dxv=None,dOdJ=True,
                               _initacfs=acfs)
        #From the progenitor orbit, determine the sigmas in J and angle
        self._sigjr= (self._progenitor.rap()-self._progenitor.rperi())/numpy.pi*self._sigv
        self._siglz= self._progenitor.rperi()*self._sigv
        self._sigjz= 2.*self._progenitor.zmax()/numpy.pi*self._sigv
        #Estimate the frequency covariance matrix from a diagonal J matrix x dOdJ
        self._sigjmatrix= numpy.diag([self._sigjr**2.,
                                      self._siglz**2.,
                                      self._sigjz**2.])
        self._sigomatrix= numpy.dot(self._dOdJp,
                                    numpy.dot(self._sigjmatrix,self._dOdJp.T))
        #Estimate angle spread as the ratio of the largest to the middle eigenvalue
        self._sigomatrixEig= numpy.linalg.eig(self._sigomatrix)
        self._sortedSigOEig= sorted(self._sigomatrixEig[0])
        if sigangle is None:
            self._sigangle= self._sigv/100.
        else:
            self._sigangle= sigangle
        self._sigangle2= self._sigangle**2.
        self._lnsigangle= numpy.log(self._sigangle)
        #Estimate the frequency mean as lying along the direction of the largest eigenvalue
        self._dsigomeanProgDirection= self._sigomatrixEig[1][:,numpy.argmax(self._sigomatrixEig[0])]
        self._progenitor_Omega_along_dOmega= \
            numpy.dot(self._progenitor_Omega,self._dsigomeanProgDirection)
        #Make sure we are modeling the correct part of the stream
        self._leading= leading
        self._sigMeanSign= 1.
        if self._leading and self._progenitor_Omega_along_dOmega < 0.:
            self._sigMeanSign= -1.
        elif not self._leading and self._progenitor_Omega_along_dOmega > 0.:
            self._sigMeanSign= -1.
        self._progenitor_Omega_along_dOmega*= self._sigMeanSign 
        self._sigomean= self._progenitor_Omega\
            +self._sigMeanOffset*self._sigMeanSign\
            *numpy.sqrt(numpy.amax(self._sigomatrixEig[0]))\
            *self._dsigomeanProgDirection
#numpy.dot(self._dOdJp,
#                          numpy.array([self._sigjr,self._siglz,self._sigjz]))
        self._dsigomeanProg= self._sigomean-self._progenitor_Omega
        #Store cholesky of sigomatrix for fast evaluation
        self._sigomatrixL= stable_cholesky(self._sigomatrix,10.**-8.)
        self._sigomatrixDet= numpy.linalg.det(self._sigomatrix)
        #Determine the stream track
        self._Vnorm= Vnorm
        self._Rnorm= Rnorm
        self._R0= R0
        self._Zsun= Zsun
        self._vsun= vsun
        self._determine_stream_track(deltaAngleTrack,nTrackChunks)
        return None

    def estimateTdisrupt(self,deltaAngle):
        """
        NAME:
           estimateTdisrupt
        PURPOSE:
           estimate the time of disruption
        INPUT:
           deltaAngle- spread in angle since disruption
        OUTPUT:
           time in natural units
        HISTORY:
           2013-11-27 - Written - Bovy (IAS)
        """
        return deltaAngle\
            /numpy.sqrt(numpy.sum(self._dsigomeanProg**2.))

    def _determine_stream_track(self,deltaAngleTrack,nTrackChunks):
        """Determine the track of the stream in real space"""
        #Determine how much orbital time is necessary for the progenitor's orbit to cover the stream
        self._deltaAngleTrack= deltaAngleTrack
        self._nTrackChunks= nTrackChunks
        dt= self._deltaAngleTrack\
            /self._progenitor_Omega_along_dOmega
        self._trackts= numpy.linspace(0.,dt,self._nTrackChunks)
        #Instantiate another Orbit for the progenitor orbit where there is data
        #This can be somewhat sped up by re-using the previously integrated
        #progenitor orbit, but because the computational cost is dominated
        #by the calculation of the Jacobian, this does not gain much (~few %)
        if dt < 0.:
            self._trackts= numpy.linspace(0.,-dt,self._nTrackChunks)
            #Flip velocities before integrating
            self._progenitorTrack= Orbit([self._progenitor.R(0.),
                                          -self._progenitor.vR(0.),
                                          -self._progenitor.vT(0.),
                                          self._progenitor.z(0.),
                                          -self._progenitor.vz(0.),
                                          self._progenitor.phi(0.)])
        else:
            self._progenitorTrack= self._progenitor(0.)
        self._progenitorTrack.integrate(self._trackts,self._pot)
        if dt < 0.:
            #Flip velocities again
            self._progenitorTrack._orb.orbit[:,1]= -self._progenitorTrack._orb.orbit[:,1]
            self._progenitorTrack._orb.orbit[:,2]= -self._progenitorTrack._orb.orbit[:,2]
            self._progenitorTrack._orb.orbit[:,4]= -self._progenitorTrack._orb.orbit[:,4]
        #Now calculate the actions, frequencies, and angles + Jacobian for each chunk
        allAcfsTrack= numpy.empty((self._nTrackChunks,9))
        alljacsTrack= numpy.empty((self._nTrackChunks,6,6))
        allinvjacsTrack= numpy.empty((self._nTrackChunks,6,6))
        thetasTrack= numpy.linspace(0.,self._deltaAngleTrack,
                                    self._nTrackChunks)
        ObsTrack= numpy.empty((self._nTrackChunks,6))
        if self._multi is None:
            for ii in range(self._nTrackChunks):
                multiOut= _determine_stream_track_single(self._aA,
                                                         self._progenitorTrack,
                                                         self._trackts[ii],
                                                         self._progenitor_angle,
                                                         self._sigMeanSign,
                                                         self._dsigomeanProgDirection,
                                                         self.meanOmega,
                                                         thetasTrack[ii])
                allAcfsTrack[ii,:]= multiOut[0]
                alljacsTrack[ii,:,:]= multiOut[1]
                allinvjacsTrack[ii,:,:]= multiOut[2]
                ObsTrack[ii,:]= multiOut[3]
        else:
            multiOut= multi.parallel_map(\
                (lambda x: _determine_stream_track_single(self._aA,self._progenitorTrack,self._trackts[x],
                                                          self._progenitor_angle,
                                                          self._sigMeanSign,
                                                          self._dsigomeanProgDirection,
                                                          self.meanOmega,
                                                          thetasTrack[x])),
                range(self._nTrackChunks),
                numcores=numpy.amin([self._nTrackChunks,
                                     multiprocessing.cpu_count(),
                                     self._multi]))
            for ii in range(self._nTrackChunks):
                allAcfsTrack[ii,:]= multiOut[ii][0]
                alljacsTrack[ii,:,:]= multiOut[ii][1]
                allinvjacsTrack[ii,:,:]= multiOut[ii][2]
                ObsTrack[ii,:]= multiOut[ii][3]
        self._thetasTrack= thetasTrack
        self._ObsTrack= ObsTrack
        self._allAcfsTrack= allAcfsTrack
        self._alljacsTrack= alljacsTrack
        self._allinvjacsTrack= allinvjacsTrack
        return None

    def calc_stream_lb(self,
                       Vnorm=None,Rnorm=None,
                       R0=None,Zsun=None,vsun=None):
        """
        NAME:
           calc_stream_lb
        PURPOSE:
           convert the stream track to observational coordinates and store
        INPUT:
           Coordinate transformation inputs (all default to the instance-wide
           values):
              Vnorm= circular velocity to normalize velocities with
              Rnorm= Galactocentric radius to normalize positions with
              R0= Galactocentric radius of the Sun (kpc)
              Zsun= Sun's height above the plane (kpc)
              vsun= Sun's motion in cylindrical coordinates (vR positive away from center)
        OUTPUT:
           (none)
        HISTORY:
           2013-12-02 - Written - Bovy (IAS)
        """
        if Vnorm is None:
            Vnorm= self._Vnorm
        if Rnorm is None:
            Rnorm= self._Rnorm
        if R0 is None:
            R0= self._R0
        if Zsun is None:
            Zsun= self._Zsun
        if vsun is None:
            vsun= self._vsun
        self._ObsTrackLB= numpy.empty_like(self._ObsTrack)
        XYZ= bovy_coords.galcencyl_to_XYZ(self._ObsTrack[:,0]*Rnorm,
                                          self._ObsTrack[:,5],
                                          self._ObsTrack[:,3]*Rnorm,
                                          Xsun=R0,Zsun=Zsun)
        vXYZ= bovy_coords.galcencyl_to_vxvyvz(self._ObsTrack[:,1]*Vnorm,
                                              self._ObsTrack[:,2]*Vnorm,
                                              self._ObsTrack[:,4]*Vnorm,
                                              self._ObsTrack[:,5],
                                              vsun=vsun)
        slbd=bovy_coords.XYZ_to_lbd(XYZ[0],XYZ[1],XYZ[2],
                                    degree=True)
        svlbd= bovy_coords.vxvyvz_to_vrpmllpmbb(vXYZ[0],vXYZ[1],vXYZ[2],
                                                slbd[:,0],slbd[:,1],slbd[:,2],
                                                degree=True)
        self._ObsTrackLB[:,0]= slbd[:,0]
        self._ObsTrackLB[:,1]= slbd[:,1]
        self._ObsTrackLB[:,2]= slbd[:,2]
        self._ObsTrackLB[:,3]= svlbd[:,0]
        self._ObsTrackLB[:,4]= svlbd[:,1]
        self._ObsTrackLB[:,5]= svlbd[:,2]
        return None

    def meanOmega(self,dangle,oned=False):
        """
        NAME:
           meanOmega
        PURPOSE:
           calculate the mean frequency as a function of angle, assuming a 
           uniform time distribution up to a maximum time
        INPUT:
           dangle - angle offset
           oned= (False) if True, return the 1D offset from the progenitor
                         (along the direction of disruption)
        OUTPUT:
           mean Omega
        HISTORY:
           2013-12-01 - Written - Bovy (IAS)
        """
        dOmin= dangle/self._tdisrupt
        meandO= self._sigMeanOffset\
            *numpy.sqrt(numpy.amax(self._sigomatrixEig[0]))
        dO1D= ((numpy.sqrt(2./numpy.pi)*numpy.sqrt(self._sortedSigOEig[2])\
                   *numpy.exp(-(meandO-dOmin)**2.\
                                   /2./self._sortedSigOEig[2])/
                (1.+special.erf((meandO-dOmin)\
                                    /numpy.sqrt(2.*self._sortedSigOEig[2]))))\
                   +meandO)
        if oned: return dO1D
        else:
            return self._progenitor_Omega+dO1D*self._dsigomeanProgDirection\
                *self._sigMeanSign

    def __call__(self,*args,**kwargs):
        """
        NAME:
           __call__
        PURPOSE:
           evaluate the DF
        INPUT:
           Either:
              a)(jr,lz,jz,Omegar,Omegaphi,Omegaz,angler,anglephi,anglez) tuple
                 where:
                    jr - radial action
                    lz - z-component of angular momentum
                    jz - vertical action
                    Omegar - radial frequency
                    Omegaphi - azimuthal frequency
                    Omegaz - vertical frequency
                    angler - radial angle
                    anglephi - azimuthal angle
                    anglez - vertical angle
              b) R,vR,vT,z,vz,phi ndarray [nobjects,ntimes]
              c) Orbit instance or list thereof
           log= if True, return the natural log
           rect= if True, R,vR,vT,z,vz,phi is actually X,Y,Z,vX,vY,vZ
        OUTPUT:
           value of DF
        HISTORY:
           2013-09-16 - Written - Bovy (IAS)
        """
        return self._callActionAngleMethod(*args,**kwargs)

    def _callActionAngleMethod(self,*args,**kwargs):
        """Evaluate the DF using the action-angle formalism"""
        #First parse log
        if kwargs.has_key('log'):
            log= kwargs['log']
            kwargs.pop('log')
        else:
            log= False
        djr,dlz,djz,dOr,dOphi,dOz,dar,daphi,daz= self.prepData4aA(*args,**kwargs)
        no= len(djr)
        logdfJ= numpy.sum(-0.5*(1./self._sigjr2*djr**2.
                                +1./self._siglz2*dlz**2.
                                +1./self._sigjz2*djz**2.))\
                                -no*(self._lnsigjr+self._lnsiglz+self._lnsigjz)
        da2= dar**2.+daphi**2.+daz**2.
        do2= dOr**2.+dOphi**2.+dOz**2.
        doa= dar*dOr+daphi*dOphi+daz*dOz
        logdfA= numpy.sum(-0.5/self._sigangle2*(da2-doa**2./do2)\
                               -0.5*numpy.log(do2))-2.*no*self._lnsigangle
        out= logdfA+logdfJ
        if log:
            return out
        else:
            return numpy.exp(out)

    def prepData4aA(self,*args,**kwargs):
        """
        NAME:
           prepData4aA
        PURPOSE:
           prepare stream data for the action-angle method
        INPUT:
           __call__ inputs
        OUTPUT:
           djr,dlz,djz,dOmegar,dOmegaphi,dOmegaz,dangler,danglephi,danglez; each [nobj,ntimes]; differences wrt the progenitor
        HISTORY:
           2013-09-17 - Written - Bovy (IAS)
        """
        if len(args) == 9: #actions, frequencies, and angles are given
            return args
        R,vR,vT,z,vz,phi= self._parse_call_args(False,*args)
        jr,lz,jz,Or,Ophi,Oz,ar,aphi,az= self._aA.actionsFreqsAngles(R,vR,vT,z,vz,phi,maxn=3)
        djr= jr-self._progenitor_jr
        dlz= lz-self._progenitor_lz
        djz= jz-self._progenitor_jz
        dOr= Or-self._progenitor_Omegar
        dOphi= Ophi-self._progenitor_Omegaphi
        dOz= Oz-self._progenitor_Omegaz
        dar= ar-self._progenitor_angler
        daphi= aphi-self._progenitor_anglephi
        daz= az-self._progenitor_anglez
        #Assuming single wrap, resolve large angle differences (wraps should be marginalized over)
        dar[(dar < -4.)]+= 2.*numpy.pi
        dar[(dar > 4.)]-= 2.*numpy.pi
        daphi[(daphi < -4.)]+= 2.*numpy.pi
        daphi[(daphi > 4.)]-= 2.*numpy.pi
        daz[(daz < -4.)]+= 2.*numpy.pi
        daz[(daz > 4.)]-= 2.*numpy.pi
        return (djr,dlz,djz,dOr,dOphi,dOz,dar,daphi,daz)

    def _parse_call_args(self,directIntegration=True,*args):
        """Helper function to parse the arguments to the __call__ and related functions"""
        if len(args) == 5:
            raise IOError("Must specify phi for streamdf")
        elif len(args) == 6:
            return args
        elif isinstance(args[0],Orbit):
            o= args[0]
            return (o.R(),o.vR(),o.vT(),o.z(),o.vz(),o.phi())
        elif isinstance(args[0],list) and isinstance(args[0][0],Orbit):
            R, vR, vT, z, vz, phi= [], [], [], [], [], []
            for o in args[0]:
                R.append(o.R())
                vR.append(o.vR())
                vT.append(o.vT())
                z.append(o.z())
                vz.append(o.vz())
                phi.append(o.phi())
        return (numpy.array(R),numpy.array(vR),numpy.array(vT),
                numpy.array(z),numpy.array(vz),numpy.array(phi))

def _determine_stream_track_single(aA,progenitorTrack,trackt,
                                   progenitor_angle,sigMeanSign,
                                   dsigomeanProgDirection,meanOmega,
                                   thetasTrack):
    #Setup output
    allAcfsTrack= numpy.empty((9))
    alljacsTrack= numpy.empty((6,6))
    allinvjacsTrack= numpy.empty((6,6))
    ObsTrack= numpy.empty((6))
    #Calculate
    tacfs= aA.actionsFreqsAngles(progenitorTrack(trackt),
                                       maxn=3)
    allAcfsTrack[0]= tacfs[0][0]
    allAcfsTrack[1]= tacfs[1][0]
    allAcfsTrack[2]= tacfs[2][0]
    for jj in range(3,9):
        allAcfsTrack[jj]= tacfs[jj]
    tjac= calcaAJac(progenitorTrack(trackt)._orb.vxvv,
                    aA,
                    dxv=None,freqs=True,
                    lb=False,
                    _initacfs=tacfs)
    alljacsTrack[:,:]= tjac
    tinvjac= numpy.linalg.inv(tjac)
    allinvjacsTrack[:,:]= tinvjac
    theseAngles= numpy.mod(progenitor_angle\
                               +thetasTrack\
                               *sigMeanSign\
                               *dsigomeanProgDirection,
                           2.*numpy.pi)
    diffAngles= theseAngles-allAcfsTrack[6:]
    diffAngles[(diffAngles > numpy.pi)]= diffAngles[(diffAngles > numpy.pi)]-2.*numpy.pi
    diffAngles[(diffAngles < -numpy.pi)]= diffAngles[(diffAngles < -numpy.pi)]+2.*numpy.pi
    thisFreq= meanOmega(thetasTrack)
    diffFreqs= thisFreq-allAcfsTrack[3:6]
    ObsTrack[:]= numpy.dot(tinvjac,
                              numpy.hstack((diffFreqs,diffAngles)))
    ObsTrack[0]+= \
        progenitorTrack(trackt).R()
    ObsTrack[1]+= \
        progenitorTrack(trackt).vR()
    ObsTrack[2]+= \
        progenitorTrack(trackt).vT()
    ObsTrack[3]+= \
        progenitorTrack(trackt).z()
    ObsTrack[4]+= \
        progenitorTrack(trackt).vz()
    ObsTrack[5]+= \
        progenitorTrack(trackt).phi()
    return [allAcfsTrack,alljacsTrack,allinvjacsTrack,ObsTrack]

def calcaAJac(xv,aA,dxv=None,freqs=False,dOdJ=False,actionsFreqsAngles=False,
              lb=False,coordFunc=None,
              Vnorm=220.,Rnorm=8.,R0=8.,Zsun=0.025,vsun=[-11.1,8.*30.24,7.25],
              _initacfs=None):
    """
    NAME:
       calcaAJac
    PURPOSE:
       calculate the Jacobian d(J,theta)/d(x,v)
    INPUT:
       xv - phase-space point: Either
          1) [R,vR,vT,z,vz,phi]
          2) [l,b,D,vlos,pmll,pmbb] (if lb=True, see below)
          3) list/array of 6 numbers that can be transformed into (normalized) R,vR,vT,z,vz,phi using coordFunc

       aA - actionAngle instance

       dxv - infinitesimal to use (rescaled for lb, so think fractionally))

       freqs= (False) if True, go to frequencies rather than actions

       dOdJ= (False), actually calculate d Frequency / d action

       actionsFreqsAngles= (False) if True, calculate d(action,freq.,angle)/d (xv)

       lb= (False) if True, start with (l,b,D,vlos,pmll,pmbb) in (deg,deg,kpc,km/s,mas/yr,mas/yr)
       Vnorm= (220) circular velocity to normalize with when lb=True
       Rnorm= (8) Galactocentric radius to normalize with when lb=True
       R0= (8) Galactocentric radius of the Sun (kpc)
       Zsun= (0.025) Sun's height above the plane (kpc)
       vsun= ([-11.1,241.92,7.25]) Sun's motion in cylindrical coordinates (vR positive away from center)

       coordFunc= (None) if set, this is a function that takes xv and returns R,vR,vT,z,vz,phi in normalized units (units where vc=1 at r=1 if the potential is normalized that way, for example)

    OUTPUT:
       Jacobian matrix
    HISTORY:
       2013-11-25 - Written - Bovy (IAS) 
    """
    if lb:
        coordFunc= lambda x: lbCoordFunc(xv,Vnorm,Rnorm,R0,Zsun,vsun)
    if not coordFunc is None:
        R, vR, vT, z, vz, phi= coordFunc(xv)
    else:
        R, vR, vT, z, vz, phi= xv[0],xv[1],xv[2],xv[3],xv[4],xv[5]
    if dxv is None:
        dxv= 10.**-8.*numpy.ones(6)
    if lb:
        #Re-scale some of the differences, to be more natural
        dxv[0]*= 180./numpy.pi
        dxv[1]*= 180./numpy.pi
        dxv[2]*= Rnorm
        dxv[3]*= Vnorm
        dxv[4]*= Vnorm/4.74047/xv[2]
        dxv[5]*= Vnorm/4.74047/xv[2]
    if actionsFreqsAngles:
        jac= numpy.zeros((9,6))
    else:
        jac= numpy.zeros((6,6))
    if dOdJ:
        jac2= numpy.zeros((6,6))
    if _initacfs is None:
        jr,lz,jz,Or,Ophi,Oz,ar,aphi,az\
            = aA.actionsFreqsAngles(R,vR,vT,z,vz,phi,maxn=3)
    else:
        jr,lz,jz,Or,Ophi,Oz,ar,aphi,az\
            = _initacfs
    for ii in range(6):
        temp= xv[ii]+dxv[ii] #Trick to make sure dxv is representable
        dxv[ii]= temp-xv[ii]
        xv[ii]+= dxv[ii]
        if not coordFunc is None:
            tR, tvR, tvT, tz, tvz, tphi= coordFunc(xv)
        else:
            tR, tvR, tvT, tz, tvz, tphi= xv[0],xv[1],xv[2],xv[3],xv[4],xv[5]
        tjr,tlz,tjz,tOr,tOphi,tOz,tar,taphi,taz\
            = aA.actionsFreqsAngles(tR,tvR,tvT,tz,tvz,tphi,maxn=3)
        xv[ii]-= dxv[ii]
        angleIndx= 3
        if actionsFreqsAngles:
            jac[0,ii]= (tjr-jr)/dxv[ii]
            jac[1,ii]= (tlz-lz)/dxv[ii]
            jac[2,ii]= (tjz-jz)/dxv[ii]
            jac[3,ii]= (tOr-Or)/dxv[ii]
            jac[4,ii]= (tOphi-Ophi)/dxv[ii]
            jac[5,ii]= (tOz-Oz)/dxv[ii]           
            angleIndx= 6
        elif freqs:
            jac[0,ii]= (tOr-Or)/dxv[ii]
            jac[1,ii]= (tOphi-Ophi)/dxv[ii]
            jac[2,ii]= (tOz-Oz)/dxv[ii]
        else:        
            jac[0,ii]= (tjr-jr)/dxv[ii]
            jac[1,ii]= (tlz-lz)/dxv[ii]
            jac[2,ii]= (tjz-jz)/dxv[ii]
        if dOdJ:
            jac2[0,ii]= (tOr-Or)/dxv[ii]
            jac2[1,ii]= (tOphi-Ophi)/dxv[ii]
            jac2[2,ii]= (tOz-Oz)/dxv[ii]
        #For the angles, make sure we do not hit a turning point
        if tar-ar > numpy.pi:
            jac[angleIndx,ii]= (tar-ar-2.*numpy.pi)/dxv[ii]
        elif tar-ar < -numpy.pi:
            jac[angleIndx,ii]= (tar-ar+2.*numpy.pi)/dxv[ii]
        else:
            jac[angleIndx,ii]= (tar-ar)/dxv[ii]
        if taphi-aphi > numpy.pi:
            jac[angleIndx+1,ii]= (taphi-aphi-2.*numpy.pi)/dxv[ii]
        elif taphi-aphi < -numpy.pi:
            jac[angleIndx+1,ii]= (taphi-aphi+2.*numpy.pi)/dxv[ii]
        else:
            jac[angleIndx+1,ii]= (taphi-aphi)/dxv[ii]
        if taz-az > numpy.pi:
            jac[angleIndx+2,ii]= (taz-az-2.*numpy.pi)/dxv[ii]
        if taz-az < -numpy.pi:
            jac[angleIndx+2,ii]= (taz-az+2.*numpy.pi)/dxv[ii]
        else:
            jac[angleIndx+2,ii]= (taz-az)/dxv[ii]
    if dOdJ:
        jac2[3,:]= jac[3,:]
        jac2[4,:]= jac[4,:]
        jac2[5,:]= jac[5,:]
        jac= numpy.dot(jac2,numpy.linalg.inv(jac))[0:3,0:3]
    return jac

def _mylogsumexp(arr,axis=0):
    """Faster logsumexp?"""
    minarr= numpy.amax(arr,axis=axis)
    if axis == 1:
        minarr= numpy.reshape(minarr,(arr.shape[0],1))
    if axis == 0:
        minminarr= numpy.tile(minarr,(arr.shape[0],1))
    elif axis == 1:
        minminarr= numpy.tile(minarr,(1,arr.shape[1]))
    elif axis == None:
        minminarr= numpy.tile(minarr,arr.shape)
    else:
        raise NotImplementedError("'_mylogsumexp' not implemented for axis > 2")
    if axis == 1:
        minarr= numpy.reshape(minarr,(arr.shape[0]))
    return minarr+numpy.log(numpy.sum(numpy.exp(arr-minminarr),axis=axis))

def lbCoordFunc(xv,Vnorm,Rnorm,R0,Zsun,vsun):
    #Input is (l,b,D,vlos,pmll,pmbb) in (deg,deg,kpc,km/s,mas/yr,mas/yr)
    X,Y,Z= bovy_coords.lbd_to_XYZ(xv[0],xv[1],xv[2],degree=True)
    R,phi,Z= bovy_coords.XYZ_to_galcencyl(X,Y,Z,
                                          Xsun=R0,Ysun=0.,Zsun=Zsun)
    vx,vy,vz= bovy_coords.vrpmllpmbb_to_vxvyvz(xv[3],xv[4],xv[5],
                                               X,Y,Z,XYZ=True)
    vR,vT,vZ= bovy_coords.vxvyvz_to_galcencyl(vx,vy,vz,R,phi,Z,galcen=True,
                                              vsun=vsun)
    R/= Rnorm
    Z/= Rnorm
    vR/= Vnorm
    vT/= Vnorm
    vZ/= Vnorm
    return (R,vR,vT,Z,vZ,phi)
