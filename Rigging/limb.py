"""
@package PKD_Tools.Rigging.limb
@brief This package creates various limb system. There are essentially three types of limb system

<i>Arm: A 2 joint solver</i><br>
<i>Hip: A 3 joint solver where the last two joints is a typical ik solver and first joint is single joint solver where it
follows the Ik</i>
<i>Quad: A 4 joint spring solver with access the special attributes to the solver</i>

Using these 3 system you can further add appendage such as Hand, Hoof, Foot or Paw
"""

from PKD_Tools.Rigging import utils
from PKD_Tools.Rigging import core
from PKD_Tools.Rigging import parts
from PKD_Tools import libUtilities
from PKD_Tools import libVector
import pymel.core as pm

# if __name__ == '__main__':
#     for mod in core, parts:
#         reload(mod)

SOLVERS = {
    "Single": "ikSCsolver",
    "RotatePlane": "ikRPsolver",
    "Spring": "ikSpringSolver",
    "2Bone": "ik2Bsolver"
}


def _build_ik_(metaClass, solver, handleSuffix, startJointNumber, endJointNumber):
    """A generic function to create a IK solver that is used by the various metaClasses.
    @param metaClass: The metaclass object
    @param solver:
    @param handleSuffix:
    @param startJointNumber:
    @param endJointNumber:
    @return:
    """
    name = utils.nameMe(metaClass.side, metaClass.part, handleSuffix)
    startJoint = metaClass.jointSystem.joints[startJointNumber].shortName()
    endJoint = metaClass.jointSystem.joints[endJointNumber].shortName()
    ikHandle = pm.ikHandle(name=name, sj=startJoint, ee=endJoint, sol=solver, sticky="sticky")[0]
    ikHandleMeta = core.MovableSystem(ikHandle.name())
    metaClass.transferPropertiesToChild(ikHandleMeta, handleSuffix[0].lower() + handleSuffix[1:])
    ikHandleMeta.v = False
    # IK Handle needs to be in it's own group in case the polevector is not set. Otherwise if you reparent it
    # the polevector value changes in relation to the parent space
    # Create the parent meta
    ikHandleMeta.part = handleSuffix
    ikHandleMeta.addParent(snap=False)
    # Set the pivot to the endJoint
    libUtilities.snap_pivot(ikHandleMeta.prnt.mNode, endJoint)
    return ikHandleMeta


