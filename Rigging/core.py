__author__ = 'pritish.dogra'

# TODO: Start documentation before the next rig system

from PKD_Tools.Red9 import Red9_Meta, Red9_CoreUtils

reload(Red9_Meta)
from PKD_Tools.Rigging import utils

reload(utils)

import pymel.core as pm
from PKD_Tools import libUtilities

reload(libUtilities)


def _fullSide_(side):
    sideDict = {"L": "Left",
                "R": "Right",
                "C": "Centre"
                }
    return sideDict[side]


_SUBCOMPONENTS_ = ["FK", "IK", "Dyn"]


class MetaEnhanced(object):
    """Some more custom properties which adds on to the base meta classes"""
    _pynode_ = None

    @property
    def pynode(self):
        import pymel.core as pm
        if self._pynode_ is None:
            self._pynode_ = pm.PyNode(self.mNode)
        return self._pynode_

    @property
    def primaryAxis(self):
        if hasattr(self, "rotateOrder"):
            return self.pynode.rotateOrder.get(asString=True)


class MetaRig(Red9_Meta.MetaRig, MetaEnhanced):
    # TODO: Move some the non Red9 func to MetaEnhanced
    # Set default values
    def __init__(self, *args, **kwargs):
        if kwargs.has_key("side") and kwargs.has_key("part"):
            # Setup defaults
            kwargs["endSuffix"] = kwargs.get("endSuffix", "Grp")
            kwargs["nodeType"] = kwargs.get("nodeType", "transform")
            full_name = utils.nameMe(kwargs["side"], kwargs["part"], kwargs["endSuffix"])
            # Remove the keyword arguement
            super(MetaRig, self).__init__(name=full_name, **kwargs)
            self.part = kwargs["part"]
            if kwargs.has_key("side"):
                self.mirrorSide = _fullSide_(kwargs["side"])
            self.rigType = kwargs["endSuffix"]
            self.mSystemRoot = False

        else:
            super(MetaRig, self).__init__(*args, **kwargs)
        self.lockState = False
        self.lockState = False
        self.isSubComponent = False
        if hasattr(self, "systemType"):
            if self.systemType in _SUBCOMPONENTS_:
                self.isSubComponent = True

        # Return connected as meta
        self.returnNodesAsMeta = True

        # debugMode
        self.debugMode = False

    def __bindData__(self, *args, **kwgs):
        # ensure these are added by default
        if not hasattr(self, "mClass"):
            # Need to add this otherwise the maya wrapped node do not get returned
            self.addAttr("mClass", self.__class__.__name__)
            self.pynode.mClass.lock(True)
        self.addAttr("part", "")
        self.addAttr('mirrorSide', enumName='Centre:Left:Right',
                     attrType='enum', hidden=True)
        self.addAttr('rigType', '')

    def setParent(self, targetSystem):
        if self.prnt is not None:
            if targetSystem.pynode.type() == "transform":
                self.prnt.pynode.setParent(targetSystem.pynode)
            else:
                libUtilities.pyLog.warning(
                    "%s is not a transform node. Unable to parent %s" % (targetSystem.pynode, self.pynode))
        else:
            self.pynode.setParent(targetSystem.pynode)

    def convertToComponent(self, component="FK"):
        componentName = "%s_%s" % (self.part, component)
        try:
            if not self.isSubComponent:
                self.pynode.rename(self.shortName().replace(self.part, componentName))
            else:
                # Node is converted to a subcomponent
                return
        except Exception as e:
            libUtilities.pyLog.info(str(e))
            libUtilities.pyLog.info("Rename failed on:%s" % self.mNode)
            self.select()
            raise Exception("Rename Failed")

        libUtilities.strip_integer(self.pynode)
        # Add a new attr
        if not hasattr(self, "systemType"):
            self.addAttr("systemType", component)
        self.isSubComponent = True

    def getRigCtrl(self, target):
        children = self.getChildren(walk=True, asMeta=self.returnNodesAsMeta,
                                    cAttrs=["%s_%s" % (self.CTRL_Prefix, target)])
        if not children:
            libUtilities.pyLog.warn("%s ctrl not found on %s" % (target, self.shortName()))
        else:
            return children[0]

    def addRigCtrl(self, data, *args, **kwargs):
        try:
            # TODO: add ctrls to rig controls
            assert isinstance(data, Red9_Meta.MetaClass)
            super(MetaRig, self).addRigCtrl(data.mNode, *args, **kwargs)
        except:
            raise AssertionError("Input must be MetaClass")

    def getSupportNode(self, target):
        children = self.getChildren(walk=True, asMeta=self.returnNodesAsMeta, cAttrs=["SUP_%s" % target])
        if not children:
            if self.debugMode:
                libUtilities.pyLog.warn("%s not support node found on %s" % (target, self.shortName()))
        else:
            if type(children[0]) == Red9_Meta.MetaClass:
                children[0] = MetaRig(children[0].mNode)

            return children[0]

    def addParent(self, **kwargs):
        snap = kwargs.get("snap", True)
        endSuffix = kwargs.get("endSuffix", "Prnt")
        if not (self.part and self.side):
            raise ValueError("Part or Side is not defined: %s" % self.shortName())
        self.prnt = MetaRig(part=self.part, side=self.side, endSuffix=endSuffix)
        if snap:
            libUtilities.snap(self.prnt.pynode, self.pynode)
        self.pynode.setParent(self.prnt.pynode)

    def addSupportNode(self, node, attr, boundData=None):
        if hasattr(node, "mNode"):
            supportNode = node.mNode
        elif isinstance(node, pm.PyNode):
            supportNode = node.name()
        else:
            supportNode = node
        super(MetaRig, self).addSupportNode(supportNode, attr, boundData=None)
        # Test that the connection has been made

    def snap(self, target, rotate=True):
        if self.prnt:
            libUtilities.snap(self.prnt.pynode, target, rotate=rotate)
        else:
            libUtilities.snap(self.pynode, target, rotate=rotate)

    def transferPropertiesToChild(self, childMeta, childType):
        try:
            # TODO: add ctrls to rig controls
            assert isinstance(childMeta, Red9_Meta.MetaClass)
        except:
            raise AssertionError("ChildMeta must be MetaClass: %s. Type is %s" % (childMeta, type(childMeta)))
        childMeta.mirrorSide = self.mirrorSide
        childMeta.rigType = childType

    def resetName(self):
        self.pynode.rename(self.trueName)

    @property
    def prnt(self):
        return self.getSupportNode("Prnt")

    @prnt.setter
    def prnt(self, data):
        self.addSupportNode(data, "Prnt")

    @property
    def side(self):
        return self.pynode.mirrorSide.get(asString=True)[0]

    @property
    def trueName(self):
        if not (self.side and self.part and self.rigType):
            raise ValueError("One of the attribute are not defined. Cannot get true name")
        return utils.nameMe(self.side, self.part, self.rigType)


