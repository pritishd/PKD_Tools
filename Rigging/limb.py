from PKD_Tools.Rigging.core import rig

__author__ = 'pritish.dogra'

from PKD_Tools.Rigging import core

reload(core)
from PKD_Tools.Rigging import utils

reload(utils)

from PKD_Tools import libUtilities

reload(libUtilities)
from PKD_Tools import libVector

import pymel.core as pm

SOLVERS = {
    "Single": "ikSCsolver",
    "RotatePlane": "ikRPsolver",
    "Spring": "ikSpringSolver",
    "2Bone": "ik2Bsolver"
}


def _build_ik_(metaClass, solver, handleSuffix, startJointNumber, endJointNumber):
    """Construct a meta Ik Handle and make sure that it is parented"""
    name = utils.nameMe(metaClass.side, metaClass.part, handleSuffix)
    startJoint = metaClass.JointSystem.Joints[startJointNumber].shortName()
    endJoint = metaClass.JointSystem.Joints[endJointNumber].shortName()
    ikHandle = pm.ikHandle(name=name,
                           sj=startJoint,
                           ee=endJoint,
                           sol=solver,
                           sticky="sticky")[0]

    ikHandleMeta = core.MetaRig(ikHandle.name(), nodeType="ikHandle")
    ikHandleMeta.part = metaClass.part
    ikHandleMeta.mirrorSide = metaClass.mirrorSide
    ikHandleMeta.rigType = "ikHandle"
    ikHandleMeta.v = False
    # IK Handle needs to be in it's own group in case the polevector is not set. Otherwise if you reparent it
    # the polevector value changes in relation to the parent space
    # Create the parent meta
    ikHandleMeta.addParent(handleSuffix + "Prnt", snap=False)
    # Set the pivot to the endJoint
    libUtilities.snap_pivot(ikHandleMeta.prnt.mNode, endJoint)

    return ikHandleMeta


class ik(core.rig):
    def __init__(self, *args, **kwargs):
        super(rig, self).__init__(*args, **kwargs)
        self.ikSolver = SOLVERS["Single"]
        self.hasParentMaster = False
        self.rotateOrder = "yzx"
        self.mirrorData = {'side': self.mirrorSide, 'slot': 1}
        self.custom_pv_position = None
        self.startJointNumber = 0
        self.endJointNumber = 1
        self.ikControlToWorld = False
        self.hasPivot = False
        self.ctrlShape = "Box"

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

        # Pole vector points at second joint
        pm.aimConstraint(self.JointSystem.Joints[self.startJointNumber + 1].pynode,self.pv.pynode,mo=1)

        pm.poleVectorConstraint(self.pv.mNode, self.ikHandle.mNode, w=1)
        self.ikHandle.twist = pvTwist

    def align_control(self):
        libUtilities.snap(self.mainIK.prnt.mNode,
                          self.JointSystem.Joints[self.endJointNumber].mNode,
                          r=not self.ikControlToWorld
                          )

    def build_control(self):
        mainIK = core.Ctrl(part=self.part, side=self.side)
        mainIK.ctrlShape = self.ctrlShape
        mainIK.build()
        mainIK.setRotateOrder(self.rotateOrder)
        mainIK.addGimbalMode()
        if self.hasParentMaster:
            mainIK.addParentMaster()
        if self.hasPivot:
            mainIK.addPivot()
        # Align based on the control
        self.mainIK = mainIK
        self.align_control()
        self.mainIK.addChild(self.ikHandle.SUP_Prnt.pynode)
        self.mainIK.setParent(self)

    def build_ik(self):
        # Setup the IK handle RP solver
        self.ikHandle = _build_ik_(self, self.ikSolver, "IkHandle", self.startJointNumber, self.endJointNumber)

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
        self.twist.pynode.attr("r%s" % self.primary_axis[0]).set(90)
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
        # Build IK
        self.build()
        # Setup the parent
        if not self.JointSystem.Joints[0].pynode.getParent():
            self.JointSystem.setParent(self)
        for i in range(len(self.JointSystem.Joints) - 1, 0):
            self.create_test_cube(self.JointSystem.Joints[i])

    @property
    def JointSystem(self):
        return self.getSupportNode("JointSystem")

    @JointSystem.setter
    def JointSystem(self, data):
        self.addSupportNode(data, "JointSystem")

    @property
    def primaryAxis(self):
        return self.pynode.rotateOrder.get(asString=True)

    @property
    def ikHandle(self):
        return self.getSupportNode("IKHandle")

    @ikHandle.setter
    def ikHandle(self, data):
        self.addSupportNode(data, "IKHandle")

    @property
    def twist(self):
        return self.mainIK.getSupportNode("Twist")

    @twist.setter
    def twist(self, data):
        self.mainIK.addSupportNode(data, "Twist")

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


