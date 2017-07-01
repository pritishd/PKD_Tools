"""
@package UnitTests.integrityUnitTest
@brief Testing that all rig type are created without any errors
@details Go through every possible rig and try to create a test build. This will used everytime we make changes to core and Red9 modules
"""
import pymel.core as pm
from PKD_Tools import libUnitTests

from PKD_Tools.Rigging import core
from PKD_Tools.Rigging import limb
from PKD_Tools.Rigging import spine

# if __name__ == '__main__':
#     for module in [libUnitTests, core, limb, spine]:
#         reload(module)
from datetime import datetime


class UnitTestCase(libUnitTests.UnitTestCase):
    """Base Class For All Unit Test."""

    def __init__(self, testName, **kwargs):
        super(UnitTestCase, self).__init__(testName, **kwargs)

    def test_created(self):
        """Test Inheritence of meta classes"""
        self.assertEqual(1, 1, "Completed")


class limbDroid(object):
    def __init__(self):
        super(limbDroid, self).__init__()
        self.ikSystem = None

    def create_ik(self):
        pm.newFile(f=1)
        self.ikSystem = limb.LimbIk(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_simple_ik(self):
        pm.newFile(f=1)
        mainSystem = core.TransSubSystem(side="C", part="Core")
        self.ikSystem = limb.LimbIk(side="C", part="Core")
        mainSystem.addMetaSubSystem(self.ikSystem, "IK")
        # ikSystem.ikControlToWorld = True
        self.ikSystem.testBuild()
        self.ikSystem.convertSystemToSubSystem(self.ikSystem.systemType)

    def create_arm(self):
        pm.newFile(f=1)
        self.ikSystem = limb.Arm(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_arm_hand(self):
        pm.newFile(f=1)
        self.ikSystem = limb.ArmHand(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_arm_foot(self):
        pm.newFile(f=1)
        self.ikSystem = limb.ArmFoot(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_arm_hoof(self):
        pm.newFile(f=1)
        self.ikSystem = limb.ArmHoof(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_arm_paw(self):
        pm.newFile(f=1)
        self.ikSystem = limb.ArmPaw(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_hip(self):
        pm.newFile(f=1)
        self.ikSystem = limb.Hip(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_hip_hand(self):
        pm.newFile(f=1)
        self.ikSystem = limb.HipHand(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_hip_foot(self):
        pm.newFile(f=1)
        self.ikSystem = limb.HipFoot(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_hip_hoof(self):
        pm.newFile(f=1)
        self.ikSystem = limb.HipHoof(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_hip_paw(self):
        pm.newFile(f=1)
        self.ikSystem = limb.HipPaw(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_quad(self):
        pm.newFile(f=1)
        self.ikSystem = limb.Quad(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_quad_hand(self):
        pm.newFile(f=1)
        self.ikSystem = limb.QuadHand(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_quad_foot(self):
        pm.newFile(f=1)
        self.ikSystem = limb.QuadFoot(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_quad_hoof(self):
        pm.newFile(f=1)
        self.ikSystem = limb.QuadHoof(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_quad_paw(self):
        pm.newFile(f=1)
        self.ikSystem = limb.QuadPaw(side="C", part="Core")
        self.ikSystem.testBuild()


class spineDroid(object):
    def create_simple_spine(self):
        pm.newFile(f=1)
        self.ikSystem = spine.SimpleSpine(side="C", part="Core")
        self.ikSystem.testBuild()

    def create_human_spine_position(self):
        pm.newFile(f=1)
        self.ikSystem = spine.HumanSpine(side="C", part="Core")
        self.ikSystem.fallOffMethod = "Position"
        self.ikSystem.testBuild()

    def create_human_spine_distance(self):
        pm.newFile(f=1)
        self.ikSystem = spine.HumanSpine(side="C", part="Core")
        self.ikSystem.fallOffMethod = "Distance"
        self.ikSystem.testBuild()

    def create_complex_spine_position(self):
        pm.newFile(f=1)
        self.ikSystem = spine.ComplexSpine(side="C", part="Core")
        self.ikSystem.fallOffMethod = "Position"
        self.ikSystem.numHighLevelCtrls = 4
        self.ikSystem.testBuild()

    def create_complex_spine_distance(self):
        pm.newFile(f=1)
        self.ikSystem = spine.ComplexSpine(side="C", part="Core")
        self.ikSystem.fallOffMethod = "Distance"
        self.ikSystem.numHighLevelCtrls = 4
        self.ikSystem.testBuild()


class BatchTest(libUnitTests.BatchTest):
    """Base batch example"""

    def __init__(self):
        super(BatchTest, self).__init__()
        self.droid = None

    def addTest(self, testName, **kwargs):
        # Generalised function to add a test to a suite
        self.suite.addTest(UnitTestCase(testName, **kwargs))

    def test_limb_creation(self):
        # Setup a batch test suite
        self.droid = limbDroid()
        start = datetime.now()
        self.droid.create_simple_ik()
        self.suite = libUnitTests.unittest.TestSuite()
        self.addTest("test_created")
        self.run_test("Testing Simple Ik: %s" % str(datetime.now() - start).split(".")[0])

        for limbType in ["arm", "hip", "quad"]:
            for appendage in ["", "hand", "foot", "hoof", "paw"]:
                self.droid = limbDroid()
                start = datetime.now()
                combination = [limbType]
                if appendage:
                    combination.append(appendage)
                exec ("self.droid.create_%s()" % "_".join(combination))
                self.suite = libUnitTests.unittest.TestSuite()
                self.addTest("test_created")
                self.run_test("Testing %s: %s" % (" ".join(combination), str(datetime.now() - start).split(".")[0]))

    def test_spine_creation(self):
        # Simple Spine
        self.droid = spineDroid()
        start = datetime.now()
        self.droid.create_simple_spine()
        self.suite = libUnitTests.unittest.TestSuite()
        self.addTest("test_created")
        self.run_test("Testing Simple Spine: %s" % str(datetime.now() - start).split(".")[0])

        for spineType in ["human", "complex"]:
            for fallOff in ["position", "distance"]:
                self.droid = spineDroid()
                start = datetime.now()
                exec ("self.droid.create_%s_spine_%s()" % (spineType, fallOff))
                self.suite = libUnitTests.unittest.TestSuite()
                self.addTest("test_created")
                self.run_test("Testing %s %s: %s" % (spineType, fallOff, str(datetime.now() - start).split(".")[0]))


unit = BatchTest()
#unit.test_limb_creation()
unit.test_spine_creation()
