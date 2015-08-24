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
    # TODO Add a meta IKHandle with parent as one of the properties
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
    ikHandleMeta.addParent(handleSuffix + "Prnt",snap=False)
    # prnt = core.MetaRig(side=metaClass.side, part=metaClass.part, endSuffix=handleSuffix + "Prnt")
    # ikHandleMeta.setParent(prnt)
    # ikHandleMeta.prnt = prnt
    #ikHandleMeta.addSupportNode(prnt, "Prnt")
    # Set the pivot to the endJoint
    libUtilities.snap_pivot(ikHandleMeta.prnt.mNode, endJoint)

    return ikHandleMeta


class ik(rig):
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

    # @property
    # def ikHandlePrnt(self):
    #     return self.ikHandle.getSupportNode("prnt")
    #
    # @ikHandlePrnt.setter
    # def ikHandlePrnt(self, data):
    #     self.ikHandle.addSupportNode(data, "prnt")

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


class fk(rig):
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

        # Aim Constraint at mainIk Handle
        pm.aimConstraint(self.ikHandle.pynode, self.aimHelper.pynode, mo=1, wut="object", wuo=upVector.mNode)
        # Orient Constraint the Hip Constraint
        hipCtrl.orientConstraint(self.aimHelper.pynode)
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


class armHoof(arm):
    """This is the IK hoof System."""
    # TODO Do the hoop
    # TODO Combine TipToe and Heel with Tip_Heel Divider name are called Roll

    def align_control(self):
        super(armHoof, self).align_control()
        # Remove the x roatation
        if not self.ikControlToWorld:
            self.mainIK.prnt.pynode.attr("r%s" % self.primaryAxis[2]).set(0)

    def build_control(self):
        self.hasPivot = True
        super(armHoof, self).build_control()
        self.RollSystem = core.Network(part=self.part + "Roll", side=self.side)
        # Create the 2 rotate system

        toeRoll = core.MetaRig(part=self.part, side=self.side, endSuffix="ToeRoll")
        toeRoll.addParent("ToeRollPrnt")
        libUtilities.snap(toeRoll.prnt.mNode, self.JointSystem.Joints[-1].mNode)
        # self.toeRoll.setParent(self.JointSystem.Joints[-1])
        heelRoll = core.MetaRig(part=self.part, side=self.side, endSuffix="HeelRoll")
        heelRoll.addParent("HeelRollPrnt")
        libUtilities.snap(heelRoll.prnt.mNode, self.JointSystem.Joints[-2].mNode)
        heelRoll.setParent(toeRoll)

        # Connect to the Roll System
        self.RollSystem.addSupportNode(toeRoll, "toeRoll")
        self.RollSystem.addSupportNode(heelRoll, "heelRoll")
        # Add atttr called "Roll"
        libUtilities.addDivAttr(self.mainIK.pynode, "Roll", "rollDiv")
        # Tip_Heel
        libUtilities.addAttr(self.mainIK.pynode, "Toe_Heel", 270, -270)
        # Create a negative multiply divide for the toe
        toeMd = libUtilities.inverseMultiplyDivide(utils.nameMe(self.side,
                                                             self.part + "ToeInverse",
                                                             "MD"))
        toeMdMeta = core.MetaRig(toeMd.name(), nodeType="multiplyDivide")
        self.mainIK.pynode.Toe_Heel >> toeMd.input1X
        self.RollSystem.addSupportNode(toeMdMeta, "toeInverseMD")

        # Create a negative multiply divide for the heel
        heelMd = libUtilities.inverseMultiplyDivide(utils.nameMe(self.side,
                                                             self.part + "HeelInverse",
                                                             "MD"))
        heelMdMeta = core.MetaRig(heelMd.name(), nodeType="multiplyDivide")


        self.RollSystem.addSupportNode(heelMdMeta, "toeInverseMD")


        # Create 2 clamp nodes one for pos and one for negative
        clamp = pm.createNode("clamp",
                              name=utils.nameMe(self.side,
                                                self.part + "ToeHeel",
                                                "Clamp"))

        clampMeta = core.MetaRig(clamp.name(), nodeType="clamp")
        self.RollSystem.addSupportNode(clampMeta, "clamp")

        clamp.maxR.set(270)
        clamp.maxG.set(270)
        # Connect to clamp
        self.mainIK.pynode.Toe_Heel>> clamp.inputR
        toeMd.outputX >> clamp.inputG

        # Connect to the Rolls
        clamp.outputR >> heelMd.input1X
        heelMd.outputX >> heelRoll.pynode.attr("r%s"%self.primaryAxis[2])

        clamp.outputG >> toeRoll.pynode.attr("r%s"%self.primaryAxis[2])

        # Reparent the IK Handles
        self.ikHandle.setParent(heelRoll)
        self.ballIKHandle.setParent(heelRoll)

        # Reparent the Syste
        self.mainIK.hasGimbal = True
        self.mainIK.addChild(toeRoll.prnt.mNode)

    def build_ik(self):
        super(armHoof, self).build_ik()
        # Reparent the toe
        self.JointSystem.Joints[-1].pynode.setParent(self.JointSystem.Joints[-3].pynode)
        self.ballIKHandle = _build_ik_(self, SOLVERS["Single"], "PalmIKHandle", self.endJointNumber,
                                       self.endJointNumber + 1)

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


class foot(arm):
    """This is the classic IK foot System."""
    pass


class paw(arm):
    """This is the IK hoof System."""
    pass


class ikSpline(rig):
    """This is a Spline IK System"""
    pass


core.Red9_Meta.registerMClassInheritanceMapping()
core.Red9_Meta.registerMClassNodeMapping(nodeTypes=['ikHandle', 'multiplyDivide', "clamp"])

if __name__ == '__main__':
    pm.newFile(f=1)

    # subSystem = SubSystem(side="U", part="Core")
    # print "s"

    # print ikSystem

    mainSystem = core.SubSystem(side="U", part="Core")

    ikSystem = mainSystem.addMetaSubSystem(armHoof, "IK")
    # ikSystem.ikControlToWorld = True
    ikSystem.test_build()
    ikSystem.convertToComponent("IK")