class fk(core.rig):
    """This is base Fk System."""
    pass


class arm(ik):
    """This is base IK System. with a three joint"""

    def __init__(self, *args, **kwargs):
        super(arm, self).__init__(*args, **kwargs)
        self.ikSolver = SOLVERS["2Bone"]
        self.endJointNumber = 2

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
        self.hipIKHandle = _build_ik_(self, SOLVERS["Single"], "ClavIkHandle", 0, 1)

    def build_control(self):
        super(hip, self).build_control()
        # Build the Hip Control
        hipCtrl = core.Ctrl(part=self.JointSystem.Joints[0].part, side=self.side)
        hipCtrl.ctrlShape = "Circle"
        hipCtrl.build()
        hipCtrl.setRotateOrder(self.rotateOrder)
        hipCtrl.addGimbalMode()
        if self.hasParentMaster:
            hipCtrl.addParentMaster()
        # First joint alias
        firstJoint = self.JointSystem.Joints[0]
        # Align with first joint
        hipCtrl.snap(firstJoint.pynode)
        # Parent the hip IkControl
        self.hipIKHandle.SUP_Prnt.setParent(hipCtrl)
        # Create a helper joint
        pm.select(cl=1)
        self.aimHelper = core.Joint(part=firstJoint.part, side=self.side, endSuffix="AimHelper")
        # Align with the first joint
        libUtilities.snap(self.aimHelper.pynode, firstJoint.pynode, r=0)

        # Freeze the rotation on joint
        self.aimHelper.pynode.jointOrient.set(firstJoint.pynode.jointOrient.get())

        # New upVector
        second_joint_position = list(
            self.JointSystem.Joints[self.startJointNumber + 1].pynode.getTranslation(space="world"))
        default_pole_vector = libVector.vector(list(self.ikHandle.poleVector))
        aimPosition = (default_pole_vector * [30, 30, 30]) + libVector.vector(second_joint_position)
        upVector = core.MetaRig(part=firstJoint.part, side=self.side, endSuffix="UpVector")
        upVector.pynode.setTranslation(aimPosition)
        self.aimHelper.addSupportNode(upVector, "UpVector")
        self.aimHelper.v = False

        # Aim Constraint at mainIk Handle
        pm.aimConstraint(self.mainIK.pynode, self.aimHelper.pynode, mo=1, wut="object", wuo=upVector.mNode)
        # Orient Constraint the Hip Constraint
        hipCtrl.orientConstraint(self.aimHelper.pynode)


        # Point constrain the first joint
        pm.pointConstraint(hipCtrl.mNode, firstJoint.mNode, mo=1)


        # Cleanup
        self.hipIK = hipCtrl

        # Create main grp
        mainGrp = core.MetaRig(part=self.part + "Main", side=self.side)
        hipGrp = core.MetaRig(part=self.part + "Hip", side=self.side)

        # Reparent
        self.addSupportNode(mainGrp, "MainGrp")
        self.addSupportNode(hipGrp, "HipGrp")

        # Parent the groups
        mainGrp.setParent(self)
        hipGrp.setParent(self)

        # Parent the hip control
        hipCtrl.setParent(hipGrp)
        self.aimHelper.setParent(hipGrp)
        upVector.setParent(hipGrp)

        # Parent the gro
        self.mainIK.setParent(mainGrp)
        firstJoint.setParent(mainGrp)

    def build_PV(self):
        super(hip, self).build_PV()
        self.pv.setParent(self.getSupportNode("MainGrp"))

    @property
    def hipIK(self):
        return self.getRigCtrl("hipIK")

    @hipIK.setter
    def hipIK(self, data):
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(data, ctrType="hipIK", mirrorData=self.mirrorData)

    @property
    def hipIKHandle(self):
        return self.getSupportNode("hipIKHandle")

    @hipIKHandle.setter
    def hipIKHandle(self, data):
        self.addSupportNode(data, "hipIKHandle")

    @property
    def aimHelper(self):
        return self.getSupportNode("aimHelper")

    @aimHelper.setter
    def aimHelper(self, data):
        self.addSupportNode(data, "aimHelper")


