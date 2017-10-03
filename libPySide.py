"""
@package PKD_Tools.libPySide
 @brief Here we do a basic PySide setup so that all GUIs are inside of maya and that they follow some common formatting
  to bring about consistency
 @details This is following documentation on best practice for Pyside in maya
 
 http://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2015/ENU/Maya-SDK/files/GUID-66ADA1FF-3E0F-469C-84C7-74CEB36D42EC-htm.html
 
 Here we break from the pep 8 convention as pyside follows a camel case convention
 """

from shiboken import wrapInstance

import PySide.QtCore as QtCore
import PySide.QtGui as QtGui
import maya.OpenMayaUI as OpenMayaUI
from maya import cmds
from PKD_Tools import logger

try:
    import libFile
except:
    from PKD_Tools import libFile

AppIcon = libFile.join(libFile.current_working_directory(), r"Icons/WinIcon.png")
AppLabel = libFile.join(libFile.current_working_directory(), r"Icons/WinLabel.png")


# This is a function that is run from your class object to get a handle
# to the main Maya window, it uses a combination of the Maya API as well as the SIP module

def getMayaMainWindow():
    """Setup so that any Pyside window are a child within the maya application"""
    accessMainWindow = OpenMayaUI.MQtUtil.mainWindow()
    return wrapInstance(long(accessMainWindow), QtGui.QMainWindow)


class QMessageBox(QtGui.QMessageBox):
    """ Setup up of convenience message boxes"""

    def __init__(self):
        super(QMessageBox, self).__init__(parent=getMayaMainWindow())
        icon = QtGui.QIcon(AppIcon)
        self.setWindowIcon(icon)
        self.setSizeGripEnabled(True)

    def event(self, e):
        """Make it a resizable window. Used most in the context of detailed box"""
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
    """ A message box with a critical icon"""

    def __init__(self):
        super(QCriticalBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Critical)


class QWarningBox(QMessageBox):
    """ A message box with a warning icon"""

    def __init__(self):
        super(QWarningBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Warning)


class QQuestionBox(QMessageBox):
    """ A message box with a question icon"""

    def __init__(self):
        super(QQuestionBox, self).__init__()
        self.setIcon(QtGui.QMessageBox.Icon.Question)


class QFormLayout(QtGui.QFormLayout):
    """An overloaded layout where you ensure that the set the text padding"""
    padding = 23

    # noinspection PyTypeChecker
    def addRow(self, *args, **kwargs):
        """Overload the add row to autofill """
        if args:
            args_list = list(args)
            text_alias = args_list[0]
            if isinstance(text_alias, basestring):
                args_list[0] = self._pad_text(text_alias)
                args = tuple(args_list)
            elif isinstance(text_alias, QtGui.QLabel):
                text_alias = QtGui.QLabel()
                text_alias.setText(self._pad_text(text_alias.text()))
        super(QFormLayout, self).addRow(*args, **kwargs)

    # noinspection PyMethodMayBeStatic
    def _pad_text(self, text):
        return '{text: <{self.padding}}'.format(**locals())

class QGroupBox(QtGui.QGroupBox):
    """ A collapsable group box widget with form layout as the default layout"""

    def __init__(self, *args, **kwargs):
        padding = kwargs.get("padding", 20)
        if kwargs.has_key("padding"):
            del kwargs["padding"]
        super(QGroupBox, self).__init__(*args, **kwargs)
        # Get the text label
        self.titleText = self.title()

        # Add a new layout
        self.form = QFormLayout()
        self.form.padding = padding
        self.setLayout(self.form)

        self.form.setRowWrapPolicy(QtGui.QFormLayout.DontWrapRows)
        self.form.setFormAlignment(QtCore.Qt.AlignTop)
        self.form.setLabelAlignment(QtCore.Qt.AlignLeading |
                                    QtCore.Qt.AlignLeft |
                                    QtCore.Qt.AlignVCenter)
        self.isCollapsed = False
        self._isCollapsable = False

        # UP Down Arrow Helper
        self.downArrowChar = u"\u25BC"
        self.upArrowChar = u"\u25B2"

    def mouseDoubleClickEvent(self, *args, **kwargs):
        """Event which toggles the collapse state"""
        if self._isCollapsable:
            if self.isCollapsed:
                self.setFixedHeight(self.minimumSizeHint().height())
                self.setTitle(u'{0} {1}'.format(self.titleText, self.upArrowChar))
            else:
                self.setFixedHeight(17)
                self.setTitle(u'{0} {1}'.format(self.titleText, self.downArrowChar))

            self.isCollapsed = not (self.isCollapsed)

            # Emit a collapse signal
            self.toggleCollapse.emit()

    def collapse(self):
        """Force the collapse state"""
        self.isCollapsed = True
        self.setFixedHeight(17)

    @property
    def isCollapsable(self):
        """Return collapsible property"""
        return self._isCollapsable

    @isCollapsable.setter
    def isCollapsable(self, boolVal):
        """Set collapsible property. If it is set to true add the special character"""
        self._isCollapsable = boolVal
        if boolVal:
            self.setTitle(self.titleText + self.upArrowChar)

    # Create a collapse signal
    toggleCollapse = QtCore.Signal()


