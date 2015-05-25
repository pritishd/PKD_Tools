'''@file libGUI.py @package PKD_Tools.libGUI
@brief This package contains all frontend interfaces through which the user can interact with the various APIs
'''
import os
from maya import cmds, mel
import pymel.core as pm
from functools import partial
import libFile, libWeights
for module in libFile, libWeights:
    reload(module)

class GUI(object):
    '''@brief Generic "GUI" class which is expanded to make skin exporter, cluster weight exporter, obj exporter etc
    @details This sets a default way of setting up a gui while at the same time give flexibility in customising it
    '''


    def __init__(self):
        '''
        The GUI constructor.
        '''
        self.window = ''
        self._setup_()
        self._connect_commands_()
        self._show_()

    def _setup_(self):
        '''Setup the window. Add more custom gui object in subclasses'''
        #Remove a prexisting window so that only version exists in maya scene
        if(cmds.window(self.title.replace(" ",'_'),ex=1)):
            cmds.deleteUI(self.title.replace(" ",'_'))
        #Set the window
        self.window = cmds.window(self.title,title=self.title,rtf=True)
        #Add the basic column layout
        cmds.columnLayout(adjustableColumn=True)

    def _connect_commands_(self):
        '''Connect the command with the gui object'''
        pass

    def _show_(self):
        '''Show the window and set the width'''
        cmds.showWindow(self.window)
        cmds.window(self.window,e=1,w=self.width)


    @property
    def title(self):
      '''The property that sets title of the window. This will be unique in all subclasses'''
      return "Maya Window"

    @property
    def width(self):
      '''The property that sets default width of the window. This may be overwritten in the subclasses
      @remark Current default value is 300px
      '''
      return 300

    ## @property window
    #@brief Return the current maya window object.

class ManagerGUI(GUI):
    '''Setup a generic deformer weight import/exporter gui. Add more custom gui object in subclasses'''
    #@cond DOXYGEN_SHOULD_SKIP_THIS
    def _setup_(self):
        # Setup the window.
        super(ManagerGUI,self)._setup_()
        self._deformer_ = None
        self.txtField = cmds.textFieldButtonGrp(text='Get %s Folder'%self.deformer, buttonLabel='Folder')
        row = cmds.rowLayout(w=self.width,numberOfColumns = 2)
        self.exportButton = cmds.button(label = "Export",w=self.width/2)
        self.importButton = cmds.button(label = "Import",w=self.width/2)

    #@endcond

    def _connect_commands_(self):
        '''Connect the command with the gui object'''
        cmds.textFieldButtonGrp(self.txtField,e=1,buttonCommand = lambda*args:self._get_folder_())
        cmds.button(self.importButton,e=1,command = lambda*args:self._import_weights_())
        cmds.button(self.exportButton,e=1,command = lambda*args:self._export_weights_())

    def _get_folder_(self):
        '''Set the starting directory'''
        res = cmds.fileDialog2(dialogStyle=1,fm=3,cap="Define %s Folder"%self.deformer,okc="Set", startingDirectory=pm.workspace.path)
        if res:
            cmds.textFieldButtonGrp(self.txtField,e=1,text=res[0])

    def _export_weights_(self):
        '''Export the weights'''
        weightManager = self._initialise_manager_class_()
        success = weightManager.export_all()
        if not success:
            nothing_selected_box()

    def _import_weights_(self):
        '''Import the weights'''
        if os.path.exists(self.infoPath):
            weightManager = self._initialise_manager_class_()
            weightManager.info_file = self.infoPath
            weightManager.import_all()
        else:
            raise Exception ("No %sInfo Xml file found"%self.deformer)

    def _initialise_manager_class_(self):
        '''initialse the weight manager class and set the info file'''
        weightManager = self.weightManager()
        weightManager.info_file = self.infoPath
        weightManager.command_mode = True
        return weightManager

    @property
    def infoPath(self):
        '''Return the @ref libWeights.Weights.data "data" file which exists in the user defined folder'''
        infoPath = libFile.join(cmds.textFieldButtonGrp(self.txtField,text=1,q=1), "%sInfo.xml"%self.deformer)
        return libFile.linux_path(infoPath)

    @property
    def deformer(self):
        '''Return the current deformer of weight manager class as camelCase string'''
        if self._deformer_ is None:
            deformerType = self.weightManager().deformer
            #Make the camelCase string
            self._deformer_ = deformerType[0].upper()+deformerType[1:]
        return self._deformer_

    @property
    def weightManager(self):
        '''The property that sets the default @ref libWeights.WeightManager "WeightManager" that is relevant to the Gui'''
        return libWeights.WeightMaps


