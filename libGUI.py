"""
@package PKD_Tools.libGUI
 This package contains all the GUI
 """

from functools import partial

import pymel.core as pm

if __name__ == '__main__':
    localPath = r"C:\Users\admin\Documents\maya\scripts\PKD_Tools"
    import sys

    if localPath not in sys.path:
        sys.path.append(localPath)

    localPath = r"H:\maya\scripts\PKD_Tools"
    import sys

    if localPath not in sys.path:
        sys.path.append(localPath)

import libPySide
import libUtilities
import libFile
import libWeights
import libGeo

for module in libWeights, libUtilities, libPySide, libFile, libGeo:
    reload(module)


class TangentSwapper(libPySide.QDockableWindow):
    """A PySide based tangent swapper"""

    def __init__(self):
        super(TangentSwapper, self).__init__()
        # Set the variables
        self.setWindowTitle("Tangent Swapper")
        self.setFixedWidth(250)
        self.init_float_state = True

    def _setup_(self):
        super(TangentSwapper, self)._setup_()
        for tangent in ["step", "linear", "clamped", "spline"]:
            push_button = libPySide.QtGui.QPushButton(tangent.capitalize(), self)
            push_button.clicked.connect(partial(libUtilities.change_tangents, tangent))
            push_button.setFixedWidth(230)
            self.main_layout.addWidget(push_button)
        self.main_layout.addStretch(False)


class ManagerGUI(libPySide.QDockableWindow):
    """Setup a generic deformer weight import/exporter gui. Add more custom gui object in subclasses"""

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(ManagerGUI, self).__init__()
        # Set the variables
        self.setWindowTitle("Manager GUI")
        self._deformer_ = None
        self.setMinimumWidth(450)
        # self.setFixedHeight(130)
        self.init_float_state = True
        self.weightManagerObj = None

    def _setup_(self):
        super(ManagerGUI, self)._setup_()
        # Text Button
        text_button_layout = libPySide.QtGui.QHBoxLayout()

        self.folder_path_line = libPySide.QLineEdit()
        self.folder_path_line.setText('Get %s Folder' % self.deformer)
        self.folder_button = libPySide.QtGui.QPushButton("Folder")
        text_button_layout.addWidget(self.folder_path_line)
        text_button_layout.addWidget(self.folder_button)

        # Export/Import button
        self.io_button_layout = libPySide.QtGui.QHBoxLayout()
        self.export_button = libPySide.QtGui.QPushButton("Export")
        self.import_button = libPySide.QtGui.QPushButton("Import")
        self.io_button_layout.addWidget(self.export_button)
        self.io_button_layout.addWidget(self.import_button)

        self.main_layout.addLayout(text_button_layout)
        self.main_layout.addWidget(libPySide.horizontal_divider())
        self.main_layout.addLayout(self.io_button_layout)

        self.main_layout.addStretch(False)

    def _connect_signals_(self):
        self.folder_button.clicked.connect(self._get_folder_)
        self.export_button.clicked.connect(self._export_data_)
        self.import_button.clicked.connect(self._import_data_)

    def _get_folder_(self):
        select_directory = libPySide.QtGui.QFileDialog.getExistingDirectory(dir=pm.workspace.path)
        if select_directory:
            self.folder_path_line.setText(select_directory)

    # @endcond

    def _do_scene_qc_(self):
        """Do a scene QC"""
        pass

    def _export_data_(self):
        """Export the weights"""

        self._check_user_input_path_()
        self.weightManagerObj = self._initialise_manager_class_()
        self.weightManagerObj.current_mode = "Export"
        if self.weightManagerObj.targets:
            self._initialise_progress_win_("Export")
            self.weightManagerObj.export_all()
        else:
            nothing_selected_box()

    def _import_data_(self):
        """Import the weights"""
        self._check_user_input_path_()
        if libFile.exists(self.infoPath):
            self.weightManagerObj = self._initialise_manager_class_()
            self.weightManagerObj.current_mode = "Import"
            self._initialise_progress_win_("Import")
            self.weightManagerObj.import_all()
        else:
            noFileBox = libPySide.QCriticalBox()
            noFileBox.setText("No exported data found")
            noFileBox.setWindowTitle("Export Data Error")
            noFileBox.setDetailedText(
                "No %sInfo Xml file found. The path should be %s" % (self.deformer, self.infoPath))
            noFileBox.exec_()
            pm.error("No %sInfo Xml file found" % self.deformer)

    def _initialise_manager_class_(self):
        """initialse the weight manager class and set the info file"""
        weightManager = self.weightManager()
        weightManager.info_file = self.infoPath
        weightManager.command_mode = True
        return weightManager

    def _check_user_input_path_(self):
        """Do a QC on the user defined path"""
        current_path = self.folder_path_line.text().strip()
        if not libFile.exists(current_path):
            noFileBox = libPySide.QCriticalBox()
            noFileBox.setText("Path does not exists")
            noFileBox.setWindowTitle("File Error")
            noFileBox.setDetailedText("The following path does not exists on disk:\n%s" % current_path)
            noFileBox.exec_()
            pm.error("The following path does not exists on disk:\n%s" % current_path)

    def _initialise_progress_win_(self, mode):
        """initialse the progress window"""
        progress_tracker = libPySide.QProgressDialog()
        self.weightManagerObj.progress_tracker = progress_tracker
        progress_tracker.setWindowModality(libPySide.QtCore.Qt.WindowModal)
        progress_tracker.setMaximum(len(self.weightManagerObj.targets))
        progress_tracker.setWindowTitle(("%sing %s Weights" % (mode, self.deformer)))
        progress_tracker.currentProcess = ("%sing" % mode)
        progress_tracker.show()

    @property
    def infoPath(self):
        """Return the @ref libWeights.Weights.data "data" file which exists in the user defined folder"""
        infoPath = libFile.join(self.folder_path_line.text().strip(), "%sInfo.xml" % self.deformer)
        return libFile.linux_path(infoPath)

    @property
    def deformer(self):
        """Return the current deformer of weight manager class as camelCase string"""
        if self._deformer_ is None:
            deformer_type = self.weightManager().deformer
            # Make the camelCase string
            self._deformer_ = deformer_type[0].upper() + deformer_type[1:]
        return self._deformer_

    @property
    def weightManager(self):
        """The property that sets the default @ref libWeights.WeightManager "WeightManager" that is relevant to the Gui"""
        return libWeights.WeightManager


