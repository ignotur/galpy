###############################################################################
#   KuzminKutuzovStaeckelPotential.py: 
#           class that implements a simple Stäckel potential
#           generated by a Kuzmin-Kutuzov potential 
#                                   - amp                   
#               Phi(r)=  ---------------------------
#                        \sqrt{lambda} + \sqrt{nu}  
###############################################################################
import numpy as nu
from Potential import Potential
class KuzminKutuzovStaeckelPotential(Potential):
    """Class that implements the Kuzmin-Kutuzov Stäckel potential

    .. math::

        \\Phi(R,z) = \\frac{-\\mathrm{amp}}{\\sqrt{\\lambda} + \\sqrt{\\nu}}

    """
    def __init__(self,amp=1.,ac=5.,Delta=1.,normalize=False):
        """
        NAME:
            __init__
        PURPOSE:
            initialize a Kuzmin-Kutuzov Stäckel potential
        INPUT:
            amp - amplitude to be applied to the potential (default: 1)
            ac  - axis ratio of the coordinate surfaces 
                        (a/c) = sqrt(-alpha) / sqrt(-gamma) (default: ???)
            Delta - focal distance that defines the spheroidal coordinate system (default: ???)
                        Delta=sqrt(gamma-alpha)
           normalize - if True, normalize such that vc(1.,0.)=1., or, if given as a number, such that the force is this fraction of the force necessary to make vc(1.,0.)=1.
        OUTPUT:
           (none)
        HISTORY:
           2015-02-15 - Written - Trick (MPIA)
        """
        Potential.__init__(self,amp=amp)
        self._ac    = ac
        self._Delta = Delta
        self._gamma = self._Delta**2 / (1.-self_ac**2)
        self._alpha = self._gamma - self._Delta**2
        if normalize or \
                (isinstance(normalize,(int,float)) \
                     and not isinstance(normalize,bool)):
            self.normalize(normalize)
        self.hasC= True
        self.hasC_dxdv= True

    def _evaluate(self,R,z,phi=0.,t=0.):
        """
        NAME:
            _evaluate
        PURPOSE:
            evaluate the potential at R,z
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
            phi - azimuth
            t - time
        OUTPUT:
            Phi(R,z)
        HISTORY:
            2015-02-15 - Written - Trick (MPIA)
        """
        l,n = self._Rz_to_ln(R,z)
        return -1./(nu.sqrt(l) + nu.sqrt(n))

    def _Rforce(self,R,z,phi=0.,t=0.):
         """
        NAME:
            _Rforce
        PURPOSE:
            evaluate the radial force for this potential
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
            phi - azimuth
            t - time
        OUTPUT:
            the radial force = -dphi/dR
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        l,n  = self._Rz_to_ln(R,z,for_disk=True)
        return - (self._dldR(R,z) * self._lderiv(l,n) + \
                  self._dndR(R,z) * self._nderiv(l,n))

    def _zforce(self,R,z,phi=0.,t=0.):
        """
        NAME:
            _zforce
        PURPOSE:
            evaluate the vertical force for this potential
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
            phi - azimuth
            t - time
        OUTPUT:
            the vertical force
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        l,n  = self._Rz_to_ln(R,z,for_disk=True)
        return - (self._dldz(R,z) * self._lderiv(l,n) + \
                  self._dndz(R,z) * self._nderiv(l,n))

    def _R2deriv(self,R,z,phi=0.,t=0.):
        """
        NAME:
            _Rderiv
        PURPOSE:
            evaluate the second radial derivative for this potential
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
            phi - azimuth
            t - time
        OUTPUT:
            the second radial derivative
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        dldR    = self._dldR  (R,z)
        dndR    = self._dndR  (R,z)
        l,n     = self._Rz_to_ln(R,z,for_disk=True)
        return self._d2ldR2(R,z)*self._lderiv(l,n)  + \
               self._d2ndR2(R,z)*self._nderiv(l,n)  + \
               (dldR)**2        *self._l2deriv(l,n) + \
               (dndR)**2        *self._n2deriv(l,n) + \
               2.*dldR*dndR     *self._nlderiv(l,n)

    def _z2deriv(self,R,z,phi=0.,t=0.):
        """
        NAME:
            _z2deriv
        PURPOSE:
            evaluate the second vertical derivative for this potential
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
            phi - azimuth
            t- time
        OUTPUT:
            the second vertical derivative
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """        
        dldz    = self._dldz  (R,z)
        dndz    = self._dndz  (R,z)
        l,n     = self._Rz_to_ln(R,z,for_disk=True)
        return self._d2ldz2(R,z)*self._lderiv(l,n)  + \
               self._d2ndz2(R,z)*self._nderiv(l,n)  + \
               (dldz)**2        *self._l2deriv(l,n) + \
               (dndz)**2        *self._n2deriv(l,n) + \
               2.*dldz*dndz     *self._nlderiv(l,n)


    def _Rzderiv(self,R,z,phi=0.,t=0.):
        """
        NAME:
            _Rzderiv
        PURPOSE:
            evaluate the mixed R,z derivative for this potential
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
            phi - azimuth
            t- time
        OUTPUT:
            d2phi/dR/dz
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """    
        dldR    = self._dldR(R,z)
        dldz    = self._dldz(R,z)
        dndR    = self._dndR(R,z)
        dndz    = self._dndz(R,z)
        l,n     = self._Rz_to_ln(R,z,for_disk=True)
        return self._d2ldRdz(R,z)   *self._lderiv(l,n)  + \
               self._d2ndRdz(R,z)   *self._nderiv(l,n)  + \
               dldR*dldz            *self._l2deriv(l,n) + \
               dndR*dndz            *self._n2deriv(l,n) + \
               (dldR*dndz+dldz*dndR)*self._lnderiv(l,n)

    def _lderiv(self,l,n):
        """
        NAME:
            _lderiv
        PURPOSE:
            evaluate the derivative w.r.t. lambda for this potential
        INPUT:
            l - prolate spheroidal coordinate lambda
            n - prolate spheroidal coordinate nu
        OUTPUT:
            derivative w.r.t. lambda
        HISTORY:
            2015-02-15 - Written - Trick (MPIA)
        """
        return 0.5/nu.sqrt(l)/(nu.sqrt(l)+nu.sqrt(n))**2

    def _nderiv(self,l,n):
        """
        NAME:
            _nderiv
        PURPOSE:
            evaluate the derivative w.r.t. nu for this potential
        INPUT:
            l - prolate spheroidal coordinate lambda
            n - prolate spheroidal coordinate nu
        OUTPUT:
            derivative w.r.t. nu
        HISTORY:
            2015-02-15 - Written - Trick (MPIA)
        """
        return 0.5/nu.sqrt(n)/(nu.sqrt(l)+nu.sqrt(n))**2

    def _l2deriv(self,l,n):
        """
        NAME:
            _l2deriv
        PURPOSE:
            evaluate the second derivative w.r.t. lambda for this potential
        INPUT:
            l - prolate spheroidal coordinate lambda
            n - prolate spheroidal coordinate nu
        OUTPUT:
            second derivative w.r.t. lambda
        HISTORY:
            2015-02-15 - Written - Trick (MPIA)
        """
        numer = -3.*nu.sqrt(l) - nu.sqrt(n)
        denom = 4. * l**1.5 * (nu.sqrt(l)+nu.sqrt(n))**3
        return numer / denom

    def _n2deriv(self,l,n):
        """
        NAME:
            _n2deriv
        PURPOSE:
            evaluate the second derivative w.r.t. nu for this potential
        INPUT:
            l - prolate spheroidal coordinate lambda
            n - prolate spheroidal coordinate nu
        OUTPUT:
            second derivative w.r.t. nu
        HISTORY:
            2015-02-15 - Written - Trick (MPIA)
        """
        numer = -nu.sqrt(l) - 3.*nu.sqrt(n)
        denom = 4. * n**1.5 * (nu.sqrt(l)+nu.sqrt(n))**3
        return numer / denom

    def _lnderiv(self,l,n):
        """
        NAME:
            _lnderiv
        PURPOSE:
            evaluate the mixed derivative w.r.t. lambda and nu for this potential
        INPUT:
            l - prolate spheroidal coordinate lambda
            n - prolate spheroidal coordinate nu
        OUTPUT:
            d2phi/dl/dn
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        return -0.5/(nu.sqrt(l) * nu.sqrt(n) * (nu.sqrt(l)+nu.sqrt(n))**3)

        
    def _ln_to_Rz(self,l,n):
        """
        NAME:
            _ln_to_Rz
        PURPOSE:
            convert the prolate spheroidal coordinates (lambda,nu) into
            galactocentric cylindrical coordinates (R,z)
            following the conversion eq. (2.2) in Dejonghe & de Zeeuw (1988a)
        INPUT:
            l        - prolate spheroidal coordinate lambda
            n        - prolate spheroidal coordinate nu
            for_disk - if set to True (default), use alpha and gamma for the 
                       disk component. These are the coordinates used in 
                       Batsleer & Dejonghe (1994).If set to False, use alpha 
                       and gamma for the halo component.
        OUTPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        a = self._alpha
        g = self._gamma
        r2 = (l + a) * (n + a) / (a - g)
        z2 = (l + g) * (n + g) / (g - a)
        if math.isnan(nu.sqrt(r2)) and (n+a) > 0. and (n+a) < 1e-10:
            r2 = 0.
        if math.isnan(nu.sqrt(z2)) and (n+g) < 0. and (n+g) > 1e-10:
            z2 = 0.
        return nu.sqrt(r2),nu.sqrt(z2)


    def _Rz_to_ln(self,R,z):
        """
        NAME:
            _Rz_to_ln
        PURPOSE:
            convert the galactocentric cylindrical coordinates (R,z) into
            prolate spheroidal coordinates (lambda,nu)
            by solving eq. (2.2) in Dejonghe & de Zeeuw (1988a) for (lambda,nu):
                R^2 = (l+a) * (n+a) / (a-g)
                z^2 = (l+g) * (n+g) / (g-a)
                Delta^2 = g-a
        INPUT:
            R        - Galactocentric cylindrical radius
            z        - vertical height
            for_disk - if set to True (default), use alpha and gamma for the 
                       disk component. These are the coordinates used in 
                       Batsleer & Dejonghe (1994).If set to False, use alpha 
                       and gamma for the halo component.
        OUTPUT:
            l - prolate spheroidal coordinate lambda
            n - prolate spheroidal coordinate nu
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        if z == 0.:
            l = R**2 - self._alpha
            n = -self._gamma
        else:
            term  =  R**2 + z**2 - self._alpha - self._gamma    # > 0
            discr = (R**2 + z**2 - self._Delta**2)**2 + (4. * self._Delta**2 * R**2)    # > 0
            l = 0.5 * (term + nu.sqrt(discr))  
            n = 0.5 * (term - nu.sqrt(discr))
        #if (n + self._gamma) < 0. or (n + self._gamma) > self._Delta**2 or (l + self._alpha) < 0.:
        #    print "nu     + gamma =  Delta**2 * cos **2(v) = ", n+gamma
        #    print "lambda + alpha =  Delta**2 * sinh**2(u) = ", l+alpha
        #    print "nu     + alpha = -Delta**2 * sin **2(v) = ", n+alpha
        #    sys.exit("Error in KuzminKutuzovStaeckelPotential._Rz_to_ln(): "+
        #             "nu and/or lambda out of bounds.")
        return l,n

    def _dldR(self,R,z):
        """
        NAME:
            _dldR
        PURPOSE:
            evaluate the derivative of lambda w.r.t. R
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d lambda / dR
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        discr =          (R**2 + z**2 - self._Delta**2)**2 + (4. * self._Delta**2 * R**2)
        return R * (1. + (R**2 + z**2 + self._Delta**2) / nu.sqrt(discr))

    def _dndR(self,R,z):
        """
        NAME:
            _dndR
        PURPOSE:
            evaluate the derivative of nu w.r.t. R
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d nu / dR
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        discr =          (R**2 + z**2 - self._Delta**2)**2 + (4. * self._Delta**2 * R**2)
        return R * (1. - (R**2 + z**2 + self._Delta**2) / nu.sqrt(discr))

    def _dldz(self,R,z):
        """
        NAME:
            _dldz
        PURPOSE:
            evaluate the derivative of lambda w.r.t. z
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d lambda / dz
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        discr =          (R**2 + z**2 - self._Delta**2)**2 + (4. * self._Delta**2 * R**2)
        return z * (1. + (R**2 + z**2 - self._Delta**2) / nu.sqrt(discr))

    def _dndz(self,R,z):
        """
        NAME:
            _dndz
        PURPOSE:
            evaluate the derivative of nu w.r.t. z
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d nu / dz
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        #derivative of lambda and nu w.r.t. R (see _Rz_to_ln() for conversion):
        discr =          (R**2 + z**2 - self._Delta**2)**2 + (4. * self._Delta**2 * R**2) 
        return z * (1. - (R**2 + z**2 - self._Delta**2) / nu.sqrt(discr))

    def _d2ldR2(self,R,z):
        """
        NAME:
            _d2ldR2
        PURPOSE:
            evaluate the second derivative of lambda w.r.t. R
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d^2 lambda / dR^2
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        D = self._Delta
        discr   = (R**2 + z**2 - self._Delta**2)**2 + (4. * self._Delta**2 * R**2)
        term1 =            (3.*R**2 + z**2 + D**2)     / discr**0.5
        term2 = (2.*R**2 * (   R**2 + z**2 + D**2)**2) / discr**1.5
        return 1. + term1 - term2

    def _d2ndR2(self,R,z):
        """
        NAME:
            _d2ndR2
        PURPOSE:
            evaluate the second derivative of nu w.r.t. R
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d^2 nu / dR^2
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        D = self._Delta
        discr =               (R**2 + z**2 - D**2)**2 + (4. * D**2 * R**2)
        term1 =            (3.*R**2 + z**2 + D**2)     / discr**0.5
        term2 = (2.*R**2 * (   R**2 + z**2 + D**2)**2) / discr**1.5
        return 1. - term1 + term2

    def _d2ldz2(self,R,z):
        """
        NAME:
            _d2ldz2
        PURPOSE:
            evaluate the second derivative of lambda w.r.t. z
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d^2 lambda / dz^2
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        D = self._Delta
        discr =            (R**2 + z**2    - D**2)**2 + (4. * D**2 * R**2)
        term1 =            (R**2 + 3.*z**2 - D**2)     / discr**0.5
        term2 = (2.*z**2 * (R**2 +    z**2 - D**2)**2) / discr**1.5
        return 1. + term1 - term2

    def _d2ndz2(self,R,z):
        """
        NAME:
            _d2ldR2
        PURPOSE:
            evaluate the second derivative of nu w.r.t. z
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d^2 nu / dz^2
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        D = self._Delta
        discr =            (R**2 +    z**2 - D**2)**2 + (4. * D**2 * R**2)
        term1 =            (R**2 + 3.*z**2 - D**2)     / discr**0.5
        term2 = (2.*z**2 * (R**2 +    z**2 - D**2)**2) / discr**1.5
        return 1. - term1 + term2

    def _d2ldRdz(self,R,z):
        """
        NAME:
            _d2ldRdz
        PURPOSE:
            evaluate the mixed derivative of lambda w.r.t. R and z
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d^2 lambda / dR / dz
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        D = self._Delta
        discr =  (R**2 + z**2 - D**2)**2 + (4. * D**2 * R**2)
        term1 = 2.*R*z                   /discr**0.5
        term2 = ((R**2 + z**2)**2 - D**4)/discr
        return term1 * (1. - term2)

    def _d2ndRdz(self,R,z):
        """
        NAME:
            _d2ndRdz
        PURPOSE:
            evaluate the mixed derivative of nu w.r.t. R and z
        INPUT:
            R - Galactocentric cylindrical radius
            z - vertical height
        OUTPUT:
            d^2 nu / dR / dz
        HISTORY:
            2015-02-13 - Written - Trick (MPIA)
        """
        D = self._Delta
        discr =  (R**2 + z**2 - D**2)**2 + (4. * D**2 * R**2)
        term1 = 2.*R*z                   /discr**0.5
        term2 = ((R**2 + z**2)**2 - D**4)/discr
        return term1 * (-1. + term2)
