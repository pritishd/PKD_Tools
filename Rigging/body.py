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
        self.JointSystem = None

    def getRigCtrl(self, target):
        children = self.getChildren(walk=True, asMeta=True, cAttrs=["%s_%s" % (self.CTRL_Prefix, target)])
        if not children:
            libUtilities.pyLog.warn("%s ctrl not found on %s" % (target, self.shortName()))
        else:
            return children[0]

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

        pm.delete(cube, ch=True)

        libUtilities.skinGeo(cube, [targetJoint])


class ik(rig):
    def __init__(self, *args, **kwargs):
        super(rig, self).__init__(*args, **kwargs)
        self._ikHandle_ = None
        self.hasParentMaster = False
        self.rotateOrder = "yxz"

    def build(self):
        # Build the IK System
        self.build_ik()
        # Build the controls
        self.build_control()
        # Setup the polevector / no flip
        pass

    def add_PV(self):
        mc.addAttr(ikCtrl.ctrl, ln="offset", at="double",
                   dv=mm.eval("source nilsNoFlipIK;nilsNoFlipIKProc(1, 0, 0,\"%s\");" % ikHndList[0]))
        mc.setAttr(ikCtrl.ctrl + ".offset", e=1, cb=0)
        mc.addAttr(ikCtrl.ctrl, ln=self.capitalize(trgLoc[1]), at="double", dv=0)
        mc.setAttr(ikCtrl.ctrl + (self.capitalize(".%s" % trgLoc[1])), e=1, k=1)

        mc.setAttr(ikHndList[0] + ".poleVectorX", .1)
        mc.setAttr(ikHndList[0] + ".poleVectorY", 0)
        mc.setAttr(ikHndList[0] + ".poleVectorZ", 0)

        ikTwistNode = mc.createNode("plusMinusAverage", n=self.name + "_" + self.sfx + "_twistPMA")
        mc.connectAttr(ikCtrl.ctrl + ".offset", ikTwistNode + ".input1D[0]")
        mc.connectAttr(ikCtrl.ctrl + (self.capitalize(".%s" % trgLoc[1])), ikTwistNode + ".input1D[1]")
        mc.connectAttr(ikTwistNode + ".output1D", ikHndList[0] + ".twist")

    def build_control(self):
        ikCtrl = core.Ctrl(part=self.part, side=self.side)
        ikCtrl.ctrlShape = "Box"
        ikCtrl.create_ctrl()
        libUtilities.snap(ikCtrl.prnt.mNode, self.ikHandle.mNode)
        self.ikHandle.pynode.setParent(ikCtrl.pynode)
        ikCtrl.setParent(self)
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(ikCtrl.mNode, "MainIK", mirrorData={'side': self.mirrorSide, 'slot': 1})

    def build_ik(self):
        # Setup the IK handle RP solver
        name = utils.nameMe(self.side, self.part, "IkHandle")
        ikHandle = \
        pm.ikHandle(name=name, sj=self.JointSystem.Joints[0], ee=self.JointSystem.Joints[-1], sol="ikRPsolver")[0]
        self.ikHandle = core.MetaRig(ikHandle.name(), nodeType="ikHandle")
        self.ikHandle.part = self.part
        self.ikHandle.mirrorSide = self.mirrorSide
        self.ikHandle.rigType = "ikHandle"
        self.addSupportNode(self.ikHandle, "IkHandle")
        self.ikHandle.v = False

    def test_build(self):
        # Build the joint system
        self.JointSystem = core.JointSystem(side="U", part="%sJoints" % self.part)
        # Build the joints
        joints = utils.create_test_joint(self.__class__.__name__)
        self.JointSystem.addJoints(joints)
        self.JointSystem.setRotateOrder(self.rotateOrder)
        self.connectChild(self.JointSystem, "Joint_System")
        # Build IK
        self.build_ik()

        self.build_control()
        # Setup the parent
        self.JointSystem.setParent(self)
        self.create_test_cube(self.JointSystem.Joints[0])
        self.getRigCtrl("MainIK").rotateOrder = self.rotateOrder


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