class SubSystem(MetaRig):
    """This is a base system. """

    def setParent(self, targetSystem):
        self.pynode.setParent(targetSystem.mNode)

    def __bindData__(self, *args, **kwgs):
        super(SubSystem, self).__bindData__(*args, **kwgs)
        self.addAttr('systemType', "")

    def addMetaSubSystem(self, subSystem, system="FK", **kwargs):
        # Parent the group
        subSystem.setParent(self)
        # Connect it as a child
        self.connectChild(subSystem, "%s_System" % system)
        subSystem.systemType = system

    def convertSystemToComponent(self, component="FK"):
        # Rename the component the child component
        for obj in [self] + self.getChildMetaNodes(walk=True):
            obj.convertToComponent(component)


class Network(MetaRig):
    def __init__(self, *args, **kwargs):
        kwargs["nodeType"] = "network"
        kwargs["endSuffix"] = "Sys"
        super(Network, self).__init__(*args, **kwargs)


class Joint(MetaRig):
    """
    Example showing that metaData isn't limited to 'network' nodes,
    by using the 'nodeType' arg in the class __init__ you can modify
    the general behaviour such that meta creates any type of Maya node.
    '''
    def __init__(self,*args,**kwargs):
        super(MyCameraMeta, self).__init__(nodeType='camera',*args,**kwargs)
        self.item = None
    """

    def __init__(self, *args, **kwargs):
        kwargs["nodeType"] = "joint"
        kwargs["endSuffix"] = kwargs.get("endSuffix", "Joint")
        super(Joint, self).__init__(*args, **kwargs)

    @property
    def prnt(self):
        return None

    @property
    def side(self):
        return self.pynode.mirrorSide.get(asString=True)[0]


