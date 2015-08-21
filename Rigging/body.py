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
        pm.select(cube.vtx[0:1])
        pm.move(0, 0, 0.9, r=1)

        pm.select(cube.vtx[0:1], cube.vtx[6:7])

        # Botton Cluster
        clusterBottom = pm.cluster()[1]
        clusterBottom.setScalePivot([0, 0, 0])
        clusterBottom.setRotatePivot([0, 0, 0])

        libUtilities.snap(clusterBottom, targetJoint.shortName())

        # Top Cluster
        pm.select(cube.vtx[2:5])
        clusterTop = pm.cluster()[1]

        childJoint = targetJoint.pynode.getChildren(type="joint")[0]
        libUtilities.snap(clusterTop, childJoint)

        pm.delete(cube, ch=True)

        libUtilities.skinGeo(cube, [targetJoint.mNode])


class ik(rig):
    def __init__(self, *args, **kwargs):
        super(rig, self).__init__(*args, **kwargs)
        self.ikSolver = "ikSCsolver"
        self.hasParentMaster = False
        self.rotateOrder = "yxz"
        self.mirrorData = {'side': self.mirrorSide, 'slot': 1}
        self.custom_pv_position = None
        self.startJointNumber = 0
        self.endJointNumber = 1
        self.freezeIkHandle = False

    def loadIKPlugin(self):
        if self.ikSolver not in ["ikRPsolver", "ikSCsolver"]:
            pm.loadPlugin(self.ikSolver, quiet=True)
            libUtilities.melEval(self.ikSolver)

    def build(self):
        # Load any IK plugin
        self.loadIKPlugin()
        # Build the IK System
        self.build_ik()
        # Build the controls
        self.build_control()

    def build_PV(self):

        self.pv = core.Ctrl(part="%s_PV" % self.part, side=self.side)
        self.pv.ctrlShape = "Locator"
        self.pv.build()
        self.pv.setParent(self)

        # Position And Align The Pole Vector Control

        default_pole_vector = libVector.vector(list(self.ikHandle.poleVector))

        # Check userdefined pos. If not then take then find the vector from the second joint in the chain
        pv_position = self.custom_pv_position
        if not self.custom_pv_position:
            second_joint_position = self.JointSystem.Joints[self.startJointNumber + 1].pynode.getTranslation(
                space="world")
            pv_position = (default_pole_vector * [30, 30, 30]) + second_joint_position

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
        ikCtrl.setRotateOrder(self.rotateOrder)
        ikCtrl.add_gimbal_node()
        if self.hasParentMaster:
            ikCtrl.add_parent_master()
        libUtilities.snap(ikCtrl.prnt.mNode, self.ikHandle.mNode)
        ikCtrl.addChild(self.ikHandle.pynode)
        ikCtrl.setParent(self)
        self.mainIK = ikCtrl

    def build_ik(self):
        # Setup the IK handle RP solver
        name = utils.nameMe(self.side, self.part, "IkHandle")
        ikHandle = pm.ikHandle(name=name,
                               sj=self.JointSystem.Joints[self.startJointNumber].shortName(),
                               ee=self.JointSystem.Joints[self.endJointNumber].shortName(),
                               sol=self.ikSolver,
                               sticky="sticky")[0]
        if self.freezeIkHandle:
            libUtilities.freeze_transform(ikHandle)
        self.ikHandle = core.MetaRig(ikHandle.name(), nodeType="ikHandle")
        self.ikHandle.part = self.part
        self.ikHandle.mirrorSide = self.mirrorSide
        self.ikHandle.rigType = "ikHandle"
        self.ikHandle.v = False

    def build_twist(self):
        # Check that that a pv exists
        if self.pv is None:
            # Create one
            self.build_PV()
        # Create a new meta node.
        self.twist = core.MetaRig(part=self.part, side=self.side, endSuffix="TwistGrp")
        # Match it to the first joint
        libUtilities.snap(self.twist.pynode, self.ikHandle.mNode)
        # Parent the PV Control
        self.pv.setParent(self.twist)
        # Rotate the new node 90 on first axis of the rotate order
        primary_axis = self.pynode.rotateOrder.get(asString=True)
        self.twist.pynode.attr("r%s" % primary_axis[0]).set(90)
        # Zero out the transform
        twistPrnt = core.MetaRig(part=self.part, side=self.side, endSuffix="TwistPrnt")
        libUtilities.snap(twistPrnt.pynode, self.twist.pynode)
        self.twist.setParent(twistPrnt)
        self.twist.addSupportNode(twistPrnt, "Prnt")
        # Parent the PV control to the ik
        self.mainIK.addChild(twistPrnt.pynode)
        # offset the twist handle back
        self.ikHandle.twist = -90
        # Add a new divider
        libUtilities.addDivAttr(self.mainIK.mNode, "Twist", "twistLbl")
        # Add a control attibute
        # TODO Get the name from the second part if more than two joints. Otherwise from the first joint
        libUtilities.addAttr(self.mainIK.mNode, "Knee", sn="twist", attrMax=720, attrMin=-720)
        # Connect the new attribute to the twist offset
        self.mainIK.pynode.twist >> self.twist.pynode.attr("r%s" % primary_axis[0])
        # Hide the PV
        # self.pv.prnt.visibility = False

    def test_build(self):
        # Build the joint system
        self.JointSystem = core.JointSystem(side="U", part="%sJoints" % self.part)
        # Build the joints
        joints = utils.create_test_joint(self.__class__.__name__)
        self.JointSystem.Joints = joints
        self.JointSystem.convertJointsToMetaJoints()
        self.JointSystem.setRotateOrder(self.rotateOrder)
        self.connectChild(self.JointSystem, "Joint_System")
        # Build IKf
        self.build()
        # Setup the parent
        self.JointSystem.setParent(self)
        for i in range(len(self.JointSystem.Joints) - 1, ):
            self.create_test_cube(self.JointSystem.Joints[i])

    @property
    def ikHandle(self):
        return self.getSupportNode("IKHandle")

    @ikHandle.setter
    def ikHandle(self, data):
        self.addSupportNode(data, "IKHandle")

    @property
    def twist(self):
        return self.getSupportNode("Twist")

    @twist.setter
    def twist(self, data):
        self.addSupportNode(data, "Twist")

    @property
    def pv(self):
        return self.getRigCtrl("PV")

    @pv.setter
    def pv(self, data):
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(data, ctrType="PV", mirrorData=self.mirrorData)

    @property
    def mainIK(self):
        return self.getRigCtrl("MainIK")

    @mainIK.setter
    def mainIK(self, data):
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(data, ctrType="MainIK", mirrorData=self.mirrorData)


