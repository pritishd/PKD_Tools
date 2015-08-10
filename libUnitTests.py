"""
@package PKD_Tools.libUnitTests
@brief Unit tests setup
@details Unit tests for various modules
"""
import sys

try:
    import pymel.core as pm

    print "Initialising Maya"
except:
    print "Not A Maya Environment"

import unittest
from PKD_Tools import libFile


class Droid(object):
    """This simulates an artist interacting with maya or a script doing job"""

    def test_activity(self):
        print "Load Test"


class UnitTestCase(unittest.TestCase):
    """Base Class For All Unit Test. If you need to test a variable you need to make it attribute
    for this class and initialise it from the kwargs
    """

    def __init__(self, testName, **kwargs):

        super(UnitTestCase, self).__init__(testName)
        self.unitTestId = "Base Unit Test Case"
        if kwargs.has_key("targetNode"):
            self.targetNode = kwargs["targetNode"]
        if kwargs.has_key("variable_name"):
            self.variable_name = kwargs["variable_name"]

    def example_test_success_case(self):
        test_condition = (1 == 1)
        self.assertEqual(test_condition, True, "Successful test case")

    def example_test_fail_case(self):
        test_condition = (1 == 0)
        self.assertEqual(test_condition, True, "Failed test case.")

    def example_test_not_equal(self):
        self.assertNotEqual(1, 1, "Not equal test. This should fail")

    def example_test_true(self):
        name = "Pritish"

        self.assertTrue("Pritish", name)

    def variable_is_not_none(self):
        variable = eval("self.targetNode.%s" % self.variable_name)
        self.assertNotEqual(variable, None, "Testing that variable %s is not None" % self.variable_name)


    def runTest(self):
        pass


class BatchTest(object):
    """Base batch example"""

    def __init__(self):
        """Initialise variables"""
        self.droid = Droid()
        self.suite = None
        self.logFile = r'D:\TEMP\UnitTest.log'
        # Delete the Log File
        if libFile.exists(self.logFile):
            try:
                libFile.remove(self.logFile)
            except:
                print "Exception: ", str(sys.exc_info())

    def addTest(self, testName, **kwargs):
        # Generalised function to add a test to a suite
        self.suite.addTest(UnitTestCase(testName, **kwargs))

    def batch_test(self):
        self.droid.test_activity()
        # Setup a batch test suite
        self.suite = unittest.TestSuite()
        for test in ["example_test_success_case",
                     "example_test_fail_case",
                     "example_test_not_equal",
                     "example_test_true"]:
            self.addTest(test)
        self.run_test("Testing a bunch of scenarios")

    def run_test(self, title=None):
        # Run Console Test
        if title:
            print "SUITE:" + title
        unittest.TextTestRunner().run(self.suite)
        # Log the Result
        f = open(self.logFile, "a")
        if title:
            f.write('\n' + title)
        unittest.TextTestRunner(f).run(self.suite)


if __name__ == '__main__':
    unittest.main()
    # print "Generalised Tests"
    # unit = BatchTest()
    # unit.batch_test()
