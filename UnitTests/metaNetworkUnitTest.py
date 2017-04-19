"""
@package UnitTests.metaNetworkUnitTest
@brief Testing for meta node functionalitis
@details Here we are testing that all the a meta network is created and saved. Once you have reopened the file you should be recall most of the data.
"""
import pymel.core as pm

from PKD_Tools import libUnitTests
from PKD_Tools.Red9 import Red9_Meta
from PKD_Tools.Rigging import core
from PKD_Tools.Rigging import limb

if __name__ == '__main__':

    for module in [libUnitTests, core, limb]:
        reload(module)


class UnitTestCase(libUnitTests.UnitTestCase):
    """Base Class For All Unit Test."""

    def __init__(self, testName, **kwargs):
        super(UnitTestCase, self).__init__(testName, **kwargs)

    def test_meta_inheritance(self):
        """Test Inheritence of meta classes"""
        self.assertTrue(isinstance(self.targetNode, Red9_Meta.MetaClass), "Checking Inheritance from Red9 meta")

    def is_sub_component(self):
        """Test Inheritence of meta classes"""
        self.assertTrue(self.targetNode.isSubComponent, "Checking if control is subcomponent")

    def is_not_sub_component(self):
        """Test Inheritence of meta classes"""
        self.assertFalse(self.targetNode.Arm.isSubComponent, "Checking that the arm system is not a subcomponent")


class Droid(object):
    """This simulates an artist interacting with maya or a script doing job"""

    def __init__(self):
        super(Droid, self).__init__()
        self.masterRig = None
        self.metaNode = None
        self.saved_file = None
        self.myCtrl = None
        self.mRig = None

    def create_simple_ctrl_meta_network(self):
        pm.newFile(f=1)
        subSystem = core.TransSubSystem(side="C", part="Core")
        self.mRig = Red9_Meta.MetaRig(name='CharacterRig', nodeType="transform")
        self.mRig.connectChild(subSystem, 'Arm')
        subSystem.setParent(self.mRig)

        fkSystem = core.TransSubSystem(side="C", part="Core")
        subSystem.addMetaSubSystem(fkSystem,"FK")
        self.myCtrl = core.Ctrl(side="C", part="Core")
        self.myCtrl.build()
        self.myCtrl.setParent(fkSystem)
        self.myCtrl.debugMode = True

        fkCtrls = [self.myCtrl]
        fkSystem.connectChildren(fkCtrls, "Ctrl")
        fkSystem.convertSystemToSubSystem("FK")

    def reinitialise_meta_network(self):
        self.save_file()
        pm.newFile(f=1)
        self.open_file()
        from PKD_Tools.Red9 import Red9_Meta
        reload(Red9_Meta)

        from PKD_Tools.Rigging import core
        reload(core)

        self.mRig = Red9_Meta.MetaClass("CharacterRig")
        self.myCtrl = Red9_Meta.MetaClass("C_Core_FK_Ctrl")

    def save_file(self):
        self.saved_file = pm.saveAs(r"c:\temp\testMeta.ma")

    def open_file(self):
        pm.openFile(r"c:\temp\testMeta.ma")

    def create_advanced_ctrl_meta_network(self):
        self.create_simple_ctrl_meta_network()
        self.myCtrl.addGimbalMode()
        self.myCtrl.add_parent_master()

class ikDroid(Droid):
    def __init__(self):
        super(ikDroid, self).__init__()
        self.ikSystem = None

    def create_simple_ik(self):
        pm.newFile(f=1)
        self.ikSystem = limb.Arm(side="C", part="Core")
        self.ikSystem.testBuild()

    def reinitialise_meta_network(self):
        self.save_file()
        pm.newFile(f=1)
        self.open_file()
        self.ikSystem = Red9_Meta.MetaClass("C_Core_Grp")


