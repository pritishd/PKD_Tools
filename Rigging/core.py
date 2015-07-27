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

class PKD_MetaClass(Red9_Meta.MetaClass):
    pass

class PKD_Meta(Red9_Meta.MetaRig):
    def __init__(self, *args, **kws):
        super(PKD_Meta, self).__init__(*args, **kws)
        self.lockState = False
        self.lockState = False

    def __bindData__(self):
        self.addAttr('rigType', '')  # ensure these are added by default
        self.addAttr('mirrorSide', enumName='Centre:Left:Right:Unique',
                     attrType='enum', hidden=True)  # ensure these are added by default

    def etParent(self,targetSystem):
        self.pynode.setParent(targetSystem.mNode)



def _add_meta_data_(node, type):
    metaNode = PKD_Meta(node.name())
    metaNode.rigType = type


class SubSystem(Red9_Meta.MetaRigSubSystem):
    """This is a base system. """

    def __init__(self, *args, **kws):
        if kws.has_key("side") and kws.has_key("part"):
            full_name = utils.nameMe(kws["side"], kws["part"], "Grp")
            super(SubSystem, self).__init__(name=full_name, nodeType="transform")
            self.side = kws["side"]
            self.mirrorSide = _fullSide_(self.side)
            self.lockState = False
            self.lockState = False
        else:
            super(SubSystem, self).__init__( *args, **kws)

    def setParent(self,targetSystem):
        self.pynode.setParent(targetSystem.mNode)

class Ctrl(PKD_Meta):
    """This is a base control System"""

    def __init__(self, *args, **kws):
        if kws.has_key("side") and kws.has_key("part"):
            full_name = utils.nameMe(kws["side"], kws["part"], "Ctrl")
            super(Ctrl, self).__init__(name=full_name, nodeType="transform")
            self.part = kws["part"]
            self.side = kws["side"]
            self.ctrl = self
            self.prnt = None
            self.xtra = None
            self.constrainNode = None
            self.hasConstrainNode = False
            self.ctrlShape = "Ball"
            self.parentMasterSN = None
            self.parentMasterPH = None
            self.hasParentMaster = False
            # Set Meta Attr
            self.rigType = "Ctrl"
            self.mirrorSide = _fullSide_(self.side)
            self.mSystemRoot = False
        else:
            super(Ctrl, self).__init__( *args, **kws)


    def __bindData__(self):
        super(Ctrl, self).__bindData__()
        self.addAttr("part","")
        self.attrSetLocked("part",True)



    def create_ctrl(self):
        # Create the xtra grp
        self.xtra = PKD_Meta(name=utils.nameMe(self.side, self.part, "Xtra"), nodeType="transform")
        self.xtra.rigType = "xtra"
        self.xtra.mirrorSide = self.mirrorSide
        self.addSupportNode(self.xtra, "Xtra")

        # Create the control
        self.prnt = PKD_Meta(name=utils.nameMe(self.side, self.part, "Prnt"), nodeType="transform")
        self.prnt.rigType = "xtra"
        self.prnt.mirrorSide = self.mirrorSide
        self.addSupportNode(self.prnt, "Prnt")

        # tempCtrlShape = utils.build_ctrl_shape(self.ctrlShape)
        tempCtrlShape = pm.circle(ch=0)[0]
        libUtilities.transfer_shape(tempCtrlShape, self.mNode)
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
        self.parentMasterSN = PKD_Meta(name="%s_SN" % self.mNodeID, nodeType="transform")
        self.parentMasterSN.rigType = "SN"
        self.parentMasterPH = PKD_Meta(name="%s_PH" % self.mNodeID, nodeType="transform")
        self.parentMasterPH.rigType = "PH"
        # Setup the parenting
        self.pynode.setParent(self.parentMasterSN.mNode)
        self.parentMasterSN.pynode.setParent(self.parentMasterPH.mNode)
        self.parentMasterPH.pynode.setParent(self.xtra.mNode)
        # Set the state of the parent master
        self.hasParentMaster = True

    def add_constrain_node(self):
        self.constrainNode = PKD_Meta(name=utils.nameMe(self.side, self.part, "Constrain"), nodeType="transform")
        self.constrainNode.rigType = "constrain"
        self.constrainNode.pynode.setParent(self.mNode)

        self.hasConstrainNode = True

    def setParent(self,targetSystem):

        # print isinstance (targetSystem, Red9_Meta.MetaClass)
        self.prnt.pynode.setParent(targetSystem.mNode)



class Anno_Loc(Red9_Meta.MetaClass):
    """This is a a annoated locator"""
    pass

class MyCameraMeta(Red9_Meta.MetaClass):
    '''
    Example showing that metaData isn't limited to 'network' nodes,
    by using the 'nodeType' arg in the class __init__ you can modify
    the general behaviour such that meta creates any type of Maya node.
    '''
    def __init__(self,*args,**kws):
        super(MyCameraMeta, self).__init__(nodeType='camera',*args,**kws)

Red9_Meta.registerMClassInheritanceMapping()
Red9_Meta.registerMClassNodeMapping(nodeTypes='transform')
Red9_Meta.registerMClassNodeMapping(nodeTypes='camera')

if __name__ == '__main__':
    pm.newFile(f=1)
    # cam = MyCameraMeta()
    subSystem = SubSystem(side = "U", part = "Core")

    mRig = Red9_Meta.MetaRig(name='CharacterRig',nodeType="transform")
    mRig.connectChild(subSystem, 'Arm')
    subSystem.setParent(mRig)


    fkSystem = SubSystem(side = "U", part = "FK")

    fkSystem.setParent(subSystem)
    subSystem.connectChild(fkSystem, 'FK_System')


    myCtrl = Ctrl(side = "U", part = "FK0")
    myCtrl.create_ctrl()
    myCtrl.add_parent_master()
    myCtrl.add_constrain_node()
    myCtrl.setParent(fkSystem)

    myCtrl1 = Ctrl(side ="U", part = "FK1")
    myCtrl1.create_ctrl()

    myCtrl1.setParent(fkSystem)

    fkCtrls = [myCtrl.mNode, myCtrl1.mNode]
    fkSystem.connectChildren(fkCtrls,"Ctrl")
    subSystem.connectChildren(fkCtrls,"FK")