class quad(ik):
    def __init__(self, *args, **kwargs):
        super(quad, self).__init__(self, *args, **kwargs)
        self.endJointNumber = 3
        self.ikSolver = SOLVERS["Spring"]

    def build_control(self):
        super(quad, self).build_control()
        # Adding controls to the sprink bias
        self.mainIK.addDivAttr("SpringBias", "lblSpringBias")
        self.mainIK.addFloatAttr("Start", sn="StartBias", df=0.5)
        self.mainIK.addFloatAttr("End", sn="EndBias", df=0.5)
        self.mainIK.pynode.StartBias >> self.ikHandle.pynode.springAngleBias[0].springAngleBias_FloatValue
        self.mainIK.pynode.EndBias >> self.ikHandle.pynode.springAngleBias[1].springAngleBias_FloatValue

    def test_build(self):
        super(quad, self).test_build()
        self.build_PV()


class hand(object):
    def build_ik(self):
        self.palmIKHandle = _build_ik_(self, SOLVERS["Single"], "PalmIKHandle", self.endJointNumber,
                                       self.endJointNumber + 1)

    def build_control(self):
        self.palmIKHandle.SUP_Prnt.setParent(self.mainIK)
        # TODO Add a pivot. the pivot shape to a locator

    @property
    def palmIK(self):
        return self.getRigCtrl("palmIK")

    @palmIK.setter
    def palmIK(self, data):
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(data, ctrType="palmIK", mirrorData=self.mirrorData)

    @property
    def palmIKHandle(self):
        return self.getSupportNode("palmIKHandle")

    @palmIKHandle.setter
    def palmIKHandle(self, data):
        self.addSupportNode(data, "palmIKHandle")


class armHand(arm, hand):
    def build_control(self):
        self.hasPivot = True
        arm.build_control(self)
        hand.build_control(self)

    def build_ik(self):
        arm.build_ik(self)
        hand.build_ik(self)


class quadHand(quad, hand):
    def build_control(self):
        self.hasPivot = True
        quad.build_control(self)
        hand.build_control(self)

    def build_ik(self):
        quad.build_ik(self)
        hand.build_ik(self)


class hipHand(hip, hand):
    def build_control(self):
        self.hasPivot = True
        hip.build_control(self)
        hand.build_control(self)

    def build_ik(self):
        hip.build_ik(self)
        hand.build_ik(self)


