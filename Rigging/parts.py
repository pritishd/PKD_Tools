"""
@package PKD_Tools.Rigging.parts
@brief Basic parts API eg Generic, IK, IK/FK, Eye, Hand
"""

#
from pymel import core as pm

from PKD_Tools import libUtilities
from PKD_Tools.Red9 import Red9_CoreUtils
from PKD_Tools.Rigging import utils
from PKD_Tools.Rigging import core

if __name__ == '__main__':
    for mod in libUtilities, utils, core:
        reload(mod)


class Rig(core.TransSubSystem):
    """This is a basic rig system. In order to build a rig component you must provide a valid JointSystem. Once a valid
    joint system is provided it will know what to do with that, eg if you provide a three joints to @ref limb.Arm it
    would generate a basic 2 bone IK system

    You must also specify the rotate order
    """

    def __init__(self, *args, **kwargs):
        super(Rig, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.isStretchable = kwargs.get("stretch", False)
            self.isCartoony = kwargs.get("cartoony", False)
            self.mainCtrlShape = kwargs.get("mainCtrlShape", "Box")
            self.rotateOrder = kwargs.get("rotateOrder", "yzx")
            self.mirrorData = {'side': self.mirrorSide, 'slot': 1}
            self.hasParentMaster = kwargs.get("parentMaster", False)
            self.hasPivot = kwargs.get("pivot", False)
            self._evaluateLastJoint = True

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

    def createCtrlObj(self, part, **kwargs):
        shape = kwargs.get("shape")
        createXtra = kwargs.get("createXtra", True)
        addGimbal = kwargs.get("addGimbal", True)
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

    def testBuild(self, **kwargs):

        jointSystem = kwargs.get("jointSystem")
        buildProxy = kwargs.get("buildProxy", True)
        buildMaster = kwargs.get("buildMaster", True)

        if not jointSystem:
            # Build the help joints
            jointSystem = core.JointSystem(side=self.side, part="%sJoints" % self.part)
            self.jointSystem = jointSystem
            pm.refresh()

            # Build the joints
            joints = None
            currentClass = self.__class__
            originalClass = self.__class__
            while not joints:
                # Try to build for current class
                try:
                    joints = utils.createTestJoint(currentClass.__name__)
                except:
                    # look in the parent class
                    if currentClass == object:
                        print originalClass.__name__
                        joints = utils.createTestJoint(originalClass.__name__)
                    else:
                        currentClass = currentClass.__bases__[0]

            # Setup the joint system
            self.jointSystem.joints = libUtilities.stringList(joints)
            self.jointSystem.convertJointsToMetaJoints()
            self.jointSystem.setRotateOrder(self.rotateOrder)
        else:
            self.jointSystem = jointSystem
            # Build the Part
        self.build()

        if buildProxy:
            # build proxy
            self.buildProxy()

        if buildMaster:
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
        if not self.jointSystem.joints[0].pynode.getParent():
            # Setup the parent of joint
            self.jointSystem.joints[0].pynode.setParent(self.pynode)

    def build(self):
        pass

    def addStretch(self):
        for position, ctrl in enumerate(self.mainCtrls):
            if position:
                # Get the driver joint
                driveJoint = self.offsetJointSystem.joints[position - 1]
                # Parent Constraint the ctrl to the previous joint
                ctrl.addConstraint(driveJoint.pynode, maintainOffset=True)
            # Connect the scale lenght
            scaleAxis = "s{0}".format(self.primaryAxis[0])
            # Connect the stretch axis
            ctrl.pynode.attr(scaleAxis) >> self.jointSystem.joints[position].pynode.attr(scaleAxis)

    def addSquash(self):
        # Add a network
        mainCartoonySystem = core.NetSubSystem(side=self.side, part="Cartoony")
        self.addMetaSubSystem(mainCartoonySystem, "Cartoony")

        axis = self.mainCtrls[0].primaryAxis.upper()
        for i in range(len(self.jointSystem) - int(bool(self.evaluateLastJoint))):
            cartoonySystem = core.CartoonySystem(side=self.side, part="{0}Toon".format(self.mainCtrls[i].part))
            mainCartoonySystem.addMetaSubSystem(cartoonySystem, "Cartoony{0}".format(self.mainCtrls[i].part))
            cartoonySystem.build()
            self.mainCtrls[i].addBoolAttr("disable")
            self.mainCtrls[i].addFloatAttr("elasticity", 50, -50)
            cartoonySystem.connectDisable(self.mainCtrls[i].pynode.disable)
            cartoonySystem.connectElasticity(self.mainCtrls[i].pynode.elasticity)
            cartoonySystem.connectTrigger(self.mainCtrls[i].pynode.attr("scale%s" % axis[0]))
            cartoonySystem.connectOutput(self.jointSystem.joints[i].pynode.attr("scale%s" % axis[1]))
            cartoonySystem.connectOutput(self.jointSystem.joints[i].pynode.attr("scale%s" % axis[2]))

        if self.systemType:
            mainCartoonySystem.convertSystemToSubSystem(self.systemType)

    def buildSquashStretch(self):
        # TODO: Ensure the rig is built already
        if self.isDeformable:
            self.addStretch()
            if self.isCartoony:
                self.addSquash()

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

    @property
    def evaluateLastJoint(self):
        if not self._evaluateLastJoint:
            return -1

    @evaluateLastJoint.setter
    def evaluateLastJoint(self, boolData):
        if not isinstance(boolData, bool):
            raise TypeError("Value must be a boolean")
        else:
            self._evaluateLastJoint = boolData

    @property
    def mainCtrls(self):
        return self.getChildren(asMeta=self.returnNodesAsMeta)

    @mainCtrls.setter
    def mainCtrls(self, ctrlList):
        raise RuntimeError("Cannot be set at this {0} object level".format(self.__class__.__name__))


class Ik(Rig):
    def __init__(self, *args, **kwargs):
        super(Ik, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.ikControlToWorld = kwargs.get("ikControlToWorld", False)

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
        for position, joint in enumerate(self.jointSystem.joints[0:self.evaluateLastJoint]):
            # Create and snap the control
            ctrlMeta = self.createCtrlObj(joint.part)
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
                                                            part=self.part,
                                                            endPosition=-1 - int(bool(self.evaluateLastJoint)),
                                                            supportType="OffsetJoints")

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
        super(Generic, self).cleanUp()

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
        self.cleanUp()

    @property
    def mainCtrls(self):
        return self.getChildren(asMeta=self.returnNodesAsMeta, walk=True, cAttrs=["MainCtrls"])

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


class Fk(Generic):
    def __init__(self, *args, **kwargs):
        super(Fk, self).__init__(*args, **kwargs)
        self.lockCtrlPositions = [-(self.elbowPosition + int(self.evaluateLastJoint is None))]

    def build(self):
        # A system where the translation and scale are locked. Elbow axis can be locked
        super(Fk, self).build()
        if self.mainCtrls:

            if self.debugMode:
                print libUtilities.print_attention()
                print "Elbow position is: {0}".format(self.elbowPosition)
                print libUtilities.print_attention()

            for i in range(len(self.mainCtrls)):
                libUtilities.lock_translate(self.mainCtrls[i].pynode)
                libUtilities.lock_scale(self.mainCtrls[i].pynode)

            # Lock the elbow
            for position in self.lockCtrlPositions:
                for attr in self.primaryAxis[:-1]:
                    attrName = "rotate{0}".format(attr.upper())
                    self.mainCtrls[position].pynode.attr(attrName).set(lock=True, keyable=False, channelBox=False)
        else:
            raise RuntimeError("Main controls are empty")

    @property
    def elbowPosition(self):
        return 2


class Quad(Fk):
    # Class where all the rotation from the solver to the locked
    @property
    def elbowPosition(self):
        return 3


class Foot(Fk):
    def _init_(self, *args, **kwargs):
        super(Foot, self)._init_(*args, **kwargs)
        self.lockCtrlPositions.append(-2)


class QuadFoot(Quad):
    def _init_(self, *args, **kwargs):
        super(Fk, self)._init_(*args, **kwargs)
        self.lockCtrlPositions.append(-2)


class Blender(Rig):
    # Class which blends two system
    def __init__(self, *args, **kwargs):
        super(Blender, self).__init__(*args, **kwargs)
        self.mainCtrlShape = "Square"
        self.addAttr("subSystems", "")
        self._subSystemA = None
        self._subSystemB = None
        self._blendAttr = None

    # noinspection PyStatementEffect
    def buildBlendCtrl(self):
        # Build Blendcontrol
        self.blender = self.createCtrlObj(self.part, createXtra=False, addGimbal=False)

        # Create reverse node
        self.inverse = core.MetaRig(side=self.side, part=self.part, endSuffix="Inverse", nodeType="reverse")
        libUtilities.lock_default_attribute(self.blender.pynode)

        # Attribute based on the system type
        libUtilities.addFloatAttr(self.blender.pynode, self.subSystems)

        # Connect the inverse node
        self.blendAttr >> self.inverse.pynode.inputX

        # Add the constraint blend type attr
        libUtilities.addDivAttr(self.blender.pynode, "Interpolation", "interpType")
        self.blender.addAttr("type", attrType='enum', enumName="Average:Shortest:Longest:")

        interpADL = core.MetaRig(side=self.side, part=self.part, endSuffix="InterpADL", nodeType="addDoubleLinear")

        interpADL.pynode.input2.set(1)
        self.blender.pynode.attr("type") >> interpADL.pynode.input1

        self.blender.addSupportNode(interpADL, "InterpADL")
        # mm.eval('setAttr -lock true "%s.Interp"' % ctrl)
        # mm.eval('addAttr -ln "Type"  -at "enum" -en "Average:Shortest:Longest:"  %s;' % ctrl)
        # mm.eval('setAttr -e-keyable true %s.Type;' % ctrl)
        # addNode = mc.createNode("addDoubleLinear", n=ctrl.replace("Ctrl", "add"))
        # mc.setAttr(addNode + ".input2", 1)
        # mc.connectAttr(ctrl + ".Type", addNode + ".input1")
        # for con in const: mc.connectAttr(addNode + ".output", con + ".interpType")

    def blendJoints(self):
        # Replicate the joint based off A
        self.jointSystem = self.subSystemA.jointSystem.replicate(part=self.part, side=self.side, endSuffix=self.rigType)

        # Constraints System
        for i in range(len(self.jointSystem) - 1):
            # Joint Aliases
            joint = self.jointSystem.joints[i]
            jointA = self.subSystemA.jointSystem.joints[i]
            jointB = self.subSystemB.jointSystem.joints[i]

            # Hide the SubJoints
            jointA.v = 0
            jointB.v = 0

            # Constraints the nodes
            joint.addConstraint(jointA)
            joint.addConstraint(jointB)

            # Reverse node in first
            self.inverse.pynode.outputX >> joint.parentConstraint.pynode.w0

            # Connect the interpType
            self.interpAttr >> joint.parentConstraint.pynode.interpType

            # Direct connection in second
            self.blendAttr >> joint.parentConstraint.pynode.w1
            if self.subSystemA.isDeformable:
                joint.addConstraint(jointA, conType="scale")
                joint.addConstraint(jointB, conType="scale")
                self.inverse.pynode.outputX >> joint.scaleConstraint.pynode.w0
                self.blendAttr >> joint.scaleConstraint.pynode.w1

    def blendVisibility(self):
        pass

    def build(self):
        self.buildBlendCtrl()
        self.blendJoints()
        self.blendVisibility()

        # Set the visibility set driven key
        blendAttrName = self.blendAttr.name()
        attrValues = [0, .5, 1]
        subSysAVis = [1, 1, 0]
        subSysBVis = [0, 1, 1]
        for ctrl in self.subSystemA.mainCtrls:
            ctrlShapeName = ctrl.pynode.getShape().v.name()
            libUtilities.set_driven_key({blendAttrName: attrValues}, {ctrlShapeName: subSysAVis}, "step")

        for ctrl in self.subSystemB.mainCtrls:
            ctrlShapeName = ctrl.pynode.getShape().v.name()
            libUtilities.set_driven_key({blendAttrName: attrValues}, {ctrlShapeName: subSysBVis}, "step")

    @property
    def blendAttr(self):
        if not self._blendAttr:
            self._blendAttr = self.blender.pynode.attr(self.subSystems)
        return self._blendAttr

    @property
    def subSystemA(self):
        if not self._subSystemA:
            subSystemA = self.subSystems.split("_")[0]
            self._subSystemA = self.getMetaSubSystem(subSystemA)
        return self._subSystemA

    @property
    def subSystemB(self):
        if not self._subSystemB:
            subSystemB = self.subSystems.split("_")[1]
            self._subSystemB = self.getMetaSubSystem(subSystemB)
        return self._subSystemB

    @property
    def blender(self):
        return self.getRigCtrl("Blender")

    @blender.setter
    def blender(self, data):
        # TODO: Pass the slot number before and axis data
        self.addRigCtrl(data, ctrType="Blender", mirrorData=self.mirrorData)

    @property
    def inverse(self):
        return self.blender.getSupportNode("Reverse")

    @inverse.setter
    def inverse(self, data):
        self.blender.addSupportNode(data, "Reverse")

    @property
    def interpAttr(self):
        return self.blender.getSupportNode("InterpADL").pynode.output

    def testBuild(self, **kwargs):
        pass


if __name__ == '__main__':
    pm.newFile(f=1)
    mainSystem = Blender(side="C", part="Core")
    mainSystem.subSystems = "FK_IK"
    fkSystem = Fk(side="C", part="Core")
    fkSystem.isCartoony = True
    # mainSystem.addMetaSubSystem(fkSystem, "FK")
    # ikSystem.ikControlToWorld = Tru
    fkSystem.evaluateLastJoint = True
    fkSystem.testBuild()
    fkSystem.convertSystemToSubSystem("FK")
    # fkSystem.buildSquashStretch()
    print "Done"
