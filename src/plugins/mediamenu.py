#if 0 /*
# -----------------------------------------------------------------------
# mediamenu.py - Basic menu for all kinds of media
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.33  2004/02/05 19:48:49  dischi
# handle directory stuff as strings
#
# Revision 1.32  2004/01/31 13:15:56  dischi
# do not use eval
#
# Revision 1.31  2004/01/25 11:40:56  dischi
# fix handling of share filenames
#
# Revision 1.30  2004/01/13 19:12:48  dischi
# Small bugfix
#
# Revision 1.29  2004/01/11 15:44:01  dischi
# changed menu display type to 'x main menu'
#
# Revision 1.28  2003/12/06 13:47:11  dischi
# better fxd handling
#
# Revision 1.27  2003/12/01 19:09:37  dischi
# better handling of the MimetypePlugin
#
# Revision 1.26  2003/11/30 14:41:10  dischi
# use new Mimetype plugin interface
#
# Revision 1.25  2003/11/28 19:26:37  dischi
# renamed some config variables
#
# Revision 1.24  2003/11/26 18:30:22  dischi
# make it possible to add fxd items and not only directories
#
# Revision 1.23  2003/10/11 12:34:36  dischi
# Add SKIN_FORCE_TEXTVIEW_STYLE and SKIN_MEDIAMENU_FORCE_TEXTVIEW to config
# to add more control when to switch to text view.
#
# Revision 1.22  2003/10/04 18:37:29  dischi
# i18n changes and True/False usage
#
# Revision 1.21  2003/09/21 13:19:13  dischi
# make it possible to change between video, audio, image and games view
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
import traceback
import copy

import config
import menu
import rc
import directory

import plugin
import plugins.rom_drives

from event import *
from item import Item


class PluginInterface(plugin.MainMenuPlugin):
    """
    Plugin to integrate a mediamenu (video/audio/image/games) into
    the Freevo main menu. This plugin is auto-loaded when you activate
    the 'video', 'audio', 'image' or 'games' plugin.
    """
    def __init__(self, type=None, force_text_view=FALSE):
        plugin.MainMenuPlugin.__init__(self)
        self.type = type
        self.force_text_view = force_text_view or config.SKIN_MEDIAMENU_FORCE_TEXTVIEW


    def items(self, parent):
        return [ menu.MenuItem('', action=MediaMenu().main_menu,
                               arg=(self.type,self.force_text_view), type='main',
                               parent=parent, skin_type = self.type) ]



class MediaMenu(Item):
    """
    This is the main menu for audio, video and images. It displays the default
    directories and the ROM_DRIVES
    """
    
    def __init__(self):
        Item.__init__(self)
        self.type = 'mediamenu'


    def main_menu_generate(self):
        """
        generate the items for the main menu. This is needed when first generating
        the menu and if something changes by pressing the EJECT button
        """
        items = copy.copy(self.normal_items)

        if config.HIDE_UNUSABLE_DISCS:
            dir_types = {
                'audio': [ 'dir', 'audiocd', 'audio', 'empty_cdrom' ],
                'video': [ 'dir', 'video', 'vcd', 'dvd', 'empty_cdrom' ],
                'image': [ 'dir', 'empty_cdrom' ],
                'games': [ 'dir', 'empty_cdrom' ],
                }
        else:
            dir_types = {}
            for type in ('audio', 'video', 'image', 'games'):
                dir_types[type] = [ 'dir', 'audiocd', 'audio', 'video',
                                    'vcd', 'dvd', 'empty_cdrom' ]
                
        if self.display_type:
            plugins_list = plugin.get('mainmenu_%s' % self.display_type)
        else:
            plugins_list = []

        dir_type = dir_types.get( self.display_type, [ ] )
        
        for p in plugins_list:
            
            if isinstance( p, plugins.rom_drives.rom_items ):
                # do not show media from other menus
                for i in p.items( self ):
                    if i.type in dir_type:
                        items.append(i)
            else:
                items += p.items( self )

        return items


    def main_menu(self, arg=None, menuw=None):
        """
        display the (IMAGE|VIDEO|AUDIO|GAMES) main menu
        """
        self.display_type, force_text_view = arg
        title = _('Media')

        self.menuw = menuw
        
        if self.display_type == 'video':
            title = _('Movie')
        if self.display_type == 'audio':
            title = _('Audio')
        if self.display_type == 'image':
            title = _('Image')
        if self.display_type == 'games':
            title = _('Games')

        menutitle = _('%s Main Menu') % title
        
        if self.display_type:
            items = getattr(config, '%s_ITEMS' % self.display_type.upper())
        else:
            items = []

        self.normal_items = []

        # add default items
        for item in items:
            try:
                add_args = None
                if isinstance(item, str):
                    title, filename = '', item
                else:
                    (title, filename) = item[:2]
                    if len(item) > 2:
                        add_args = item[2:]

                if vfs.isdir(filename):
                    item = directory.DirItem(String(filename), self,
                                             display_type=self.display_type,
                                             add_args=add_args)
                    if title:
                        item.name = title
                    self.normal_items.append(item)
                else:
                    if not vfs.isfile(filename):
                        filename = filename[len(os.getcwd()):]
                        if filename[0] == '/':
                            filename = filename[1:]
                        filename = vfs.join(config.SHARE_DIR, filename)
                    # normal file
                    for p in plugin.mimetype(self.display_type):
                        items = p.get(self, [ String(filename) ])
                        if title:
                            for i in items:
                                i.name = title
                        self.normal_items += items
                        

            except:
                traceback.print_exc()


        item_menu = menu.Menu(menutitle, self.main_menu_generate(),
                              item_types = '%s main menu' % self.display_type,
                              umount_all=1, reload_func = self.reload)
        item_menu.skin_force_text_view = force_text_view
        self.menuw = menuw
        menuw.pushmenu(item_menu)


    def reload(self):
        menuw = self.menuw

        menu = menuw.menustack[1]

        sel = menu.choices.index(menu.selected)
        new_choices = self.main_menu_generate()
        if not menu.selected in new_choices:
            if len(new_choices) <= sel:
                menu.selected = new_choices[-1]
            else:
                menu.selected = new_choices[sel]
        menu.choices = new_choices
        return menu


    def eventhandler(self, event = None, menuw=None):
        """
        eventhandler for the main menu. The menu must be regenerated
        when a disc in a rom drive changes
        """
        if plugin.isevent(event):
            if not menuw:
                menuw = self.menuw

            menu = menuw.menustack[1]

            sel = menu.choices.index(menu.selected)
            menuw.menustack[1].choices = self.main_menu_generate()
            if not menu.selected in menu.choices:
                if len( menu.choices ) > sel:
                    menu.selected = menu.choices[sel]
                elif menu.choices:
                    menu.selected = menu.choices[ -1 ]
                else:
                    menu.selected = None

            if menu == menuw.menustack[-1] and not rc.app():
                menuw.init_page()
                menuw.refresh()
            return True

        if event in (PLAY_END, USER_END, STOP) and event.context != 'menu':
            menuw.show()
            return True

        # give the event to the next eventhandler in the list
        return Item.eventhandler(self, event, menuw)
