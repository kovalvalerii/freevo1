#if 0 /*
# -----------------------------------------------------------------------
# item.py - Template for an item
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.37  2003/12/29 22:31:10  dischi
# do not delete empty strings as file
#
# Revision 1.36  2003/12/29 22:06:01  dischi
# Add support for url inside an item. This is usefull for items depending
# on files or other types of url. If set_url is used, other special
# attributes are set.
#
# Revision 1.35  2003/12/06 13:46:47  dischi
# return nothing if there is no length (e.g. webradio)
#
# Revision 1.34  2003/11/30 14:34:29  dischi
# but the skin parsing (e.g. outicon) in Item to avoid duplicate code
#
# Revision 1.33  2003/11/28 20:08:56  dischi
# renamed some config variables
#
# Revision 1.32  2003/10/28 19:32:36  dischi
# do not inherit watermark images
#
# Revision 1.31  2003/10/19 14:03:25  dischi
# external i18n support for plugins
#
# Revision 1.30  2003/10/17 18:48:37  dischi
# every item has a description now
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2002 Krister Lagerstrom, et al. 
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# ----------------------------------------------------------------------- */
#endif

import os
import gettext
import shutil
import mmpython

import config
from event import *
import plugin
import util

class FileInformation:
    """
    file operations for an item
    """
    def __init__(self):
        self.files     = []
        self.fxd_file  = ''
        self.image     = ''
        self.read_only = False


    def append(self, filename):
        self.files.append(filename)


    def get(self):
        return self.files


    def copy_possible(self):
        return self.files != []

    
    def copy(self, destdir):
        for f in self.files + [ self.fxd_file, self.image ]:
            if f:
                shutil.copy(f, destdir)


    def move_possible(self):
        return self.files and not self.read_only


    def move(self, destdir):
        for f in self.files + [ self.fxd_file, self.image ]:
            if f:
                os.system('mv "%s" "%s"' % (f, destdir))

    def delete_possible(self):
        return self.files and not self.read_only


    def delete(self):
        for f in self.files + [ self.fxd_file, self.image ]:
            if not f:
                continue
            if os.path.isdir(f):
                shutil.rmtree(f, ignore_errors=1)
            else:
                try:
                    os.unlink(f)
                except:
                    print 'can\'t delete %s' % f
        
                