class JointSystem(Network):
    def __init__(self, *args, **kwargs):
        super(JointSystem, self).__init__(*args, **kwargs)
        self.joint_data = None

    def __bindData__(self, *args, **kwgs):
        super(JointSystem, self).__bindData__()
        # ensure these are added by default
        self.addAttr("joint_data", "")

    def __len__(self):
        return len(self.Joints)

    def build(self):
        if self.joint_data:
            metaJoints = []
            for i, joint in enumerate(self.joint_data):
                metaJoint = Joint(side=self.side, part=joint["Name"])
                metaJoint.pynode.setTranslation(joint["Position"], space="world")
                metaJoint.pynode.jointOrient.set(joint["JointOrient"])
                for attr in ["jointOrientX", "jointOrientY", "jointOrientZ"]:
                    metaJoint.pynode.attr(attr).setKeyable(True)
                metaJoints.append(metaJoint)
                if i:
                    metaJoint.pynode.setParent(metaJoints[i - 1].mNode)

            self.Joints = metaJoints
        else:
            libUtilities.pyLog.error("No Joint Data Specified")

    def convertJointsToMetaJoints(self):
        # Build the joint data map
        jointData = []
        pyJoints = []
        for joint in self.Joints:
            joint = pm.PyNode(joint.mNode)
            joint.setParent(w=1)
            libUtilities.freeze_transform(joint)
            # TODO: Need to refactorise this when using for anno
            jointData.append({
                "Name": joint.shortName(),
                "JointOrient": list(joint.jointOrient.get()),
                "Position": list(joint.getTranslation(space="world"))
            })
            pyJoints.append(joint)

        # Delete all the joints
        self.joint_data = jointData

        # Build the data
        self.build()
        pm.delete(pyJoints)

    def rebuildJointData(self):
        jointData = []
        for joint in self.Joints:
            joint.pynode.select()
            newJoint = pm.joint()
            newJoint.setParent(w=1)
            jointData.append({
                "Name": joint.part,
                "JointOrient": list(newJoint.jointOrient.get()),
                "Position": list(newJoint.getTranslation(space="world"))
            })
            pm.delete(newJoint)
        self.joint_data = jointData

    def setParent(self, targetSystem):
        self.Joints[0].pynode.setParent(targetSystem.mNode)

    def setRotateOrder(self, rotateOrder):
        for joint in self.Joints:
            joint.rotateOrder = rotateOrder

    def replicate(self, *args, **kwargs):
        if self.joint_data:
            replicateJoint = JointSystem(*args, **kwargs)
            if kwargs.has_key("supportType"):
                # Change the system name
                newSuffix = kwargs["supportType"] + "Sys"
                replicateJoint.rigType = newSuffix
                # Rename the joint data
                joint_data = self.joint_data
                # Add the suffix to the name for support type
                for jointInfo in joint_data:
                    jointInfo["Name"] = jointInfo["Name"] + kwargs["supportType"]
                replicateJoint.joint_data = joint_data
            else:
                replicateJoint.joint_data = self.joint_data

            replicateJoint.setRotateOrder(self.Joints[0].rotateOrder)
            replicateJoint.build()
            return replicateJoint
        else:
            libUtilities.pyLog.error("Unable to replicate as there is no joint data")

    @property
    def Joints(self):
        return self.getChildren(asMeta=self.returnNodesAsMeta, walk=True, cAttrs=["SUP_Joints"])

    @Joints.setter
    def Joints(self, jointList):
        jointList = [joint.shortName() for joint in jointList]
        self.connectChildren(jointList, "SUP_Joints", allowIncest=True, cleanCurrent=True)

    @property
    def jointList(self):
        return [joint.shortName() for joint in self.Joints]

    @property
    def positions(self):
        positionList = []
        if self.joint_data:
            for joint in self.joint_data:
                positionList.append(joint["Position"])
        else:
            libUtilities.pyLog.error("No joint data found")
        return positionList


