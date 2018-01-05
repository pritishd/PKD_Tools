"""
@package PKD_Tools.Rigging.limb
@brief This package creates various limb system. There are essentially three types of limb system

<i>Arm: A 2 joint solver</i><br>
<i>Hip: A 3 joint solver where the last two joints is a typical ik solver and first joint is single joint solver where it
follows the Ik</i>
<i>Quad: A 4 joint spring solver with access the special attributes to the solver</i>

Using these 3 system you can further add appendage such as Hand, Hoof, Foot or Paw
"""
import pymel.core as pm

from PKD_Tools.Red9 import Red9_CoreUtils
from PKD_Tools import libUtilities, libVector
from PKD_Tools.Rigging import core, joints, parts, utils

# if __name__ == '__main__':
#     for mod in core, parts:
#         reload(mod)

SOLVERS = {
    "Single": "ikSCsolver",
    "RotatePlane": "ikRPsolver",
    "Spring": "ikSpringSolver",
    "2Bone": "ik2Bsolver"
}


# noinspection PyUnresolvedReferences
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
    startJoint = metaClass.jointSystem.joints[startJointNumber].mNode
    endJoint = metaClass.jointSystem.joints[endJointNumber].mNode
    ikHandle = pm.ikHandle(name=name, sj=startJoint, ee=endJoint, sol=solver, sticky="sticky")[0]
    ikHandleMeta = core.MovableSystem(ikHandle.name())
    metaClass.transferPropertiesToChild(ikHandleMeta, handleSuffix[0].lower() + handleSuffix[1:])
    ikHandleMeta.v = False
    # IK Handle needs to be in it's own group in case the polevector is not set. Otherwise if you reparent it
    # the polevector value changes in relation to the parent space
    # Create the parent meta
    ikHandleMeta.part = metaClass.part
    ikHandleMeta.addParent(snap=False, endSuffix="{}Prnt".format(handleSuffix))
    # Set the pivot to the endJoint
    libUtilities.snap_pivot(ikHandleMeta.prnt.mNode, endJoint)
    return ikHandleMeta