class hoof(object):
    """This is the IK hoof System."""

    def __init__(self, *args, **kwargs):
        super(hoof, self).__init__(*args, **kwargs)
        self.rollAttrs = ["Heel", "TipToe"]

    def align_control(self):
        # Remove the x roatation

        if not self.ikControlToWorld:
            # Create a new joint at the position of the end joint
            pm.select(self.JointSystem.Joints[self.endJointNumber].mNode)
            helperJnt = pm.joint()
            # Reset the joint orientation
            pm.parent(helperJnt, world=True)
            # Remove the primary axis
            helperJnt.attr("jointOrient%s" % self.primaryAxis[2].upper()).set(0)
            # Align the control to this joint
            libUtilities.snap(self.mainIK.prnt.mNode, helperJnt)
            # Delete helper joint
            pm.delete(helperJnt)

    def build_control(self):
        # Create the roll system
        self.RollSystem = core.Network(part=self.part + "Roll", side=self.side)

        # Add the rolls attrs
        libUtilities.addDivAttr(self.mainIK.pynode, "Roll", "rollDiv")
        # Tip_Heel
        for attr in self.rollAttrs:
            libUtilities.addAttr(self.mainIK.pynode, attr, 270, -270)

            # Create the 2 rotate system
        tipToeRoll = core.MetaRig(part=self.part, side=self.side, endSuffix="TipToeRoll")
        tipToeRoll.addParent("TipToeRollPrnt")
        libUtilities.snap(tipToeRoll.prnt.mNode, self.JointSystem.Joints[-2].mNode, r=0)
        libUtilities.snap(tipToeRoll.prnt.mNode, self.JointSystem.Joints[self.endJointNumber].mNode, t=0)

        # self.toeRoll.setParent(self.JointSystem.Joints[-1])
        heelRoll = core.MetaRig(part=self.part, side=self.side, endSuffix="HeelRoll")
        heelRoll.addParent("HeelRollPrnt")
        libUtilities.snap(heelRoll.prnt.mNode, self.JointSystem.Joints[-1].mNode, r=0)
        libUtilities.snap(heelRoll.prnt.mNode, self.JointSystem.Joints[self.endJointNumber].mNode, t=0)

        # Create a negative multiply divide for the heel
        heelMd = libUtilities.inverseMultiplyDivide(utils.nameMe(self.side,
                                                                 self.part + "HeelInverse",
                                                                 "MD"))
        heelMdMeta = core.MetaRig(heelMd.name(), nodeType="multiplyDivide")
        self.RollSystem.addSupportNode(heelMdMeta, "heelMD")


        # Parent to the heel
        heelRoll.setParent(tipToeRoll)

        # Connect to the Roll System
        self.RollSystem.addSupportNode(tipToeRoll, "tipToeRoll")
        self.RollSystem.addSupportNode(heelRoll, "heelRoll")

        # Connect the Rolls
        self.mainIK.pynode.Heel >> heelMd.input1X
        heelMd.outputX >> heelRoll.pynode.attr("r%s" % self.primaryAxis[2])
        self.mainIK.pynode.TipToe >> tipToeRoll.pynode.attr("r%s" % self.primaryAxis[2])

        # Reparent the IK Handles
        self.ikHandle.setParent(heelRoll)
        self.ballIKHandle.setParent(heelRoll)

        # Reparent the Syste
        self.mainIK.addChild(tipToeRoll.prnt.mNode)

    def reparent_joints(self):
        self.JointSystem.Joints[-1].setParent(
            self.JointSystem.Joints[self.endJointNumber])

    def build_ik(self):
        # Reparent the toe
        self.reparent_joints()
        self.ballIKHandle = _build_ik_(self,
                                       SOLVERS["Single"],
                                       "BallIKHandle",
                                       -3,
                                       -2)

    @property
    def RollSystem(self):
        return self.getSupportNode("RollSystem")

    @RollSystem.setter
    def RollSystem(self, data):
        self.addSupportNode(data, "RollSystem")

    @property
    def ballIKHandle(self):
        return self.getSupportNode("ballIKHandle")

    @ballIKHandle.setter
    def ballIKHandle(self, data):
        self.addSupportNode(data, "ballIKHandle")


class armHoof(arm, hoof):
    def __init__(self, *args, **kwargs):
        arm.__init__(self, *args, **kwargs)
        hoof.__init__(self, *args, **kwargs)

    def build_control(self):
        self.hasPivot = True
        arm.build_control(self)
        hoof.build_control(self)

    def build_ik(self):
        arm.build_ik(self)
        hoof.build_ik(self)

    def align_control(self):
        arm.align_control(self)
        hoof.align_control(self)


class hipHoof(hip, hoof):
    def __init__(self, *args, **kwargs):
        hip.__init__(self, *args, **kwargs)
        hoof.__init__(self, *args, **kwargs)

    def build_control(self):
        self.hasPivot = True
        hip.build_control(self)
        hoof.build_control(self)

    def build_ik(self):
        hip.build_ik(self)
        hoof.build_ik(self)

    def align_control(self):
        hip.align_control(self)
        hoof.align_control(self)