class Item:
    """
    Item class. This is the base class for all items in the menu. It's a template
    for MenuItem and for other info items like VideoItem, AudioItem and ImageItem
    """
    def __init__(self, parent=None, info=None, skin_type=None):
        """
        Init the item. Sets all needed variables, if parent is given also inherit
        some settings from there. Set self.info to info if given.
        """
        if not hasattr(self, 'type'):
            self.type     = None            # e.g. video, audio, dir, playlist
        self.name         = ''              # name in menu
        self.image        = None            # imagefile
        self.icon         = None
        if info:
            self.info     = info
        else:
            self.info     = {}
        self.parent       = parent          # parent item to pass unmapped event
        self.fxd_file     = None            # skin informationes etc.
        self.menuw        = None
        self.description  = ''
        self.handle_type  = None            # handle item in skin as video, audio, image
                                            # e.g. a directory has all video info like
                                            # directories of a cdrom

        self.media        = None

        self.eventhandler_plugins = []

        try:
            if parent.DIRECTORY_USE_MEDIAID_TAG_NAMES:
                self.name = info['title']
            
        except (TypeError, AttributeError, KeyError):
            pass
        
        if parent:
            self.image = parent.image
            if self.image and isinstance(self.image, str) and \
                   self.image.find('watermark') > 0 and \
                   self.image.find(config.IMAGE_DIR) == 0:
                self.image = None
            self.handle_type = parent.handle_type
            self.fxd_file    = parent.fxd_file
            self.media       = parent.media
            if hasattr(self.parent, 'fxd_file') and not self.fxd_file:
                self.fxd_file = self.parent.fxd_file
            if hasattr(parent, '_'):
                self._ = parent._

        if skin_type:
            import skin
            settings  = skin.get_singleton().settings
            skin_info = settings.mainmenu.items
            if skin_info.has_key(skin_type):
                skin_info  = skin_info[skin_type]
                self.name  = skin_info.name
                self.image = skin_info.image
                if skin_info.icon:
                    self.icon = os.path.join(settings.icon_dir, skin_info.icon)
                if skin_info.outicon:
                    self.outicon = os.path.join(settings.icon_dir, skin_info.icon)
            


    def copy(self, obj):
        """
        copy all known attributes from 'obj'
        """
        if not self.image:
            self.image = obj.image
        if not self.name:
            self.name  = obj.name
            
        self.fxd_file     = obj.fxd_file
        self.handle_type  = obj.handle_type
        self.info         = obj.info
        self.media        = obj.media

        # copy additional attributes if the item has an url, which
        # means it also has attributes like mimetype
        if hasattr(obj, 'url'):
            self.url          = obj.url
            self.network_play = obj.network_play
            self.id           = obj.id
            self.media_id     = obj.media_id
            self.mimetype     = obj.mimetype
            self.filename     = obj.filename
            self.dirname      = obj.dirname
            self.files        = obj.files


    def set_url(self, url, info=True):
        """
        Set a new url to the item and adjust all attributes depending
        on the url.
        """
        self.network_play = True        # network url, like http
        self.url          = url         # the url itself
        self.filename     = ''          # filename if it's a file:// url
        self.dirname      = ''          # directory of the file:// url
        self.mode         = ''          # the type of the url (file, http, dvd...)
        self.mimetype     = ''          # extention or mode
        self.media_id     = ''

        if not url:
            self.files = None
            return
        
        if url.find('://') == -1:
            self.url = 'file://' + url
        
        self.files = FileInformation()
        if self.media:
            self.files.read_only = True

        if self.url.startswith('file://'):
            self.network_play = False
            self.filename     = self.url[7:]
            if os.path.isfile(self.filename):
                self.files.append(self.filename)
                self.dirname = os.path.dirname(self.filename)
                self.image   = util.getimage(self.dirname+'/cover', self.image)

                image = util.getimage(self.filename[:self.filename.rfind('.')])
                if image:
                    self.image = image
                    self.files.image = image
            else:
                self.filename = ''
                self.url      = ''
                return
            
        if info and self.filename:
            if self.parent and self.parent.media:
                mmpython_url = 'cd://%s:%s:%s' % (self.parent.media.devicename,
                                                  self.parent.media.mountdir,
                                                  self.filename[len(self.media.mountdir)+1:])
            else:
                mmpython_url = self.filename
            info = mmpython.parse(mmpython_url)
            if info:
                self.info = info

                
        if not self.name:
            if self.filename:
                self.name = util.getname(self.filename)
            else:
                self.name = self.url

        self.id   = self.url
        self.mode = self.url[:self.url.find('://')]

        if self.mode == 'file':
            try:
                self.mimetype = self.filename[self.filename.rfind('.')+1:].lower()
            except:
                self.mimetype = self.type
        elif self.network_play:
            self.mimetype = self.type
        else:
            self.mimetype = self.url[:self.url.find('://')].lower()


    def translation(self, application):
        """
        Loads the gettext translation for this item (and all it's children).
        This can be used in plugins who are not inside the Freevo distribution.
        After loading the translation, gettext can be used by self._() instead
        of the global _().
        """
        try:
            self._ = gettext.translation(application, os.environ['FREEVO_LOCALE'],
                                         fallback=1).gettext
        except:
            self._ = lambda m: m


    def actions(self):
        """
        returns a list of possible actions on this item. The first
        one is autoselected by pressing SELECT
        """
        return None


    def __call__(self, arg=None, menuw=None):
        """
        call first action in the actions() list
        """
        if self.actions():
            return self.actions()[0][0](arg=arg, menuw=menuw)
        

    def eventhandler(self, event, menuw=None):
        """
        simple eventhandler for an item
        """
        
        if not menuw:
            menuw = self.menuw

        for p in self.eventhandler_plugins:
            if p(event, self, menuw):
                return True
            
        # give the event to the next eventhandler in the list
        if self.parent:
            return self.parent.eventhandler(event, menuw)

        else:
            if event in (STOP, PLAY_END, USER_END) and menuw:
                if menuw.visible:
                    menuw.refresh()
                else:
                    menuw.show()
                return True

        return False


    def plugin_eventhandler(self, event, menuw=None):
        """
        eventhandler for special pligins for this item
        """
        if not hasattr(self, '__plugin_eventhandler__'):
            self.__plugin_eventhandler__ = []
            for p in plugin.get('item') + plugin.get('item_%s' % self.type):
                if hasattr(p, 'eventhandler'):
                    self.__plugin_eventhandler__.append(p.eventhandler)
        for e in self.__plugin_eventhandler__:
            if e(self, event, menuw):
                return True
        return False
    

    def __getitem__(self, attr):
        """
        return the specific attribute as string or an empty string
        """
        if attr == 'length':
            try:
                length = int(self.info['length'])
            except ValueError:
                return self.info['length']
            except:
                try:
                    length = int(self.length)
                except:
                    return ''
            if length == 0:
                return ''
            if length / 3600:
                return '%d:%02d:%02d' % ( length / 3600, (length % 3600) / 60, length % 60)
            else:
                return '%d:%02d' % (length / 60, length % 60)

        if attr[:4] == 'len(' and attr[-1] == ')':
            try:
                r = self.info[attr[4:-1]]
            except:
                try:
                    r = getattr(self,attr[4:-1])
                except:
                    return 0
                
            if r != None:
                return len(r)

        else:
            r = None
            try:
                r = self.info[attr]
            except:
                pass
            if not r:
                try:
                    r = getattr(self,attr)
                except:
                    pass
                
            if r != None and str(r):
                return str(r)
        return ''


    def getattr(self, attr):
        """
        wrapper for __getitem__
        """
        return self.__getitem__(attr)
