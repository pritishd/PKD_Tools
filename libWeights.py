"""
@package PKD_Tools.libWeights
@brief This package allows you to import/export weights of various deformers.

@details For a seamless import/export the following is assumed
<ol>
<li>The geometry is imported and not referenced. </li>
<li>The number of vertices on the geometry itself has not changed.</li>
<li>During export, the target geometry must be selected.</li>
<li>If there are existing deformers on the geometry, make sure their names are the same as the exported data so that correct weights are imported</li>
<li>If you want the deformer to be rebuilt ensure that the same deformer name does not exists in target/import scene. As a best practice, always rename your
deformers in your source/export scene.</li>
</ol>

Current supported deformers are
<ul>
<li>SkinClusters</li>
<li>Clusters</li>
<li>Blendshapes</li>
</ul>

<h3>Weights/MultiWeights</h3>
Deals with exporting and importing the weight of the deformer on a target geometry. By default we use Maya native <i>deformerWeights</i> command which
exports out a json file. However in the case of blendshapes this is not possible yet. (Maya limitation? Needs for exploration)

With this, we save the hassle of reading the weights and exporting them as Maya does that for us. Similarly it takes care of the same on the import side.

Furthermore this will ensure a smooth data transfer between different versions of Maya as hopefully Maya will take care of legacy compalitiy issues.
<ul>
<li>Weights class deals with deformers which usually only has one iteration on a geometry eg skinCluster.</li>
<li>MultiWeights class deals with deformers where muliple instances of the geometry eg blendshapes and clusters</li>
</ul>

<h4>Data</h4>
In addition to the weights file this class would also gather data which will be useful in rebuilding the deformers eg the order of the clusters,
whether it is a relative cluster, the joints used in the skinCluster etc.

<h3>Weightmanager</h3>
The WeightManager class works with multiple geometry at the same time. An json file saves out the following information
<ol>
<li>the list of geometeries processed</li>
<li>Data(as explained before) about the deformers for each geometry</li>
</ol>

<h3>Further Notes</h3>
 With the Weights/Multiweights class you may choose to reimport the weights to a renamed geometry by passing the target to the relevant class, however this may
mean you will have rewrite/extend the capability of the of relevant WeightManager class to handle this

@attention
@htmlonly <li> @endhtmlonlyThis module has not been tested with referenced objects. You may want to set the namespace to ":". Alternatively use the @ref libFile.importFile() command to import your file without namespace. @htmlonly </li> @endhtmlonly
@htmlonly <li> @endhtmlonlyCurrently only polygon models are supported@htmlonly </li> @endhtmlonly
"""

import libUtilities
import libFile
from maya import cmds
import pymel.core as pm


