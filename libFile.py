"""
@package PKD_Tools.libFile
@brief Common OS methods encapsulated in a user friendly method.
"""

import inspect
import os
import shutil
import fnmatch
import json

import pymel.core as pm
from maya import mel


def linux_path(windowsPath):
    """Convert Windows Path to Linux Path
    @code
    print libFile.linux_path(r"c:\myDir\mayaFile.ma")
    # Result: 'c:/myDir/mayaFile.ma' #
    @endcode

    @param windowsPath (string) Folder or file path
    @return maya compliant file path

    """
    return str(windowsPath.replace("\\", "/"))


def windows_path(linuxPath):
    """Convert Linux Path to Windows Path
    @code
    print libFile.windows_path('c:/myDir/mayaFile.ma')
    # Result: 'c:\\myDir\\mayaFile.ma' #
    @endcode

    @param linuxPath (string) Folder or file path
    @return return a windows based file path
    """
    return str(linuxPath.replace("/", "\\"))


def importFile(filePath):
    """
    Import a file without any namespace or any top groups. Works on both .ma and .mb extensions

    @code
    import libFile
    libFile.importFile(r"c:\myFolder\test.ma")
    @endcode

    @attention Watch out for Fashing names with existing nodes.
    """
    extension = None
    # Determine what kind of maya file are we dealing with
    if has_extension(filePath, "mb"):
        extension = "mayaBinary"
    elif has_extension(filePath, "obj"):
        pm.loadPlugin("objExport")
        extension = "OBJ"
    else:
        extension = "mayaAscii"
    # Make sure the filepath is maya compliant filepath
    filePath = linux_path(filePath)

    # Import the file
    evalLine = 'file -import -type "%s" -ra true -rpr "PKDTemp" -options "v=0" -pr -loadReferenceDepth "all" "%s";' % (
        extension, filePath)

    # Print out the file debug statement
    print(evalLine)
    mel.eval(evalLine)

    # Remove the namespace from the nodes.
    for node in pm.ls("PKDTemp*"):
        node.unlock()
        newName = str(node).replace("PKDTemp_", "")
        node.rename(newName)
        if ":" in node.name():
            print ("Unable to rename: " + node)


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
    path = linux_path(path)
    if path[-1] != "/":
        path += "/"
    return path


def folder_check(dirPath):
    """
    Check the existence of a folder. If not, create the necessary folder tree
    @param dirPath (string) Folder path
    @return same folder path with the '/' at the end
    """
    dirPath = linux_path(dirPath)
    if not os.path.exists(dirPath):
        os.makedirs(dirPath)
    return safePath(dirPath)


def folder_check_advanced(folder):
    """
    Advanced Folder Checking. Raise exception in case an folder type is not given or it does not exists
    @param folder (string) Folder path
    @return folder (string) maya compliant path
    """
    # Get the root folder from the user
    # Make sure it exists
    if exists(folder):
        # Make sure that it is not a file
        if isdir(folder):
            # Save as maya compliant path
            return safePath(folder)
        else:
            raise RuntimeError("Not a folder: " + folder)
    else:
        raise RuntimeError("Folder does not exists: " + folder)


def get_parent_folder(filePath):
    """Get the parent folder for the path.
    @param filePath (string) The path that is being queried
    @return The parent folder of the path

    """
    return os.path.dirname(filePath)


def join(folder, fileName):
    """Return a Maya Compliant File Path
    @param folder (string) The target folder
    @param fileName (string) The file name
    @return Joined maya compliant path
    """
    return linux_path(os.path.join(folder, fileName))


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


def has_extension(path, extension):
    """Return bool if a path ends with certain extension
    @param path (string) Path that is used for checking
    @param extension (string) Extension that is being checked. No need to add a '.' in front
    @return bool status whether it ends with the extension
    """
    return path.lower().endswith('.%s' % extension)


def listfolders(path):
    """
    List the folders for the path
    @param path (string) Path that is queried for folders
    @return list of folders for this path
    """
    res = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
    return res


def listfiles(path, extension=''):
    """
    List the files for the path
    @param path (string) Path that is queried for files
    @param extension (string) Filter result based on certain extension
    @return list of files in that folder
    """
    res = [d for d in os.listdir(path) if os.path.isfile(os.path.join(path, d))]
    if extension:
        extRes = [f for f in res if has_extension(f, extension)]
        return extRes
    else:
        return res


def ma_export(path):
    """Export a maya file
    @param path (string) Path where the maya selection will be exported to
    """
    mel.eval('file -force -options "v=0;" -typ "mayaAscii" -es "%s";' % path)


def get_file_folder_extension(path):
    """Return a tuple of split paths
    @param path (string) Path which needs to be evaluated
    """
    fileOnlyName = os.path.basename(path)
    # Filter out the extension
    fileName = fileOnlyName[:fileOnlyName.rfind('.')]
    folder = get_parent_folder(path)
    extension = path.split(".")[-1]
    return fileName, folder, extension


def copyfile(source, target):
    """Convenience method tp copy file from one location to another
    @param source (string) Path for the source file
    @param target (string) Path for the destination file
    """
    shutil.copy(source, target)

def delete_folder_content(folderPath):
    """Delete all the contents in folder path
    @param folderPath (string) Folder whose content needs to be deleted
    """
    if exists(folderPath):
        for root, dirs, files in os.walk(folderPath):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))


def open_folder_in_windows_explorer(path):
    """
    Open a path in windows explorer
    @param path (string) Path to open in windows explorer
    """
    os.startfile(linux_path(path))


def current_working_directory():
    """
    Returns the location where this module is being excecuted
    @return (string) Path on the drive.
    """
    currentPath = os.path.normpath(os.path.dirname(inspect.getfile(inspect.currentframe())))
    return currentPath


def search_pattern_in_folder(searchPattern, folder):
    """
    Search for certain files in a folder based on a pattern
    @param searchPattern (string) Search pattern that is queried
    @param folder (string) The target folder
    @return list of file names that matches the pattern
    """
    result = []
    for fileName in listfiles(folder):
        if fnmatch.fnmatch(fileName, searchPattern):
            result.append(fileName)
    return result


def load_json(path):
    """Read json information
    @param path (string) The path to the json file"""

    with open(path, 'r') as f:
        return json.load(f)


def write_json(path, data):
    """Write json information
    @param path (string) The path to the json file
    @param data (string) The information that is written
    """
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)


def remove(path):
    """Delete a file
    @param path (string) Delete filepath
    """
    os.remove(path)
