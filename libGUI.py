# This scripts creates an empty PySide custom window in Maya
# To run the script you need to have built Shiboken and PySide
# Following documentation on best practice for Pyside in maya
# http://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2015/ENU/Maya-SDK/files/GUID-66ADA1FF-3E0F-469C-84C7-74CEB36D42EC-htm.html

from shiboken import wrapInstance
from functools import partial

import PySide.QtCore as QtCore
import PySide.QtGui as QtGui
import maya.OpenMayaUI as OpenMayaUI
from maya import cmds

from pymel.internal.plogging import pymelLogger as pyLog

from PKD_Tools import libFile
from PKD_Tools import libUtilities
for module in libFile, libUtilities,libWeights:
    reload(module)

# abcIcon = "//file04/Repository/maya/2015/mds/general/icons/abc.png"
# abcIcon = r"C:/Users/admin/Documents/maya/scripts/AdvancedSkeleton4Files/icons/AS4.png"


AppIcon = libFile.join(libFile.current_working_directory(), r"Icons/WinIcon.png")
AppLabel = libFile.join(libFile.current_working_directory(), r"Icons/WinLabel.png")


def getMayaMainWindow():
    """
    This is a function that is run from your class object to get a handle
    to the main Maya window, it uses a combination of the Maya API as well as the SIP module

    @return QtGui.QMainWindow of the opened maya applications
    """
    accessMainWindow = OpenMayaUI.MQtUtil.mainWindow()
    return wrapInstance(long(accessMainWindow), QtGui.QMainWindow)


class QMessageBox(QtGui.QMessageBox):
    """
    Convenience class method for the message boxes which comes with PKD Icon and ideal settings for resizing the GUI
    """

    def __init__(self):
        super(QMessageBox, self).__init__(parent=getMayaMainWindow())
        icon = QtGui.QIcon(AppIcon)
        self.setWindowIcon(icon)
        self.setSizeGripEnabled(True)

    def event(self, e):
        """
        Made the window resizable
        """
        result = QtGui.QMessageBox.event(self, e)

        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

        textEdit = self.findChild(QtGui.QTextEdit)
        if textEdit != None:
            textEdit.setMinimumHeight(0)
            textEdit.setMaximumHeight(16777215)
            textEdit.setMinimumWidth(0)
            textEdit.setMaximumWidth(16777215)
            textEdit.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

        return result


class QCriticalBox(QMessageBox):
    """
    Convenience class for a messagebox with QCritical icon
    """

    def __init__(self):
        super(QCriticalBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Critical)


class QWarningBox(QMessageBox):
    """
    Convenience class for a messagebox with QWarning icon
    """

    def __init__(self):
        super(QWarningBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Warning)


class QQuestionBox(QMessageBox):
    """
    Convenience class for a messagebox with QQuestion icon
    """

    def __init__(self):
        super(QQuestionBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Question)


class QInformationBox(QMessageBox):
    """
    Convenience class for a messagebox with QInformation icon
    """

    def __init__(self):
        super(QInformationBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Information)


class QGroupBox(QtGui.QGroupBox):
    """
    Convenience class for a QGroupbox with a form layout and alignment settings
    """

    def __init__(self, *args, **kwargs):
        super(QGroupBox, self).__init__(*args, **kwargs)
        # Add a new layout
        self.form = QtGui.QFormLayout()
        self.setLayout(self.form)

        self.form.setRowWrapPolicy(QtGui.QFormLayout.DontWrapRows)
        # self.form.setFieldGrowthPolicy(QtGui.QFormLayout.FieldsStayAtSizeHint)
        self.form.setFormAlignment(QtCore.Qt.AlignTop)
        self.form.setLabelAlignment(QtCore.Qt.AlignLeft)


class QLineEdit(QtGui.QLineEdit):
    """
    Convenience class for a QLineEdit where the cursor will go to the end of the line by default
    """

    def mousePressEvent(self, e):
        """Make sure that you always go to the start of the line whenever clicks on this"""
        super(QLineEdit, self).mousePressEvent(e)

        self.setCursorPosition(len(self.text()))