class SpaceLocator(MetaRig):
    """
    Space locator meta. Allow to create fake meta
    """

    def __init__(self, *args, **kwargs):
        super(SpaceLocator, self).__init__(*args, **kwargs)
        if not self.pynode.getShape():
            # Create a new temp locator
            tempLoc = pm.spaceLocator()
            # Tranfer the locator shape to the main node
            libUtilities.transfer_shape(tempLoc, self.mNode)
            # Rename the shape node
            libUtilities.fix_shape_name(self.pynode)
            # Delete the temp loc
            pm.delete(tempLoc)

    def clusterCV(self, cv):
        self.snap(cv.name(), rotate=False)
        libUtilities.cheap_point_constraint(self.pynode, cv)


class Ctrl(MetaRig):
    """This is a base control System"""

    def __init__(self, *args, **kwargs):
        # TODO: Allow option to disable extra
        kwargs["endSuffix"] = "Ctrl"
        super(Ctrl, self).__init__(*args, **kwargs)
        self.mSystemRoot = False
        self.ctrl = self
        self.createXtra = True
        # Internal Var
        self.ctrlShape = kwargs.get("shape", "Ball")
        self.hasParentMaster = kwargs.get("parentMaster", False)
        self.mirrorData = {'side': self.mirrorSide, 'slot': 1}

    def build(self):
        # Create the xtra grp
        if self.createXtra:
            self.xtra = MetaRig(part=self.part, side=self.side, endSuffix="Xtra")
        # Create the Parent
        self.prnt = MetaRig(part=self.part, side=self.side, endSuffix="Prnt")
        tempCtrlShape = utils.build_ctrl_shape(self.ctrlShape)
        libUtilities.transfer_shape(tempCtrlShape, self.mNode)
        libUtilities.fix_shape_name(self.pynode)
        pm.delete(tempCtrlShape)
        if self.createXtra:
            # Parent the ctrl to the xtra
            self.pynode.setParent(self.xtra.mNode)
            # Parent the xtra to prnt
            self.xtra.pynode.setParent(self.prnt.mNode)
        else:
            # Parent the ctrl to prnt
            self.pynode.setParent(self.prnt.mNode)
        # Transform Nodes
        node = [self.pynode, self.prnt.pynode]
        if self.createXtra:
            node.append(self.xtra.pynode)
        # lock and hide the visibility attributes
        for node in [self.pynode, self.xtra.pynode, self.prnt.pynode]:
            libUtilities.set_lock_status(node, {"v": True})
            node.v.showInChannelBox(True)
            node.v.showInChannelBox(False)

    def addParentMaster(self):
        # Create the parent master group if need be
        self.parentMasterSN = MetaRig(name="%s_SN" % self.mNodeID, nodeType="transform")
        self.parentMasterSN.rigType = "SN"
        self.parentMasterPH = MetaRig(name="%s_PH" % self.mNodeID, nodeType="transform")
        self.parentMasterPH.rigType = "PH"
        # Setup the parenting
        self.pynode.setParent(self.parentMasterSN.mNode)
        self.parentMasterSN.pynode.setParent(self.parentMasterPH.mNode)
        self.parentMasterPH.pynode.setParent(self.xtra.mNode)
        # set the parts
        self.parentMasterSN.part = self.part
        self.parentMasterPH.part = self.part

    def addGimbalMode(self):
        self.gimbal = MetaRig(name=utils.nameMe(self.side, self.part, "Gimbal"), nodeType="transform")
        self.gimbal.part = self.part
        self.gimbal.rigType = "gimbalHelper"
        self.gimbal.pynode.setParent(self.mNode)
        # Set the shape
        tempCtrlShape = utils.build_ctrl_shape("Spike")
        libUtilities.transfer_shape(tempCtrlShape, self.gimbal.pynode)
        libUtilities.fix_shape_name(self.gimbal.pynode)
        pm.delete(tempCtrlShape)
        # Add Attribute control the visibility
        self.addDivAttr("Show", "gimbVis")
        self.addBoolAttr("Gimbal")
        self.pynode.Gimbal >> self.gimbal.pynode.v

    def addSpaceLocator(self, parent=False):
        # spaceLocator -p 0 0 0;
        self.locator = SpaceLocator(side=self.side, part=self.part, endSuffix="Loc")
        if parent:
            if self.hasGimbal:
                self.locator.pynode.setParent(self.gimbal.pynode)
            else:
                self.locator.pynode.setParent(self.pynode)

    def setParent(self, targetSystem):
        # Instead of the node itself, the parent is reparented
        self.prnt.pynode.setParent(targetSystem.mNode)

    def addPivot(self):
        self.pivot = MetaRig(name=utils.nameMe(self.side, self.part, "Pivot"), nodeType="transform")
        self.pivot.part = self.part
        self.pivot.rigType = "pivot"
        self.pivot.pynode.setParent(self.mNode)
        # Set the shape
        tempCtrlShape = utils.build_ctrl_shape("Locator")
        libUtilities.transfer_shape(tempCtrlShape, self.pivot.pynode)
        libUtilities.fix_shape_name(self.pivot.pynode)
        pm.delete(tempCtrlShape)
        # Snap ctrl
        libUtilities.snap(self.pivot.mNode, self.mNode)

        self.pivot.pynode.setParent(self.mNode)

        self.pivot.pynode.translate >> self.pynode.rotatePivot
        self.pivot.pynode.translate >> self.pynode.scalePivot

        # Add Attribute control the visibility
        self.addDivAttr("Show", "pivotVis")
        self.addBoolAttr("Pivot")
        self.pynode.Pivot >> self.pivot.pynode.v

    def addChild(self, targetNode):
        # TODO Does not work in some scenairos
        if self.hasGimbal:
            pm.parent(targetNode, self.gimbal.mNode)
        else:
            pm.parent(targetNode, self.ctrl.mNode)

    def setRotateOrder(self, rotateOrder):
        self.rotateOrder = rotateOrder
        self.xtra.rotateOrder = rotateOrder
        self.prnt.rotateOrder = rotateOrder
        if self.hasGimbal:
            self.gimbal.rotateOrder = rotateOrder
        if self.hasParentMaster:
            self.parentMasterPH.rotateOrder = rotateOrder
            self.parentMasterSN.rotateOrder = rotateOrder

    def addDivAttr(self, label, ln):
        libUtilities.addDivAttr(self.mNode, label=label, ln=ln)

    def addBoolAttr(self, label, sn=""):
        libUtilities.addBoolAttr(self.mNode, label=label, sn=sn)

    def addFloatAttr(self, attrName="", attrMax=1, attrMin=0, SV=0, sn="", df=0):
        libUtilities.addAttr(self.mNode, attrName=attrName, attrMax=attrMax, attrMin=attrMin, SV=0, sn=sn, df=df)

    def addConstraint(self, target, conType="parent", **kwargs):
        if kwargs.has_key("maintainOffset"):
            kwargs["mo"] = kwargs["maintainOffset"]
        else:
            kwargs["mo"] = kwargs.get("mo", True)
        libUtilities.pyLog.warning("%sConstrainting %s to %s. Maintain offset is %s "
                                   % (conType, self.prnt.pynode, target, kwargs["mo"]))
        # Get the constraint function from the library
        consFunc = getattr(pm, "%sConstraint" % conType)
        # Set the constraint
        constraintNode = consFunc(target, self.prnt.pynode, maintainOffset=kwargs["mo"]).name()
        if not eval("self.%sConstraint" % conType):
            constraintMeta = MetaRig(str(constraintNode))
            constraintMeta.rigType = "%sCon" % libUtilities.capitalize(conType)
            constraintMeta.mirrorSide = self.mirrorSide
            constraintMeta.part = self.part
            self.addSupportNode(constraintMeta, "%sConstraint" % conType)

    def lockTranslate(self):
        for item in [self, self.prnt, self.xtra]:
            if item:
                libUtilities.lock_translate(item.pynode)

    def lockRotate(self):
        for item in [self, self.prnt, self.xtra]:
            if item:
                libUtilities.lock_rotate(item.pynode)

    def lockScale(self):
        for item in [self, self.prnt, self.xtra]:
            if item:
                libUtilities.lock_scale(item.pynode)

    def _create_rotate_driver_(self):
        pmaMeta = MetaRig(side=self.side,
                          part=self.part,
                          endSuffix="RotateDriver",
                          nodeType="plusMinusAverage")

        pmaMeta.addAttr("connectedAxis", {"X": False, "Y": False, "Z": False})
        self.addSupportNode(pmaMeta, "RotateDriver")
        return pmaMeta

    def _connect_axis_rotate_driver_(self, axis):
        pmaMeta = self.getSupportNode("RotateDriver")
        if not pmaMeta:
            pmaMeta = self._create_rotate_driver_()

        # Is the rotate axis connected
        rotateStatus = pmaMeta.connectedAxis
        if not rotateStatus[axis.upper()]:
            # Connect the rotate axis to PMA
            nodes = [self.pynode]
            if self.hasGimbal:
                nodes.append(self.gimbal.pynode)

            for i, node in zip(range(len(nodes)), nodes):
                node.attr("rotate%s" % axis.upper()) >> pmaMeta.pynode.input3D[i].attr("input3D%s" % axis.lower())

            # Set the rotate axis
            rotateStatus[axis.upper()] = True
            pmaMeta.connectedAxis = rotateStatus
        return pmaMeta

    def get_rotate_driver(self, axis):
        pmaMeta = self._connect_axis_rotate_driver_(axis)
        if axis == "X":
            return pmaMeta.pynode.output3Dx
        elif axis == "Y":
            return pmaMeta.pynode.output3Dy
        else:
            return pmaMeta.pynode.output3Dz

    @property
    def parentDriver(self):
        # Is the driver going to be the gimbal or the control itself. Useful for skinning, correct constraint target
        if self.hasGimbal:
            return self.gimbal
        else:
            return self

    @property
    def parentConstraint(self):
        return self.getSupportNode("ParentConstraint")

    @property
    def orientConstraint(self):
        return self.getSupportNode("OrientConstraint")

    @property
    def pointConstraint(self):
        return self.getSupportNode("PointConstraint")

    @property
    def aimConstraint(self):
        return self.getSupportNode("AimConstraint")

    @property
    def xtra(self):
        return self.getSupportNode("Xtra")

    @xtra.setter
    def xtra(self, data):
        self.addSupportNode(data, "Xtra")

    @property
    def gimbal(self):
        data = self.getSupportNode("Gimbal")
        return data

    @gimbal.setter
    def gimbal(self, data):
        self.addSupportNode(data, "Gimbal")

    @property
    def hasGimbal(self):
        return self.getSupportNode("Gimbal") is not None

    @property
    def pivot(self):
        data = self.getSupportNode("Pivot")
        return data

    @pivot.setter
    def pivot(self, data):
        self.addSupportNode(data, "Pivot")

    @property
    def hasPivot(self):
        return self.getSupportNode("Pivot") is not None

    @property
    def locator(self):
        data = self.getSupportNode("Locator")
        return data

    @locator.setter
    def locator(self, data):
        self.addSupportNode(data, "Locator")

    @property
    def hasLocator(self):
        return self.getSupportNode("Locator") is not None

    @property
    def parentMasterPH(self):
        data = self.getSupportNode("ParentMasterPH")
        if data is not None:
            self.hasParentMaster = True
        return data

    @parentMasterPH.setter
    def parentMasterPH(self, data):
        # TODO: Pass the slot number before and axis data
        self.addSupportNode(data, "ParentMasterPH")
        if data is not None:
            self.hasParentMaster = True

    @property
    def parentMasterSN(self):
        return self.getSupportNode("ParentMasterSN")

    @parentMasterSN.setter
    def parentMasterSN(self, data):
        # TODO: Pass the slot number before and axis data
        self.addSupportNode(data, "ParentMasterSN")