class SkinManagerGUI(ManagerGUI):
    """
    Setup the Skin Import/Exporter Gui
    @code
    import libGUI
    gui = libGUI.SkinManagerGUI()
    gui.show()
    @endcode
    """
    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(SkinManagerGUI, self).__init__()
        self.setWindowTitle("Skin Cluster Manager")

    @property
    def weightManager(self):
        """Return the default the skin weight manager
        @remark
        The property ManagerGUI.weightManager is overwritten in this class
        """
        return libWeights.SkinWeightManager
        # @endcond


class ClusterManagerGUI(ManagerGUI):
    """
    Setup the Skin Import/Exporter Gui
    @code
    import libGUI
    gui = libGUI.ClusterManagerGUI()
    gui.show()
    @endcode
    """
    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(ClusterManagerGUI, self).__init__()
        self.setWindowTitle("Cluster Manager")

    @property
    def weightManager(self):
        """Return the default the skin weight manager
        @remark
        The property ManagerGUI.weightManager is overwritten in this class
        """
        return libWeights.ClusterWeightManager

        # @endcond
        #
        # @property
        # def infoPath(self):
        #     """Return the user defined folder"""
        #     return libFile.linux_path(self.folder_path_line.text())


class BlendshapeManagerGUI(ManagerGUI):
    """
    Setup the Skin Import/Exporter Gui
    @code
    import libGUI
    gui = libGUI.BlendshapeManagerGUI()
    gui.show()
    @endcode
    """
    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(BlendshapeManagerGUI, self).__init__()
        self.setWindowTitle("Blendshape Manager")

    @property
    def weightManager(self):
        """Return the default the skin weight manager
        @remark
        The property ManagerGUI.weightManager is overwritten in this class
        """
        return libWeights.BlendsWeightManager
        # @endcond


