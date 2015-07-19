"""
@package PKD_Tools.libPySide
 This scripts creates an empty PySide custom window in Maya
 To run the script you need to have built Shiboken and PySide
 Following documentation on best practice for Pyside in maya
 http://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2015/ENU/Maya-SDK/files/GUID-66ADA1FF-3E0F-469C-84C7-74CEB36D42EC-htm.html"""

from shiboken import wrapInstance

import PySide.QtCore as QtCore
import PySide.QtGui as QtGui
import maya.OpenMayaUI as OpenMayaUI
from maya import cmds
from pymel.internal.plogging import pymelLogger as pyLog

import libFile

AppIcon = libFile.join(libFile.current_working_directory(), r"Icons/WinIcon.png")
AppLabel = libFile.join(libFile.current_working_directory(), r"Icons/WinLabel.png")

# This is a function that is run from your class object to get a handle
# to the main Maya window, it uses a combination of the Maya API as well as the SIP module

def getMayaMainWindow():
    accessMainWindow = OpenMayaUI.MQtUtil.mainWindow()
    return wrapInstance(long(accessMainWindow), QtGui.QMainWindow)

class QMessageBox(QtGui.QMessageBox):
    """ Setup up convience message boxes"""

    def __init__(self):
        super(QMessageBox, self).__init__(parent=getMayaMainWindow())
        icon = QtGui.QIcon(AppIcon)
        self.setWindowIcon(icon)
        self.setSizeGripEnabled(True)


    def event(self, e):
        # Make it a resizable window
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
    def __init__(self):
        super(QCriticalBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Critical)


class QWarningBox(QMessageBox):
    def __init__(self):
        super(QWarningBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Warning)


class QQuestionBox(QMessageBox):
    def __init__(self):
        super(QQuestionBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Question)


class QGroupBox(QtGui.QGroupBox):
    """ A collapsable group box widget with form layout as the default layout"""

    def __init__(self, *args, **kwargs):
        super(QGroupBox, self).__init__(*args, **kwargs)
        # Add a new layout
        self.form = QtGui.QFormLayout()
        self.setLayout(self.form)

        self.form.setRowWrapPolicy(QtGui.QFormLayout.DontWrapRows)
        # self.form.setFieldGrowthPolicy(QtGui.QFormLayout.FieldsStayAtSizeHint)
        self.form.setFormAlignment(QtCore.Qt.AlignTop)
        self.form.setLabelAlignment(QtCore.Qt.AlignLeft)
        self.isCollapsed = False
        self.isCollapsable = False

    def mouseDoubleClickEvent(self, *args, **kwargs):
        """Event which toggles the collapse state"""
        if self.isCollapsable:
            if self.isCollapsed:
                self.setFixedHeight(self.minimumSizeHint().height())
            else:
                self.setFixedHeight(17)

            self.isCollapsed = not (self.isCollapsed)

            # Emit a collapse signal
            self.toggleCollapse.emit()

    def collapse(self):
        self.isCollapsed = True
        self.setFixedHeight(17)

    # Create a collapse signal
    toggleCollapse = QtCore.Signal()


class QLineEdit(QtGui.QLineEdit):
    """Qline widget which make sure that your cursor always go to the end of the current text"""

    def mousePressEvent(self, e):
        super(QLineEdit, self).mousePressEvent(e)
        self.setCursorPosition(len(self.text()))


class QInputDialog(QtGui.QInputDialog):
    """Convience class for QInput dialog"""

    def __init__(self, *args, **kwargs):
        super(QInputDialog, self).__init__(parent=getMayaMainWindow())
        icon = QtGui.QIcon(AppIcon)
        self.setWindowIcon(icon)
        self.setSizeGripEnabled(True)

    def getText(self):
        text, ok = super(QInputDialog, self).getText(self, self.windowTitle(), self.labelText(), QtGui.QLineEdit.Normal,
                                                     self.textValue())
        return text, ok

    def getInt(self):
        text, ok = super(QInputDialog, self).getInt(self, self.windowTitle(), self.labelText(), self.intValue())
        return text, ok

    def getDouble(self):
        text, ok = super(QInputDialog, self).getDouble(self, self.windowTitle(), self.labelText(), self.doubleValue(),
                                                       decimal=self.doubleDecimals())
        return text, ok


class QMainWindow(QtGui.QMainWindow):
    """Common Functions used in various pySide GUI """

    def __init__(self):
        # Intilise the PySide GUI
        super(QMainWindow, self).__init__(parent=getMayaMainWindow())
        self.setObjectName(self.__class__.__name__)
        # Set the default title
        self.setWindowTitle("Maya Window")
        # Always show the tooltip
        self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips, True)
        # Set the window icon
        self.setWindowIcon(AppIcon)

    def _setup_(self):
        '''Setup the window. Add more custom gui object in subclasses'''
        # C:/Users/admin/Documents/maya/scripts/AdvancedSkeleton4Files/icons/AS4.png
        #  Add the basic column layout
        self.main_layout = QtGui.QVBoxLayout()
        centralWidget = QtGui.QFrame()
        centralWidget.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Sunken)
        centralWidget.setLayout(self.main_layout)
        centralWidget.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)

        # Set up the mainFrame of the window
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft)

        # Add the central widget
        self.setCentralWidget(centralWidget)

    def _connect_signals_(self):
        '''Connect the command with the gui object'''
        pass

    def setWindowIcon(self, iconPath):
        """Set the icon for via QIcon"""
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

    def resize_window(self, *args, **kwargs):
        # Method to resize whenever a widget is hidden
        for i in range(0, 10):
            QtGui.QApplication.processEvents()

        self.resize(self.minimumSizeHint())