# Set an icon for an window
class QMainWindow(QtGui.QMainWindow):
    """Base class for all Pyside GUI"""

    def __init__(self):
        """Initialise the PySide GUI with the App Icon"""
        super(QMainWindow, self).__init__(parent=getMayaMainWindow())
        self.setObjectName(self.__class__.__name__)
        # Set the default title
        self.setWindowTitle("Maya Window")
        # Always show the tooltip
        self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips, True)
        # Set the PKD windows Icon
        self.setWindowIcon(AppIcon)

    def _setup_(self):
        """Setup the window. Add more custom gui object in subclasses. Add the AppLabel in a frame """
        #  Add the basic column layout
        self.main_layout = QtGui.QVBoxLayout()
        centralWidget = QtGui.QFrame()
        centralWidget.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Sunken)
        centralWidget.setLayout(self.main_layout)
        centralWidget.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)

        # Add new frame for the app frame
        companyFrame = QtGui.QLabel()
        companyFrame.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Sunken)
        companyFrame.setAlignment(QtCore.Qt.AlignVCenter)
        # Add Image
        companyLabel = QtGui.QPixmap(AppLabel)
        companyFrame.setPixmap(companyLabel)

        # Add widget to the main layout
        self.main_layout.addWidget(companyFrame)

        # Set the default alignment
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft)

        # Add the central widget
        self.setCentralWidget(centralWidget)

    def _connect_signals_(self):
        """Connect the command with the gui object"""
        pass

    def setWindowIcon(self, iconPath):
        """Set the icon for the window via QIcon with checks"""
        # Make sure the icon exists
        if not libFile.exists(iconPath):
            pyLog.warning("No Icon exists for path:%s" % iconPath)
        else:
            # Set the icon
            icon = QtGui.QIcon(QtGui.QPixmap(iconPath))
            try:
                super(QMainWindow, self).setWindowIcon(icon)
            except Exception as e:
                print e
                pyLog.warning("Failed to set Icon")

    def show(self, *args, **kwargs):
        """Show the window after intialising it"""
        self._closeExistingWindow_()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self._setup_()
        self._connect_signals_()
        super(QMainWindow, self).show()
        self.resize(self.sizeHint())

    def _closeExistingWindow_(self):
        """Ensures there is only instance of the PySide GUI"""
        for qt in QtGui.qApp.topLevelWidgets():
            # Check that there is only one instance of the APP
            try:
                if qt.__class__.__name__ == self.__class__.__name__:
                    qt.close()
            except:
                pyLog.warning('Failed to close an instance of this GUI:%s' % str(self))


class QDockableWindow(QMainWindow):
    """Create a dockable window"""
    def __init__(self):
        super(QDockableWindow, self).__init__()
        self._dockedwidget_ = None

    def show(self, *args, **kwargs):
        """Create Dockable UI"""
        # Set the docked object name
        dockedName = (self.objectName() + "Dock")
        # Set the default docked object name
        floatingState = True
        if cmds.dockControl(dockedName, q=1, ex=1):
            # If the docked UI exists get the float status before deleting
            floatingState = cmds.dockControl(dockedName, q=1, floating=1)
            # Delete the UI
            cmds.deleteUI(dockedName)
        try:
            self._dockedwidget_ = cmds.dockControl(dockedName, label=self.windowTitle(), allowedArea='all',
                                                   area='right',
                                                   floating=floatingState,
                                                   content=self.objectName(),
                                                   floatChangeCommand=self._auto_resize_
                                                   )
        except:
            pyLog.info("Maya dockable window failed")

        super(QDockableWindow, self).show()

    def _auto_resize_(self):
        """Resize the widget to the suggested size"""
        sizeHint = self.sizeHint()
        self.resize(sizeHint)

# @cond DOXYGEN_SHOULD_SKIP_THIS
class TestGUI(QMainWindow):
    def __init__(self):
        super(TestGUI, self).__init__()
        # Set the name of the window
        self.setWindowTitle("Test GUI")
        # Create a list of rows and buttons
        self.rows = ["Row1", "Row2", "Row3"]
        self.buttons = ["Button1", "Button2", "Button3"]

    def _setup_(self):
        super(TestGUI, self)._setup_()
        pyLog.info("Child Info Called")
        # Create a series of rows, and in each row, put our buttons
        for row in self.rows:

            self.row_Hbox = QtGui.QGroupBox()
            self.layout = QtGui.QGridLayout()

            for button in self.buttons:
                # Label the button with it's list name
                self.push_button = QtGui.QPushButton(button, self)

                # Give each button a unique object name
                self.b_name = row + "_" + button
                self.push_button.setObjectName(self.b_name)

                # Add a QLine Edit to each particular button
                self.q_line_name = self.b_name + "_TextEdit"
                self.my_line_edit = QtGui.QLineEdit()
                self.my_line_edit.setText("Hi! I'm " + self.q_line_name)

                # Also give it a unique name
                self.my_line_edit.setObjectName(self.q_line_name)

                # Offset each button in the layout by it's index number
                self.layout.addWidget(self.push_button, 0, self.buttons.index(button))

                # Offset each QLine Edit in the layout to be underneath each button
                self.layout.addWidget(self.my_line_edit, 1, self.buttons.index(button))

                # Connect the button to an event
                self.push_button.clicked.connect(self.on_button_event)

            # Add the buttons to our layout
            self.row_Hbox.setLayout(self.layout)
            self.main_layout.addWidget(self.row_Hbox)

    def on_button_event(self):
        sender = self.sender()
        print sender.objectName() + ' was pressed'
        # Get the text from the text line edit linked with the button
        self.line_edit_name = sender.objectName() + "_TextEdit"
        self.line_edit = self.findChild(QtGui.QLineEdit, self.line_edit_name)
        print self.line_edit
        print self.line_edit.text()
# @endcond