class Weights(object):
    """
    Class to export and import single json weight maps from a geometry.

    @details This class is used when there normaly just one iteration of deformer in the rig eg skinCluster, muscle , cloth etc

    @remarks
    @htmlonly <li> @endhtmlonly A single json file contains the weight map for the deformer.
    The name of this json file is derived from the name of the geometry.
    """

    def __init__(self):
        '''
        @property import_data
        @brief The deformer data that is read from the data json file. This content should be same as @ref export_data
        @property export_data
        @brief The deformer data that is written to the data json file. This content should be same as @ref import_data
        @property target
        @brief The current geometry that is being processed.
        @property data
        @brief Data property which is exported to the single data file.
        @details The deformer is rebuilt from the information that is exported eg joints used in skinning, cluster pivot point. This property will be customised in further subclasses as per their requirement.


        '''
        self.target = None
        self._deformer_ = None
        self._folder_ = None
        self._file_ = None
        self._target_deformer_ = None
        self.import_data = {}
        self.export_data = {}

    def export_weights(self):
        '''@brief Export out the weights. @details Does error checks before exporting. This method may be written in the subclasses
        By default we use the maya deformerWeights command to export the weight'''
        self._error_checks_()

        # NOTE: While maya writes xml files, for the weight, to keep the data type unified we are using json extension
        # for our files
        evalStatment = 'deformerWeights -export -method "index" -deformer "%s" -path "%s" "%s"' % (
            self.target_deformer, self.folder, self.file)
        libUtilities.melEval(evalStatment)
        print "Export Weights for " + self.target

    def _error_checks_(self):
        '''Check that the folder and deformer type is defined'''
        if self.folder is None:
            raise RuntimeError("No Path Defined")
        if self.deformer is None:
            raise RuntimeError("No Deformer Defined")

    def _get_target_defomer_(self):
        '''Define the current deformer property'''
        if self._target_deformer_ is None:
            self._target_deformer_ = libUtilities.get_target_defomer(self.target, self.deformer)
        return self._target_deformer_

    def import_weights(self):
        '''Import the previously exported weights. Attempt to recreate the deformer first in case none are found
        Use the default maya command as much as possible.'''
        # Create the deformers before importing the weights
        self._create_deformers_()
        # Use the maya deformerWeights command to export the weight
        evalStatment = 'deformerWeights -import -method "index" -deformer "%s" -path "%s" "%s"' % (
            self.target_deformer, self.folder, self.file)
        libUtilities.melEval(evalStatment, echo=True)
        print "Import Weights for " + self.target

    def _get_deformer_(self):
        # Return the type of deformer used
        return self._deformer_

    def _set_deformer_(self, deformerString=""):
        # Set the type of deformer property
        sel = cmds.ls(sl=1)
        node = pm.createNode(deformerString)
        # Make sure the deformer type is a supported by Maya
        if node.type() == "unknown":
            raise RuntimeError("Unknown Deformer:" + deformerString)
        self._deformer_ = deformerString
        pm.delete(node)
        if sel:
            cmds.select(sel)

    def _get_file_(self):
        # Return the name of data json file that is linked to the geo
        if not self._file_:
            self._file_ = self.target.split(":")[-1] + ".json"
        return self._file_

    def _set_file_(self, fileName):
        # Check the file ends with json file
        if not libFile.has_extension(fileName, "json"):
            raise RuntimeError("Weight file must end with .json extension")
        # Set the name of data json file that is linked to the geo
        self._file_ = fileName

    def _get_folder_(self):
        # Return the root folder as defined by the user
        return self._folder_

    def _set_folder_(self, folder):
        # Get the root folder from the user
        # Make sure it exists
        if libFile.exists(folder):
            # Make sure that it is not a file
            if libFile.isdir(folder):
                # Save as maya compliant path
                self._folder_ = libFile.linux_path(folder)
            else:
                raise RuntimeError("Not a folder: %s" % folder)
        else:
            raise RuntimeError("Folder does not exists: %s" % folder)

    def _create_deformers_(self):
        '''To be defined in the subclasses'''
        # print a debug statement
        print "Weight class _create_deformers_ called"

    def _set_target_defomer_(self, deformer):
        # Convert target deformer string to pynode
        deformer = pm.PyNode(deformer)
        # Ensure that deformer processes belong to the deformer class
        if deformer.type() != self.deformer:
            raise RuntimeError("Deformer type mismatch")
        else:
            self._target_deformer_ = deformer

    def save_data(self):
        """Save out the deformer information to a test json file"""
        libFile.write_json(self.datapath, {"DeformerInfo": self.data})

    def load_data(self):
        """Load the data information from the test json file"""
        self.data = libFile.load_json(self.datapath)["DeformerInfo"]

    @property
    def datapath(self):
        '''File path to the json file which contains data relevant to the deformer. This property is used in testing scenarios along with @ref load_data /@ref save_data method.
        @code
        import libWeights
        test = libWeights.Weights()
        test.folder = r"C:\temp\test"
        print test.datapath
        # Result: 'c:/temp/test/info.json' #
        @endcode
        @return joined path of folder and the info json file
        '''
        return libFile.join(self.folder, "info.json")

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def data(self):
        # Print debug statement
        print "Base _get_data_ called"

    @data.setter
    def data(self, data):
        # Recieve data from the outside class
        self.import_data = data

    # @endcond

    ##
    # @property folder
    # User defined folder where the weight and data file are saved

    folder = property(_get_folder_, _set_folder_)

    ##
    # @property deformer
    # Which type of deformer is processed. This must be a valid maya node type eg 'skinCluster', 'blendShape' etc

    deformer = property(_get_deformer_, _set_deformer_)

    ##
    # @property target_deformer
    # The target maya deformer on which the export and import commands will be processed
    target_deformer = property(_get_target_defomer_, _set_target_defomer_)

    ##
    # @property file
    # The file name which contains the individual weights'''

    file = property(_get_file_, _set_file_)


