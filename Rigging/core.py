__author__ = 'pritish.dogra'

from PKD_Tools.Red9 import Red9_Meta

reload(Red9_Meta)
from PKD_Tools.Rigging import utils

reload(utils)

import pymel.core as pm
from PKD_Tools import libUtilities

reload(libUtilities)


def _fullSide_(side):
    sideDict = {"L": "Left",
                "R": "Right",
                "C": "Centre",
                "U": "Unique"
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


class MetaClass(Red9_Meta.MetaClass, MetaEnhanced):
    pass


class MetaRig(Red9_Meta.MetaRig, MetaEnhanced):
    # Set default values
    def __init__(self, *args, **kwargs):
        if kwargs.has_key("side") and kwargs.has_key("part"):
            # Setup defaults
            if not kwargs.has_key("endSuffix"):
                kwargs["endSuffix"] = "Grp"
            if not kwargs.has_key("nodeType"):
                kwargs["nodeType"] = "transform"
            full_name = utils.nameMe(kwargs["side"], kwargs["part"], kwargs["endSuffix"])
            # Remove the keyword arguement
            super(MetaRig, self).__init__(name=full_name, **kwargs)
            self.part = kwargs["part"]
            if kwargs.has_key("side"):
                self.mirrorSide = _fullSide_(kwargs["side"])
            self.rigType = kwargs["endSuffix"]
            self.lockState = False
            self.lockState = False
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
        self.addAttr("part", "")
        # TODO Remove Unique from all packages
        self.addAttr('mirrorSide', enumName='Centre:Left:Right:Unique',
                     attrType='enum', hidden=True)
        self.addAttr('rigType', '')

    def setParent(self, targetSystem):
        self.pynode.setParent(targetSystem.mNode)

    def convertToComponent(self, component="FK"):
        componentName = "%s_%s" % (self.part, component)
        try:
            self.pynode.rename(self.shortName().replace(self.part, componentName))
        except Exception, e:
            libUtilities.pyLog.info(str(e))
            libUtilities.pyLog.info("Rename failed on:%s" % self.mNode)
            self.select()
            raise Exception("Rename Failed")

        libUtilities.strip_integer(self.pynode)
        # Add a new attr
        if not hasattr(self, "systemType"):
            self.addAttr("systemType", component)
        self.isSubComponent = True
        # Rename the component the child component
        for child in self.getChildMetaNodes():
            child.convertToComponent(component)

    @property
    def side(self):
        return self.pynode.attr("mirrorSide").get(asString=True)[0]

    def getRigCtrl(self, target):
        children = self.getChildren(walk=True, asMeta=self.returnNodesAsMeta,
                                    cAttrs=["%s_%s" % (self.CTRL_Prefix, target)])
        if not children:
            libUtilities.pyLog.warn("%s ctrl not found on %s" % (target, self.shortName()))
        else:
            return children[0]

    def addRigCtrl(self, data, *args, **kwargs):
        try:
            assert isinstance(data, Red9_Meta.MetaClass)
            super(MetaRig, self).addRigCtrl(data.mNode, *args, **kwargs)
        except:
            raise Exception("Input must be MetaClass")

    def getSupportNode(self, target):
        children = self.getChildren(walk=True, asMeta=self.returnNodesAsMeta, cAttrs=["SUP_%s" % target])
        if not children:
            libUtilities.pyLog.warn("%s support node found on %s" % (target, self.shortName()))
        else:
            if type(children[0]) == Red9_Meta.MetaClass:
                children[0] = MetaRig(children[0].mNode)

            return children[0]


class SubSystem(MetaRig):
    """This is a base system. """

    def setParent(self, targetSystem):
        self.pynode.setParent(targetSystem.mNode)

    def __bindData__(self, *args, **kwgs):
        super(SubSystem, self).__bindData__(*args, **kwgs)
        self.addAttr('systemType', "")

    def addMetaSubSystem(self, MClass, system="FK", **kwargs):
        # Add subgroup
        subSystem = MClass(side=self.side, part=self.part, **kwargs)
        subSystem.setParent(self)
        self.connectChild(subSystem, "%s_System" % system)
        subSystem.systemType = system
        return subSystem


class Joint(MetaRig, MetaEnhanced):
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
        kwargs["endSuffix"] = "Joint"
        super(Joint, self).__init__(*args, **kwargs)


class JointSystem(MetaRig):
    def __init__(self, *args, **kwargs):
        kwargs["nodeType"] = "network"
        kwargs["endSuffix"] = "Sys"
        super(JointSystem, self).__init__(*args, **kwargs)
        self.joint_data = None

    def build(self):
        if self.joint_data:
            metaJoints = []
            for joint, i in zip(self.joint_data, range(len(self.joint_data))):
                metaJoint = Joint(side=self.side, part=joint["Name"])
                metaJoint.pynode.setTranslation(joint["Position"], space="world")
                metaJoint.pynode.jointOrient.set(joint["JointOrient"])
                metaJoints.append(metaJoint)
                if i:
                    metaJoint.pynode.setParent(metaJoints[i - 1].mNode)

            metaJoints.reverse()
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
                "JointOrient": joint.jointOrient.get(),
                "Position": joint.getTranslation(space="world")
            })
            pyJoints.append(joint)

        # Delete all the joints

        self.joint_data = jointData

        self.build()

        pm.delete(pyJoints)

    def setParent(self, targetSystem):
        self.Joints[0].pynode.setParent(targetSystem.mNode)

    def setRotateOrder(self, rotateOrder):
        for joint in self.Joints:
            joint.rotateOrder = rotateOrder

    @property
    def Joints(self):
        return self.getChildren(asMeta=self.returnNodesAsMeta, walk=True, cAttrs=["SUP_Joints"])

    @Joints.setter
    def Joints(self, jointList):
        jointList = [joint.shortName() for joint in jointList]
        jointList.reverse()
        self.connectChildren(jointList, "SUP_Joints")