class quadHoof(quad, hoof):
    def __init__(self, *args, **kwargs):
        quad.__init__(self, *args, **kwargs)
        hoof.__init__(self, *args, **kwargs)

    def build_control(self):
        self.hasPivot = True
        quad.build_control(self)
        hoof.build_control(self)

    def build_ik(self):
        quad.build_ik(self)
        hoof.build_ik(self)

    def align_control(self):
        quad.align_control(self)
        hoof.align_control(self)


class foot(hoof):
    """This is the classic IK foot System."""

    def __init__(self, *args, **kwargs):
        super(foot, self).__init__(*args, **kwargs)
        self.rollAttrs = ["Heel", "Ball", "Toe", "TipToe"]

    def build_ik(self):
        self.reparent_joints()
        self.ballIKHandle = _build_ik_(self,
                                       SOLVERS["Single"],
                                       "BallIKHandle",
                                       -4,
                                       -3)

        self.toeIKHandle = _build_ik_(self,
                                      SOLVERS["Single"],
                                      "ToeIKHandle",
                                      -3,
                                      -2)

    def build_control(self):
        super(foot, self).build_control()
        # Create reverse foot
        ballRoll = core.MetaRig(part=self.part, side=self.side, endSuffix="BallRoll")
        ballRoll.addParent("ballRollPrnt")
        self.RollSystem.addSupportNode(ballRoll, "ballRoll")
        # Snap to ball
        libUtilities.snap(ballRoll.prnt.mNode, self.JointSystem.Joints[-3].mNode, r=0)
        libUtilities.snap(ballRoll.prnt.mNode, self.JointSystem.Joints[self.endJointNumber].mNode, t=0)

        # Create toe control
        toeRoll = core.MetaRig(part=self.part, side=self.side, endSuffix="ToeRoll")
        toeRoll.addParent("toeRollPrnt")

        self.RollSystem.addSupportNode(toeRoll, "toeRoll")
        # Snap to toe
        libUtilities.snap(toeRoll.prnt.mNode, self.JointSystem.Joints[-3].mNode, r=0)
        libUtilities.snap(toeRoll.prnt.mNode, self.JointSystem.Joints[self.endJointNumber].mNode, t=0)
        # Parent main ik to reverse
        self.ikHandle.setParent(ballRoll)
        # Parent the toe handle to to control
        self.toeIKHandle.setParent(toeRoll)
        # Parent reverse foot and toe to heel roll
        for roll in [ballRoll, toeRoll]:
            roll.setParent(self.RollSystem.getSupportNode("heelRoll"))

        # Connect to the attributes to the rolls
        self.mainIK.pynode.Ball >> ballRoll.pynode.attr("r%s" % self.primaryAxis[2])
        self.mainIK.pynode.Toe >> toeRoll.pynode.attr("r%s" % self.primaryAxis[2])

    @property
    def toeIKHandle(self):
        return self.getSupportNode("toeIKHandle")

    @toeIKHandle.setter
    def toeIKHandle(self, data):
        self.addSupportNode(data, "toeIKHandle")


class armFoot(arm, foot):
    def __init__(self, *args, **kwargs):
        arm.__init__(self, *args, **kwargs)
        foot.__init__(self, *args, **kwargs)

    def build_control(self):
        self.hasPivot = True
        arm.build_control(self)
        foot.build_control(self)

    def build_ik(self):
        arm.build_ik(self)
        foot.build_ik(self)

    def align_control(self):
        arm.align_control(self)
        foot.align_control(self)


class hipFoot(hip, foot):
    def __init__(self, *args, **kwargs):
        hip.__init__(self, *args, **kwargs)
        foot.__init__(self, *args, **kwargs)

    def build_control(self):
        self.hasPivot = True
        hip.build_control(self)
        foot.build_control(self)

    def build_ik(self):
        hip.build_ik(self)
        foot.build_ik(self)

    def align_control(self):
        hip.align_control(self)
        foot.align_control(self)


class quadFoot(quad, foot):
    def __init__(self, *args, **kwargs):
        quad.__init__(self, *args, **kwargs)
        foot.__init__(self, *args, **kwargs)

    def build_control(self):
        self.hasPivot = True
        quad.build_control(self)
        foot.build_control(self)

    def build_ik(self):
        quad.build_ik(self)
        foot.build_ik(self)

    def align_control(self):
        quad.align_control(self)
        foot.align_control(self)