class Anno_Loc(SpaceLocator):
    """This is a a annoated locator"""
    pass


class MyCameraMeta(Red9_Meta.MetaClass, MetaEnhanced):
    """
    Example showing that metaData isn't limited to 'network' nodes,
    by using the 'nodeType' arg in the class __init__ you can modify
    the general behaviour such that meta creates any type of Maya node.
    '''
    def __init__(self,*args,**kwargs):
        super(MyCameraMeta, self).__init__(nodeType='camera',*args,**kwargs)
        self.item = None
    """

    def __init__(self, *args, **kwargs):
        super(MyCameraMeta, self).__init__(nodeType='camera', *args, **kwargs)


class Rig(SubSystem):
    """This is base System. Transform is the main"""

    def __init__(self, *args, **kwargs):
        super(Rig, self).__init__(*args, **kwargs)
        self.mainCtrlShape = "Box"

    def create_test_cube(self, targetJoint, childJoint):
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

    def addScale(self):
        pass

    def addCartoony(self):
        self.addScale()
        self._create_cartoon_network_()
        self._connect_cartoony_scale_()

    @property
    def JointSystem(self):
        return self.getSupportNode("JointSystem")

    @JointSystem.setter
    def JointSystem(self, data):
        self.addSupportNode(data, "JointSystem")