class LimbIk(parts.Ik):
    def __init__(self, *args, **kwargs):
        super(LimbIk, self).__init__(*args, **kwargs)
        self.ikSolver = SOLVERS["Single"]
        self.customPVPosition = None
        self.startJointNumber = 0
        self.endJointNumber = 1

    def loadIKPlugin(self):
        if self.ikSolver not in ["ikRPsolver", "ikSCsolver"]:
            pm.loadPlugin(self.ikSolver, quiet=True)
            libUtilities.melEval(self.ikSolver)

    def build(self):
        # Load any IK plugin
        self.loadIKPlugin()
        # Build the IK System
        self.buildIk()
        # Build the controls
        self.buildControl()
        # Clean up the heirachy
        self.cleanUp()

    def buildPv(self):
        self.pv = core.Ctrl(part="%s_PV" % self.part, side=self.side)
        self.pv.ctrlShape = "Locator"
        self.pv.build()
        self.pv.setParent(self)

        # Position And Align The Pole Vector Control

        default_pole_vector = libVector.vector(list(self.ikHandle.poleVector))

        # Check user user defined pos. If not then take then find the vector from the second joint in the chain
        pv_position = self.customPVPosition
        if not pv_position:
            second_joint_position = self.jointSystem.joints[self.startJointNumber + 1].pynode.getTranslation(
                space="world")
            pv_position = (default_pole_vector * [30, 30, 30]) + second_joint_position

        # Get the Pole vector position that it wants to snap to
        self.pv.prnt.pynode.setTranslation(pv_position, space="world")
        pvTwist = 0

        # Find the twist of the new pole vector if to a new positiion
        if self.customPVPosition:
            pm.poleVectorConstraint(self.pv.mNode, self.ikHandle.mNode, w=1)
            offset_pole_vector = self.ikHandle.poleVector

            # Delete the polevector
            pm.delete(self.ikHandle.mNode, cn=1)
            self.ikHandle.poleVector = default_pole_vector

            # Find the twist value so it goes back to zero
            from PKD_Tools.Rigging import nilsNoFlipIK
            pvTwist = nilsNoFlipIK.nilsNoFlipIKProc(offset_pole_vector[0],
                                                    offset_pole_vector[1],
                                                    offset_pole_vector[2],
                                                    self.ikHandle.mNode)

        # Pole vector points at second joint
        pm.aimConstraint(self.jointSystem.joints[self.startJointNumber + 1].pynode,
                         self.pv.pynode,
                         aimVector=(0, 0, 1),
                         upVector=(0, 0, 1))

        pm.poleVectorConstraint(self.pv.mNode, self.ikHandle.mNode, weight=1)
        self.ikHandle.twist = pvTwist

    def alignControl(self):
        self.mainIK.snap(self.jointSystem.joints[self.endJointNumber].mNode, not self.ikControlToWorld)

    def buildControl(self):
        self.mainIK = self.createCtrlObj(self.part)
        self.alignControl()
        self.mainIK.addChild(self.ikHandle.SUP_Prnt.pynode)

    def buildIk(self):
        # Setup the IK handle RP solver
        self.ikHandle = _build_ik_(self, self.ikSolver, "IkHandle", self.startJointNumber, self.endJointNumber)

    def buildTwist(self):
        # Check that that a pv exists
        if self.pv is None:
            # Create one
            self.buildPv()
        # Create a new meta node.
        self.twist = core.MovableSystem(part=self.part, side=self.side, endSuffix="TwistGrp")
        # Match it to the first joint
        self.twist.snap(self.ikHandle.mNode, True)
        # Parent the PV Control
        self.pv.setParent(self.twist)
        # Rotate the new node 90 on first axis of the rotate order
        self.twist.pynode.attr("r%s" % self.primary_axis[0]).set(90)
        # Zero out the transform
        twistPrnt = core.MovableSystem(part=self.part, side=self.side, endSuffix="TwistPrnt")
        twistPrnt.snap(self.twist.pynode, rotate=True)
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
        libUtilities.addFloatAttr(self.mainIK.mNode, "Knee", shortName="twist", attrMax=720, attrMin=-720)
        # Connect the new attribute to the twist offset
        self.mainIK.pynode.twist >> self.twist.pynode.attr("r%s" % self.primary_axis[0])
        # Hide the PV
        # self.pv.prnt.visibility = False

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


class Arm(LimbIk):
    """This is base IK System. with a three joint"""

    def __init__(self, *args, **kwargs):
        super(Arm, self).__init__(*args, **kwargs)
        self.ikSolver = SOLVERS["2Bone"]
        self.endJointNumber = 2

    def testBuild(self, **kwargs):
        super(Arm, self).testBuild(**kwargs)
        self.buildPv()