class SkinWeights(Weights):
    '''
    Class to import/export skinweights

    @code
    import libWeights
    reload(libWeights)
    test = libWeights.SkinWeights()

    #REQUIRED SETUP
    #Set the target geometry
    test.target = "pCube1"
    #Set the folder where the weights will be exported
    test.folder = r"C:\temp\test"

    ##EXPORT SETUP
    #Save out the weights
    test.export_weights()
    #Test that deformer related data is gathered
    test.save_data()

    ##IMPORT SETUP
    #Load the deformer data from the test json file
    test.load_data()
    #Create deformer if needed and import in the weights
    test.import_weights()
    @endcode

    @attention
    This module works only with joints at the moment. If you are using surfaces as an influence object, you will need to extend capability of this class.
    '''

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(SkinWeights, self).__init__()
        self.deformer = "skinCluster"
        # @endcond

    def import_weights(self):
        '''Import the weight of the SkinCluster. After that normalise the weights
        @remark The behaviour of Weights.import_weights is extended in this class
        '''
        super(SkinWeights, self).import_weights()
        # Normalise the skin weights
        pm.select(self.target)
        libUtilities.melEval('doNormalizeWeightsArgList 1 {"4"}')

    def copy_weights(self, newTarget):
        '''@brief Additional function to copy weights from the source geometry to a new one.
        @details This new geometry will be skinned with the same influence joints.
        @code
        test = libWeights.SkinWeights()
        #Set the target geometry
        test.target = "pCube1"
        #copy the weights to the new gometery
        test.copy_weights("pCube2")
        @endcode
        '''
        currentInfluences = pm.skinCluster(self.target_deformer, inf=True, q=True)
        res = libUtilities.skinGeo(newTarget, currentInfluences)
        # Transfer the weights
        pm.copySkinWeights(ss=self.target_deformer, ds=res, noMirror=True, surfaceAssociation="rayCast",
                           influenceAssociation="closestJoint")

    def _create_deformers_(self):
        # Create the skin deformer if none exists
        if not self.target_deformer:
            jnts = []
            noJnts = []
            # Alias for the joint list from the import data. Make sure the data is list
            joint_data = self.import_data["Joints"]
            # Iterate through all the joints in the list
            for jnt in joint_data:
                # Only bind joints that exists
                if pm.objExists(jnt):
                    jnts.append(jnt)
                else:
                    # Log non existing joins
                    noJnts.append(jnt)

            # @cond DOXYGEN_SHOULD_SKIP_THIS
            self.target_deformer = libUtilities.skinGeo(self.target, jnts)
            # @endcond

            # Print out the list of missing joints
            if noJnts:
                print '\n%sThe Following Joints do not exists%s' % (
                    libUtilities.print_attention(), libUtilities.print_attention())
                libUtilities.print_list(noJnts)
                print "\n"

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @Weights.data.getter
    def data(self):
        '''Return the joints in this list to the data property
        @return the joints used for the target skincluster.
        '''
        self.export_data = {"Joints": cmds.skinCluster(str(self.target_deformer), q=1, inf=1)}
        return self.export_data
        # @endcond


