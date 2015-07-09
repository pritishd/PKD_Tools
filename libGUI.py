from functools import partial

import pymel.core as pm

from PKD_Tools import libPySide
from PKD_Tools import libUtilities
from PKD_Tools import libFile
from PKD_Tools import libWeights
from PKD_Tools import libGeo

for module in libUtilities, libPySide, libFile, libGeo:
    reload(module)

reload(libPySide)


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
            push_button.clicked.connect(partial(libUtilities.changeTangents, tangent))
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
        weightManager = self._initialise_manager_class_()
        success = weightManager.export_all()
        if not success:
            nothing_selected_box()

    def _import_data_(self):
        """Import the weights"""
        self._check_user_input_path_()
        if libFile.exists(self.infoPath):
            weightManager = self._initialise_manager_class_()
            weightManager.info_file = self.infoPath
            weightManager.import_all()
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
            noFileBox.setDetailedText("The following path does exists on disk:\n%s" % current_path)
            noFileBox.exec_()
            pm.error("The following path does exists on disk:\n%s" % current_path)

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

    @property
    def infoPath(self):
        """Return the user defined folder"""
        return libFile.linux_path(self.folder_path_line.text())


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


class ObjExportGUI(ManagerGUI):
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
        super(ObjExportGUI, self).__init__()
        self.setWindowTitle("Obj Manager")

    def _setup_(self):
        super(ObjExportGUI, self)._setup_()
        # Add the heirachy checker

        self.main_layout.insertWidget(1, libPySide.horizontal_divider())
        self.scene_check_button = libPySide.QtGui.QPushButton("Check Scene")
        self.main_layout.insertWidget(1, self.scene_check_button)

        # Add Cleanse button
        self.cleanse_button = libPySide.QtGui.QPushButton("Cleanse")
        self.io_button_layout.addWidget(self.cleanse_button)

    def _connect_signals_(self):
        super(ObjExportGUI, self)._connect_signals_()
        self.cleanse_button.clicked.connect(self._cleanse_geo_)
        self.scene_check_button.clicked.connect(self._check_scene_)

    # @endcond

    def _check_scene_(self):
        # Get the errors
        topNode = libGeo.get_top_node()

        warnWindow = libPySide.QWarningBox()

        if not topNode:
            warnWindow.setText("No topnode found")
            warnWindow.setWindowTitle("Missing TopNode")
            warnWindow.exec_()
            return
        else:
            errorInfo = libGeo.find_heirachy_errors(topNode)
            detailed_text = ""

            if errorInfo["Namespace Transform"]:
                warnWindow.setText("Namespace transform found")
                warnWindow.setWindowTitle("Namespace Error")
                detailed = "The following transforms have namespace in them\n\n"
                for namespace in errorInfo["Namespace Transform"]:
                    detailed += "select -r %s;\n" % namespace.name()
                warnWindow.setDetailedText(detailed)
                warnWindow.exec_()
                return
            if errorInfo["Duplicate Transform"]:
                warnWindow.setText("Duplicate transform found")
                warnWindow.setWindowTitle("Duplicate Transform Error")
                detailed = "The following transforms are duplicated\n\n"
                for duplicate in errorInfo["Duplicate Transform"]:
                    detailed += "select -r %s;\n" % duplicate.name()
                warnWindow.setDetailedText(detailed)
                warnWindow.exec_()
                return

            if errorInfo["Duplicate Shapes"]:
                warnWindow.setText("Duplicate Shapes")
                warnWindow.setWindowTitle("Duplicate Shapes Error")
                detailed = "The following shapes are duplicated\n\n"
                for duplicate in errorInfo["Duplicate Shapes"]:
                    detailed += "select -r %s;\n" % duplicate.name()
                warnWindow.setDetailedText(detailed)
                warnWindow.exec_()
                return

            if errorInfo["History Geos"]:
                warnWindow.setText("Geo with history")
                warnWindow.setWindowTitle("Geo History Error")
                detailed = "The following mesh has history on them\n\n"
                for historyGeo in errorInfo["History Geos"]:
                    detailed += "select -r %s;\n" % historyGeo.name()
                warnWindow.setDetailedText(detailed)
                warnWindow.exec_()
                return

        # Give the all clear
        congratWin = libPySide.QMessageBox()
        congratWin.setText("Everything seems ok")
        congratWin.setWindowTitle("All Clear")
        congratWin.exec_()

    def _cleanse_geo_(self):
        objManager = self._initialise_manager_class_()
        objManager.cleansing_mode = True
        objManager.cleanse_geo()

    def _export_data_(self):
        """Export the weights"""
        self._check_user_input_path_()
        objManager = self._initialise_manager_class_()
        objManager.export_all()

    def _import_data_(self):
        """Import the weights"""
        self._check_user_input_path_()

        objManager = self._initialise_manager_class_()
        objManager.info_file = self.infoPath

        # Error out if no information is found
        if not (libFile.exists(objManager.geoListPath) and libFile.exists(objManager.datapath)):
            noFileBox = libPySide.QCriticalBox()
            noFileBox.setText("No exported data found")
            noFileBox.setWindowTitle("Export Data Error")
            noFileBox.setDetailedText("No export obj data found at \n%s" % self.infoPath)
            noFileBox.exec_()
            pm.error("No export obj data found at \n%s" % self.infoPath)

        objManager.import_all()

    def _initialise_manager_class_(self):
        """initialse the weight manager class and set the info file"""
        self.objManager = libGeo.ObjManager()
        if libFile.exists(self.infoPath):
            self.objManager.export_dir = self.infoPath
        return self.objManager

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
    win = ObjExportGUI()
    win.show()
