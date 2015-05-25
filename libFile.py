'''
@package PKD_Tools.libFile
@brief Common OS methods encapsulated in a user friendly method.
'''

import pymel.core as pm
from maya import mel
import os

def linux_path(windowsPath):
    """Convert Windows Path to Linux Path
    @code
    print libFile.linux_path(r"c:\myDir\mayaFile.ma")
    # Result: 'c:/myDir/mayaFile.ma' #
    @endcode

    @param windowsPath (string) folder or file path
    @return maya compliant file path

    """
    return str(windowsPath.replace("\\","/"))

def windows_path(linuxPath):
    """Convert Linux Path to Windows Path
    @code
    print libFile.windows_path('c:/myDir/mayaFile.ma')
    # Result: 'c:\\myDir\\mayaFile.ma' #
    @endcode

    @param linuxPath (string) folder or file path
    @return return a windows based file path
    """
    return str(linuxPath.replace("/","\\"))

def importFile(filePath):
    """
    Import a file without any namespace or any top groups. Works on both .ma and .mb extensions

    @code
    import libFile
    libFile.importFile(r"c:\myFolder\test.ma")
    @endcode

    @attention Watch out for clashing names with existing nodes.
    """
    extension = None
    #Determine what kind of maya file are we dealing with
    if filePath.split(".")[-1] == "mb":
        extension = "mayaBinary"
    else:
        extension = "mayaAscii"
    #Make sure the filepath is maya compliant filepath
    filePath = linux_path(filePath)

    #Import the file
    evalLine = 'file -import -type "%s" -ra true -rpr "PKDTemp" -options "v=0" -pr -loadReferenceDepth "all" "%s";'%(extension,filePath)

    #Print out the file debug statement
    print  evalLine
    mel.eval(evalLine)

    #Remove the namespace from the nodes.
    for node in pm.ls("PKDTemp*"):
        node.unlock()
        node.rename(str(node).replace("PKDTemp_",""))


def safePath(path):
    '''
    Take care of common syntax by a coder where he forgets to add '/' at the end of folder path. It would first replace the "\\" with "/"

    @code
    print libFile.safePath(r"c:\myDir")
    # Result: 'c:/myDir/' #
    @endcode

    @param path (string) Path that needs to be made safe"
    @return Maya compliant path with the '/' at the end

    '''
    path=linux_path(path)
    if path[-1] != "/":
        path=path+"/"
    return path

def folder_check(dirPath):
    """Check the existence of a folder. If not, create the necessary folder tree
    @param dirPath (string) folder path
    @return same folder path with the '/' at the end
    """
    dirPath=linux_path(dirPath)
    if not os.path.exists(dirPath):
        os.makedirs(dirPath)
    return safePath(dirPath)

def get_parent_folder(filePath):
    """Get Parent Folder
    @param filePath (string)
    @return The parent folder of the path

    """
    return os.path.dirname(filePath)

def join(folder,fileName):
    """Return a Maya Compliant File Path
    @param folder (string) The target folder
    @param fileName (string) the File name
    @return Joined maya compliant path
    """
    return linux_path(os.path.join(folder,fileName))

def exists(path):
    """Check if a path exists
    @param path (string) Path that is used for checking
    @return bool status of the path exists
    """
    return os.path.exists(path)

def isdir(path):
    """Return bool if path is a folder
    @param path (string) Path that is used for checking
    @return bool status of whether it is a directory"""
    return os.path.isdir(path)

def has_extension(path,extension):
    """Return bool if a path ends with certain extension
    @param path (string) Path that is used for checking
    @param extension (string) Extension that is being checked. No need to add a '.' in front
    @return bool status whether it ends with the extension
    """
    return path.lower().endswith('.%s'%extension)