class MultiWeights(Weights):
    '''
    Class to export and import weight maps for multiple instances of the same deformers eg blendshapes, wire, clusters etc.
    A folder is created for each geo which contains the weights of the deformers. This class will be customised for each type of deformer.
    '''

    def __init__(self):
        '''@property deformer_data
        @brief Contains @ref Weights.data "data" of each iteration of the deformer. The name of the deformer acts as a key for this dictionary variable'''
        super(MultiWeights, self).__init__()
        self._target_deformers_ = []
        self._target_folder_ = ''
        self.deformer_data = {}

    def export_weights(self):
        '''

        @brief Export the individual weights for each iteration of the deformers.  @details Does error checks before exporting. By default we try to use the maya deformerWeights command to export the weight
        @remark The behaviour of Weights.export_weights is overriden in this class

        '''
        self._error_checks_()
        self._export_individual_weights_()
        print "Export Weights for " + self.target

    def _export_individual_weights_(self):
        # Itererate through all target deformer
        for self.target_deformer in self.target_deformers:
            # Export the weight with the name being the same as deformer
            evalStatment = 'deformerWeights -export -method "index" -deformer "%s" -path "%s" "%s"' % (
                self.target_deformer, self.target_folder, self.file)
            libUtilities.melEval(evalStatment)

    def import_weights(self):
        '''@brief  Import the previously exported weights. @details Attempt to recreate the deformer first in case it is missing. All exported deformers will be recreated.
        Use the default maya command as much as possible.
        @remark The behaviour of Weights.import_weights is overriden in this class
        '''
        self._create_deformers_()
        self._import_individual_weights_()
        print "Import Weights for " + self.target

    def _import_individual_weights_(self):
        # Iterate through all the deformers and import the weigths
        for self.target_deformer in self.import_data["Order"]:
            # Import weight of cluster
            weightInfo = libFile.load_json(libFile.join(self.target_folder, self.file))
            if weightInfo['deformerWeight'].has_key("weights"):
                evalStatment = 'deformerWeights -import -method "index" -deformer "%s" -path "%s" "%s"' % (
                    self.target_deformer, self.target_folder, self.file)
                libUtilities.melEval(evalStatment)

    def _get_deformer_data_(self):
        '''To be defined in the subclasses'''
        # print a debug statement
        print "MultiWeights class _get_deformer_data_ called"

    def _create_deformers_(self):
        '''To be defined in the subclasses'''
        # print a debug statement
        print "MultiWeights class _create_deformers_ called"

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @Weights.data.getter
    def data(self):
        '''The deformer data property'''
        # Gather the export data
        self._get_deformer_data_()
        # Order of deformer
        self.export_data = {"Order": self.target_deformers,
                            "Data": self.deformer_data
                            }
        # Return the export data
        return self.export_data

    @property
    def datapath(self):
        # File path to the json file which contains data relevant to the deformer. Here the data is saved in the subfolder This variable is usually used in testing scenarios
        return libFile.join(self.target_folder, "%sInfo.json" % self.deformer.capitalize())

    @property
    def file(self):
        # Each exported file is based on the name of the deformer rather than the target
        return ("%s.json" % self.target_deformer)

    @property
    def target_deformers(self):
        # Return the list of target deformer type for the geometry
        if not self._target_deformers_:
            self._target_deformers_ = libUtilities.get_target_defomer(self.target, self.deformer, multiple=True)
        return self._target_deformers_

    @property
    def target_folder(self):
        # Create a subfolder with geometry name as the name of the folder
        if not self._target_folder_:
            self._target_folder_ = libFile.folder_check(libFile.join(self.folder, str(self.target)))
        return self._target_folder_

        # @endcond