class QLineEdit(QtGui.QLineEdit):
    """Qline widget which make sure that your cursor always go to the end of the current text"""

    def mousePressEvent(self, event):
        """
        Ensure cursor is always at the end of the line when it is selected
        @param event: The event we are capture
        """
        super(QLineEdit, self).mousePressEvent(event)
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
        self.mainLayout = QtGui.QVBoxLayout()
        centralWidget = QtGui.QFrame()
        centralWidget.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Sunken)
        centralWidget.setLayout(self.mainLayout)
        centralWidget.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)

        # Set up the mainFrame of the window
        self.mainLayout.setAlignment(QtCore.Qt.AlignLeft)

        # Add the central widget
        self.setCentralWidget(centralWidget)

    def _connect_signals_(self):
        '''Connect the command with the gui object'''
        pass

    def setWindowIcon(self, iconPath):
        """Set the icon for via QIcon"""
        # Make sure the icon exists
        if not libFile.exists(iconPath):
            logger.warning("No Icon exists for path:%s" % iconPath)
        else:
            # Set the icon
            icon = QtGui.QIcon(QtGui.QPixmap(iconPath))
            try:
                super(QMainWindow, self).setWindowIcon(icon)
            except Exception as e:
                print e
                logger.warning("Failed to set Icon")

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
                logger.warning('Failed to close an instance of this GUI:%s' % str(self))

    def resizeWindow(self):
        """Method to resize whenever a widget is hidden"""
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
        self.mainLayout.addWidget(companyFrame)

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
                                                   floatChangeCommand=self._autoResize_
                                                   )
        except Exception, e:
            logger.info(str(e))
            logger.info("Maya dock window failed")

        super(QDockableWindow, self).show()

    def _autoResize_(self):
        sizeHint = self.sizeHint()
        # pyLog.info("Recommend Size:%s" % sizeHint)
        # pyLog.info("Current Central Size:%s" % self.centralWidget().size())
        self.resize(sizeHint)
        # if cmds.dockControl(self._dockedwidget_, q=1, floating=1):
        #     pyLog.info(cmds.dockControl(self._dockedwidget_, q=1, w=1))
        #     pyLog.info(cmds.dockControl(self._dockedwidget_, q=1, h=1))
        # cmds.dockControl(self._dockedwidget_, e=1, w=278,h=296)


# @cond DOXYGEN_SHOULD_SKIP_THIS
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
        logger.info("Child Info Called")
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
            self.mainLayout.addWidget(self.row_Hbox)

    def on_button_event(self):

        sender = self.sender()
        print sender.objectName() + ' was pressed'

        # Get the text from the text line edit linked with the button
        self.line_edit_name = sender.objectName() + "_TextEdit"
        self.line_edit = self.findChild(QtGui.QLineEdit, self.line_edit_name)
        print self.line_edit
        print self.line_edit.text()


# @endcond

class VerticalTabBar(QtGui.QTabBar):
    """A tab bar with a vertical side bar with text written horizontally instead of vertically
    @details This is a modification of the following http://stackoverflow.com/questions/3607709/how-to-change-text-alignment-in-qtabwidget"""

    def __init__(self, *args, **kwargs):
        self.tabSize = QtCore.QSize(kwargs.pop('width'), kwargs.pop('height'))
        super(VerticalTabBar, self).__init__(*args, **kwargs)

    def paintEvent(self, event):
        """Write the text horizontally instead of vertically"""
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

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def tabSizeHint(self, index):
        return self.tabSize
        # @endcond


class CheckableTabWidget(QtGui.QTabWidget):
    """A tab widget with a checkbox
    source:http://stackoverflow.com/questions/5818387/qtabwidget-with-checkbox-in-title
    """
    checkBoxList = []
    titleDict = {}
    stateChanged = QtCore.Signal(int, int, str)

    def addTab(self, widget, title):
        QtGui.QTabWidget.addTab(self, widget, title)
        checkBox = QtGui.QCheckBox()
        self.checkBoxList.append(checkBox)
        self.tabBar().setTabButton(self.tabBar().count() - 1, QtGui.QTabBar.LeftSide, checkBox)
        self.titleDict[checkBox] = title
        checkBox.stateChanged.connect(lambda checkState: self._emitStateChanged_(checkBox, checkState))

    def isChecked(self, index):
        return self.tabBar().tabButton(index, QtGui.QTabBar.LeftSide).checkState() != QtCore.Qt.Unchecked

    def setCheckState(self, index, checkState):
        self.tabBar().tabButton(index, QtGui.QTabBar.LeftSide).setCheckState(checkState)

    def _emitStateChanged_(self, checkBox, checkState):
        index = self.checkBoxList.index(checkBox)
        self.setCurrentIndex(index)
        self.stateChanged.emit(index, checkState, self.titleDict[checkBox])