class BatchTest(libUnitTests.BatchTest):
    """Base batch example"""

    def __init__(self):
        super(BatchTest, self).__init__()
        self.droid = None

    def addTest(self, testName, **kwargs):
        # Generalised function to add a test to a suite
        self.suite.addTest(UnitTestCase(testName, **kwargs))

    def test_meta_simple_create(self):
        self.droid = Droid()
        self.droid.create_simple_ctrl_meta_network()
        # Setup a batch test suite
        self.suite = libUnitTests.unittest.TestSuite()
        self.addTest("test_meta_inheritance", targetNode=self.droid.mRig)
        self.addTest("test_meta_inheritance", targetNode=self.droid.myCtrl)
        self.addTest("test_meta_inheritance", targetNode=self.droid.myCtrl, targetClass=core.Ctrl)
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="xtra")
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="prnt")
        self.addTest("is_sub_component", targetNode=self.droid.myCtrl)
        self.addTest("is_not_sub_component", targetNode=self.droid.mRig)
        self.run_test("Testing meta creation")

    def test_meta_reopen(self):
        self.droid = Droid()
        self.droid.reinitialise_meta_network()
        self.suite = libUnitTests.unittest.TestSuite()
        self.addTest("test_meta_inheritance", targetNode=self.droid.mRig)
        self.addTest("test_meta_inheritance", targetNode=self.droid.myCtrl)
        self.addTest("test_meta_inheritance", targetNode=self.droid.myCtrl, targetClass=core.Ctrl)
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="xtra")
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="prnt")
        self.run_test("Testing meta reopen")

    def test_ik_creation(self):
        self.droid = ikDroid()
        self.droid.create_simple_ik()
        self.suite = libUnitTests.unittest.TestSuite()
        self.addTest("test_meta_inheritance", targetNode=self.droid.ikSystem)
        self.addTest("variable_is_not_none", targetNode=self.droid.ikSystem, variable_name="jointSystem")
        self.addTest("variable_is_not_none", targetNode=self.droid.ikSystem, variable_name="ikHandle")
        self.addTest("variable_is_not_none", targetNode=self.droid.ikSystem, variable_name="mainIK")
        self.run_test("Testing IK")

    def test_ik_reopen(self):
        self.droid = ikDroid()
        self.droid.reinitialise_meta_network()
        self.suite = libUnitTests.unittest.TestSuite()
        self.addTest("test_meta_inheritance", targetNode=self.droid.ikSystem)
        self.addTest("variable_is_not_none", targetNode=self.droid.ikSystem, variable_name="jointSystem")
        self.addTest("variable_is_not_none", targetNode=self.droid.ikSystem, variable_name="ikHandle")
        self.addTest("variable_is_not_none", targetNode=self.droid.ikSystem, variable_name="mainIK")
        self.addTest("variable_is_not_none", targetNode=self.droid.ikSystem, variable_name="pv")
        self.run_test("Testing IK reopen")

    def test_meta_advanced_create(self):
        self.droid = Droid()
        self.droid.create_advanced_ctrl_meta_network()
        # Setup a batch test suite
        self.suite = libUnitTests.unittest.TestSuite()
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="parentMasterSN")
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="parentMasterPH")
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="gimbal")
        self.addTest("variable_is_true", targetNode=self.droid.myCtrl, variable_name="hasGimbal")
        self.addTest("variable_is_true", targetNode=self.droid.myCtrl, variable_name="hasParentMaster")
        self.run_test("Testing advanced ctrl creation")

    def test_meta_advanced_reopen(self):
        self.droid = Droid()
        self.droid.reinitialise_meta_network()
        self.suite = libUnitTests.unittest.TestSuite()
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="parentMasterSN")
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="parentMasterPH")
        self.addTest("variable_is_not_none", targetNode=self.droid.myCtrl, variable_name="gimbal")
        self.addTest("variable_is_true", targetNode=self.droid.myCtrl, variable_name="hasGimbal")
        self.addTest("variable_is_true", targetNode=self.droid.myCtrl, variable_name="hasParentMaster")
        self.run_test("Testing advanced ctrl reopen")


unit = BatchTest()
# unit.test_meta_simple_create()
# unit.test_meta_reopen()
# #
# unit.test_meta_advanced_create()
# unit.test_meta_advanced_reopen()
unit.test_ik_creation()
unit.test_ik_reopen()


# if __name__ == '__main__':
#     print "######################"
#     print "Generalised Tests"
#     unit = BatchTest()
#     unit.test_meta_create()
