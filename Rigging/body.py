__author__ = 'pritish.dogra'

from PKD_Tools.Rigging import core

reload(core)
from PKD_Tools.Rigging import utils

reload(utils)

from PKD_Tools import libUtilities

reload(libUtilities)
import pymel.core as pm


class rig(core.SubSystem):
    """This is base System. Transform is the main"""

    def __init__(self, *args, **kwargs):
        super(rig, self).__init__(*args, **kwargs)
        self.Joints = None
        self.ctrls = None


class ik(rig):
    def __init__(self, *args, **kwargs):
        super(rig, self).__init__(*args, **kwargs)
        self._ikHandle_ = None
        self.hasParentMaster = False

    def build(self):
        # Build the IK System
        self.build_ik()
        # Build the controls
        self.build_control()
        # Setup the polevector / no flip
        pass

    def build_control(self):
        ikCtrl = core.Ctrl(part=self.part, side=self.side)
        ikCtrl.ctrlShape = "Box"
        ikCtrl.create_ctrl()
        libUtilities.snap(ikCtrl.prnt.mNode, self.ikHandle.mNode)
        self.ikHandle.pynode.setParent(ikCtrl.pynode)
        ikCtrl.setParent(self)

    def build_ik(self):
        # Setup the IK handle RP solver
        name = utils.nameMe(self.side, self.part, "IkHandle")
        ikHandle = pm.ikHandle(name=name, sj=self.Joints[0], ee=self.Joints[-1], sol="ikRPsolver")[0]
        self.ikHandle = core.MetaRig(ikHandle.name(), nodeType="ikHandle")
        self.ikHandle.part = self.part
        self.ikHandle.mirrorSide = self.mirrorSide
        self.ikHandle.rigType = "ikHandle"
        self.addSupportNode(self.ikHandle, "IkHandle")
        self.ikHandle.v = False

    def create_test_cube(self, targetJoint):
        cube = pm.polyCube(ch=False)[0]
        pm.select(cube.vtx[0:1], cube.vtx[6:7])
        # Botton Cluster
        clusterBottom = pm.cluster()[1]
        libUtilities.snap(clusterBottom, targetJoint)

        # Top Cluster
        pm.select(cube.vtx[2:5])
        clusterTop = pm.cluster()[1]

        childJoint = pm.PyNode("joint1").getChildren(type="joint")[0]
        libUtilities.snap(clusterTop, childJoint)

        pm.delete(cube,ch=True)

        libUtilities.skinGeo(cube, [targetJoint])


    def test_build(self):
        # Build the joint system
        jointSystem = core.JointSystem(side="U", part="%sJoints" % self.part)
        # Build the joints
        self.Joints = utils.create_test_joint(self.__class__.__name__)
        jointSystem.addJoints(self.Joints)
        self.connectChild(jointSystem, "Joint_System")
        # Build IK
        self.build_ik()

        self.build_control()
        # Setup the parent
        jointSystem.setParent(self)
        self.create_test_cube(self.Joints[0])

    @property
    def ikHandle(self):
        return self._relink_meta_internal_variables_("_ikHandle_")

    @ikHandle.setter
    def ikHandle(self, data):
        self._set_initialise_internal_("_ikHandle_", data)


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


core.Red9_Meta.registerMClassInheritanceMapping()
core.Red9_Meta.registerMClassNodeMapping(nodeTypes=['ikHandle'])

if __name__ == '__main__':
    pm.newFile(f=1)

    # subSystem = SubSystem(side="U", part="Core")
    # print "s"
    ikSystem = ik(side="U", part="Core")
    # print ikSystem
    ikSystem.test_build()