# @cond DOXYGEN_SHOULD_SKIP_THIS
class CheckableTabTest(QMainWindow):
    def _setup_(self):
        super(CheckableTabTest, self)._setup_()
        tabs = CheckableTabWidget()
        tabs.setTabBar(QtGui.QTabBar())
        digits = ['Thumb', 'Pointer', 'Rude', 'Ring', 'Pinky']
        for i, d in enumerate(digits):
            widget = QtGui.QLabel("Area #%s <br> %s Finger" % (i, d))
            tabs.addTab(widget, d)
        # tabs.setTabPosition(QtGui.QTabWidget.West)
        tabs.show()
        self.mainLayout.addWidget(tabs)
        tabs.stateChanged.connect(self.myFunction)

    def myFunction(self, index, checkState, title):
        print "I am current positioned on: %i" % index
        print "The State is: %i" % bool(checkState)
        print "My title is: %s" % title


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
        self.mainLayout.addWidget(tabs)


# @endcond DOXYGEN_SHOULD_SKIP_THIS

class QProgressDialog(QtGui.QProgressDialog):
    """Convience class for QProgressDialog dialog"""

    def __init__(self):
        super(QProgressDialog, self).__init__(parent=getMayaMainWindow())
        self.setCancelButton(None)
        self.currentProgress = 1
        self.setValue(self.currentProgress)
        self.currentTarget = None
        self.currentProcess = ""
        self.setFixedWidth(300)

    def update(self, *args, **kwargs):
        """Update function that moves the progress bar forward. Also sets the label"""
        if self.currentProgress <= self.maximum():
            self.setValue(self.currentProgress)
            self.setLabelText("%s %s" % (self.currentProcess, self.currentTarget))
            self.currentProgress += 1

        if self.maximum() == 1:
            self.cancel()


def horizontal_divider():
    """Return a horizontal divider"""
    divider = QtGui.QFrame()
    divider.setFrameShape(QtGui.QFrame.HLine)
    divider.setFrameShadow(QtGui.QFrame.Sunken)
    return divider


def vertical_divider():
    """Return a vertical divider"""
    divider = QtGui.QFrame()
    divider.setFrameShape(QtGui.QFrame.VLine)
    divider.setFrameShadow(QtGui.QFrame.Sunken)
    return divider


# @cond DOXYGEN_SHOULD_SKIP_THIS
class SearchAbleTextWin(QMainWindow):
    """An example of how to setup a searchable list with QLineEdit"""
    def _setup_(self):
        super(SearchAbleTextWin, self)._setup_()
        self.setWindowTitle("Searchable List")
        self.myList = QtGui.QListWidget()
        self.myList.addItems(["Alaska", "Germany", "Germfigher", "Germ02", "Oasis"])
        self.myList.setCurrentRow(1)
        self.quickSearchText = QLineEdit()
        self.mainLayout.addWidget(self.quickSearchText)
        self.mainLayout.addWidget(self.myList)

        #
        mainGroupBox = QGroupBox("Details")
        self.detailedText = QtGui.QLabel()
        self.detailedText.setWordWrap(True)
        self.detailedText.setText(self.myList.currentItem().text())
        self.detailedText2 = QtGui.QLabel()
        self.detailedText2.setWordWrap(True)
        self.detailedText2.setText(self.myList.currentItem().text())

        mainGroupBox.form.addWidget(self.detailedText)
        mainGroupBox.form.addWidget(self.detailedText2)
        mainGroupBox.isCollapsable = True

        mainGroupBox.toggleCollapse.connect(self.resizeWindow)
        self.mainLayout.addWidget(mainGroupBox)

        self.myList.currentRowChanged.connect(self.updateDetails)
        self.quickSearchText.textChanged.connect(self.filterSearch)

    def updateDetails(self):
        self.detailedText.setText(self.myList.currentItem().text())
        self.detailedText2.setText(self.myList.currentItem().text())

    def filterSearch(self):
        item = self.myList.findItems(self.quickSearchText.text(), QtCore.Qt.MatchStartsWith)
        if item:
            self.myList.setCurrentItem(item[0])
# @endcond DOXYGEN_SHOULD_SKIP_THIS


if __name__ == '__main__':
    win = SearchAbleTextWin()
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