class Ctrl(MetaRig):
    """This is a base control System"""

    def __init__(self, *args, **kwargs):
        kwargs["endSuffix"] = "Ctrl"
        super(Ctrl, self).__init__(*args, **kwargs)
        self.mSystemRoot = False
        self.ctrl = self
        self._prnt_ = None
        # Internal Var
        self.hasGimbalNode = False
        self.ctrlShape = "Ball"
        self.hasParentMaster = False
        self.mirrorData = {'side': self.mirrorSide, 'slot': 1}

    def build(self):
        # Create the xtra grp
        self.xtra = MetaRig(part=self.part, side=self.side, endSuffix="Xtra")
        # self.addSupportNode(self.xtra, "Xtra")

        # Create the control
        self.prnt = MetaRig(part=self.part, side=self.side, endSuffix="Prnt")
        # self.addSupportNode(self.prnt, "Prnt")

        tempCtrlShape = utils.build_ctrl_shape(self.ctrlShape)
        # tempCtrlShape = pm.circle(ch=0)[0]
        libUtilities.transfer_shape(tempCtrlShape, self.mNode)
        self.pynode.getShape().rename("%sShape" % self.shortName())

        pm.delete(tempCtrlShape)

        # Parent the ctrl to the xtra
        # self.pynode.unlock()
        self.pynode.setParent(self.xtra.mNode)

        # Parent the xtra to ctrl
        self.xtra.pynode.setParent(self.prnt.mNode)
        # lock and hide the visibility attributes
        for node in [self.pynode, self.xtra.pynode, self.prnt.pynode]:
            libUtilities.set_lock_status(node, {"v": True})
            node.v.showInChannelBox(True)
            node.v.showInChannelBox(False)

    def add_parent_master(self):
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

    def add_gimbal_node(self):
        self.gimbal = MetaRig(name=utils.nameMe(self.side, self.part, "Gimbal"), nodeType="transform")
        self.gimbal.part = self.part
        self.gimbal.rigType = "gimbalHelper"
        self.gimbal.pynode.setParent(self.mNode)
        self.hasGimbalNode = True

    def setParent(self, targetSystem):
        # Instead of the node itself, the parent is reparented
        self.prnt.pynode.setParent(targetSystem.mNode)

    def addChild(self, targetNode):
        if self.hasGimbalNode:
            pm.parent(targetNode, self.gimbal.mNode)
        else:
            pm.parent(targetNode, self.ctrl.mNode)

    def setRotateOrder(self, rotateOrder):
        self.rotateOrder = rotateOrder
        self.xtra.rotateOrder = rotateOrder
        self.prnt.rotateOrder = rotateOrder
        if self.hasGimbalNode:
            self.gimbal = rotateOrder
        if self.hasParentMaster:
            self.parentMasterPH.rotateOrder = rotateOrder
            self.parentMasterSN.rotateOrder = rotateOrder

    @property
    def side(self):
        return self.pynode.mirrorSide.get(asString=True)[0]

    @property
    def prnt(self):
        return self.getSupportNode("Prnt")

    @prnt.setter
    def prnt(self, data):
        self.addSupportNode(data, "Prnt")

    @property
    def xtra(self):
        return self.getSupportNode("Xtra")

    @xtra.setter
    def xtra(self, data):
        self.addSupportNode(data, "Xtra")

    @property
    def gimbal(self):
        data = self.getSupportNode("Gimbal")
        if data is not None:
            self.hasGimbalNode = True
        return data

    @gimbal.setter
    def gimbal(self, data):
        self.addSupportNode(data, "Gimbal")
        if data is not None:
            self.hasGimbalNode = True

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


class Anno_Loc(Red9_Meta.MetaClass, MetaEnhanced):
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


# class Joint(PKD_Meta):
#     def __init__(self, *args, **kwargs):
#         if kwargs.has_key("side") and kwargs.has_key("part"):
#             full_name = utils.nameMe(kwargs["side"], kwargs["part"], "Ctrl")
#             super(Joint, self).__init__(name=full_name, nodeType="transform")
#         else:
#             super(Joint, self).__init__(nodeType='joint', *args, **kwargs)


Red9_Meta.registerMClassInheritanceMapping()
Red9_Meta.registerMClassNodeMapping(nodeTypes=['transform', 'camera', 'joint'])

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
    cam = MyCameraMeta()
    # subSystem = SubSystem(side="L", part="Core")
    #
    # mRig = Red9_Meta.MetaRig(name='CharacterRig', nodeType="transform")
    # mRig.connectChild(subSystem, 'Arm')
    # subSystem.setParent(mRig)

    # fkSystem = subSystem.addMetaSubSystem()
    # fkSystem = SubSystem(side="U", part="Arm")
    # fkSystem.setParent(subSystem)
    # subSystem.connectChild(fkSystem, 'FK_System')


    # myCtrl = Ctrl(side="L", part="Hand")
    # myCtrl.build()
    # myCtrl.add_constrain_node()
    # myCtrl.add_parent_master()
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

    # jntSystem = JointSystem(side="U", part="Cora")

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
    # k = Red9_Meta.MetaClass("CharacterRig")
    # pm.newFile(f=1)
