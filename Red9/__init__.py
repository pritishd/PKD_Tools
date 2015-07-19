'''

Red9 Studio Pack: Maya Pipeline Solutions
Author: Mark Jackson
email: rednineinfo@gmail.com

Red9 blog : http://red9-consultancy.blogspot.co.uk/
MarkJ blog: http://markj3d.blogspot.co.uk


Core is the library of Python modules that make the backbone of the Red9 Pack
    
:Note that the registerMClassInheritanceMapping() call is after all the imports
so that the global RED9_META_REGISTERY is built up correctly

'''

import General
import Meta
import Tools
import CoreUtils
import AnimationUtils
import PoseSaver
import Audio



def _reload():
    '''
    reload carefully and re-register the RED9_META_REGISTRY
    '''
    reload(General)
    reload(Meta)
    reload(Tools)
    reload(Audio)
    reload(CoreUtils)
    reload(AnimationUtils)
    reload(PoseSaver)
        
    Meta.metaData_sceneCleanups()
    Meta.registerMClassInheritanceMapping()
    print('Red9 Core Reloaded and META REGISTRY updated')
    
def _setlogginglevel_debug(module='all'):
    '''
    Dev wrapper to set the logging level to debug
    '''
    if module=='r9Core' or  module=='all':
        CoreUtils.log.setLevel(CoreUtils.logging.DEBUG)
        print('Red9_CoreUtils set to DEBUG state')
    if module=='r9Anim' or  module=='all':
        AnimationUtils.log.setLevel(AnimationUtils.logging.DEBUG)
        print('Red9_AnimationUtils set to DEBUG state')
    if module=='r9General' or  module=='all':
        General.log.setLevel(General.logging.DEBUG)
        print('Red9_General set to DEBUG state')
    if module=='r9Tools' or  module=='all':
        Tools.log.setLevel(Tools.logging.DEBUG)
        print('Red9_Tools set to DEBUG state')
    if module=='r9Audio' or module=='all':
        Audio.log.setLevel(Audio.logging.DEBUG)
        print('Red9_Meta set to DEBUG state')
    if module=='r9Pose' or  module=='all':
        PoseSaver.log.setLevel(PoseSaver.logging.DEBUG)
        print('Red9_PoseSaver set to DEBUG state')
    if module=='r9Meta' or  module=='all':
        Meta.log.setLevel(Meta.logging.DEBUG)
        print('Red9_Meta set to DEBUG state')

        
def _setlogginglevel_info(module='all'):
    '''
    Dev wrapper to set the logging to Info, usual state
    '''
    if module=='r9Core' or  module=='all':
        CoreUtils.log.setLevel(CoreUtils.logging.INFO)
        print('Red9_CoreUtils set to INFO state')
    if module=='r9Anim' or  module=='all':
        AnimationUtils.log.setLevel(AnimationUtils.logging.INFO)
        print('Red9_AnimationUtils set to INFO state')
    if module=='r9General' or  module=='all':
        General.log.setLevel(General.logging.INFO)
        print('Red9_General set to INFO state')
    if module=='r9Tools' or  module=='all':
        Tools.log.setLevel(Tools.logging.INFO)
        print('Red9_Tools set to INFO state')
    if module=='r9Audio' or module=='all':
        Audio.log.setLevel(Audio.logging.INFO)
        print('Red9_Meta set to DEBUG state')
    if module=='r9Pose' or  module=='all':
        PoseSaver.log.setLevel(PoseSaver.logging.INFO)
        print('Red9_PoseSaver set to INFO state')
    if module=='r9Meta' or  module=='all':
        Meta.log.setLevel(Meta.logging.INFO)
        print('Red9_Meta set to INFO state')


#========================================================================
# This HAS to be at the END of this module so that the RED9_META_REGISTRY
# picks up all inherited subclasses when Red9.core is imported
#========================================================================
Meta.registerMClassInheritanceMapping()
Meta.registerMClassNodeMapping()



