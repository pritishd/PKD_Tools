__author__ = 'pritish.dogra'

from PKD_Tools.Red9 import Red9_Meta
reload(Red9_Meta)
from PKD_Tools.Rigging import core
reload(core)
from PKD_Tools.Rigging import utils

reload(utils)
import sys

sys.modules.clear()
import pymel.core as pm


class rig(core.SubSystem):
    """This is base System. Transform is the main"""

    def __init__(self, *args, **kwargs):
        super(rig, self).__init__(*args, **kwargs)
        self.joints = None
        self.ctrls = None


class ik(rig):
    def __init__(self, *args, **kwargs):
        super(rig, self).__init__(*args, **kwargs)
        self.ikHandle = None

    def build(self):
        # Build the IK System
        # Build the controls
        # Setup the polevector / no flip
        pass

    def test_build(self):
        joints = utils.create_test_joint(self.__class__.__name__)



class fk(rig):
    """This is base Fk System."""


class ik3jnt(rig):
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


class ikSpline(rig):
    """This is a Spline IK System"""
    pass

Red9_Meta.registerMClassInheritanceMapping()

if __name__ == '__main__':
    pm.newFile(f=1)
    # cam = MyCameraMeta()
    #subSystem = SubSystem(side="U", part="Core")
    #print "s"
    # ikSystem = ik()
    # print ikSystem
    # ikSystem.test_build()