class QDockableWindow(QMainWindow):
    """Create a dockable window"""

    def __init__(self):
        super(QDockableWindow, self).__init__()
        self._dockedwidget_ = None
        self.init_float_state = False

    def _setup_(self):
        super(QDockableWindow, self)._setup_()
        # Setup a company frame for dockable windows as the windows icon is missing
        # Add A new frame
        companyFrame = QtGui.QLabel()
        companyFrame.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Sunken)
        companyFrame.setAlignment(QtCore.Qt.AlignVCenter)

        # Add new frame for the app frame
        companyFrame = QtGui.QLabel()
        companyFrame.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Sunken)
        companyFrame.setAlignment(QtCore.Qt.AlignVCenter)
        # Add Image
        companyLabel = QtGui.QPixmap(AppLabel)
        companyFrame.setPixmap(companyLabel)
        self.main_layout.addWidget(companyFrame)

    def show(self, *args, **kwargs):
        """Create Dockable UI"""

        # Set the docked object name
        dockedName = (self.objectName() + "Dock")
        # Set the default docked object name
        floatingState = self.init_float_state
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
            pyLog.info("Maya dock window failed")

        super(QDockableWindow, self).show()

    def _auto_resize_(self):
        sizeHint = self.sizeHint()
        # pyLog.info("Recommend Size:%s" % sizeHint)
        # pyLog.info("Current Central Size:%s" % self.centralWidget().size())
        self.resize(sizeHint)
        # if cmds.dockControl(self._dockedwidget_, q=1, floating=1):
        #     pyLog.info(cmds.dockControl(self._dockedwidget_, q=1, w=1))
        #     pyLog.info(cmds.dockControl(self._dockedwidget_, q=1, h=1))
        # cmds.dockControl(self._dockedwidget_, e=1, w=278,h=296)


class TestGUI(QDockableWindow):
    """A test GUI"""

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


class VerticalTabBar(QtGui.QTabBar):
    """A tab bar with a vertical side bar with text written horizontally instead of vertically
    http://stackoverflow.com/questions/3607709/how-to-change-text-alignment-in-qtabwidget"""

    def __init__(self, *args, **kwargs):
        self.tabSize = QtCore.QSize(kwargs.pop('width'), kwargs.pop('height'))
        super(VerticalTabBar, self).__init__(*args, **kwargs)

    def paintEvent(self, event):
        super(VerticalTabBar, self).paintEvent(event)
        painter = QtGui.QStylePainter(self)
        option = QtGui.QStyleOptionTab()

        painter.begin(self)
        for index in range(self.count()):
            self.initStyleOption(option, index)
            tabRect = self.tabRect(index)
            tabRect.moveLeft(10)
            painter.drawControl(QtGui.QStyle.CE_TabBarTabShape, option)
            # Take care of mnemonic keys when redrawing the text
            painter.drawText(tabRect,
                             QtCore.Qt.AlignVCenter | QtCore.Qt.TextDontClip,
                             self.tabText(index).replace("&", ""))
        painter.end()

    def tabSizeHint(self, index):
        return self.tabSize


class VerticalTabTest(QMainWindow):
    """A vertical tab test"""

    def _setup_(self):
        super(VerticalTabTest, self)._setup_()
        tabs = QtGui.QTabWidget()
        tabs.setTabBar(VerticalTabBar(width=100, height=25))
        digits = ['Thumb', 'Pointer', 'Rude', 'Ring', 'Pinky']
        for i, d in enumerate(digits):
            widget = QtGui.QLabel("Area #%s <br> %s Finger" % (i, d))
            tabs.addTab(widget, d)
        tabs.setTabPosition(QtGui.QTabWidget.West)
        tabs.show()
        self.main_layout.addWidget(tabs)


def horizontal_divider():
    divider = QtGui.QFrame()
    divider.setFrameShape(QtGui.QFrame.HLine)
    divider.setFrameShadow(QtGui.QFrame.Sunken)
    return divider


def vLine_divider():
    divider = QtGui.QFrame()
    divider.setFrameShape(QtGui.QFrame.VLine)
    divider.setFrameShadow(QtGui.QFrame.Sunken)
    return divider


if __name__ == '__main__':
    win = VerticalTabTest()
    win.show()

    # input = QInputDialog()
    # input.setWindowTitle("ChuckTesta")
    # input.setLabelText("Gloworms")
    # input.setDoubleValue(1.545454)
    # input.setDoubleDecimals(3)
    # res, ok = input.getDouble()
    # print res, ok



    # pySideWindow = TangentSwapper()
    # pySideWindow.exec_()
    #
    # pySideWindow = ABCTools()
    # pySideWindow.show()
    # nothing_selected_box()
    # print confirm_box("Test","Blah blah blah")
    # icon = r"C:\Users\admin\Pictures\bat.JPG"
    # pySideWindow.setWindowIcon(icon)