class TangentSwapper(QDockableWindow):
    """GUI to change the default tangents"""
    def __init__(self):
        super(TangentSwapper, self).__init__()
        # Set the variables
        self.setWindowTitle("Tangent Swapper")
        self.setFixedSize(192, 206)

    def _setup_(self):
        super(TangentSwapper, self)._setup_()
        buttonGroup = QGroupBox()
        for tangent in ["step", "linear", "clamped", "spline"]:
            push_button = QtGui.QPushButton(tangent.capitalize(), self)
            push_button.clicked.connect(partial(libUtilities.changeTangents, tangent))
            buttonGroup.form.addRow(push_button)
            push_button.setFixedWidth(150)

        self.main_layout.addWidget(buttonGroup)

class ManagerGUI(QMainWindow):

    """Setup a generic deformer weight import/exporter gui. Add more custom gui object in subclasses"""
    # @cond DOXYGEN_SHOULD_SKIP_THIS

    def _setup_(self):
        # Setup the window.
        super(ManagerGUI, self)._setup_()
        self._deformer_ = None
        self.txtField = cmds.textFieldButtonGrp(
            text='Get %s Folder' % self.deformer, buttonLabel='Folder')
        cmds.rowLayout(w=self.width, numberOfColumns=2)
        self.exportButton = cmds.button(label="Export", w=self.width / 2)
        self.importButton = cmds.button(label="Import", w=self.width / 2)

    # @endcond

    def _connect_commands_(self):
        """Connect the command with the gui object"""
        cmds.textFieldButtonGrp(
            self.txtField, e=1, buttonCommand=lambda*args: self._get_folder_())
        cmds.button(self.importButton,
                    e=1,
                    command=lambda*args: self._import_weights_())
        cmds.button(self.exportButton,
                    e=1,
                    command=lambda*args: self._export_weights_())

    def _get_folder_(self):
        """Set the starting directory"""
        res = cmds.fileDialog2(dialogStyle=1,
                               fm=3,
                               cap="Define %s Folder" % self.deformer,
                               okc="Set",
                               startingDirectory=pm.workspace.path)
        if res:
            cmds.textFieldButtonGrp(self.txtField, e=1, text=res[0])

    def _export_weights_(self):
        """Export the weights"""
        weightManager = self._initialise_manager_class_()
        success = weightManager.export_all()
        if not success:
            nothing_selected_box()

    def _import_weights_(self):
        """Import the weights"""
        if libFile.exists(self.infoPath):
            weightManager = self._initialise_manager_class_()
            weightManager.info_file = self.infoPath
            weightManager.import_all()
        else:
            raise Exception("No %sInfo Xml file found" % self.deformer)

    def _initialise_manager_class_(self):
        """initialse the weight manager class and set the info file"""
        weightManager = self.weightManager()
        weightManager.info_file = self.infoPath
        weightManager.command_mode = True
        return weightManager

    @property
    def infoPath(self):
        """Return the @ref libWeights.Weights.data "data" file which exists in the user defined folder"""
        infoPath = libFile.join(cmds.textFieldButtonGrp(
            self.txtField, text=1, q=1), "%sInfo.xml" % self.deformer)
        return libFile.linux_path(infoPath)

    @property
    def deformer(self):
        """Return the current deformer of weight manager class as camelCase string"""
        if self._deformer_ is None:
            deformerType = self.weightManager().deformer
            # Make the camelCase string
            self._deformer_ = deformerType[0].upper() + deformerType[1:]
        return self._deformer_

    @property
    def weightManager(self):
        """The property that sets the default @ref libWeights.WeightManager "WeightManager" that is relevant to the Gui"""
        return libWeights.WeightManager


def nothing_selected_box():
    """Bring up error message in case nothing is selected"""
    msgBox = QCriticalBox()
    msgBox.setText("Nothing is Selected")
    msgBox.setWindowTitle("User Error")
    msgBox.exec_()


def confirm_box(title, message, detailedMessage=""):
    """A Simple Yes No Dialog"""
    msgBox = QQuestionBox()
    msgBox.setText(message)
    msgBox.setWindowTitle(title)
    msgBox.setStandardButtons(QtGui.QMessageBox.No | QtGui.QMessageBox.Yes)
    msgBox.setDefaultButton(QtGui.QMessageBox.No)
    if detailedMessage:
        msgBox.setDetailedText(detailedMessage)
    ret = msgBox.exec_()
    if ret == QtGui.QMessageBox.Yes:
        return True
    else:
        return False

def horizontal_divider():
    """Convience method which return a horizontal divider"""
    frame = QtGui.QFrame()
    frame.setFrameShape(QtGui.QFrame.HLine)
    frame.setFrameShadow(QtGui.QFrame.Sunken)
    return frame


def vLine_divider():
    """Convience method which return a vertical divider"""
    frame = QtGui.QFrame()
    frame.setFrameShape(QtGui.QFrame.VLine)
    frame.setFrameShadow(QtGui.QFrame.Sunken)
    return frame


pySideWindow = TestGUI()
pySideWindow.show()
#
# pySideWindow = ABCTools()
# pySideWindow.show()
# nothing_selected_box()
# print confirm_box("Test","Blah blah blah")
# icon = r"C:\Users\admin\Pictures\bat.JPG"
# pySideWindow.setWindowIcon(icon)
