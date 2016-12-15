# Generic, IK, IK/FK, Eye, Hand
from pymel import core as pm

from PKD_Tools import libUtilities
from PKD_Tools.Red9 import Red9_CoreUtils
from PKD_Tools.Rigging import core
from PKD_Tools.Rigging import utils


# if __name__ == '__main__':
#     for module in core, utils, libUtilities:
#         reload(module)

class Rig(core.SubSystem):
    """This is base System. Transform is the main"""

    def __init__(self, *args, **kwargs):
        super(Rig, self).__init__(*args, **kwargs)
        self.isStretchable = False
        self.isCartoony = False
        self.mainCtrlShape = "Box"
        self.rotateOrder = "yzx"
        self.mirrorData = {'side': self.mirrorSide, 'slot': 1}
        self.hasParentMaster = False
        self.hasPivot = False

    def createProxyCube(self, targetJoint, childJoint):
        # Get the height
        height = Red9_CoreUtils.distanceBetween(targetJoint.shortName(), childJoint.shortName())

        # Create the cube of that height
        cube = pm.polyCube(height=height, ch=False)[0]

        cube.translateY.set(height * .5)

        # Freeze Transform
        libUtilities.freeze_transform(cube)

        # reset the pivot to origin
        cube.scalePivot.set([0, 0, 0])
        cube.rotatePivot.set([0, 0, 0])
        # Snap the pivot of the cube to this cluster

        # Snap the cube to joint
        libUtilities.snap(cube, targetJoint)
        libUtilities.skinGeo(cube, [targetJoint])

    def createCtrlObj(self, part, shape="", createXtra=True, addGimbal=True):
        ctrl = core.Ctrl(part=part, side=self.side)
        if not shape:
            shape = self.mainCtrlShape
        ctrl.ctrlShape = shape
        ctrl.createXtra = createXtra
        ctrl.build()
        if addGimbal:
            ctrl.addGimbalMode()
        if self.hasParentMaster:
            ctrl.addParentMaster()
        if self.hasPivot:
            ctrl.addPivot()
        ctrl.setRotateOrder(self.rotateOrder)
        ctrl.setParent(self)
        return ctrl

    def testBuild(self):
        # Build the help joints
        self.jointSystem = core.JointSystem(side=self.side, part="%sJoints" % self.part)
        # Build the joints
        joints = None
        currentClass = self.__class__
        originalClass = self.__class__
        while not joints:
            # Try to build for current class
            try:
                joints = utils.create_test_joint(currentClass.__name__)
            except:
                # look in the parent class
                if currentClass == object:
                    print originalClass.__name__
                    joints = utils.create_test_joint(originalClass.__name__)
                else:
                    currentClass = currentClass.__bases__[0]

        # Setup the joint system
        self.jointSystem.joints = joints
        self.jointSystem.convertJointsToMetaJoints()
        self.jointSystem.setRotateOrder(self.rotateOrder)
        # Build the Part
        self.build()

        # build proxy
        self.buildProxy()

        # Build Master Control
        pm.select(cl=1)
        masterControl = self.createCtrlObj("master", shape="Square", createXtra=False)
        masterControl.prnt.pynode.setParent(world=True)

        self.addConstraint(masterControl.pynode)
        self.addConstraint(masterControl.pynode, "scale")

    def buildProxy(self):
        # Build the proxy cube
        for i in range(len(self.jointSystem.joints) - 1):
            self.createProxyCube(self.jointSystem.joints[i].pynode, self.jointSystem.joints[i + 1].pynode)

    def cleanUp(self):
        pass

    def build(self):
        pass

    def addStretch(self):
        for position, ctrl in enumerate(self.MainCtrls):
            if position:
                # Get the driver joint
                driveJoint = self.offsetJointSystem.joints[position - 1]
                # Parent Constraint the ctrl to the previous joint
                ctrl.addConstraint(driveJoint.pynode, maintainOffset=True)
            # Connect the scale lenght
            scaleAxis = "s%s" % self.primaryAxis[0]
            # Connect the stretch axis
            ctrl.pynode.attr(scaleAxis) >> self.jointSystem.joints[position].pynode.attr(scaleAxis)

    def buildSquashStretch(self):
        if self.isDeformable:
            self.addStretch()
            if self.isCartoony:
                self.add_squash()

    @property
    def jointSystem(self):
        return self.getSupportNode("JointSystem")

    @jointSystem.setter
    def jointSystem(self, data):
        self.addSupportNode(data, "JointSystem")

    @property
    def ctrlGrp(self):
        return self.getSupportNode("CtrlGrp")

    @ctrlGrp.setter
    def ctrlGrp(self, data):
        self.addSupportNode(data, "CtrlGrp")

    @property
    def isDeformable(self):
        return self.isCartoony or self.isStretchable


class Ik(Rig):
    def __init__(self, *args, **kwargs):
        super(Ik, self).__init__(*args, **kwargs)
        self.ikControlToWorld = False

    @property
    def ikHandle(self):
        return self.getSupportNode("IKHandle")

    @ikHandle.setter
    def ikHandle(self, data):
        self.addSupportNode(data, "IKHandle")


