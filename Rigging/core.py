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


class PKD_Meta(Red9_Meta.MetaRig):
    def __init__(self, *args, **kws):
        super(PKD_Meta, self).__init__(*args, **kws)
        self.lockState = False
        self.lockState = False

    def __bindData__(self):
        self.addAttr('rigType', '')  # ensure these are added by default
        self.addAttr('mirrorSide', enumName='Centre:Left:Right:Unique',
                     attrType='enum', hidden=True)  # ensure these are added by default


def _add_meta_data_(node, type):
    metaNode = PKD_Meta(node.name())
    metaNode.rigType = type


class SubSystem(Red9_Meta.MetaRigSubSystem):
    """This is a base system. """

    def __init__(self, side=None, name=None, *args, **kws):
        full_name = utils.nameMe(side, name, "Grp")
        if full_name:
            super(SubSystem, self).__init__(name=full_name, nodeType="transform")
            self.side = side
            self.mirrorSide = _fullSide_(self.side)

class Ctrl(PKD_Meta):
    """This is a base control System"""

    def __init__(self, side=None, name=None, *args, **kws):
        full_name = utils.nameMe(side, name, "Ctrl")
        if full_name:
            super(Ctrl, self).__init__(name=full_name, nodeType="transform")
            self.name = name
            self.side = side
            self.constrainNode = None
            self.ctrl = self
            self.prnt = None
            self.xtra = None
            self.ctrlShape = "Ball"
            self.parentMasterSN = None
            self.parentMasterPH = None
            # Set Meta Attr
            self.rigType = "Ctrl"
            self.mirrorSide = _fullSide_(self.side)
            self.mSystemRoot = False

    def create_ctrl(self):
        # Create the xtra grp
        self.xtra = PKD_Meta(name=utils.nameMe(self.side, self.name, "Xtra"), nodeType="transform")
        self.xtra.rigType = "xtra"
        self.xtra.mirrorSide = self.mirrorSide
        self.addSupportNode(self.xtra, "Xtra")

        # Create the control
        self.prnt = PKD_Meta(name=utils.nameMe(self.side, self.name, "Prnt"), nodeType="transform")
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

    def add_constrain_node(self):
        self.constrainNode = PKD_Meta(name=utils.nameMe(self.side, self.name, "Constrain"), nodeType="transform")
        self.constrainNode.rigType = "constrain"
        self.constrainNode.pynode.setParent(self.mNode)



class Anno_Loc(Red9_Meta.MetaClass):
    """This is a a annoated locator"""
    pass


Red9_Meta.registerMClassInheritanceMapping()
Red9_Meta.registerMClassNodeMapping(nodeTypes='transform')

if __name__ == '__main__':
    pm.newFile(f=1)
    subSystem = SubSystem("U", "Core")

    mRig = Red9_Meta.MetaRig(name='CharacterRig')
    mRig.connectChild(subSystem, 'Arm')

    fkSystem = SubSystem("U", "FK")
    subSystem.connectChild(fkSystem, 'FK')

    # lArm = mRig.addMetaSubSystem('Main', 'Unique', nodeName='U_ArmSystem')
    #
    # pm.createNode("transform", name="U_Generic")
    #
    # # print subSystem.mirrorSide
    myCtrl = Ctrl("U", "FK0")
    myCtrl.create_ctrl()
    myCtrl.add_parent_master()
    myCtrl.add_constrain_node()
    # subSystem.addGenericCtrls(myCtrl.ctrl.name())
    # lArm.addRigCtrl(myCtrl.ctrl.name(),'Wrist', mirrorData={'side':'Unique','slot':1,'axis':'translateX,translateY,translateZ'})
    # subSystem.addRigCtrl(myCtrl.ctrl.name(),'FK0', mirrorData={'side':'Unique','slot':1,'axis':'translateX,translateY,translateZ'})

    myCtrl1 = Ctrl("U", "FK1")
    myCtrl1.create_ctrl()
    # myCtrl1.add_parent_master()
    # myCtrl1.add_constrain_node()
    # fkSystem.connectChildren([myCtrl.ctrl.name(), myCtrl1.ctrl.name()],"Ctrl")
    #
    # subSystem.addRigCtrl(myCtrl1.ctrl.name(),'FK1', mirrorData={'side':'Unique','slot':2,'axis':'translateX,translateY,translateZ'})
    #
    #
    #
    #
    #
    # myCtrl.ctrl.select()