class Ik(Rig):
    def __init__(self, *args, **kwargs):
        super(Ik, self).__init__(*args, **kwargs)
        self.rotateOrder = "yzx"
        self.mirrorData = {'side': self.mirrorSide, 'slot': 1}
        self.ikControlToWorld = False
        self.hasParentMaster = False
        self.mainCtrlShape = "Box"
        self.hasPivot = False

    def _create_ctrl_obj_(self, part, shape="", createXtra=True, addGimbal=True):
        ctrl = Ctrl(part=part, side=self.side)
        if not shape:
            shape = self.mainCtrlShape
        ctrl.ctrlShape = shape
        ctrl.build()
        if addGimbal:
            ctrl.addGimbalMode()
        ctrl.createXtra = createXtra
        if self.hasParentMaster:
            ctrl.addParentMaster()
        if self.hasPivot:
            ctrl.addPivot()
        ctrl.setRotateOrder(self.rotateOrder)
        ctrl.setParent(self)
        return ctrl

    @property
    def ikHandle(self):
        return self.getSupportNode("IKHandle")

    @ikHandle.setter
    def ikHandle(self, data):
        self.addSupportNode(data, "IKHandle")


Red9_Meta.registerMClassInheritanceMapping()
Red9_Meta.registerMClassNodeMapping(nodeTypes=['transform',
                                               'camera',
                                               'joint',
                                               'plusMinusAverage',
                                               'multiplyDivide'])