class SkinManagerGUI(ManagerGUI):

    '''
    Setup the Skin Import/Exporter Gui
    @code
    import libGUI
    libGUI.SkinManagerGUI()
    @endcode
    '''
    #@cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def title(self):
        '''The property that sets title of the window
          @remark The property ManagerGUI.title is overwritten in this class


        '''
        return "Skin Cluster Manager"

    @property
    def weightManager(self):
        '''Return the default the skin weight manager
        @remark
        The property ManagerGUI.weightManager is overwritten in this class
        '''
        return libWeights.SkinWeightManager
    #@endcond

class ClusterManagerGUI(ManagerGUI):

    '''
    Setup the Cluster Import/Exporter
    @code
    import libGUI
    libGUI.ClusterManagerGUI()
    @endcode
    '''


    #@cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def title(self):
        '''The property that sets title of the window
        @remark The property ManagerGUI.title is overwritten in this class

        '''

        return "Cluster Manager"

    @property
    def weightManager(self):
        '''Return the default the cluster weight manager
        @remark The property ManagerGUI.weightManager is overwritten in this class
        '''
        return libWeights.ClusterWeightManager
    #@endcond


class BlendshapeManagerGUI(ManagerGUI):
    '''
    Setup the Blendshape Import/Exporter
    @code
    import libGUI
    libGUI.BlendshapeManagerGUI()
    @endcode
    '''

    #@cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def title(self):
        '''The property that sets title of the window
        @remark The property ManagerGUI.title is overwritten in this class
        '''
        return "Blendshape Manager"

    @property
    def weightManager(self):
        '''Return the default the blendshape weight manager
        @remark The property ManagerGUI.weightManager is overwritten in this class'''
        return libWeights.BlendsWeightManager
    #@endcond


class ObjExportGUI(GUI):
    '''
    Bonus tool for exporting out the selected geometery as obj to a single destination folder. The name of the geometery is used as file name.
    Setup the Obj Exporter
    @code
    import libGUI
    libGUI.ObjExportGUI()
    @endcode
    '''

    #@cond DOXYGEN_SHOULD_SKIP_THIS
    def _setup_(self):
        super(ObjExportGUI,self)._setup_()
        self.txtField = cmds.textFieldButtonGrp(text='Get Obj Exporter', buttonLabel='Folder')
        row = cmds.rowLayout(w=self.width,numberOfColumns = 2)
        self.exportButton = cmds.button(label = "Export",w=self.width)
    #@endcond

    def _connect_commands_(self):
        cmds.textFieldButtonGrp(self.txtField,e=1,buttonCommand = lambda*args:self._get_folder_())
        cmds.button(self.exportButton,e=1,command = lambda*args:self._export_objs_())

    def _export_objs_(self):
        folder = cmds.textFieldButtonGrp(self.txtField,text=1,q=1)
        if not folder:
            print "No Folder Defined"
            return

        #Get selected Geo
        selection = libUtilities.get_selected(stringMode=True)

        #If nothing is selected let the user know
        if not selection:
            nothing_selected_box()
            return

        #Iterate though
        for geo in selection:
            cmds.select(geo)
            path = libFile.linux_path(os.path.join(folder,geo+".obj"))
            mel.eval('file -force -options "groups=0;ptgroups=0;materials=0;smoothing=0;normals=0" -typ "OBJexport" -pr -es "%s";'%path)

    def _get_folder_(self):
        res = cmds.fileDialog2(dialogStyle=1,fm=3,cap="Define Obj Export Folder",okc="Set", startingDirectory=pm.workspace.path)
        if res:
            cmds.textFieldButtonGrp(self.txtField,e=1,text=res[0])

    #@cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def title(self):
        '''The property that sets title of the window
        @remark The property ManagerGUI.title is overwritten in this class

        '''

        return "Obj Exporter"
    #@endcond

def nothing_selected_box():
    '''Bring the error message in case nothing is selected'''
    cmds.confirmDialog(title = "Error" ,message = "Nothing is Selected" )