class Hip(Arm):
    def __init__(self, *args, **kwargs):
        super(Hip, self).__init__(*args, **kwargs)
        self.startJointNumber = 1
        self.endJointNumber = 3

    def buildIk(self):
        super(Hip, self).buildIk()
        self.hipIKHandle = _build_ik_(self, SOLVERS["Single"], "ClavIkHandle", 0, 1)

    # noinspection PyArgumentList
    def buildControl(self):
        super(Hip, self).buildControl()
        # Build the Hip Control
        hipCtrl = core.Ctrl(part=self.jointSystem.joints[0].part, side=self.side)
        hipCtrl.ctrlShape = "Circle"
        hipCtrl.build()
        hipCtrl.addGimbalMode()
        if self.hasParentMaster:
            hipCtrl.addParentMaster()
        hipCtrl.setRotateOrder(self.rotateOrder)
        # First joint alias
        firstJoint = self.jointSystem.joints[0]
        # Align with first joint
        hipCtrl.snap(firstJoint.pynode)
        # Parent the hip IkControl
        self.hipIKHandle.SUP_Prnt.setParent(hipCtrl)
        # Create a helper joint
        pm.select(cl=1)
        self.aimHelper = core.Joint(part=firstJoint.part, side=self.side, endSuffix="AimHelper")
        # Align with the first joint
        self.aimHelper.snap(firstJoint.pynode)

        # Freeze the rotation on joint
        # self.aimHelper.pynode.jointOrient.set(firstJoint.pynode.jointOrient.get())
        self.aimHelper.jointOrient = firstJoint.jointOrient
        # New upVector
        second_joint_position = list(
            self.jointSystem.joints[self.startJointNumber + 1].pynode.getTranslation(space="world"))
        default_pole_vector = libVector.vector(list(self.ikHandle.poleVector))
        aimPosition = (default_pole_vector * [30, 30, 30]) + libVector.vector(second_joint_position)
        upVector = core.MovableSystem(part=firstJoint.part, side=self.side, endSuffix="UpVector")
        upVector.pynode.setTranslation(aimPosition)
        self.aimHelper.addSupportNode(upVector, "UpVector")
        self.aimHelper.v = False

        # Aim Constraint at mainIk Handle
        pm.aimConstraint(self.mainIK.pynode, self.aimHelper.pynode, mo=1, wut="object", wuo=upVector.mNode)

        # Orient Constraint the Hip Constraint
        hipCtrl.addConstraint(self.aimHelper.pynode, "orient")

        # Point constrain the first joint
        pm.pointConstraint(hipCtrl.mNode, firstJoint.mNode, mo=1)

        # Cleanup
        self.hipIK = hipCtrl

        # Create main grp
        mainGrp = core.MovableSystem(part=self.part + "Main", side=self.side)
        hipGrp = core.MovableSystem(part=self.part + "Hip", side=self.side)

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

    def buildPv(self):
        super(Hip, self).buildPv()
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


class Quad(LimbIk):
    def __init__(self, *args, **kwargs):
        super(Quad, self).__init__(self, *args, **kwargs)
        self.endJointNumber = 3
        self.ikSolver = SOLVERS["Spring"]

    def buildControl(self):
        super(Quad, self).buildControl()
        # Adding controls to the sprink bias
        self.mainIK.addDivAttr("SpringBias", "lblSpringBias")
        self.mainIK.addFloatAttr("Start", sn="StartBias", df=0.5)
        self.mainIK.addFloatAttr("End", sn="EndBias", df=0.5)
        self.mainIK.pynode.StartBias >> self.ikHandle.pynode.springAngleBias[0].springAngleBias_FloatValue
        self.mainIK.pynode.EndBias >> self.ikHandle.pynode.springAngleBias[1].springAngleBias_FloatValue

    def testBuild(self, **kwargs):
        super(Quad, self).testBuild(**kwargs)
        self.buildPv()


# noinspection PyUnresolvedReferences
class Hand(object):
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

    """"""
class ArmHand(Arm, Hand):
    def buildControl(self):
        self.hasPivot = True
        Arm.buildControl(self)
        Hand.build_control(self)

    def buildIk(self):
        Arm.buildIk(self)
        Hand.build_ik(self)


class QuadHand(Quad, Hand):
    def buildControl(self):
        self.hasPivot = True
        Quad.buildControl(self)
        Hand.build_control(self)

    def buildIk(self):
        Quad.buildIk(self)
        Hand.build_ik(self)


class HipHand(Hip, Hand):
    def buildControl(self):
        self.hasPivot = True
        Hip.buildControl(self)
        Hand.build_control(self)

    def buildIk(self):
        Hip.buildIk(self)
        Hand.build_ik(self)


