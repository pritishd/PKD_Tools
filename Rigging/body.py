__author__ = 'pritish.dogra'

from PKD_Tools.Red9 import Meta


class base(Meta.MetaClass):
    """This is base System. Transform is the main"""


class fk(base):
    """This is base Fk System."""
    pass


class ikjnt(base):
    """This is base IK System. with a three or four joint"""
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


class ikSpline(base):
    """This is a Spline IK System"""
    pass
