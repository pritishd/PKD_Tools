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

    @property
    def pynode(self):
        import pymel.core as pm
        return pm.PyNode(self.mNode)


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

        # debugMode
        self.debugMode = False

    def __bindData__(self, *args, **kwgs):
        # ensure these are added by default
        self.addAttr("part", "")
        self.addAttr('mirrorSide', enumName='Centre:Left:Right:Unique',
                     attrType='enum', hidden=True)
        self.addAttr('rigType', '')

    def setParent(self, targetSystem):
        self.pynode.setParent(targetSystem.mNode)

    def convertToComponent(self, component="FK"):
        componentName = "%s_%s" % (component, self.part)
        self.pynode.rename(self.shortName().replace(self.part, componentName))
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

    def _relink_meta_internal_variables_(self, internalVariableName):
        # Check that there is connection
        if self.__dict__[internalVariableName] is None:
            # Look for the connection
            nodeAttrName = "SUP_%s" % libUtilities.capitalize(internalVariableName.replace("_", ""))
            if self.hasAttr(nodeAttrName):
                # Initialise the parent class
                self.__dict__[internalVariableName] = eval("self.%s" % nodeAttrName)
            elif self.debugMode:
                libUtilities.pyLog.info("%s not found on %s" % (nodeAttrName, self.mNode))

        # Ensure that internal variable are always meta classes
        if type(self.__dict__[internalVariableName]) == list:
            self.__dict__[internalVariableName] = MetaRig(self.__dict__[internalVariableName][0])
        return self.__dict__[internalVariableName]

    def _set_initialise_internal_(self, internalVariableName, data):
        try:
            assert isinstance(data, Red9_Meta.MetaClass)
            self.__dict__[internalVariableName] = data
        except:
            raise Exception("Input must be MetaClass")


class SubSystem(MetaRig):
    """This is a base system. """

    def setParent(self, targetSystem):
        self.pynode.setParent(targetSystem.mNode)

    def __bindData__(self, *args, **kwgs):
        super(SubSystem, self).__bindData__(*args, **kwgs)
        self.addAttr('systemType', "")

    def addMetaSubSystem(self, system="FK", **kwargs):
        # Add subgroup
        subSystem = SubSystem(side=self.side, part=self.part, **kwargs)
        subSystem.setParent(self)
        self.connectChild(subSystem, "%s_System" % system)
        subSystem.systemType = system
        return subSystem


class JointSystem(MetaRig):
    def __init__(self, *args, **kwargs):
        kwargs["nodeType"] = "network"
        kwargs["endSuffix"] = "Sys"
        super(JointSystem, self).__init__(*args, **kwargs)

    def addJoints(self, joints):
        joints = libUtilities.stringList(joints)
        joints.reverse()
        self.connectChildren(libUtilities.stringList(joints), "Joints")

    def setParent(self, targetSystem):
        pm.PyNode(self.Joints[0]).setParent(targetSystem.mNode)

    def setRotateOrder(self, rotateOrder):
        for joint in self.Joints:
            pm.PyNode(joint).rotateOrder.set(rotateOrder)


class Ctrl(MetaRig):
    """This is a base control System"""

    def __init__(self, *args, **kwargs):
        kwargs["endSuffix"] = "Ctrl"
        super(Ctrl, self).__init__(*args, **kwargs)
        self.mSystemRoot = False
        self.ctrl = self
        self._prnt_ = None
        # Internal Var
        self._xtra_ = None
        self._side_ = None
        self._gimbal_ = None
        self._parentMasterPH_ = None
        self._parentMasterSN_ = None
        self.hasGimbalNode = False
        self.ctrlShape = "Ball"
        self.hasParentMaster = False

    def create_ctrl(self):
        # Create the xtra grp
        self.xtra = MetaRig(part=self.part, side=self.side, endSuffix="Xtra")
        self.addSupportNode(self.xtra, "Xtra")

        # Create the control
        self.prnt = MetaRig(part=self.part, side=self.side, endSuffix="Prnt")
        self.addSupportNode(self.prnt, "Prnt")

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
        # Add support node
        self.addSupportNode(self.parentMasterSN, "ParentMasterSN")
        self.addSupportNode(self.parentMasterPH, "ParentMasterPH")

    def add_constrain_node(self):
        self.gimbal = MetaRig(name=utils.nameMe(self.side, self.part, "Gimbal"), nodeType="transform")
        self.gimbal.rigType = "constrain"
        self.gimbal.pynode.setParent(self.mNode)
        self.hasGimbalNode = True
        self.addSupportNode(self.gimbal, "Gimbal")

    def setParent(self, targetSystem):
        # print isinstance (targetSystem, Red9_Meta.MetaClass)
        self.prnt.pynode.setParent(targetSystem.mNode)

    @property
    def side(self):
        return self.pynode.mirrorSide.get(asString=True)[0]

    @property
    def prnt(self):
        return self._relink_meta_internal_variables_("_prnt_")

    @prnt.setter
    def prnt(self, data):
        self._set_initialise_internal_("_prnt_", data)

    @property
    def xtra(self):
        return self._relink_meta_internal_variables_("_xtra_")

    @xtra.setter
    def xtra(self, data):
        self._set_initialise_internal_("_xtra_", data)

    @property
    def gimbal(self):
        return self._relink_meta_internal_variables_("_gimbal_")

    @gimbal.setter
    def gimbal(self, data):
        data = self._set_initialise_internal_("_gimbal_", data)
        if data is not None:
            self.hasGimbalNode = True

    @property
    def parentMasterPH(self):
        data = self._relink_meta_internal_variables_("_parentMasterPH_")
        if data is not None:
            self.hasParentMaster = True
        return data

    @parentMasterPH.setter
    def parentMasterPH(self, data):
        self._set_initialise_internal_("_parentMasterPH_", data)

    @property
    def parentMasterSN(self):
        return self._relink_meta_internal_variables_("_parentMasterSN_")

    @parentMasterSN.setter
    def parentMasterSN(self, data):
        self._set_initialise_internal_("_parentMasterSN_", data)


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
    # cam = MyCameraMeta()
    subSystem = SubSystem(side="L", part="Core")

    mRig = Red9_Meta.MetaRig(name='CharacterRig', nodeType="transform")
    mRig.connectChild(subSystem, 'Arm')
    subSystem.setParent(mRig)

    fkSystem = subSystem.addMetaSubSystem()
    # fkSystem = SubSystem(side="U", part="Arm")
    # fkSystem.setParent(subSystem)
    # subSystem.connectChild(fkSystem, 'FK_System')


    myCtrl = Ctrl(side="L", part="Hand")
    myCtrl.create_ctrl()
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
