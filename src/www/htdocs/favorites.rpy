#!/usr/bin/python

#if 0 /*
# -----------------------------------------------------------------------
# favorites.rpy - Web interface to display your favorite programs.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.1  2003/05/11 22:48:21  rshortt
# Replacements for the cgi files to be used with the new webserver.  These
# already use record_client / record_server.
#
#
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

import sys, time

import record_client as ri
import tv_util

from twisted.web.resource import Resource
from web_types import HTMLResource

TRUE = 1
FALSE = 0

class FavoritesResource(Resource):

    def render(self, request):
        fv = HTMLResource()
        form = request.args

        action = fv.formValue(form, 'action')
        oldname = fv.formValue(form, 'oldname')
        name = fv.formValue(form, 'name')
        title = fv.formValue(form, 'title')
        chan = fv.formValue(form, 'chan')
        dow = fv.formValue(form, 'dow')
        mod = fv.formValue(form, 'mod')
        priority = fv.formValue(form, 'priority')


        if action == 'remove':
            ri.removeFavorite(name)
            pass
        elif action == 'add':
            ri.addEditedFavorite(name, title, chan, dow, mod, priority)
            pass
        elif action == 'edit':
            ri.removeFavorite(oldname)
            ri.addEditedFavorite(name, title, chan, dow, mod, priority)
        elif action == 'bump':
            ri.adjustPriority(name, priority)
        else:
            pass

        (status, favorites) = ri.getFavorites()


        days = {
            '0' : 'Monday',
            '1' : 'Tuesday',
            '2' : 'Wednesday',
            '3' : 'Thursday',
            '4' : 'Friday',
            '5' : 'Saturday',
            '6' : 'Sunday'
        }

        fv.printHeader('Favorites', 'styles/main.css')

        fv.tableOpen('border="0" cellpadding="4" cellspacing="1" width="100%"')
        fv.tableRowOpen('class="chanrow"')
        fv.tableCell('<img src="images/logo_200x100.png" />', 'align=left')
        fv.tableCell('Favorites', 'class="heading" align="left"')
        fv.tableRowClose()
        fv.tableClose()

        fv.tableOpen('border="0" cellpadding="4" cellspacing="1" width="100%"')
        fv.tableRowOpen('class="chanrow"')
        fv.tableCell('Favorite Name', 'class="guidehead" align="center" colspan="1"')
        fv.tableCell('Program', 'class="guidehead" align="center" colspan="1"')
        fv.tableCell('Channel', 'class="guidehead" align="center" colspan="1"')
        fv.tableCell('Day of week', 'class="guidehead" align="center" colspan="1"')
        fv.tableCell('Time of day', 'class="guidehead" align="center" colspan="1"')
        fv.tableCell('Actions', 'class="guidehead" align="center" colspan="1"')
        fv.tableCell('Priority', 'class="guidehead" align="center" colspan="1"')
        fv.tableRowClose()

        f = lambda a, b: cmp(a.priority, b.priority)
        favs = favorites.values()
        favs.sort(f)
        for fav in favs:
            status = 'favorite'

            fv.tableRowOpen('class="chanrow"')
            fv.tableCell(fav.name, 'class="'+status+'" align="left" colspan="1"')
            fv.tableCell(fav.title, 'class="'+status+'" align="left" colspan="1"')
            fv.tableCell(fav.channel_id, 'class="'+status+'" align="left" colspan="1"')

            if fav.dow != 'ANY':
                # cell = time.strftime('%b %d %H:%M', time.localtime(fav.start))
                cell = '%s' % days[fav.dow]
            else:
                cell = 'ANY'
            fv.tableCell(cell, 'class="'+status+'" align="left" colspan="1"')

            if fav.mod != 'ANY':
                # cell = time.strftime('%b %d %H:%M', time.localtime(fav.start))
                cell = '%s' % tv_util.minToTOD(fav.mod)
            else:
                cell = 'ANY'
            fv.tableCell(cell, 'class="'+status+'" align="left" colspan="1"')

            # cell = '<input type="hidden" name="action" value="%s">' % action
            cell = '<a href="edit_favorite.rpy?action=edit&name=%s">Edit</a>, ' % fav.name
            cell += '<a href="favorites.rpy?action=remove&name=%s">Remove</a>' % fav.name
            fv.tableCell(cell, 'class="'+status+'" align="left" colspan="1"')

            cell = ''

            if favs.index(fav) != 0:
                tmp_prio = int(fav.priority) - 1
                cell += '<a href="favorites.rpy?action=bump&name=%s&priority=-1">Higher</a>' % fav.name

            if favs.index(fav) != 0 and favs.index(fav) != len(favs)-1:
                cell += ' | '

            if favs.index(fav) != len(favs)-1:
                tmp_prio = int(fav.priority) + 1
                cell += '<a href="favorites.rpy?action=bump&name=%s&priority=1">Lower</a>' % fav.name

            fv.tableCell(cell, 'class="'+status+'" align="left" colspan="1"')
        
            fv.tableRowClose()

        fv.tableClose()

        fv.printSearchForm()

        fv.printLinks()

        fv.printFooter()

        return fv.res
    
resource = FavoritesResource()