class ObjManagerGUI(ManagerGUI):
    """
    Bonus tool for exporting out the selected geometery as obj to a single destination folder. The name of the geometery is used as file name.
    Setup the Obj Exporter
    @code
    import libGUI
    gui = libGUI.ObjExportGUI()
    gui.show()
    @endcode
    """


    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(ObjManagerGUI, self).__init__()
        self.setWindowTitle("Obj Manager")
        self.objManager = None

    def _setup_(self):
        super(ObjManagerGUI, self)._setup_()
        # Add the heirachy checker

        self.main_layout.insertWidget(1, libPySide.horizontal_divider())
        self.scene_check_button = libPySide.QtGui.QPushButton("Check Scene")
        self.main_layout.insertWidget(1, self.scene_check_button)

        # Add Cleanse button
        self.cleanse_button = libPySide.QtGui.QPushButton("Cleanse")
        self.io_button_layout.addWidget(self.cleanse_button)

    def _connect_signals_(self):
        super(ObjManagerGUI, self)._connect_signals_()
        self.cleanse_button.clicked.connect(self._cleanse_geo_)
        self.scene_check_button.clicked.connect(self._check_scene_)

    # @endcond

    def _check_scene_(self):
        # Get the errors
        topNode = libGeo.get_top_node()

        warnWindow = libPySide.QWarningBox()

        if not topNode:
            warnWindow.setText("No top group found")
            warnWindow.setWindowTitle("Missing Top Group")
            warnWindow.exec_()
            return
        else:
            # Check that there is only top node in the scene
            if libGeo.multiple_top_nodes_exists():
                warnWindow.setText("Multiple top groups found")
                warnWindow.setWindowTitle("Multiple Top Groups")
                detailed = """There are multiple top groups in the scene. The tool would perform better if you merge the groups.
Otherwise this tool would work on the first top group which is determined by Maya."""
                warnWindow.setDetailedText(detailed)
                warnWindow.exec_()
                return

            errorInfo = libGeo.find_heirachy_errors(topNode)
            detailed_text = ""

            if errorInfo["Namespace Transform"]:
                warnWindow.setText("Namespace transform found")
                warnWindow.setWindowTitle("Namespace Error")
                detailed = "The following transforms have namespace in them\n\n"
                for namespace in errorInfo["Namespace Transform"]:
                    detailed += "select -add %s;\n" % namespace.name()
                warnWindow.setDetailedText(detailed)
                warnWindow.exec_()
                return

            if errorInfo["Duplicate Transform"]:
                warnWindow.setText("Duplicate transform found")
                warnWindow.setWindowTitle("Duplicate Transform Error")
                detailed = "The following transforms are duplicated\n\n"
                for duplicate in errorInfo["Duplicate Transform"]:
                    detailed += "select -add %s;\n" % duplicate.name()
                warnWindow.setDetailedText(detailed)
                warnWindow.exec_()
                return

            if errorInfo["Duplicate Shapes"]:
                warnWindow.setText("Duplicate Shapes")
                warnWindow.setWindowTitle("Duplicate Shapes Error")
                detailed = "The following shapes are duplicated however they seem to appear to come under different parent name\n\n"
                for duplicate in errorInfo["Duplicate Shapes"]:
                    detailed += "select -add %s;\n" % duplicate.name()
                detailed += '\n\nThis tool can attempt to fix the problem. Run the scene checker again to see if problem is resolved'
                fixButton = libPySide.QtGui.QPushButton("Attempt Fix")
                abortButton = libPySide.QtGui.QPushButton("Abort")
                warnWindow.addButton(abortButton, libPySide.QtGui.QMessageBox.NoRole)
                warnWindow.addButton(fixButton, libPySide.QtGui.QMessageBox.YesRole)
                warnWindow.setDetailedText(detailed)
                ret = warnWindow.exec_()
                if ret:
                    libGeo.fix_duplicates_shapes(errorInfo["Duplicate Shapes"])
                return

            if errorInfo["Incorrect Shape Names"]:
                warnWindow.setText("Incorrect Shape Names")
                warnWindow.setWindowTitle("Incorrect Shape Names Error")
                detailed = '''The following names of the shapes do not follow maya's "[parentName]Shape naming convention"\n\n'''
                for duplicate in errorInfo["Duplicate Shapes"]:
                    detailed += "select -add %s;\n" % duplicate.name()
                detailed += '\n\nThis tool can attempt to fix the problem. Run the scene checker again to see if problem is resolved'
                warnWindow.addButton("Abort", libPySide.QtGui.QMessageBox.NoRole)
                warnWindow.addButton("Attempt Fix", libPySide.QtGui.QMessageBox.YesRole)
                warnWindow.setDetailedText(detailed)
                ret = warnWindow.exec_()
                if ret:
                    libGeo.fix_duplicates_shapes(errorInfo["Incorrect Shape Names"])
                return

            if errorInfo["History Geos"]:
                warnWindow.setText("Geo with history")
                warnWindow.setWindowTitle("Geo History Error")
                detailed = '''The following object may have construction history on them. This may not be issue as sometime maya thinks that shader assignement is construction history. However be careful if you have any deformers such blendshapes, as these will be baked during export process\n\n'''
                for historyGeo in errorInfo["History Geos"]:
                    detailed += "select -add %s;\n" % historyGeo.name()
                warnWindow.setDetailedText(detailed)
                warnWindow.addButton("Ignore", libPySide.QtGui.QMessageBox.NoRole)
                warnWindow.addButton("Ok", libPySide.QtGui.QMessageBox.YesRole)
                ret = warnWindow.exec_()
                if ret:
                    return

        # Give the all clear
        congratsWin = libPySide.QMessageBox()
        congratsWin.setText("Everything is good to go.")
        congratsWin.setWindowTitle("All Clear")
        congratsWin.exec_()

    def _cleanse_geo_(self):
        self.objManager = self._initialise_manager_class_()
        self.objManager.cleansing_mode = True
        self._initialise_progress_win_("Export")
        self.objManager.export_all()
        self.objManager.setup_cleanse_scene()
        self._initialise_progress_win_("Import")
        self.objManager.import_all()

    def _export_data_(self):
        """Export the weights"""
        self._check_user_input_path_()
        self.objManager = self._initialise_manager_class_()
        self._initialise_progress_win_("Export")
        self.objManager.export_all()

    def _import_data_(self):
        """Import the weights"""
        self._check_user_input_path_()
        self.objManager = self._initialise_manager_class_()
        self.objManager.info_file = self.infoPath

        # Error out if no information is found
        if not (libFile.exists(self.objManager.geoListPath) and libFile.exists(self.objManager.datapath)):
            noFileBox = libPySide.QCriticalBox()
            noFileBox.setText("No exported data found")
            noFileBox.setWindowTitle("Export Data Error")
            noFileBox.setDetailedText("No export obj data found at \n%s" % self.infoPath)
            noFileBox.exec_()
            pm.error("No export obj data found at \n%s" % self.infoPath)

        self._initialise_progress_win_("Import")
        self.objManager.import_all()

    def _initialise_manager_class_(self):
        """initialse the weight manager class and set the info file"""
        self.objManager = libGeo.ObjManager()
        if libFile.exists(self.infoPath):
            self.objManager.export_dir = self.infoPath
        return self.objManager

    def _initialise_progress_win_(self, mode):
        """initialse the progress window"""
        progress_tracker = libPySide.QProgressDialog()
        self.objManager.progress_tracker = progress_tracker
        self.objManager.current_mode = mode
        progress_tracker.setWindowModality(libPySide.QtCore.Qt.WindowModal)
        progress_tracker.setMaximum(len(self.objManager.geo_list))
        progress_tracker.setWindowTitle(("%sing Objs" % mode))
        progress_tracker.currentProcess = ("%sing" % mode)
        progress_tracker.show()

    @property
    def infoPath(self):
        """Return the @ref libWeights.Weights.data "data" file which exists in the user defined folder"""
        return self.folder_path_line.text().strip()

    @property
    def deformer(self):
        """Return value for the initial text"""
        return "Obj"


