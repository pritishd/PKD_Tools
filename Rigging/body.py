__author__ = 'pritish.dogra'

from PKD_Tools.Red9 import Red9_Meta


class rig(Red9_Meta.MetaClass):
    """This is base System. Transform is the main"""


class fk(rig):
    """This is base Fk System."""
    pass


class ikjnt(rig):
    """This is base IK System. with a three or four joint"""
    pass

class ik(ik):
    """This is a basic IK hand System."""
    pass

class ikHand(ik):
    """This is IK hand System."""
    pass


class ikFoot(ik):
    """This is the classic IK foot System."""
    pass


class ikHoof(ik):
    """This is the IK hoof System."""
    pass


class ikSpline(rig):
    """This is a Spline IK System"""
    pass