class fk(rig):
    """This is base Fk System."""
    pass


class arm(ik):
    """This is base IK System. with a three joint"""

    def __init__(self, *args, **kwargs):
        super(arm, self).__init__(*args, **kwargs)
        self.ikSolver = "ik2Bsolver"
        self.endJointNumber = 2
        self.freezeIkHandle = True

    def test_build(self):
        super(arm, self).test_build()
        self.build_PV()


# class arm(ik2jnt):
#     """This is IK System. with a joint"""
#
#     def __init__(self, *args, **kwargs):
#         super(arm, self).__init__(*args, **kwargs)
#         self.ikSolver = "ikRPsolver"
#         self.endJointNumber = 2
#
#     def test_build(self):
#         super(arm, self).test_build()
#         self.build_PV()


class hip(arm):
    def __init__(self, *args, **kwargs):
        super(hip, self).__init__(*args, **kwargs)
        # self.ikSolver = "ikRPsolver"
        self.startJointNumber = 1
        self.endJointNumber = 3

    def test_build(self):
        super(hip, self).test_build()
        self.create_test_cube(self.JointSystem.Joints[2])

    def build_ik(self):
        super(hip, self).build_ik()

        name = utils.nameMe(self.side, self.part, "Clav"
                                                  "IkHandle")
        ikHandle = pm.ikHandle(name=name,
                               sj=self.JointSystem.Joints[self.startJointNumber].shortName(),
                               ee=self.JointSystem.Joints[self.endJointNumber].shortName(),
                               sol=self.ikSolver,
                               sticky="sticky")[0]
        if self.freezeIkHandle:
            libUtilities.freeze_transform(ikHandle)
        self.ikHandle = core.MetaRig(ikHandle.name(), nodeType="ikHandle")
        self.ikHandle.part = self.part
        self.ikHandle.mirrorSide = self.mirrorSide
        self.ikHandle.rigType = "ikHandle"
        self.ikHandle.v = False


class quad(ik):
    def __init__(self, *args, **kwargs):
        super(quad, self).__init__(self, *args, **kwargs)
        self.endJointNumber = 3
        self.ikSolver = "ikSpringSolver"

    def build_control(self):
        super(quad, self).build_control()
        self.mainIK.addDivAttr("SpringBias", "lblSpringBias")
        self.mainIK.addFloatAttr("Start", sn="StartBias", df=0.5)
        self.mainIK.addFloatAttr("End", sn="EndBias", df=0.5)
        self.mainIK.pynode.StartBias >> self.ikHandle.pynode.springAngleBias[0].springAngleBias_FloatValue
        self.mainIK.pynode.EndBias >> self.ikHandle.pynode.springAngleBias[1].springAngleBias_FloatValue

    def test_build(self):
        super(quad, self).test_build()
        self.build_PV()


class ikArm(arm):
    """This is IK hand System."""
    pass


class ikFoot(arm):
    """This is the classic IK foot System."""
    pass


class ikHoof(ikFoot):
    """This is the IK hoof System."""
    pass


class ikPaw(ikFoot):
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

    # print ikSystem

    mainSystem = core.SubSystem(side="U", part="Core")

    ikSystem = mainSystem.addMetaSubSystem(arm, "IK")
    ikSystem.test_build()
    ikSystem.convertToComponent("IK")