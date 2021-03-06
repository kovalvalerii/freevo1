# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A plugin to view your list of favorites.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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
# -----------------------------------------------------------------------
import logging
logger = logging.getLogger("freevo.tv.plugins.view_favorites")


import os
import config, plugin, menu, rc
from tv.record_client import RecordClient

from item import Item
from tv.favoriteitem import FavoriteItem
from gui.AlertBox import AlertBox
import dialog


class ViewFavoritesItem(Item):
    def __init__(self, parent):
        logger.log( 9, 'ViewFavoritesItem.__init__(parent=%r)', parent)
        Item.__init__(self, parent, skin_type='tv')
        self.name = _('View Favorites')
        self.menuw = None
        self.recordclient = RecordClient()


    def actions(self):
        logger.log( 9, 'actions()')
        return [ ( self.view_favorites , _('View Favorites') ),
                 ( self.reschedule_favorites, _('Reschedule Favorites'))]


    def view_favorites(self, arg=None, menuw=None):
        logger.log( 9, 'view_favorites(arg=%r, menuw=%r)', arg, menuw)
        if not self.recordclient.pingNow():
            dialog.show_alert(self.recordclient.recordserverdown)
            return

        items = self.get_items()
        if not len(items):
            dialog.show_alert(_('No favorites.'))
            return

        favorite_menu = menu.Menu(_( 'View Favorites'), items, reload_func=self.reload, item_types='tv favorite menu')
        self.menuw = menuw
        menuw.pushmenu(favorite_menu)
        menuw.refresh()


    def reschedule_favorites(self, arg=None, menuw=None):
        """
        Force rescheduling of favorites
        """
        logger.log( 9, 'resched_favs(arg=%r, menuw=%r)', arg, menuw)
        dialog.show_message(_('Rescheduling Favorites...'))
        self.recordclient.updateFavoritesScheduleCo().connect(self.reschedule_favorites_complete)
        if menuw:
            menuw.delete_submenu()

    def reschedule_favorites_complete(self, result):
        if result:
            dialog.show_message(_('Favorites rescheduled'))
        else:
            dialog.show_alert(_('Reschedule failed'))


    def reload(self):
        logger.log( 9, 'reload()')
        menuw = self.menuw

        menu = menuw.menustack[-1]

        new_choices = self.get_items()
        if not menu.selected in new_choices and len(new_choices):
            sel = menu.choices.index(menu.selected)
            if len(new_choices) <= sel:
                menu.selected = new_choices[-1]
            else:
                menu.selected = new_choices[sel]

        menu.choices = new_choices

        return menu


    def get_items(self):
        logger.log( 9, 'get_items()')
        items = []

        (status, favorites) = self.recordclient.getFavoritesNow()
        if status:
            f = lambda a, b: cmp(a.priority, b.priority)
            favs = favorites.values()
            favs.sort(f)
            for fav in favs:
                items.append(FavoriteItem(self, fav))

        return items



class PluginInterface(plugin.MainMenuPlugin):
    """
    This plugin is used to display your list of favorites.

    | plugin.activate('tv.view_favorites')
    """

    def __init__(self):
        logger.log( 9, 'PluginInterface.__init__()')
        plugin.MainMenuPlugin.__init__(self)

    def items(self, parent):
        logger.log( 9, 'items(parent=%r)', parent)
        return [ ViewFavoritesItem(parent) ]
