__author__ = 'pritish.dogra'

from PKD_Tools.Red9 import Meta

class ctrl(Meta.MetaRig):
    """This is a base control System"""
    def __init__(self,name,side):
        full_name = "%s_%s_Prnt"%(name,side)
        super(ctrl, self).__init__(name = full_name,nodeType = "transform")
        self.mSystemRoot = False
        self.name = name
        self.side = side
        self.prnt = self.pynode
        self.constrainNode = ""
        self.ctrl = ""
        self.xtra = ""

    def __bindData__(self):
        self.addAttr('version',1.0)  # ensure these are added by default
        self.addAttr('rigType', '')  # ensure these are added by default

    def create_ctrl(self):
        pass
        # Create the parent master group
        # Create the xtra grp
        # Create the constrain node
        # Create the control

        # lock and hide the visibility




class anno_loc(Meta.MetaClass):
    """This is a a annoated locator"""
    pass


Meta.registerMClassInheritanceMapping()
Meta.registerMClassNodeMapping(nodeTypes='transform')