# noinspection PyUnresolvedReferences,PyStatementEffect
class LimbIk(parts.Ik):
    def __init__(self, *args, **kwargs):
        super(LimbIk, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.ikSolver = SOLVERS[kwargs.get("solver", "Single")]
        self.pvPosition = kwargs.get("pvPosition")
        self.startJointNumber = 0
        self.endJointNumber = -1
        self.offsetIKControlPosition = 0
        self.kwargs = kwargs

    def __bindData__(self, *args, **kwgs):
        super(LimbIk, self).__bindData__(*args, **kwgs)
        self.addAttr("pvPosition", [])
        self.addAttr("ikSolver", '')

    def loadIKPlugin(self):
        if self.ikSolver not in ["ikRPsolver", "ikSCsolver"]:
            pm.loadPlugin(self.ikSolver, quiet=True)
            libUtilities.melEval(self.ikSolver)

    def build(self):
        super(LimbIk, self).build()
        # Load any IK plugin
        self.loadIKPlugin()
        # Build the IK System
        self.buildIk()
        # Build the controls
        self.buildControl()
        # Clean up the heirachy
        self.cleanUp()

    def buildPvControl(self):
        self.pv = core.Ctrl(part="%s_PV" % self.part, side=self.side)
        self.pv.ctrlShape = "Locator"
        self.pv.build()
        self.pv.setParent(self)
        self.pv.setRotateOrder(self.rotateOrder)

    def buildPVConstraint(self):
        # Position And Align The Pole Vector Control
        default_pole_vector = libVector.vector(list(self.ikHandle.poleVector))

        # Check user user defined pos. If not then take then find the vector from the second joint in the chain
        pv_position = self.pvPosition
        if not pv_position:
            second_joint_position = self.jointSystem.joints[self.absStartJointNumber + 1].pynode.getTranslation(
                space="world")
            self.pvPosition = list(
                (default_pole_vector * [30, 30, 30] * ([self.scaleFactor] * 3)) + second_joint_position)

        # Get the Pole vector position that it wants to snap to
        self.pv.prnt.pynode.setTranslation(self.pvPosition, space="world")
        pvTwist = 0

        # Find the twist of the new pole vector if to a new position
        if self.pvPosition:
            pm.poleVectorConstraint(self.pv.mNode, self.ikHandle.mNode, w=1)
            offset_pole_vector = self.ikHandle.poleVector

            # Delete the pole vector
            pm.delete(self.ikHandle.mNode, cn=1)
            self.ikHandle.pynode.poleVector.set(default_pole_vector)

            # Find the twist value so it goes back to zero
            from PKD_Tools.Rigging import nilsNoFlipIK
            pvTwist = nilsNoFlipIK.nilsNoFlipIKProc(offset_pole_vector[0],
                                                    offset_pole_vector[1],
                                                    offset_pole_vector[2],
                                                    self.ikHandle.mNode)

        # Pole vector points at second joint
        aimCon = pm.aimConstraint(self.jointSystem.joints[self.startJointNumber + 1].pynode,
                                  self.pv.pynode,
                                  aimVector=self.upVector,
                                  upVector=self.upVector)
        self.constraintToMetaConstraint(aimCon, "AimCon{}".format(self.pv.rigType), "PVAim")
        pvCon = pm.poleVectorConstraint(self.pv.mNode, self.ikHandle.mNode, weight=1)
        self.constraintToMetaConstraint(pvCon, "PVCon", "poleVectorConstraint")
        self.ikHandle.twist = pvTwist

    def buildPv(self):
        self.buildPvControl()
        self.buildPVConstraint()
        self.finalisePV()

    def finalisePV(self):
        self.pv.lockRotate()
        self.pv.lockScale()

    def alignControl(self):
        controlPosition = self.absEndJointNumber + self.offsetIKControlPosition
        self.mainIK.snap(self.jointSystem.joints[controlPosition].mNode, not self.ikControlToWorld)

    def buildControl(self):
        if not self.mainIK:
            self.mainIK = self.createCtrlObj(self.part)
            self.mainIK.lockScale()
            self.alignControl()
            self.mainIK.addChild(self.ikHandle.SUP_Prnt.pynode)

        # Is it a spring solver
        # Adding control control the spring solver
        if self.ikSolver == "ikSpringSolver":
            pm.refresh()
            ikHandle = pm.PyNode(self.ikHandle.mNode)
            if hasattr(ikHandle, "springAngleBias"):
                springAngleBias = ikHandle.springAngleBias
                numBias = springAngleBias.numElements()

                self.springBiasCtrl.addDivAttr("SpringBias", "lblSpringBias")
                self.springBiasCtrl.addFloatAttr("Start", sn="StartBias", dv=0.5)
                self.springBiasCtrl.pynode.StartBias >> springAngleBias[0].springAngleBias_FloatValue

                if numBias > 2:
                    for i in range(1, numBias - 1):
                        attr = "MidBias{}".format(i)
                        self.springBiasCtrl.addFloatAttr("Mid{}".format(i), sn=attr, dv=0.5)
                        self.springBiasCtrl.pynode.attr(attr) >> springAngleBias[i].springAngleBias_FloatValue

                self.springBiasCtrl.addFloatAttr("End", sn="EndBias", dv=0.5)
                self.springBiasCtrl.pynode.EndBias >> springAngleBias[numBias - 1].springAngleBias_FloatValue
            else:
                print "Could not find srpingAngleBias in {}".format(self.ikHandle.pynode)

        else:
            pass

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

    @property
    def springBiasCtrl(self):
        springBiasCtrl = self.getRigCtrl("SpringBias")
        if springBiasCtrl:
            return springBiasCtrl
        else:
            return self.mainIK

    @springBiasCtrl.setter
    def springBiasCtrl(self, data):
        self.addRigCtrl(data, ctrType="SpringBias", mirrorData=self.mirrorData)

    @property
    def absEndJointNumber(self):
        return self.jointSystem.jointList.index(self.jointSystem.jointList[self.endJointNumber])

    @property
    def absStartJointNumber(self):
        return self.jointSystem.jointList.index(self.jointSystem.jointList[self.startJointNumber])

    @property
    def scaleFactor(self):
        key = "scaleFactor"
        if not self.metaCache.setdefault(key, []):
            total = sum(self.jointSystem.lengths[self.absStartJointNumber:self.absEndJointNumber])
            self.metaCache[key] = total / 17.575
        return self.metaCache[key]


class Spring(LimbIk):
    def __init__(self, *args, **kwargs):
        super(Spring, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.ikSolver = SOLVERS[kwargs.get("solver", "Spring")]
        self.endJointNumber = -1


class Arm(LimbIk):
    """This is base IK System. with a three joint"""

    def __init__(self, *args, **kwargs):
        super(Arm, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.ikSolver = SOLVERS[kwargs.get("solver", "RotatePlane")]
        self.endJointNumber = 2

    def testBuild(self, **kwargs):
        super(Arm, self).testBuild(**kwargs)
        self.buildPv()


# noinspection PyStatementEffect
class Hip(Arm):
    def __init__(self, *args, **kwargs):
        super(Hip, self).__init__(*args, **kwargs)
        self.startJointNumber = 1
        self.endJointNumber = -1
        self.hipIkSolver = kwargs.get('hipIkSolver', 'Single')
        self.hipEndJointNumber = kwargs.get('hipEndJointNumber', 1)
        # Ensure the next start joint number of the main always start from the next joint
        self.startJointNumber = self.hipEndJointNumber

    def buildIk(self):
        super(Hip, self).buildIk()
        self.hipIKHandle = _build_ik_(self, SOLVERS[self.hipIkSolver], "ClavIkHandle", 0, self.hipEndJointNumber)

    def positionHipControl(self, aimJoint):
        hipCtrl = core.Ctrl(part=self.jointSystem.joints[0].part, side=self.side, shape="Circle")

        hipCtrl.build()
        hipCtrl.lockScale()
        hipCtrl.addGimbalMode()
        if self.hasParentMaster:
            hipCtrl.addParentMaster()
        hipCtrl.setRotateOrder(self.rotateOrder)
        # Cleanup
        self.hipIK = hipCtrl

        # Align with first joint
        self.hipIK.snap(aimJoint.pynode)
        # Parent the hip IkControl
        if self.hipIkSolver == "RotatePlane":
            snapJoint = self.jointSystem.joints[self.hipEndJointNumber]
            hipIKCtrl = core.Ctrl(part=snapJoint.part, side=self.side, shape=self.mainCtrlShape)
            hipIKCtrl.build()
            hipCtrl.setRotateOrder(self.rotateOrder)
            hipIKCtrl.lockScale()
            hipIKCtrl.lockRotate()
            hipIKCtrl.snap(snapJoint)
            hipIKCtrl.setParent(self.hipIK)
            self.hipIKHandle.setParent(hipIKCtrl)
            self.secondHipIK = hipIKCtrl
        else:
            self.hipIKHandle.setParent(self.hipIK.parentDriver)

    def buildHipSpaceSwitch(self, aimJoint):
        # Create a helper joint
        pm.select(cl=1)
        self.aimHelper = core.MovableSystem(part=aimJoint.part, side=self.side, endSuffix="AimHelper")
        # self.aimHelper.jointOrient = firstJoint.jointOrient
        self.aimHelper.rotateOrder = aimJoint.rotateOrder
        # Align with the first joint
        self.aimHelper.snap(aimJoint.pynode)

        # Figure out the up vector position.
        second_joint_position = self.jointSystem.positions[self.hipEndJointNumber]
        hipIkPoleVector = self.hipIKHandle.poleVector if self.hipIkSolver == "RotatePlane" else None
        default_pole_vector = libVector.vector(list(hipIkPoleVector or self.ikHandle.poleVector))
        # noinspection PyTypeChecker
        aimPosition = list(((default_pole_vector * [30, 30, 30] * ([self.scaleFactor] * 3)) + second_joint_position))
        if hipIkPoleVector:
            upVector = core.Ctrl(part="{}PV".format(aimJoint.part),
                                 side=self.side,
                                 endSuffix="HipPV",
                                 shape="Locator")
            upVector.build()
            self.addRigCtrl(upVector, "HipPV")
            upVector.constrainedNode.pynode.setTranslation(aimPosition)
            pvCon = pm.poleVectorConstraint(upVector.mNode, self.hipIKHandle.mNode, weight=1)
            self.constraintToMetaConstraint(pvCon, "HipPVCon", "poleVectorConstraint")
            self.secondHipIK.addDivAttr("Show", "showPV")
            self.secondHipIK.addBoolAttr("PoleVector", "pvVis")
            self.secondHipIK.pynode.pvVis >> upVector.pynode.getShape().visibility
            upVector.lockRotate()
            upVector.lockScale()

        else:
            upVector = core.MovableSystem(part=aimJoint.part, side=self.side, endSuffix="UpVector")
            self.aimHelper.addSupportNode(upVector, "UpVector")
            upVector.constrainedNode.pynode.setTranslation(aimPosition)

        # Aim Constraint at mainIk Handle
        aimConArgs = [self.mainIK.pynode, self.aimHelper.pynode]
        aimConKwgs = {"mo": False, "wut": "object", "wuo": upVector.mNode}
        pm.delete(pm.aimConstraint(*aimConArgs, **aimConKwgs))
        self.aimHelper.addParent(endSuffix="AimHelperPrnt")
        aimCon = pm.aimConstraint(*aimConArgs, **aimConKwgs)
        self.constraintToMetaConstraint(aimCon, "HipAimCon", "HipAim")

        # Setup the space switching
        constraintType = 'orient'
        if self.hipIkSolver != "Single":
            constraintType = "parent"
        self.aimHelper.prnt.v = False

        # Orient Constraint the Hip Constraint
        ikJoint = joints.Joint(part=self.part, side=self.side, endSuffix="HipIkFollow")
        ikJoint.v = False
        ikJoint.rotateOrder = self.rotateOrder
        ikJoint.setParent(aimJoint)
        ikJoint.snap(aimJoint)
        libUtilities.freeze_rotation(ikJoint.pynode)
        ikJoint.setParent(self.aimHelper)
        self.hipIK.addConstraint(ikJoint.pynode, constraintType, mo=True, weightAlias="IK")
        # Create a base joint
        hipIKCon = getattr(self.hipIK, "{}Constraint".format(constraintType))
        hipIKCon.pynode.w0.set(0)

        homeJoint = joints.Joint(part=self.part, side=self.side, endSuffix="HomeJnt")
        homeJoint.v = False
        homeJoint.rotateOrder = self.rotateOrder
        homeJoint.setParent(aimJoint)
        homeJoint.snap(aimJoint)
        libUtilities.freeze_rotation(homeJoint.pynode)
        homeJoint.setParent(self)
        # Add another contraint
        self.hipIK.addConstraint(homeJoint, constraintType, mo=True, weightAlias=self.part)

        # Blend between the two constraint
        self.inverse = core.MetaRig(side=self.side, part=self.part, endSuffix="Inverse", nodeType="reverse")

        # Attribute based on the system type
        libUtilities.addDivAttr(self.hipIK.pynode, "SpaceSwitch")
        attrName = "IK_Parent"
        libUtilities.addFloatAttr(self.hipIK.pynode, attrName)
        blendAttr = self.hipIK.pynode.attr(attrName)
        # Connect the inverse node
        blendAttr >> self.inverse.pynode.inputX
        self.inverse.pynode.outputX >> hipIKCon.pynode.w0
        blendAttr >> hipIKCon.pynode.w1

        # Point constrain the first joint
        aimJoint.addConstraint(self.hipIK, 'point')
        return upVector

    def buildAutoCompress(self):
        autoCompressSys = core.NetSubSystem(part="{}HipCompress".format(self.part), side=self.side)

        autoCompress = core.DistanceMove(part="{}HipCompress".format(self.part), side=self.side)
        self.addSupportNode(autoCompressSys, "AutoCompressSys")
        autoCompressSys.addSupportNode(autoCompress, "DistanceMove")
        autoCompress.point1.setParent(self.hipIK)
        autoCompress.point1.v = False
        autoCompress.point1.snap(self.hipIK)
        autoCompress.point2.setParent(self.mainIK)
        autoCompress.point2.snap(self.mainIK)
        autoCompress.point2.v = False
        autoCompress.mathNode.relativeMeasure = Red9_CoreUtils.distanceBetween(self.hipIK.mNode,
                                                                               self.secondHipIK.mNode)
        autoCompress.mathNode.biDirection = False
        autoCompress.reset()

        aimCompressGrp = core.MovableSystem(part="{}HipCompress".format(self.part),
                                            side=self.side)
        aimCompressGrp.setParent(self.hipIK.parentDriver)

        compressAimHelper = core.MovableSystem(part="{}HipCompress".format(self.part),
                                               side=self.side,
                                               endSuffix="AimHelper")

        compressAimHelper.setParent(aimCompressGrp)
        compressAimHelper.snap(self.secondHipIK)
        self.secondHipIK.addConstraint(compressAimHelper, "point")
        aimKwargs = {"mo": False,
                     "aimVector": [0, 1, 0],
                     "upVector": [1, 0, 0],
                     "worldUpType": "scene"}

        pm.delete(pm.aimConstraint(self.hipIK.pynode, compressAimHelper.pynode, **aimKwargs))
        compressAimHelper.addZeroPrnt()

        aimCon = pm.aimConstraint(self.hipIK.pynode, compressAimHelper.pynode, **aimKwargs)
        self.constraintToMetaConstraint(aimCon, "CompressCon", "CompressAim")

        autoCompress.connectOutput(compressAimHelper.pynode.ty)

        self.secondHipIK.addDivAttr("AutoCompress")
        self.secondHipIK.addFloatAttr("Factor", 10, 0, sn="autoCompressFactor", dv=1)
        autoCompress.connectDisable(self.secondHipIK.pynode.autoCompressFactor)

    # noinspection PyArgumentList
    def buildControl(self):
        super(Hip, self).buildControl()
        # First joint alias
        aimJoint = self.jointSystem.joints[0]

        self.positionHipControl(aimJoint)
        upVector = self.buildHipSpaceSwitch(aimJoint)

        if self.hipIkSolver != "Single":
            self.buildAutoCompress()

        # Create main grp
        mainGrp = core.MovableSystem(part="{}Main".format(self.part), side=self.side)
        hipGrp = core.MovableSystem(part="{}Hip".format(self.part), side=self.side)

        # Reparent
        self.addSupportNode(mainGrp, "MainGrp")
        self.addSupportNode(hipGrp, "HipGrp")

        # Parent the groups
        mainGrp.setParent(self)
        hipGrp.setParent(self)

        # Parent the hip control
        self.hipIK.setParent(hipGrp)
        self.aimHelper.setParent(hipGrp)
        upVector.setParent(hipGrp)

        # Parent the group
        self.mainIK.setParent(mainGrp)
        aimJoint.setParent(mainGrp)

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
    def secondHipIK(self):
        return self.getRigCtrl("secondHipIK")

    @secondHipIK.setter
    def secondHipIK(self, data):
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(data, ctrType="secondHipIK", mirrorData=self.mirrorData)

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
        if self._build_mode:
            self.endJointNumber = 3
            self.ikSolver = SOLVERS[kwargs.get("solver", "Spring")]


# noinspection PyUnresolvedReferences,PyTypeChecker
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


# noinspection PyUnresolvedReferences,PyArgumentList,PyStatementEffect,PyTypeChecker
class Foot(object):
    """This is the classic IK foot System."""

    def __init__(self, *args, **kwargs):
        super(Foot, self).__init__(*args, **kwargs)
        self.endJointNumber = -4

    def alignControl(self):
        # Remove the x roatation
        if not self.ikControlToWorld:
            # Create a new joint at the position of the end joint
            controlPosition = self.absEndJointNumber + self.offsetIKControlPosition
            pm.select(self.jointSystem.joints[controlPosition].mNode)
            helperJnt = pm.joint()
            # Reset the joint orientation
            pm.parent(helperJnt, world=True)
            # Remove the primary axis
            helperJnt.attr("jointOrient%s" % self.bendAxis.upper()).set(0)
            # Align the control to this joint
            self.mainIK.snap(helperJnt, rotate=False)
            # Delete helper joint
            pm.delete(helperJnt)

    def reparentJoints(self):
        self.jointSystem.joints[-1].setParent(
            self.jointSystem.joints[self.endJointNumber])

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

    def buildRoll(self, attr, jointTarget):
        rollName = "{}Roll".format(attr)
        roll = core.MovableSystem(part=self.part, side=self.side, endSuffix=rollName)
        roll.addParent(snap=False, endSuffix="{}Prnt".format(rollName))
        roll.snap(self.jointSystem.joints[jointTarget].mNode)
        self.RollSystem.addSupportNode(roll, rollName)
        inverseMeta = core.MetaRig(part="{}{}".format(self.part, attr),
                                   side=self.side,
                                   endSuffix="InverseMD",
                                   nodeType="multiplyDivide")
        self.mainIK.pynode.attr(attr) >> inverseMeta.pynode.input1X
        inverseMeta.pynode.outputX >> roll.pynode.attr("r{}".format(self.bendAxis.lower()))
        self.RollSystem.addSupportNode(inverseMeta, "{}MD".format(attr))
        return roll

    def buildControl(self):
        # Create the roll system
        self.RollSystem = core.Network(part=self.part + "Roll", side=self.side)

        # Add the rolls attrs
        libUtilities.addDivAttr(self.mainIK.pynode, "Roll", "rollDiv")

        # Tip_Heel
        for attr in self.rollAttrs:
            libUtilities.addFloatAttr(self.mainIK.pynode, attr, 270, -270)

        # Create the 2 rotate system
        tipToeRoll = self.buildRoll("TipToe", -2)
        heelRoll = self.buildRoll("Heel", -1)
        ballRoll = self.buildRoll("Ball", -3)

        # Parent to the heel
        heelRoll.setParent(tipToeRoll)

        # Reparent the IK Handles
        self.ikHandle.setParent(heelRoll)
        self.ballIKHandle.setParent(heelRoll)

        # Reparent the Syste
        self.mainIK.addChild(tipToeRoll.prnt.mNode)
        # Parent main ik to reverse
        self.ikHandle.setParent(ballRoll)

        rolls = [ballRoll]

        # Create toe control
        if hasattr(self.mainIK, "Toe"):
            toeRoll = self.buildRoll("Toe", -3)
            rolls.append(toeRoll)
            self.toeIKHandle.setParent(toeRoll)
        else:
            self.toeIKHandle.setParent(heelRoll)

        # Parent the toe handle to to control
        # Parent reverse foot and toe to heel roll
        for roll in rolls:
            roll.setParent(self.RollSystem.getSupportNode("HeelRoll"))

    @property
    def toeIKHandle(self):
        return self.getSupportNode("toeIKHandle")

    @toeIKHandle.setter
    def toeIKHandle(self, data):
        self.addSupportNode(data, "toeIKHandle")

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

    @property
    def rollAttrs(self):
        return ["Heel", "Ball", "Toe", "TipToe"]


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
        Foot.alignControl(self)


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
        Foot.alignControl(self)


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
        Foot.alignControl(self)


# noinspection PyUnresolvedReferences,PyArgumentList,PyStatementEffect
class Hoof(Foot):
    """This is the IK hoof System."""
    offsetIKControlPosition = 1

    @property
    def rollAttrs(self):
        return ["Heel", "Ball", "TipToe"]


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
        Hoof.alignControl(self)


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
        Hoof.alignControl(self)


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
        Hoof.alignControl(self)


# noinspection PyUnresolvedReferences,PyArgumentList,PyStatementEffect,PyTypeChecker
class Paw(Foot):
    def __init__(self, *args, **kwargs):
        super(Foot, self).__init__(*args, **kwargs)
        self.endJointNumber = -5

    @property
    def rollAttrs(self):
        return ["Heel", "Ball", "Ankle", "Toe", "TipToe"]

    def reparentJoints(self):
        self.jointSystem.joints[-1].setParent(self.jointSystem.joints[self.endJointNumber + 1])

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

        ankleRoll = self.buildRoll("Ankle", self.absEndJointNumber + 1)
        ballRoll = self.RollSystem.getSupportNode("BallRoll")

        # Reparent the heirachy
        self.ankleIKHandle.setParent(ballRoll)
        ankleRoll.setParent(ballRoll)
        self.ikHandle.setParent(ankleRoll)


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
        Paw.alignControl(self)


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
        Paw.alignControl(self)


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
        Paw.alignControl(self)


class BlendIK(LimbIk):
    def __init__(self, *args, **kwargs):
        super(BlendIK, self).__init__(*args, **kwargs)
        # TODO: Need to validate this
        self.ikTypes = kwargs.get("ikSystemType", ["Hip", "Spring"])
        self._subIKA = self._subIKB = None

    def __bindData__(self, *args, **kwgs):
        super(BlendIK, self).__bindData__(*args, **kwgs)
        self.addAttr("subIKs", "")

    def buildIk(self):
        self.ikHandle = _build_ik_(self, SOLVERS["Single"], "IkHandle", self.endJointNumber - 1, self.endJointNumber)
        for label, ikType in zip(self.subIKNames, self.ikTypes):
            ikMetaClass = globals()[ikType]
            kwargs = self.kwargs.copy()
            kwargs['part'] = "{}{}".format(self.part, label)
            kwargs['solver'] = "Spring"
            ikMeta = ikMetaClass(**kwargs)
            ikMeta.endJointNumber = self.endJointNumber
            ikJointSystem = joints.JointSystem(part="{}{}".format(self.part, label), side=self.side)
            ikJointSystem.buildData = self.jointSystem.buildData
            jointData = ikJointSystem.jointData
            for jointInfo in jointData:
                jointInfo["Name"] = "{}{}".format(jointInfo["Name"], label)
            ikJointSystem.jointData = jointData
            self.addMetaSubSystem(ikMeta, label)
            ikJointSystem.build()
            ikMeta.jointSystem = ikJointSystem
            ikMeta.loadIKPlugin()
            ikMeta.buildIk()

    def parseLabels(self):
        labels = []
        for ikType in self.ikTypes:
            capitalChar = list(set(ikType) - set(ikType.capitalize()))
            labels.append(ikType.split(capitalChar[0])[0] if capitalChar else ikType)
        self.subIKs = "_".join(labels)

    def buildControl(self):
        # self.ikHandle = self.subIKA.ikHandle
        super(BlendIK, self).buildControl()
        # self.delAttr("SUP_IKHandle")
        for count, system, sysType in zip(range(len(self.subIKNames)), self.subIKSystems, self.subIKNames):
            self.mainIK.addChild(system.ikHandle.prnt.pynode)
            if system.ikSolver == "ikSpringSolver":
                part = "SpringBias"
                if "Spring" not in sysType:
                    part = "{}{}".format(sysType, part)

                ctrl = self.createCtrlObj(part=part, createXtra=False, addGimbal=False, shape="Circle")
                ctrl.snap(self.mainIK)
                translateValue = 5 * self.scaleFactor * (1 if count else -1)
                ctrl.prnt.pynode.attr("translate{}".format(self.rollAxis)).set(translateValue)
                ctrl.setParent(self.mainIK)
                system.springBiasCtrl = ctrl
            system.mainIK = self.mainIK
            system.buildControl()
            system.delAttr("{}_MainIK".format(self.CTRL_Prefix))
        self.mainIK.setParent(self)

    def cleanUp(self):
        super(BlendIK, self).cleanUp()
        for system in self.subIKSystems:
            system.cleanUp()
            system.setParent(self)

    def build(self):
        self.parseLabels()
        super(BlendIK, self).build()
        self.blendSystems()

    def blendSystems(self):
        self.buildBlendCtrl()
        self.blendJoints()
        self.blendVisibility()

    def blendVisibility(self):
        # Set the visibility set driven key
        blendAttrName = self.blendAttr.name()
        attrValues = [0, .5, 1]
        subSysAVis = [1, 1, 0]
        subSysBVis = [0, 1, 1]

        for attrVis, system in zip([subSysAVis, subSysBVis], self.subIKSystems):
            for ctrl in system.allCtrls:
                ctrlShape = ctrl.pynode.getShape()
                if not (ctrlShape.v.isLocked() or ctrlShape.v.listConnections()):
                    libUtilities.set_driven_key({blendAttrName: attrValues}, {ctrlShape.v.name(): attrVis}, "step")

    def blendJoints(self):
        # for jointA, jointB, joint, count in zip(self.subIKA.jointSystem.pyJoints,
        #                                         self.subIKB.jointSystem.pyJoints,
        #                                         self.jointSystem.joints,
        #                                         range(len(self.jointSystem.joints))):
        jointRange = range(len(self.jointSystem.jointList[0:self.endJointNumber]))
        for count in jointRange:
            jointA = self.subIKA.jointSystem.pyJoints[count]
            jointB = self.subIKB.jointSystem.pyJoints[count]
            joint = self.jointSystem.joints[count]
            pairBlend = core.MetaRig(part=joint.part, side=self.side, endSuffix='PairBlend', nodeType='pairBlend')
            pairPyNode = pairBlend.pynode

            connectAttrs = ['Rotate', 'Translate']

            if count == jointRange[-1]:
                connectAttrs.remove('Rotate')

            for attr in connectAttrs:
                attrLower = attr.lower()
                jointA.attr(attrLower) >> pairPyNode.attr('in{}1'.format(attr))
                jointB.attr(attrLower) >> pairPyNode.attr('in{}2'.format(attr))
                pairPyNode.attr('out{}'.format(attr)) >> joint.pynode.attr(attrLower)

            self.blendAttr >> pairPyNode.weight

    def buildBlendCtrl(self):
        # Build Blendcontrol
        self.blender = self.createCtrlObj("{}Blend".format(self.part), createXtra=False, addGimbal=False, shape="Star")

        self.blender.prntPy.translate.set(self.jointSystem.midPoint)

        transRollAttr = self.blender.prntPy.attr("translate{}".format(self.rollAxis))
        transRollAttr.set(transRollAttr.get() + 5 * self.scaleFactor)

        self.blender.snap(self.jointSystem.joints[self.absEndJointNumber], translate=False)

        # Attribute based on the system type
        libUtilities.addFloatAttr(self.blender.pynode, self.subIKs)
        self.blender.lockDefaultAttributes()

    @property
    def blendAttr(self):
        return self.blender.pynode.attr(self.subIKs)

    @property
    def inverse(self):
        return self.blender.getSupportNode("Reverse")

    @inverse.setter
    def inverse(self, data):
        self.blender.addSupportNode(data, "Reverse")

    @property
    def blender(self):
        return self.getRigCtrl("Blender")

    @blender.setter
    def blender(self, data):
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(data, ctrType="Blender", mirrorData=self.mirrorData)

    def testBuild(self, **kwargs):
        super(BlendIK, self).testBuild(**kwargs)
        self.buildPv()

    def buildPVConstraint(self):

        pvPosition = []
        for system in self.subIKSystems:
            system.pv = self.pv
            if pvPosition:
                system.pvPosition = pvPosition
            system.buildPVConstraint()
            pvPosition = system.pvPosition
            system.delAttr("{}_PV".format(self.CTRL_Prefix))

    def buildPv(self):
        self.buildPvControl()
        self.buildPVConstraint()
        self.finalisePV()

    def _getSubIk(self, subIK):
        if not self.metaCache.setdefault(subIK, None):
            self.metaCache[subIK] = self.getMetaSubSystem(subIK)
        return self.metaCache[subIK]

    @property
    def subIKNames(self):
        return self.subIKs.split("_")

    @property
    def subIKA(self):
        return self._getSubIk(self.subIKNames[0])

    @property
    def subIKB(self):
        return self._getSubIk(self.subIKNames[1])

    @property
    def subIKSystems(self):
        return [self.subIKA, self.subIKB]


class SpringDev(Hip):
    def __init__(self, *args, **kwargs):
        super(SpringDev, self).__init__(*args, **kwargs)
        self.ikSolver = SOLVERS[kwargs.get("solver", "Spring")]
        self.endJointNumber = -1


core.Red9_Meta.registerMClassInheritanceMapping()
core.Red9_Meta.registerMClassNodeMapping(nodeTypes=['ikHandle',
                                                    'distanceBetween',
                                                    'multiplyDivide',
                                                    'clamp',
                                                    'pairBlend'])
if __name__ == '__main__':
    pm.newFile(f=1)
    # mainSystem = parts.Blender(side="C", part="Core")
    # ikSystem = Hip(side="C", part="Core", hipIkSolver='RotatePlane', hipEndJointNumber=2)
    ikSystem = HipPaw(side="C", part="Core")

    # ikSystem = BlendIK(side="C", part="Core", hipIkSolver='RotatePlane', hipEndJointNumber=2)
    # system = "IK"
    # mainSystem.addMetaSubSystem(ikSystem, system)
    # ikSystem.ikControlToWorld = True

    # jointSystem = joints.JointSystem(side="C", part="CoreJoints")
    # testJoints = utils.createTestJoint("BlendIK")
    # jointSystem.joints = libUtilities.stringList(testJoints)
    # jointSystem.convertJointsToMetaJoints()
    jointSystem = None
    ikSystem.testBuild(buildMaster=False, jointSystem=jointSystem)

    # ikSystem.convertSystemToSubSystem(system)
    # ikSystem.buildPv()
    pm.refresh()



    # fkSystem = parts.FK(side="C", part="Core")
    # mainSystem.addMetaSubSystem(fkSystem, "FK")
    # fkJointSystem = ikSystem.jointSystem.replicate(part=mainSystem.part, side=mainSystem.side)
    # fkJointSystem.part = ikSystem.jointSystem.part
    # fkJointSystem.rigType = ikSystem.jointSystem.rigType
    # fkSystem.evaluateLastJoint = False
    # fkSystem.testBuild(jointSystem=fkJointSystem, buildProxy=False, buildMaster=False)
    # fkSystem.convertSystemToSubSystem(fkSystem.systemType)
    # mainSystem.subSystems = "IK_FK"
    # pm.refresh()
    # mainSystem.build()
    # fkSystem = parts.FK(side="C", part="Core")
    # mainSystem.addMetaSubSystem(fkSystem, "FK")
    # core.JointSystem.replicate()
    # fkJointSystem = ikSystem.jointSystem.replicate()
    # fkSystem.testBuild(fkJointSystem)part
    # fkSystem.convertSystemToSubSystem(fkSystem.systemType)

    # ikSystem.convertSystemToSubSystem(ikSystem.systemType)
    # TODO: Double transform node for the mainSystem
    # mainSystem.blender.pynode.attr(mainSystem.subSystems)