# noinspection PyUnresolvedReferences,PyArgumentList,PyStatementEffect
class Hoof(object):
    """This is the IK hoof System."""

    def __init__(self, *args, **kwargs):
        super(Hoof, self).__init__(*args, **kwargs)
        self.rollAttrs = ["Heel", "TipToe"]

    def align_control(self):
        # Remove the x roatation

        if not self.ikControlToWorld:
            # Create a new joint at the position of the end joint
            pm.select(self.jointSystem.joints[self.endJointNumber].mNode)
            helperJnt = pm.joint()
            # Reset the joint orientation
            pm.parent(helperJnt, world=True)
            # Remove the primary axis
            helperJnt.attr("jointOrient%s" % self.primaryAxis[2].upper()).set(0)
            # Align the control to this joint
            self.mainIK.snap(helperJnt, rotate=False)
            # Delete helper joint
            pm.delete(helperJnt)

    def buildControl(self):
        # Create the roll system
        self.RollSystem = core.Network(part=self.part + "Roll", side=self.side)

        # Add the rolls attrs
        libUtilities.addDivAttr(self.mainIK.pynode, "Roll", "rollDiv")
        # Tip_Heel
        for attr in self.rollAttrs:
            libUtilities.addFloatAttr(self.mainIK.pynode, attr, 270, -270)

            # Create the 2 rotate system
        tipToeRoll = core.MovableSystem(part=self.part, side=self.side, endSuffix="TipToeRoll")
        tipToeRoll.addParent(snap=False, endSuffix="TipToeRollPrnt")
        tipToeRoll.snap(self.jointSystem.joints[-2].mNode)
        libUtilities.snap(tipToeRoll.prnt.mNode, self.jointSystem.joints[self.endJointNumber].mNode, translate=False)

        # self.toeRoll.setParent(self.jointSystem.Joints[-1])
        heelRoll = core.MovableSystem(part=self.part, side=self.side, endSuffix="HeelRoll")
        heelRoll.addParent(snap=False, endSuffix="HeelRollPrnt")
        heelRoll.snap(self.jointSystem.joints[-1].mNode)
        libUtilities.snap(heelRoll.prnt.mNode, self.jointSystem.joints[self.endJointNumber].mNode, translate=False)

        # Create a negative multiply divide for the heel
        heelMd = libUtilities.inverseMultiplyDivide()
        heelMdMeta = core.MovableSystem(heelMd.name(), nodeType="multiplyDivide")
        heelMdMeta.part = "%sHeel" % self.part
        heelMdMeta.rigType = "InverseMD"
        heelMdMeta.resetName()
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

    def reparentJoints(self):
        self.jointSystem.joints[-1].setParent(
            self.jointSystem.joints[self.endJointNumber])

    def buildIk(self):
        # Reparent the toe
        self.reparentJoints()
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


class ArmHoof(Arm, Hoof):
    def __init__(self, *args, **kwargs):
        Arm.__init__(self, *args, **kwargs)
        Hoof.__init__(self, *args, **kwargs)

    def buildControl(self):
        self.hasPivot = True
        Arm.buildControl(self)
        Hoof.buildControl(self)

    def buildIk(self):
        Arm.buildIk(self)
        Hoof.buildIk(self)

    def alignControl(self):
        Arm.alignControl(self)
        Hoof.align_control(self)


class HipHoof(Hip, Hoof):
    def __init__(self, *args, **kwargs):
        Hip.__init__(self, *args, **kwargs)
        Hoof.__init__(self, *args, **kwargs)

    def buildControl(self):
        self.hasPivot = True
        Hip.buildControl(self)
        Hoof.buildControl(self)

    def buildIk(self):
        Hip.buildIk(self)
        Hoof.buildIk(self)

    def alignControl(self):
        Hip.alignControl(self)
        Hoof.align_control(self)


class QuadHoof(Quad, Hoof):
    def __init__(self, *args, **kwargs):
        Quad.__init__(self, *args, **kwargs)
        Hoof.__init__(self, *args, **kwargs)

    def buildControl(self):
        self.hasPivot = True
        Quad.buildControl(self)
        Hoof.buildControl(self)

    def buildIk(self):
        Quad.buildIk(self)
        Hoof.buildIk(self)

    def alignControl(self):
        Quad.alignControl(self)
        Hoof.align_control(self)