class paw(foot):
    def __init__(self, *args, **kwargs):
        super(paw, self).__init__(*args, **kwargs)
        self.rollAttrs = ["Heel", "Ball", "Ankle", "Toe", "TipToe"]

    def reparent_joints(self):
        self.JointSystem.Joints[-1].setParent(
            self.JointSystem.Joints[self.endJointNumber + 1])

    def build_ik(self):
        # Reparent the toe
        self.reparent_joints()
        super(paw, self).build_ik()
        self.ankleIKHandle = _build_ik_(self,
                                        SOLVERS["Single"],
                                        "AnkleIKHandle",
                                        self.endJointNumber,
                                        self.endJointNumber + 1)

    def build_control(self):
        super(paw, self).build_control()
        # Create toe control
        ankleRoll = core.MetaRig(part=self.part, side=self.side, endSuffix="AnkleRoll")
        ankleRoll.addParent("ankleRollPrnt")

        self.RollSystem.addSupportNode(ankleRoll, "ankleRoll")
        # Snap to toe
        libUtilities.snap(ankleRoll.prnt.mNode, self.JointSystem.Joints[self.endJointNumber + 1].mNode, r=0)
        libUtilities.snap(ankleRoll.prnt.mNode, self.JointSystem.Joints[self.endJointNumber].mNode, t=0)

        self.RollSystem.addSupportNode(ankleRoll, "ankleRoll")
        ballRoll = self.getSupportNode("ballRoll")

        # Reparent the heirachy
        self.ankleIKHandle.setParent(ballRoll)
        ankleRoll.setParent(ballRoll)
        self.ikHandle.setParent(ankleRoll)

        # Connect to the attributes to the rolls
        self.mainIK.pynode.Ankle >> ankleRoll.pynode.attr("r%s" % self.primaryAxis[2])

    @property
    def ankleIKHandle(self):
        return self.getSupportNode("ankleIKHandle")

    @ankleIKHandle.setter
    def ankleIKHandle(self, data):
        self.addSupportNode(data, "ankleIKHandle")


class armPaw(arm, paw):
    def __init__(self, *args, **kwargs):
        arm.__init__(self, *args, **kwargs)
        paw.__init__(self, *args, **kwargs)

    def build_control(self):
        self.hasPivot = True
        arm.build_control(self)
        paw.build_control(self)

    def build_ik(self):
        arm.build_ik(self)
        paw.build_ik(self)

    def align_control(self):
        arm.align_control(self)
        paw.align_control(self)


class hipPaw(hip, paw):
    def __init__(self, *args, **kwargs):
        hip.__init__(self, *args, **kwargs)
        paw.__init__(self, *args, **kwargs)

    def build_control(self):
        self.hasPivot = True
        hip.build_control(self)
        paw.build_control(self)

    def build_ik(self):
        hip.build_ik(self)
        paw.build_ik(self)

    def align_control(self):
        hip.align_control(self)
        paw.align_control(self)


class quadPaw(quad, paw):
    def __init__(self, *args, **kwargs):
        quad.__init__(self, *args, **kwargs)
        paw.__init__(self, *args, **kwargs)

    def build_control(self):
        self.hasPivot = True
        quad.build_control(self)
        paw.build_control(self)

    def build_ik(self):
        quad.build_ik(self)
        paw.build_ik(self)

    def align_control(self):
        quad.align_control(self)
        paw.align_control(self)

core.Red9_Meta.registerMClassInheritanceMapping()
core.Red9_Meta.registerMClassNodeMapping(nodeTypes=['ikHandle', 'multiplyDivide', "clamp"])

if __name__ == '__main__':
    pm.newFile(f=1)

    # subSystem = SubSystem(side="U", part="Core")
    # print "s"

    # print ikSystem

    mainSystem = core.SubSystem(side="U", part="Core")

    ikSystem = mainSystem.addMetaSubSystem(hipPaw, "IK")
    # ikSystem.ikControlToWorld = True
    ikSystem.test_build()
    ikSystem.convertToComponent("IK")