class ClusterWeights(MultiWeights):
    '''
      Class to import/export cluster weights

      @code
      import libWeights
      reload(libWeights)
      test = libWeights.ClusterWeights()

      #REQUIRED SETUP
      #Set the target geometry
      test.target = "pCube1"
      #Set the folder where the weights will be exported
      test.folder = r"C:\temp\test"

      ##EXPORT SETUP
      #Save out the weights
      test.export_weights()
      #Test that deformer related data is gathered
      test.save_data()

      ##IMPORT SETUP
      #Load the deformer data from the test json file
      test.load_data()
      #Create deformer if needed and import in the weights
      test.import_weights()
      @endcode

      @remark
      The @ref data json file contains the vertices that are affected by the cluster deformer. This takes into account when the user creates a cluster from selected vertices.

    '''

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(ClusterWeights, self).__init__()
        self.deformer = "cluster"
        # @endcond

    def _get_deformer_data_(self):
        # Itererate through all target deformer
        for self.target_deformer in self.target_deformers:
            info = {}
            handle = libUtilities.pyList(self.target_deformer.getDeformerTools())[0]
            # Cluster Handle Name
            info["ClusterHandleName"] = handle.name()
            # Cluster Handle Pivot positions
            info["RotatePivot"] = list(handle.getRotatePivot())
            info["ScalePivot"] = list(handle.getScalePivot())
            # Relative
            info["Relative"] = int(self.target_deformer.relative.get())
            # Vertices affected
            verticesSet = self.target_deformer.listSets()[0]
            info["Vertices"] = libUtilities.indexize_vertice_group(verticesSet.members())
            self.deformer_data[str(self.target_deformer)] = info

    def _create_deformers_(self):
        # Build in the order of the clusters
        for cluster in self.import_data["Order"]:
            if not pm.objExists(cluster):
                # Read info for each cluster
                info = self.import_data["Data"][cluster]
                # select vertices
                libUtilities.select_vertices(self.target, info["Vertices"])
                # Create the cluster
                cltr, cTransform = pm.cluster(rel=info["Relative"])
                # Set the pivot
                pm.setAttr(cTransform.scalePivot, info["ScalePivot"])
                pm.setAttr(cTransform.rotatePivot, info["RotatePivot"])
                # Rename
                cTransform.rename(info["ClusterHandleName"])
                cltr.rename(cluster)


class BlendShapeWeights(MultiWeights):
    '''
      Class to import/export blendshape weights

      @code
      import libWeights
      reload(libWeights)
      test = libWeights.BlendShapeWeights()

      #REQUIRED SETUP
      #Set the target geometry
      test.target = "pCube1"
      #Set the folder where the weights will be exported
      test.folder = r"C:\temp\test"

      ##EXPORT SETUP
      #Save out the weights
      test.export_weights()
      #Test that deformer related data is gathered
      test.save_data()

      ##IMPORT SETUP
      #Load the deformer data from the test json file
      test.load_data()
      #Create deformer if needed and import in the weights
      test.import_weights()
      @endcode

      @attention &bull; This class does not supports painted weights on the envelope. However individual painted weights are supported.
      @attention &bull; If you are rebuilding the blendshapes, then the target shapes needs to imported first before the weights are imported. You may use the @ref libFile.importFile() command to import the file with the blendshapes.

    '''

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(BlendShapeWeights, self).__init__()
        self.deformer = "blendShape"

    # @endcond

    def _get_deformer_data_(self):
        # Itererate through all blendshape
        for self.target_deformer in self.target_deformers:
            self.deformer_data[str(self.target_deformer)] = self.target_deformer.getTarget()

    def _export_individual_weights_(self):
        vertices = pm.polyEvaluate(self.target, vertex=True)
        # Itererate through all target deformer
        for self.target_deformer in self.target_deformers:
            weightMap = {}
            # Iterate through shapes.
            for index, niceName in zip(self.target_deformer.weightIndexList(), self.target_deformer.getTarget()):
                # Get the weights
                weight_cmd = '%s.inputTarget[0].inputTargetGroup[%i].targetWeights[0:%d]' % (
                    self.target_deformer, index, vertices - 1)
                weights = cmds.getAttr(weight_cmd)
                # Check if there are any painted weights.
                if len(list(set(weights))) > 1:
                    weightMap[niceName] = weights

            # Export out the weights map information
            if len(weightMap):
                # Save the json file
                libFile.write_json(self.weight_file, {"WeightMap": weightMap})

    def _create_deformers_(self):
        # Setup missing geo shapes dictionary
        missing_shapes = {}
        # Build in the order of blendshapes
        for blendshape in self.import_data["Order"]:
            # Check if the blendshapes exists. If so create one.
            shapes = self.import_data["Data"][blendshape]
            if not pm.objExists(blendshape):
                # Read info for each blendshape
                # select select the shapes.
                pm.select(cl=1)
                for shape in shapes:
                    # Check the shape exists
                    if pm.objExists(shape):
                        # Add to the selection
                        pm.select(shape, add=1)
                    else:
                        # If not then then add to error list dictionary
                        if missing_shapes.has_key(blendshape):
                            missing_shapes[blendshape].append(shape)
                        else:
                            missing_shapes[blendshape] = [shape]
                # Select the target geo and create blendshape
                pm.select(self.target, add=1)
                pm.blendShape(name=blendshape)

        if missing_shapes:
            print "#######The following blends had missing shapes#######"
            for key in missing_shapes.keys():
                print key.upper()
                libUtilities.print_list(missing_shapes[key])

    def _import_individual_weights_(self):
        # Iterate through all the deformers
        for self.target_deformer in self.target_deformers:
            # Load the weights if they were exported
            if libFile.exists(self.weight_file):
                weightMap = libFile.load_json(self.weight_file)["WeightMap"]
                for index, niceName in zip(self.target_deformer.weightIndexList(), self.target_deformer.getTarget()):
                    # Apply the weight if there was a weight map
                    if weightMap.has_key(niceName):
                        # Get the weight from the dictionary
                        weights = weightMap[niceName]
                        # Set the weight
                        weight_cmd = '%s.inputTarget[0].inputTargetGroup[%i].targetWeights[0:%d]' % (
                            self.target_deformer, index, len(weights) - 1)
                        cmds.setAttr(weight_cmd, *weights)

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def weight_file(self):
        # Return the weight map file for each blendshape
        return libFile.join(self.target_folder, self.file)
        # @endcond


