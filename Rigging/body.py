__author__ = 'pritish.dogra'

from PKD_Tools.Red9 import Red9_Meta
reload(Red9_Meta)
from PKD_Tools.Rigging import core
reload(core)

import sys

sys.modules.clear()
import pymel.core as pm


class rig(core.SubSystem):
    """This is base System. Transform is the main"""

    def __init__(self, *args, **kwargs):
        print kwargs
        super(rig, self).__init__(*args, **kwargs)
        self.joints = None


class ik(rig):
    def test_build(self):
        joints = [{'orient': [0.0, -0.0, 0.0], 'position': [0.0, 0, 0.0]},
                  {'orient': [0.0, -0.0, 0.0], 'position': [0.0, 4.000000000000001, 0.0]}]

        for joint in joints:
            pm.select(cl=1)
            self.joints.append(pm.joint(position=joint["position"], orientation=joint["orient"]))

        for i in range(1, len(self.joints)):
            self.joint[i].setParent(self.joint[i - 1])


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
