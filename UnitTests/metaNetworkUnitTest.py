__author__ = 'admin'
import pymel.core as pm

from PKD_Tools import libUnitTests
from PKD_Tools.Red9 import Red9_Meta
from PKD_Tools.Rigging import core

for module in [libUnitTests, Red9_Meta, core]:
    reload(module)


class Droid(object):
    """This simulates an artist interacting with maya or a script doing job"""

    def __init__(self):
        super(Droid, self).__init__()
        self.masterRig = None
        self.metaNode = None
        self.saved_file = None
        self.myCtrl = None
        self.mRig = None

    def new_file(self):
        pm.newFile(f=1)

    def create_simple_ctrl_meta_network(self):
        self.new_file()
        subSystem = core.SubSystem(side="U", part="Core")
        self.mRig = Red9_Meta.MetaRig(name='CharacterRig', nodeType="transform")
        self.mRig.connectChild(subSystem, 'Arm')
        subSystem.setParent(self.mRig)

        fkSystem = core.SubSystem(side="U", part="FK")

        fkSystem.setParent(subSystem)
        subSystem.connectChild(fkSystem, 'FK_System')

        self.myCtrl = core.Ctrl(side="U", part="FK0")
        self.myCtrl.setParent(fkSystem)

    def reinitialise_meta_network(self):
        from PKD_Tools.Red9 import Red9_Meta
        reload(Red9_Meta)

        from PKD_Tools.Rigging import core
        reload(core)

        self.mRig = Red9_Meta.MetaClass("CharacterRig")

    def save_file(self):
        self.saved_file = pm.saveAs(r"C:\temp\testMeta.ma")

    def open_file(self):
        pm.openFile(r"C:\temp\testMeta.ma")


class BatchTest(libUnitTests.BatchTest):
    """Base batch example"""

    def __init__(self):
        super(BatchTest, self).__init__()
        self.droid = Droid()

    def test_meta_open_close(self):
        self.droid.create_simple_ctrl_meta_network()


if __name__ == '__main__':
    print "Generalised Tests"
    unit = BatchTest()
    unit.batch_test()
