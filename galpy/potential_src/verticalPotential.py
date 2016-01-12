from galpy.potential_src.linearPotential import linearPotential
from galpy.potential_src.Potential import PotentialError, Potential
class verticalPotential(linearPotential):
    """Class that represents a vertical potential derived from a RZPotential:
    phi(z;R)= phi(R,z)-phi(R,0.)"""
    def __init__(self,RZPot,R=1.):
        """
        NAME:
           __init__
        PURPOSE:
           Initialize
        INPUT:
           RZPot - RZPotential instance
           R  - Galactocentric radius at which to create the vertical potential
        OUTPUT:
           verticalPotential instance
        HISTORY:
           2010-07-13 - Written - Bovy (NYU)
        """
        linearPotential.__init__(self,amp=1.)
        self._RZPot= RZPot
        self._R= R
        # Also transfer ro and vo
        self._ro= RZPot._ro
        self._roSet= RZPot._roSet
        self._vo= RZPot._vo
        self._voSet= RZPot._voSet
        return None

    def _evaluate(self,z,t=0.):
        """
        NAME:
           _evaluate
        PURPOSE:
           evaluate the potential
        INPUT:
           z
           t
        OUTPUT:
          Pot(z,t;R)
        HISTORY:
           2010-07-13 - Written - Bovy (NYU)
        """
        return self._RZPot(self._R,z,t=t,use_physical=False)\
            -self._RZPot(self._R,0.,t=t,use_physical=False)
            
    def _force(self,z,t=0.):
        """
        NAME:
           _force
        PURPOSE:
           evaluate the force
        INPUT:
           z
           t
        OUTPUT:
          F_z(z,t;R)
        HISTORY:
           2010-07-13 - Written - Bovy (NYU)
        """
        return self._RZPot.zforce(self._R,z,t=t,use_physical=False)\
            -self._RZPot.zforce(self._R,0.,t=t,use_physical=False)

def RZToverticalPotential(RZPot,R):
    """
    NAME:

       RZToverticalPotential

    PURPOSE:

       convert a RZPotential to a vertical potential at a given R

    INPUT:

       RZPot - RZPotential instance or list of such instances

       R - Galactocentric radius at which to evaluate the vertical potential

    OUTPUT:

       (list of) linearPotential instance(s)

    HISTORY:

       2010-07-21 - Written - Bovy (NYU)

    """
    if isinstance(RZPot,list):
        out= []
        for pot in RZPot:
            if isinstance(pot,linearPotential):
                out.append(pot)
            else:
                out.append(verticalPotential(pot,R))
        return out
    elif isinstance(RZPot,Potential):
        return verticalPotential(RZPot,R)
    elif isinstance(RZPot,linearPotential):
        return RZPot
    else: #pragma: no cover
        raise PotentialError("Input to 'RZToverticalPotential' is neither an RZPotential-instance or a list of such instances")