# noinspection PyUnresolvedReferences,PyArgumentList,PyStatementEffect,PyTypeChecker
class Foot(Hoof):
    """This is the classic IK foot System."""

    def __init__(self, *args, **kwargs):
        super(Foot, self).__init__(*args, **kwargs)
        self.rollAttrs = ["Heel", "Ball", "Toe", "TipToe"]

    def buildIk(self):
        self.reparentJoints()
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

    def buildControl(self):
        super(Foot, self).buildControl()
        # Create reverse foot
        ballRoll = core.MovableSystem(part=self.part, side=self.side, endSuffix="BallRoll")
        ballRoll.addParent(snap=False, endSuffix="ballRollPrnt")
        self.RollSystem.addSupportNode(ballRoll, "ballRoll")
        # Snap to ball
        ballRoll.snap(self.jointSystem.joints[-3].mNode)
        libUtilities.snap(ballRoll.prnt.mNode, self.jointSystem.joints[self.endJointNumber].mNode, translate=False)

        # Create toe control
        toeRoll = core.MovableSystem(part=self.part, side=self.side, endSuffix="ToeRoll")
        toeRoll.addParent(snap=False, endSuffix="toeRollPrnt")

        self.RollSystem.addSupportNode(toeRoll, "toeRoll")
        # Snap to toe
        toeRoll.snap(self.jointSystem.joints[-3].mNode)
        libUtilities.snap(toeRoll.prnt.mNode, self.jointSystem.joints[self.endJointNumber].mNode, translate=False)
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


class ArmFoot(Arm, Foot):
    def __init__(self, *args, **kwargs):
        Arm.__init__(self, *args, **kwargs)
        Foot.__init__(self, *args, **kwargs)

    def buildControl(self):
        self.hasPivot = True
        Arm.buildControl(self)
        Foot.buildControl(self)

    def buildIk(self):
        Arm.buildIk(self)
        Foot.buildIk(self)

    def alignControl(self):
        Arm.alignControl(self)
        Foot.align_control(self)

# noinspection PyUnresolvedReferences,PyArgumentList,PyStatementEffect,PyTypeChecker
class HipFoot(Hip, Foot):
    def __init__(self, *args, **kwargs):
        Hip.__init__(self, *args, **kwargs)
        Foot.__init__(self, *args, **kwargs)

    def buildControl(self):
        self.hasPivot = True
        Hip.buildControl(self)
        Foot.buildControl(self)

    def buildIk(self):
        Hip.buildIk(self)
        Foot.buildIk(self)

    def alignControl(self):
        Hip.alignControl(self)
        Foot.align_control(self)


class QuadFoot(Quad, Foot):
    def __init__(self, *args, **kwargs):
        Quad.__init__(self, *args, **kwargs)
        Foot.__init__(self, *args, **kwargs)

    def buildControl(self):
        self.hasPivot = True
        Quad.buildControl(self)
        Foot.buildControl(self)

    def buildIk(self):
        Quad.buildIk(self)
        Foot.buildIk(self)

    def alignControl(self):
        Quad.alignControl(self)
        Foot.align_control(self)

# noinspection PyUnresolvedReferences,PyArgumentList,PyStatementEffect,PyTypeChecker
class Paw(Foot):
    def __init__(self, *args, **kwargs):
        super(Paw, self).__init__(*args, **kwargs)
        self.rollAttrs = ["Heel", "Ball", "Ankle", "Toe", "TipToe"]

    def reparentJoints(self):
        self.jointSystem.joints[-1].setParent(
            self.jointSystem.joints[self.endJointNumber + 1])

    def buildIk(self):
        # Reparent the toe
        self.reparentJoints()
        super(Paw, self).buildIk()
        self.ankleIKHandle = _build_ik_(self,
                                        SOLVERS["Single"],
                                        "AnkleIKHandle",
                                        self.endJointNumber,
                                        self.endJointNumber + 1)

    def buildControl(self):
        super(Paw, self).buildControl()
        # Create toe control
        ankleRoll = core.MovableSystem(part=self.part, side=self.side, endSuffix="AnkleRoll")
        ankleRoll.addParent(snap=False, endSuffix="ankleRollPrnt")

        self.RollSystem.addSupportNode(ankleRoll, "ankleRoll")
        # Snap to toe
        ankleRoll.snap(self.jointSystem.joints[self.endJointNumber + 1].mNode)
        libUtilities.snap(ankleRoll.prnt.mNode, self.jointSystem.joints[self.endJointNumber].mNode, translate=False)

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


