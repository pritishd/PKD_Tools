"""
@package PKD_Tools.Rigging.parts
@brief Basic parts API eg Generic, IK, IK/FK, Eye, Hand
"""

#
from pymel import core as pm

from PKD_Tools import libUtilities, libJoint
from PKD_Tools.Rigging import core, joints, utils


class ProxyCube(core.MetaShape):
    """A proxy cube system, which allows you to manipulate shape. This maintains the skinning data whenenever the
    shape is changed."""
    joint = None

    def clusterShape(self, shapeCentric=True):
        self.joint = pm.skinCluster(self.pynode, inf=True, query=True)
        libUtilities.detach_skin(self.pynode)
        return super(ProxyCube, self).clusterShape(shapeCentric)

    def cleanShapeHistory(self, transform=None):
        super(ProxyCube, self).cleanShapeHistory(transform)
        libUtilities.skinGeo(self.pynode, self.joint)



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
            self.rotateOrder = kwargs.get("rotateOrder", libJoint.get_rotate_order(libJoint.default_gimbal_data()))
            self.mirrorData = {'side': self.mirrorSide, 'slot': 1}
            self.hasParentMaster = kwargs.get("parentMaster", False)
            self.hasPivot = kwargs.get("pivot", False)
            self._evaluateLastJoint = kwargs.get("evaluateLastJoint", True)
            self.flipProxyCube = kwargs.get("flipProxyCube", False)

    def createProxyCube(self, targetJoint, count):
        # Create the cube of that height
        try:
            height = self.jointSystem.lengths[count]
        except IndexError:
            height = self.jointSystem.lengths[count - 1]

        cube = pm.polyCube(height=height, ch=False)[0]

        cubeMeta = ProxyCube(part=targetJoint.part.get(), side=self.side, endSuffix="Geo")
        cubeMeta.transferShape(cube)
        cube = cubeMeta.pynode
        cube.translateY.set(height * .5)

        # Freeze Transform
        libUtilities.freeze_transform(cube)

        # reset the pivot to origin
        cube.scalePivot.set([0, 0, 0])
        cube.rotatePivot.set([0, 0, 0])

        if self.flipProxyCube:
            cube.attr(self.bendAxis).set(180)
            libUtilities.freeze_rotation(cube)

        cube.rotateOrder.set(self.rotateOrder)
        # Snap the pivot of the cube to this cluster

        # Snap the cube to joint
        libUtilities.snap(cube, targetJoint)
        libUtilities.skinGeo(cube, [targetJoint])

        return cubeMeta

    def createCtrlObj(self, part, **kwargs):
        shape = kwargs.get("shape", self.mainCtrlShape)
        createXtra = kwargs.get("createXtra", True)
        addGimbal = kwargs.get("addGimbal", True)
        ctrl = core.Ctrl(part=part, side=self.side, createXtra=createXtra, shape=shape)
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
            jointSystem = joints.JointSystem(side=self.side, part="%sJoints" % self.part)
            self.jointSystem = jointSystem
            pm.refresh()

            # Build the joints
            testJoints = None
            currentClass = self.__class__
            originalClass = self.__class__
            while not testJoints:
                # Try to build for current class
                try:
                    testJoints = utils.createTestJoint(currentClass.__name__)
                except:
                    # look in the parent class
                    if currentClass == object:
                        print originalClass.__name__
                        testJoints = utils.createTestJoint(originalClass.__name__)
                    else:
                        currentClass = currentClass.__bases__[0]

            # Setup the joint system
            self.jointSystem.joints = libUtilities.stringList(testJoints)
            self.jointSystem.convertJointsToMetaJoints()
            self.jointSystem.setRotateOrder(self.rotateOrder)
        else:
            self.jointSystem = jointSystem
            # Build the Part
        self.rotateOrder = self.jointSystem.rotateOrder
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
        proxyGrp = core.NoInheritsTransform(side=self.side, part=self.part, endSuffix="ProxyGrp")
        proxyGrp.setParent(self)
        cubeMetaList = []
        for count, joint in enumerate(self.jointSystem.pyJoints):
            cubeMeta = self.createProxyCube(joint, count)
            cubeMeta.setParent(proxyGrp)
            cubeMetaList.append(cubeMeta)

        self.metaCache["ProxyGeo"] = cubeMetaList

    def cleanUp(self):
        if not self.jointSystem.joints[0].pynode.getParent():
            # Setup the parent of joint
            self.jointSystem.joints[0].setParent(self)

    def build(self):
        self.rotateOrder = self.jointSystem.rotateOrder

    def addStretch(self):
        for position, ctrl in enumerate(self.mainCtrls):
            if position:
                # Get the driver joint
                driveJoint = self.offsetJointSystem.joints[position - 1]
                # Parent Constraint the ctrl to the previous joint
                ctrl.addConstraint(driveJoint.pynode, maintainOffset=True)
            # Connect the scale lenght
            scaleAxis = "scale{0}".format(self.twistAxis)
            # Connect the stretch axis
            self.jointSystem.joints[position].pynode.attr(scaleAxis)

            ctrl.pynode.attr(scaleAxis) >> self.jointSystem.joints[position].pynode.attr(scaleAxis)

    def addSquash(self):
        # Add a network
        mainCartoonySystem = core.NetSubSystem(side=self.side, part="Cartoony")
        self.addMetaSubSystem(mainCartoonySystem, "Cartoony")

        bend = self.bendAxis.upper()
        roll = self.rollAxis.upper()
        twist = self.twistAxis.upper()
        for i in range(len(self.jointSystem) - int(bool(self.evaluateLastJoint))):
            cartoonySystem = core.CartoonySystem(side=self.side, part="{0}Toon".format(self.mainCtrls[i].part))
            mainCartoonySystem.addMetaSubSystem(cartoonySystem, "Cartoony{0}".format(self.mainCtrls[i].part))
            cartoonySystem.build()
            self.mainCtrls[i].addBoolAttr("disable")
            self.mainCtrls[i].addFloatAttr("elasticity", 50, -50)
            cartoonySystem.connectDisable(self.mainCtrls[i].pynode.disable)
            cartoonySystem.connectElasticity(self.mainCtrls[i].pynode.elasticity)
            cartoonySystem.connectTrigger(self.mainCtrls[i].pynode.attr("scale%s" % twist))
            cartoonySystem.connectOutput(self.jointSystem.joints[i].pynode.attr("scale%s" % roll))
            cartoonySystem.connectOutput(self.jointSystem.joints[i].pynode.attr("scale%s" % bend))

        if self.systemType:
            mainCartoonySystem.convertSystemToSubSystem(self.systemType)

    def buildSquashStretch(self):
        # TODO: Ensure the rig is built already
        if self.isDeformable:
            self.addStretch()
            if self.isCartoony:
                self.addSquash()

    def buildSkinJoints(self):
        # Build the skin system
        self.skinJointSystem = self.jointSystem.replicate(side=self.side,
                                                          part="{}SkinJoints".format(self.part),
                                                          supportType="Skin")

        # Connect joints
        for skinJoint, finalJoint in zip(self.skinJointSystem.joints, self.jointSystem.joints):
            skinJoint.addConstraint(finalJoint, zeroOut=False, mo=True)
            if self.isDeformable:
                for attr in ["sx", "sz", "sz"]:
                    skinScaleAttr = skinJoint.pynode.attr(attr)
                    finalScaleAttr = finalJoint.pynode.attr(attr)

                    if finalScaleAttr.listConnections():
                        finalScaleAttr >> skinScaleAttr

    @property
    def jointDict(self):
        return self.jointSystem.jointDict

    @property
    def jointSystem(self):
        return self.getSupportNode("JointSystem")

    @jointSystem.setter
    def jointSystem(self, data):
        self.addSupportNode(data, "JointSystem")

    @property
    def skinJointSystem(self):
        return self.getSupportNode("SkinJointSystem")

    @skinJointSystem.setter
    def skinJointSystem(self, data):
        self.addSupportNode(data, "SkinJointSystem")

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
    def evaluateLastJointBool(self):
        return self._evaluateLastJoint

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
        key = "mainCtrls"
        if not self.metaCache.setdefault(key, None):
            self.metaCache[key] = self.getChildren(asMeta=self.returnNodesAsMeta)
        return self.metaCache[key]

    @mainCtrls.setter
    def mainCtrls(self, ctrlList):
        raise RuntimeError("Cannot be set at this {0} object level".format(self.__class__.__name__))

    @property
    def allCtrls(self):
        return self.mainCtrls

    @property
    def twistAxis(self):
        return self.jointSystem.gimbalData["twist"].upper()

    @property
    def rollAxis(self):
        return self.jointSystem.gimbalData["roll"].upper()

    @property
    def bendAxis(self):
        return self.jointSystem.gimbalData["bend"].upper()

    @property
    def parenterJointSystem(self):
        return self.jointSystem