def nothing_selected_box():
    """Bring the error message in case nothing is selected"""
    msgBox = libPySide.QCriticalBox()
    msgBox.setText("Nothing is Selected")
    msgBox.setWindowTitle("User Error")
    msgBox.exec_()


def confirm_box(title, message, detailedMessage=""):
    """A Simple Yes No Dialog"""
    msgBox = libPySide.QQuestionBox()
    msgBox.setText(message)
    msgBox.setWindowTitle(title)
    msgBox.setStandardButtons(libPySide.QtGui.QMessageBox.No | libPySide.QtGui.QMessageBox.Yes)
    msgBox.setDefaultButton(libPySide.QtGui.QMessageBox.No)
    if detailedMessage:
        msgBox.setDetailedText(detailedMessage)
    ret = msgBox.exec_()
    if ret == libPySide.QtGui.QMessageBox.Yes:
        return True
    else:
        return False


if __name__ == '__main__':
    win = ObjManagerGUI()
    win.show()

    # ProgressGroupBox = libPySide.QGroupBox()
    # ProgressGroupBox.setAlignment(libPySide.QtCore.Qt.AlignHCenter)
    # progress = libPySide.QtGui.QProgressBar()
    #
    # progress.setMinimum(0)
    # progress.setMaximum(100)
    # progress.setFormat("Exporting: %p%")
    # ProgressGroupBox.form.addWidget(progress)
    # win.main_layout.addWidget(ProgressGroupBox )

    # for i in range(0,103):
    #     progress.setValue(i)
    #     time.sleep(.3)
    #
    # progress.reset()