class ArmPaw(Arm, Paw):
    def __init__(self, *args, **kwargs):
        Arm.__init__(self, *args, **kwargs)
        Paw.__init__(self, *args, **kwargs)

    def buildControl(self):
        self.hasPivot = True
        Arm.buildControl(self)
        Paw.buildControl(self)

    def buildIk(self):
        Arm.buildIk(self)
        Paw.buildIk(self)

    def alignControl(self):
        Arm.alignControl(self)
        Paw.align_control(self)


class HipPaw(Hip, Paw):
    def __init__(self, *args, **kwargs):
        Hip.__init__(self, *args, **kwargs)
        Paw.__init__(self, *args, **kwargs)

    def buildControl(self):
        self.hasPivot = True
        Hip.buildControl(self)
        Paw.buildControl(self)

    def buildIk(self):
        Hip.buildIk(self)
        Paw.buildIk(self)

    def alignControl(self):
        Hip.alignControl(self)
        Paw.align_control(self)


class QuadPaw(Quad, Paw):
    def __init__(self, *args, **kwargs):
        Quad.__init__(self, *args, **kwargs)
        Paw.__init__(self, *args, **kwargs)

    def buildControl(self):
        self.hasPivot = True
        Quad.buildControl(self)
        Paw.buildControl(self)

    def buildIk(self):
        Quad.buildIk(self)
        Paw.buildIk(self)

    def alignControl(self):
        Quad.alignControl(self)
        Paw.align_control(self)


core.Red9_Meta.registerMClassInheritanceMapping()
core.Red9_Meta.registerMClassNodeMapping(nodeTypes=['ikHandle',
                                                    'multiplyDivide',
                                                    "clamp"])
if __name__ == '__main__':
    pm.newFile(f=1)
    mainSystem = parts.Blender(side="C", part="Core")

    ikSystem = ArmHand(side="C", part="Core")
    system = "IK"
    mainSystem.addMetaSubSystem(ikSystem, system)
    # ikSystem.ikControlToWorld = True
    ikSystem.testBuild(buildProxy=False, buildMaster=False)
    ikSystem.convertSystemToSubSystem(system)
    pm.refresh()

    fkSystem = parts.FK(side="C", part="Core")
    mainSystem.addMetaSubSystem(fkSystem, "FK")
    fkJointSystem = ikSystem.jointSystem.replicate(part=mainSystem.part, side=mainSystem.side)
    fkJointSystem.part = ikSystem.jointSystem.part
    fkJointSystem.rigType = ikSystem.jointSystem.rigType
    fkSystem.evaluateLastJoint = False
    fkSystem.testBuild(jointSystem=fkJointSystem, buildProxy=False, buildMaster=False)
    fkSystem.convertSystemToSubSystem(fkSystem.systemType)
    mainSystem.subSystems = "IK_FK"
    pm.refresh()
    mainSystem.build()
    # fkSystem = parts.FK(side="C", part="Core")
    # mainSystem.addMetaSubSystem(fkSystem, "FK")
    # core.JointSystem.replicate()
    # fkJointSystem = ikSystem.jointSystem.replicate()
    # fkSystem.testBuild(fkJointSystem)part
    # fkSystem.convertSystemToSubSystem(fkSystem.systemType)

    # ikSystem.convertSystemToSubSystem(ikSystem.systemType)
    # TODO: Double transform node for the mainSystem
    # mainSystem.blender.pynode.attr(mainSystem.subSystems)