class Generic(Rig):
    def __init__(self, *args, **kwargs):
        super(Generic, self).__init__(*args, **kwargs)
        self.mainCtrlShape = "Circle"
        self.lockTranslation = False
        self.lockRotation = False
        self.jointDriverSystem = None

    # A basic Type system
    def buildControl(self):
        # Setup the mainCtrl
        ctrls = []
        # Iterate through all the joints
        for position, joint in enumerate(self.jointSystem.joints):
            # Create and snap the control
            ctrlMeta = self.createCtrlObj(joint.part, self.mainCtrlShape)
            ctrlMeta.snap(joint.pynode)
            ctrls.append(ctrlMeta)
            if position and not self.isDeformable:
                ctrlMeta.setParent(ctrls[position - 1].parentDriver)

        # Add it to the main control
        self.mainCtrls = ctrls

    def connectControl(self):
        for position, ctrl in enumerate(self.mainCtrls):
            # Constraint the joint by the parent joint1
            self.jointSystem.joints[position].addConstraint(ctrl.parentDriver.pynode)
            # If it is deformable control then add a contraint to the parent
            if self.isDeformable and position:
                ctrl.prnt.addConstraint(self.offsetJointSystem.joints[position - 1].pynode)

    def buildOffsetJoint(self):
        # Build the help joint system
        self.offsetJointSystem = self.jointSystem.replicate(side=self.side,
                                                            part="%sOffsetJoints" % self.part,
                                                            endPosition=-1,
                                                            supportType="Offset")

        # snap each offset joint to the same position as the next joint
        for i in range(len(self.offsetJointSystem)):
            # Alias the current node
            currentJoint = self.offsetJointSystem.joints[i]
            # Alias the child joint
            childJoint = self.jointSystem.joints[i + 1]
            # Snap to the next joint
            currentJoint.snap(self.jointSystem.joints[i + 1].mNode, rotate=False)
            # Parent the next joint to the this joint
            childJoint.setParent(currentJoint)
            # Parent the offjoint to current joint
            currentJoint.setParent(self.jointSystem.joints[i])

    def cleanUp(self):
        # Setup the parent of tjoint
        if not self.jointSystem.joints[0].pynode.getParent():
            self.jointSystem.setParent(self)

        # parent the main ctrols
        if self.mainCtrls and self.isDeformable:
            self.ctrlGrp = core.MovableSystem(side=self.side, part=self.part, endSuffix="MainCtrlGrp")
            self.ctrlGrp.rotateOrder = self.rotateOrder
            self.ctrlGrp.setParent(self)
            for ctrl in self.mainCtrls:
                ctrl.setParent(self.ctrlGrp)

    def build(self):
        self.buildControl()
        if self.isDeformable:
            self.buildOffsetJoint()
        self.connectControl()
        self.buildSquashStretch()
        self.cleanUp()

    @property
    def mainCtrls(self):
        return self.getChildren(asMeta=self.returnNodesAsMeta, walk=True, cAttrs=["SUP_MainCtrls"])

    @mainCtrls.setter
    def mainCtrls(self, ctrlList):
        if not ctrlList:
            raise RuntimeError("Please input a list of meta Ctrls")
        self.connectChildren(ctrlList, "MainCtrls", allowIncest=True, cleanCurrent=True)

    @property
    def offsetJointSystem(self):
        return self.getSupportNode("OffsetJointSystem")

    @offsetJointSystem.setter
    def offsetJointSystem(self, data):
        self.addSupportNode(data, "OffsetJointSystem")


class FK(Generic):
    # A system where the translation are locked. Elbow axis can be locked locked
    pass


class Hand(FK):
    # Where the hand is free
    pass


class Quad(FK):
    # Class where all the rotation from the solver to the locked
    pass


class Blender(Rig):
    # Class which blends two system
    pass


if __name__ == '__main__':
    pm.newFile(f=1)
    mainSystem = core.SubSystem(side="C", part="Core")
    fkSystem = Generic(side="C", part="Core")
    fkSystem.isStretchable = True
    mainSystem.addMetaSubSystem(fkSystem, "FK")
    # ikSystem.ikControlToWorld = Tru
    fkSystem.testBuild()
    fkSystem.convertSystemToSubSystem(fkSystem.systemType)
    # TODO: Double transform node for the mainSystem
    cartoonySystem = core.CartoonySystem(side="C", part=fkSystem.mainCtrls[0].part)
    cartoonySystem.build()
    mainSystem.addMetaSubSystem(cartoonySystem, "Cartoony")
    axis = fkSystem.mainCtrls[0].primaryAxis.upper()
    fkSystem.mainCtrls[0].addBoolAttr("disable")
    fkSystem.mainCtrls[0].addFloatAttr("elasticity", 50, -50)

    cartoonySystem.convertSystemToSubSystem("Toon")
    cartoonySystem.connectDisable(fkSystem.mainCtrls[0].pynode.disable)
    cartoonySystem.connectElasticity(fkSystem.mainCtrls[0].pynode.elasticity)
    cartoonySystem.connectTrigger(fkSystem.mainCtrls[0].pynode.attr("scale%s" % axis[0]))
    cartoonySystem.connectOutput(fkSystem.jointSystem.joints[0].pynode.attr("scale%s" % axis[1]))
    cartoonySystem.connectOutput(fkSystem.jointSystem.joints[0].pynode.attr("scale%s" % axis[2]))

    fkSystem.mainCtrls[0].pynode.attr("scale%s" % axis[0]) >> fkSystem.jointSystem.joints[0].pynode.attr(
        "scale%s" % axis[0])
    print "Done"
