__author__ = 'admin'

from PKD_Tools.Rigging import core
reload(core)
from PKD_Tools.Rigging import utils
reload(utils)
from PKD_Tools import libUtilities
reload(libUtilities)


class ikSpline(core.rig):
    """This is a Spline IK System"""
    def build_ik(self):
        # Build the curve
        pass
        # Build the spline IK


    def build_control(self):
        pass

class simpleSpine(ikSpline):
    def build_control(self):
        pass

class multiSpine(ikSpline):
    pass

    


core.Red9_Meta.registerMClassInheritanceMapping()
core.Red9_Meta.registerMClassNodeMapping(nodeTypes=['ikHandle', 'multiplyDivide', "clamp"])