"----------------------------------------------------------------------------------------------------------------------------------------------"


class WeightManager(object):
    '''
    Class which manages the mass import/export of deformers. For import geometry must be selected

    '''

    def __init__(self):
        '''
        @property weight_class
        @brief The Weights class that is used to export/import the weights and deformer data.

        @property command_mode
        @brief boolean flag that is used in @ref libUtilities.get_selected command. By default set to False

        @property progress_tracker
        @brief custom PyQt @ref libPySide.QProgressDialog QProgressDialog to track the progress of a window

        @property current_geo
        @brief the current geo that is being processed

        @property current_mode
        @brief Is it import mode or export mode?

        '''

        self._json_file_ = None
        self.weight_class = None
        self.command_mode = False
        self._deformer_ = None
        self.progress_tracker = None
        self.current_geo = None
        self.current_mode = ""

    def export_all(self):
        """Exports the weights and deformer data of the selected objects using the @ref weight_class"""
        # get the selected geo

        if not self.targets:
            # In nothing has been selected
            return False

        # Setup the geo dictionary
        geoInfo = {}
        targets = self.targets
        # Iterate through all the geo
        for self.current_geo in self.targets:
            # Ensure the geometry has the deformer
            if not libUtilities.get_target_defomer(self.current_geo, self.deformer, multiple=True):
                print ("No %s Found for %s" % (self.deformer.capitalize(), self.current_geo))
                self.update_progress()
                continue
            # Initialise the weight class
            deformerWeight = self._initialise_class_(self.current_geo)
            # Export the weight
            deformerWeight.export_weights()
            # Get the export data
            geoInfo[self.current_geo] = deformerWeight.data
            self.update_progress()

        # Save out the json file
        if geoInfo:
            deformerType = self.deformer.capitalize()
            print ("========{0} Info Path========\n{0}".format(deformerType, self.info_file))
            libFile.write_json(self.info_file, {"{}Info".format(deformerType): geoInfo})

        pm.select(targets)

        # Return a success result
        return True

    def import_all(self):
        """Import the exported weights and data using the @ref weight_class"""
        # Import all Weights for selected object based on the information in the skinInfo
        geoInfo = libFile.load_json(self.info_file)["{}Info".format(self.deformer.capitalize())]
        for self.current_geo in geoInfo:
            if pm.objExists(self.current_geo):
                # Initialise the weight class
                deformerWeight = self._initialise_class_(self.current_geo)
                # Set the deformer data
                deformerWeight.data = geoInfo[self.current_geo]
                # Import the weights
                deformerWeight.import_weights()
            else:
                # Ensure the geometry exists
                print "GEO DOES NOT EXISTS: {}".format(self.current_geo)
            self.update_progress()
        pm.select(cl=1)

    def _initialise_class_(self, geo):
        # Initialise the target class with the target geo
        deformerWeight = self.weight_class()
        deformerWeight.folder = self.folder
        deformerWeight.target = geo
        return deformerWeight

    def _get_json_file_(self):
        # Is the json file defined
        if self._json_file_ is None:
            # raise error
            cmds.error("Json file not defined")
        else:
            # return the Json path
            return self._json_file_

    def _set_json_file_(self, path):
        # Check that the file path ends with json path
        if not libFile.has_extension(path, "json"):
            cmds.error('File path must end with ".json" extensions:{}'.format(path))
        # Check that parent folder exists for the json path
        parent_folder = libFile.get_parent_folder(path)
        if not libFile.exists(parent_folder):
            # Create the parent folder
            libFile.folder_check(parent_folder)
            print "Parent folder of the json file did not exist. A folder was created"
        # Set the json path
        self._json_file_ = libFile.linux_path(path)

    def update_progress(self):
        '''Update the progress tracker'''
        if self.progress_tracker is not None:
            self.progress_tracker.currentTarget = self.current_geo
            self.progress_tracker.update()

    ##
    # @property info_file
    # User defined data path which contains the @ref Weights.data "deformer data" of all the processed geometry.
    info_file = property(_get_json_file_, _set_json_file_)

    @property
    def deformer(self):
        '''returns the Weights.deformer property information'''
        if self._deformer_ is None:
            self._deformer_ = self.weight_class().deformer
        return self._deformer_

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def folder(self):
        # Return the parent folder of the info file
        return libFile.get_parent_folder(self.info_file)

    @property
    def targets(self):
        if self.current_mode == "Export":
            return libUtilities.get_selected(stringMode=True, scriptEditorWarning=self.command_mode)
        else:
            return libFile.load_json(self.info_file)["{}Info".format(self.deformer.capitalize())].keys()
            # @endcond