if __name__ == '__main__':
    # pm.newFile(f=1)
    # cam = MyCameraMeta(name="MyCam")
    # cam.item = "test"
    # print cam.mNode
    # print cam.item
    #
    # filePath = pm.saveAs(r"C:\temp\testMeta.ma")
    # pm.newFile(f=1)
    # pm.openFile(filePath)
    # cam = Red9_Meta.MetaClass("MyCam")
    # print cam.mNode
    # print cam.item
    #

    pm.newFile(f=1)
    # # cam = MyCameraMeta()
    # subSystem = SubSystem(side="L", part="Core")
    #
    # mRig = Red9_Meta.MetaRig(name='CharacterRig', nodeType="transform")
    # mRig.connectChild(subSystem, 'Arm')
    # subSystem.setParent(mRig)
    #
    # fkSystem = subSystem.addMetaSubSystem(MetaRig)
    # fkSystem = SubSystem(side="U", part="Arm")
    # fkSystem.setParent(subSystem)
    # subSystem.connectChild(fkSystem, 'FK_System')
    # # l = rig(side="L", part="Test")
    #
    # myCtrl = Ctrl(side="L", part="Hand")
    # myCtrl.build()
    # myCtrl.addGimbalMode()

    myCtrl = Ik(side="L", part="Hand")
    #
    # myCtrl.addSpaceLocator()
    # myCtrl.setParent(fkSystem)
    #
    # myCtrl1 = Ctrl(side="U", part="FK1")
    # myCtrl1.create_ctrl()
    #
    # myCtrl1.setParent(fkSystem)
    #
    # fkCtrls = [myCtrl.mNode, myCtrl1.mNode]
    # fkCtrls = [myCtrl]
    # fkSystem.connectChildren(fkCtrls, "Ctrl")
    # fkSystem.convertToComponent("FK")
    # subSystem.connectChildren(fkCtrls, "FK")

    # jntSystem = JointSystem(side="C", part="Cora")
    # joints = utils.create_test_joint("ik2jnt")
    # jntSystem.Joints = joints
    # jntSystem.convertJointsToMetaJoints()
    # rep = jntSystem.replicate(side="L", part="CoraHelp", supportType="Help")
    #
    #
    # # Need to run this in case of opening and closing file
    #
    # from PKD_Tools.Red9 import Red9_Meta
    # reload(Red9_Meta)
    #
    # from PKD_Tools.Rigging import core
    # reload(core)
    #
    # # k = Red9_Meta.MetaClass("CharacterRig")
    # pm.newFile(f=1)
    # SpaceLocator(part="main", side="C")