class Ik(Rig):
    def __init__(self, *args, **kwargs):
        super(Ik, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.ikControlToWorld = kwargs.get("ikControlToWorld", False)
        self.mirrorBehaviour = kwargs.get("mirrorBehaviour", False)

    def addStretch(self):
        """TODO: Add stretch"""
        stretchSystem = core.StretchSystem(side=self.side, part="Stretch")
        stretchSystem.build()
        self.addMetaSubSystem(stretchSystem, "Stretch")

    @property
    def ikHandle(self):
        return self.getSupportNode("IKHandle")

    @ikHandle.setter
    def ikHandle(self, data):
        self.addSupportNode(data, "IKHandle")

    @property
    def stretchSystem(self):
        return self.getMetaSubSystem("Stretch")

    @property
    def upVector(self):
        return [int(self.rollAxis == "x"),
                int(self.rollAxis == "y"),
                int(self.rollAxis == "z")]


class Generic(Rig):
    def __init__(self, *args, **kwargs):
        super(Generic, self).__init__(*args, **kwargs)
        self.mainCtrlShape = "Circle"
        self.lockTranslation = False
        self.lockRotation = False
        self.lockScale = False
        self.jointDriverSystem = None

    # A basic Type system
    def buildControl(self):
        # Setup the mainCtrl
        ctrls = []
        # Iterate through all the joints
        for position, joint in enumerate(self.jointSystem.joints[0:self.evaluateLastJoint]):
            # Create and snap the control
            ctrlMeta = self.createCtrlObj(joint.part)
            if self.lockTranslation:
                ctrlMeta.lockTranslate()
            if self.lockRotation:
                ctrlMeta.lockRotate()
            if self.lockScale:
                ctrlMeta.lockScale()
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
                                                            startPosition=1,
                                                            endPosition=self.evaluateLastJoint,
                                                            supportType="Offset")

        offsetJointPrntSystem = self.jointSystem.replicate(side=self.side,
                                                            part=self.part,
                                                            startPosition=1,
                                                            endPosition=self.evaluateLastJoint,
                                                            supportType="OffsetPrnt")

        self.addSupportNode(offsetJointPrntSystem, "OffsetPrntJointSystem")

        # snap each offset joint to the same position as the next joint
        for i in range(len(self.offsetJointSystem)):
            # Alias the current node
            currentJoint = self.offsetJointSystem.joints[i]
            # Alias for the parent joint
            prntJoint = offsetJointPrntSystem.joints[i]
            currentJoint.setParent(prntJoint)
            currentJoint.prnt = prntJoint
            # Alias the child joint
            trgJoint = self.jointSystem.joints[i + 1]
            # Snap to the next joint
            prntJoint.snap(self.jointSystem.joints[i + 1].mNode, rotate=False)
            # Parent the next joint to the this joint
            trgJoint.setParent(currentJoint)
            # Parent the offjoint to current joint
            prntJoint.setParent(self.jointSystem.joints[i])

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
        super(Generic, self).build()
        self.buildControl()
        if self.isDeformable:
            self.buildOffsetJoint()
        self.connectControl()
        self.cleanUp()

    @property
    def mainCtrls(self):
        key = "mainCtrls"
        if not self.metaCache.setdefault(key, None):
            self.metaCache[key] = self.getChildren(asMeta=self.returnNodesAsMeta,
                                                   walk=True,
                                                   cAttrs=["MainCtrls"])
        return self.metaCache[key]

    @mainCtrls.setter
    def mainCtrls(self, ctrlList):
        if not ctrlList:
            raise RuntimeError("Please input a list of meta Ctrls")
        self.connectChildren(ctrlList, "MainCtrls", allowIncest=True, cleanCurrent=True)
        self.metaCache["mainCtrls"] = ctrlList

    @property
    def allCtrls(self):

        attr = "allCtrls"
        if self.metaCache.setdefault(attr):
            self.metaCache[attr] = self.getChildren(asMeta=True,
                                                    walk=True,
                                                    cAttrs=["MainCtrls", '%s_*' % self.CTRL_Prefix])
        return self.metaCache[attr]

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
                if not self.isDeformable:
                    libUtilities.lock_scale(self.mainCtrls[i].pynode)

            # Lock the elbow
            for position in self.lockCtrlPositions:
                for attr in [self.rollAxis, self.rollAxis]:
                    attrName = "rotate{0}".format(attr)
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

    # noinspection PyStatementEffect
    def buildBlendCtrl(self):
        # Build Blendcontrol
        self.blender = self.createCtrlObj('{}Blend'.format(self.part), createXtra=False, addGimbal=False)
        self.blender.lockDefaultAttributes()

        # Create reverse node
        self.inverse = core.MetaRig(side=self.side, part=self.part, endSuffix="Inverse", nodeType="reverse")

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

            if i:
                pairConstraint = pm.PyNode(
                    joint.addConstraint(jointA, "orient", zeroOut=False))
                joint.addConstraint(jointB,  "orient", zeroOut=False)
            else:
                # Constraints the first node
                pairConstraint = pm.PyNode(joint.addConstraint(jointA, zeroOut=False))
                joint.addConstraint(jointB, zeroOut=False)

            # Reverse node in first
            self.inverse.pynode.outputX >> pairConstraint.w0

            # Connect the interpType
            self.interpAttr >> pairConstraint.interpType

            # Direct connection in second
            self.blendAttr >> pairConstraint.w1

            if self.subSystemA.isDeformable:
                pairBlend = core.MetaRig(part=joint.part, side=self.side,
                                         endSuffix='PairBlend',
                                         nodeType='pairBlend')
                pairPyNode = pairBlend.pynode
                jointA.pynode.attr("scale") >> pairPyNode.attr('inTranslate1')
                jointB.pynode.attr("scale") >> pairPyNode.attr('inTranslate2')
                pairPyNode.attr('outTranslate') >> joint.pynode.attr("scale")

                self.blendAttr >> pairPyNode.weight

    def blendVisibility(self):
        # Set the visibility set driven key
        blendAttrName = self.blendAttr.name()
        attrValues = [0, .5, 1]
        subSysAVis = [1, 1, 0]
        subSysBVis = [0, 1, 1]

        for visValue, subSystem in zip([subSysAVis, subSysBVis], [self.subSystemA, self.subSystemB]):
            for ctrl in subSystem.mainCtrls:
                visAttr = ctrl.pynode.getShape().v
                if not pm.listConnections(visAttr) and not visAttr.isLocked():
                    ctrlShapeName = visAttr.name()
                    try:
                        libUtilities.set_driven_key({blendAttrName: attrValues}, {ctrlShapeName: visValue}, "step")
                    except RuntimeError:
                        print("Skipping Blending of {}".format(ctrlShapeName))

    def build(self):
        self.buildBlendCtrl()
        self.blendJoints()
        self.rotateOrder = self.jointSystem.rotateOrder
        self.blendVisibility()

    @property
    def blendAttr(self):
        return self.blender.pynode.attr(self.subSystems)

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

core.Red9_Meta.registerMClassInheritanceMapping()
core.Red9_Meta.registerMClassNodeMapping(nodeTypes=['pairBlend'])

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