class SkinWeightManager(WeightManager):
    '''
    Class which manages the mass import/export of skinCluster.
    @code
    import libWeights
    reload(libWeights)
    test = libWeights.SkinWeightManager()

    #REQUIRED SETUP
    #Set the json file path where all deformer info of the selected geometry will be saved
    test.info_file = r"C:/test/SkinData/SkinInfo.json"

    ##EXPORT SETUP
    #Save out the weights
    test.export_all()

    ##IMPORT SETUP
    #Create deformers if needed and import in the weights for all the geometry
    test.import_all()
    @endcode
    '''

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(SkinWeightManager, self).__init__()
        self.weight_class = SkinWeights
        # @endcond


class ClusterWeightManager(WeightManager):
    '''
    Class which manages the mass import/export of clusters.
    @code
    import libWeights
    reload(libWeights)
    test = libWeights.ClusterWeightManager()

    #REQUIRED SETUP
    #Set the json file path where all deformer info of the selected geometry will be saved
    test.info_file = r"C:/test/ClusterData/ClusterInfo.json"

    ##EXPORT SETUP
    #Save out the weights
    test.export_all()

    ##IMPORT SETUP
    #Create deformers if needed and import in the weights for all the geometry
    test.import_all()
    @endcode

    '''

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(ClusterWeightManager, self).__init__()
        self.weight_class = ClusterWeights
        # @endcond


class BlendsWeightManager(WeightManager):
    '''
    Class which manages the mass import/export of blendshapes.
    @code
    import libWeights
    reload(libWeights)
    test = libWeights.BlendsWeightManager()

    #REQUIRED SETUP
    #Set the json file path where all deformer info of the selected geometry will be saved
    test.info_file = r"C:/test/BlendData/BlendInfo.json"

    ##EXPORT SETUP
    #Save out the weights
    test.export_all()

    ##IMPORT SETUP
    #Create deformers if needed and import in the weights for all the geometry
    test.import_all()
    @endcode

    '''

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self):
        super(BlendsWeightManager, self).__init__()
        self.weight_class = BlendShapeWeights
        # @endcond
