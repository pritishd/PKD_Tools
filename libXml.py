'''
@package PKD_Tools.libXml
@brief This package allows you to convert from XML to a dictionary and vice versa
@details Copied from the following link along with some more custom methods

Eventually this module will be phased out in favor of the superior JSON string. However we will keep it just as a backup.

Also some studios sometimes insists on the XML format.

http://libstoragemgmt.sourceforge.net/srcdoc/html/xmltodict_8py_source.html

@code
#Usage
import libXml
#To write a file
libXml.write_xml("c:/test/myXml.xml",myDict["Root"])
#To load the dictionary
myDict= libXml.ConvertXmlToDict("c:/test/myXml.xml")["Root"]
@endcode

'''
from xml.etree import ElementTree
# @cond DOXYGEN_SHOULD_SKIP_THIS
def main():
    configdict = ConvertXmlToDict('config.xml')
    print(configdict)

    # you can access the data as a dictionary
    print configdict['settings']['color']
    configdict['settings']['color'] = 'red'

    # or you can access iings.color
    configdict.settings.color = 'red'

    root = ConvertDictToXml(configdict)

    tree = ElementTree.ElementTree(root)
    tree.write('config.new.xml')


# @endcond

def write_xml(path, to_xml_dict):
    '''
    Write a dictonary to an xml file
    @param path (string) Target path of the xml file
    @param to_xml_dict (dict) Dictionary which will be converted
    '''
    root = ConvertDictToXml(to_xml_dict)
    tree = ElementTree.ElementTree(root)
    tree.write(path)


# @cond DOXYGEN_SHOULD_SKIP_THIS
# Module Code:
class XmlDictObject(dict):
    """
    Adds object like functionality to the standard dictionary.
    """

    def __init__(self, initdict=None):
        if initdict is None:
            initdict = {}
        dict.__init__(self, initdict)

    def __getattr__(self, item):
        return self.__getitem__(item)

    def __setattr__(self, item, value):
        self.__setitem__(item, value)

    def __str__(self):
        if self.has_key('_text'):
            return self.__getitem__('_text')
        else:
            return ''

    @staticmethod
    def Wrap(x):
        """
        Static method to wrap a dictionary recursively as an XmlDictObject
        """

        if isinstance(x, dict):
            return XmlDictObject((k, XmlDictObject.Wrap(v)) for (k, v) in x.iteritems())
        elif isinstance(x, list):
            return [XmlDictObject.Wrap(v) for v in x]
        else:
            return x

    @staticmethod
    def _UnWrap(x):
        if isinstance(x, dict):
            return dict((k, XmlDictObject._UnWrap(v)) for (k, v) in x.iteritems())
        elif isinstance(x, list):
            return [XmlDictObject._UnWrap(v) for v in x]
        else:
            return x

    def UnWrap(self):
        """
        Recursively converts an XmlDictObject to a standard dictionary and returns the result.
        """

        return XmlDictObject._UnWrap(self)
#@endcond
def _ConvertDictToXmlRecurse(parent, dictitem):
    assert type(dictitem) is not type([])

    if isinstance(dictitem, dict):
        for (tag, child) in dictitem.iteritems():
            if str(tag) == '_text':
                parent.text = str(child)
            elif type(child) is type([]):
                # iterate through the array and convert
                for listchild in child:
                    elem = ElementTree.Element(tag)
                    parent.append(elem)
                    _ConvertDictToXmlRecurse(elem, listchild)
            else:
                elem = ElementTree.Element(tag)
                parent.append(elem)
                _ConvertDictToXmlRecurse(elem, child)
    else:
        parent.text = str(dictitem)

def ConvertDictToXml(xmldict):
    """
    Converts a dictionary to an XML ElementTree Element
    """

    roottag = xmldict.keys()[0]
    root = ElementTree.Element(roottag)
    _ConvertDictToXmlRecurse(root, xmldict[roottag])
    return root

def _ConvertXmlToDictRecurse(node, dictclass):
    nodedict = dictclass()

    if len(node.items()) > 0:
        # if we have attributes, set them
        nodedict.update(dict(node.items()))

    for child in node:
        # recursively add the element's children
        newitem = _ConvertXmlToDictRecurse(child, dictclass)
        if type(newitem) == type(""):
            # Convert to a float item if string is a number
            if newitem.replace('e-', '', 1).replace("-", "", 1).replace('.', '', 1).isdigit():
                newitem = float(newitem)
        if nodedict.has_key(child.tag):
            # found duplicate tag, force a list
            if type(nodedict[child.tag]) is type([]):
                # append to existing list
                nodedict[child.tag].append(newitem)
            else:
                # convert to list
                nodedict[child.tag] = [nodedict[child.tag], newitem]
        else:
            # only one, directly set the dictionary
            nodedict[child.tag] = newitem

    if node.text is None:
        text = ''
    else:
        text = node.text.strip()

    if len(nodedict) > 0:
        # if we have a dictionary add the text as a dictionary value (if there is any)
        if len(text) > 0:
            nodedict['_text'] = text
    else:
        # if we don't have child nodes or attributes, just set the text
        nodedict = text

    return nodedict

def ConvertXmlToDict(root, dictclass=XmlDictObject):
    """
    Converts an XML file or ElementTree Element to a dictionary
    """
    # If a string is passed in, try to open it as a file
    if type(root) == type(''):
        root = ElementTree.parse(root).getroot()
    elif not isinstance(root, ElementTree.Element):
        raise TypeError, 'Expected ElementTree.Element or file path string'

    return dictclass({root.tag: _ConvertXmlToDictRecurse(root, dictclass)})


def list_persist(target):
    '''Make sure a item is a list. if not then make one'''
    if type(target) != list:
        target = [target]
    return target

if __name__ == '__main__':
    main()