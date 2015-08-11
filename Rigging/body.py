__author__ = 'pritish.dogra'

from PKD_Tools.Rigging import core
reload(core)
from PKD_Tools.Rigging import utils
reload(utils)

from PKD_Tools import libUtilities
from PKD_Tools import libVector
reload(libUtilities)
import pymel.core as pm


class rig(core.SubSystem):
    """This is base System. Transform is the main"""

    def __init__(self, *args, **kwargs):
        super(rig, self).__init__(*args, **kwargs)
        self.JointSystem = None

    def create_test_cube(self, targetJoint):
        cube = pm.polyCube(ch=False)[0]
        pm.select(cube.vtx[0:1], cube.vtx[6:7])
        # TODO: make the base pointy in z
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
        self.hasParentMaster = False
        self.rotateOrder = "yxz"
        self.mirrorData = {'side': self.mirrorSide, 'slot': 1}
        self.custom_pv_position = None

    def build(self):
        # Build the IK System
        self.build_ik()
        # Build the controls
        self.build_control()
        # Setup the polevector / no flip
        pass

    def add_PV(self):

        self.pv = core.Ctrl(part="%s_PV" % self.part, side=self.side)
        self.pv.ctrlShape = "Locator"
        self.pv.build()

        # Position And Align The Pole Vector Control

        default_pole_vector = libVector.vector(list(self.ikHandle.poleVector))

        # Check userdefined pos. If not then take then find the vector from the second joint in the chain

        pv_position = self.custom_pv_position
        if not self.custom_pv_position:
            second_joint_position = libVector.vector(pm.joint(self.JointSystem.Joints[1], q=1, p=1))
            pv_position = (default_pole_vector * [40, 40, 40]) + second_joint_position


        # Get the Pole vector position that it wants to snap to
        self.pv.prnt.pynode.setTranslation(pv_position, space="world")
        pvTwist = 0

        # Find the twist of the new pole vector if to a new positiion
        if self.custom_pv_position:
            pm.poleVectorConstraint(self.pv.mNode, self.ikHandle.mNode, w=1)
            offset_pole_vector = self.ikHandle.poleVector

            # Delete the polevector
            pm.delete(self.ikHandle.mNode, cn=1)
            self.ikHandle.poleVector = default_pole_vector

            from PKD_Tools.Rigging import nilsNoFlipIK

            pvTwist = nilsNoFlipIK.nilsNoFlipIKProc(offset_pole_vector[0],
                                                    offset_pole_vector[1],
                                                    offset_pole_vector[2],
                                                    self.ikHandle.mNode)

        pm.poleVectorConstraint(self.pv.mNode, self.ikHandle.mNode, w=1)
        self.ikHandle.twist = pvTwist

    def build_control(self):
        ikCtrl = core.Ctrl(part=self.part, side=self.side)
        ikCtrl.ctrlShape = "Box"
        ikCtrl.build()
        libUtilities.snap(ikCtrl.prnt.mNode, self.ikHandle.mNode)
        self.ikHandle.pynode.setParent(ikCtrl.pynode)
        ikCtrl.setParent(self)
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(ikCtrl, "MainIK", mirrorData=self.mirrorData)

    def build_ik(self):
        # Setup the IK handle RP solver
        name = utils.nameMe(self.side, self.part, "IkHandle")
        ikHandle = pm.ikHandle(name=name,
                               sj=self.JointSystem.Joints[0],
                               ee=self.JointSystem.Joints[-1],
                               sol="ikRPsolver",
                               sticky="sticky")[0]
        self.ikHandle = core.MetaRig(ikHandle.name(), nodeType="ikHandle")
        self.ikHandle.part = self.part
        self.ikHandle.mirrorSide = self.mirrorSide
        self.ikHandle.rigType = "ikHandle"
        self.ikHandle.v = False

    def build_twist(self):

        # TODO https://www.youtube.com/watch?v=KhZHjqHedPI
        from PKD_Tools.Rigging import nilsNoFlipIK
        reload(nilsNoFlipIK)
        offSet = nilsNoFlipIK.nilsNoFlipIKProc(0, 0, 1, self.ikHandle.mNode)
        ctrl = self.getRigCtrl("MainIK")
        ctrl.addAttr("offset", offSet, hidden=True)

        ctrl.addAttr("twist", 0.0)

        self.ikHandle.poleVector = [0, 0, 0.1]

        ikTwistNode = pm.createNode("plusMinusAverage", n=utils.nameMe(self.side, self.shortName(), "twistPMA"))

        ctrl.pynode.offset >> ikTwistNode.input1D[0]
        ctrl.pynode.twist >> ikTwistNode.input1D[1]

        ikTwistNode.output1D >> self.ikHandle.pynode.twist

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
        self.add_PV()
        # self.build_twist()

    @property
    def ikHandle(self):
        return self.getSupportNode("IKHandle")

    @ikHandle.setter
    def ikHandle(self, data):
        self.addSupportNode(data, "IKHandle")

    @property
    def pv(self):
        return self.getRigCtrl("PV")

    @pv.setter
    def pv(self, data):
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(data, ctrType="PV", mirrorData=self.mirrorData)


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
