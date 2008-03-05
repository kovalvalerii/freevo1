# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Types for the Freevo Electronic Program Guide module.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
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
# -----------------------------------------------------------------------


import sys
import copy
import time, os, string
import config

# The file format version number. It must be updated when incompatible
# changes are made to the file format.
EPG_VERSION = 6


class TvProgram:

    channel_id = None
    title      = None
    desc       = None
    sub_title  = None
    start      = None
    pdc_start  = None
    stop       = None
    ratings    = None
    advisories = None
    categories = None
    date       = None
    # this information is added by the recordserver
    scheduled  = None
    overlap    = None
    previouslyRecorded = None
    allowDuplicates = None
    onlyNew = None


    def __init__(self, title='', channel_id='', start=0, stop=0, desc=''):
        self.title      = title
        self.channel_id = channel_id
        self.desc       = desc
        self.sub_title  = ''
        self.start      = start
        self.pdc_start  = 0.0
        self.stop       = stop
        self.ratings    = {}
        self.advisories = []
        self.categories = []
        self.date       = None

        # Due to problems with Twisted's marmalade this should not be changed
        # to a boolean type.
        self.scheduled  = 0
        self.overlap    = 0
        self.previouslyRecorded = 0
        self.allowDuplicates = 1
        self.onlyNew = 0


    def __str__(self):
        st = time.localtime(self.pdc_start) # PDC start time
        bt = time.localtime(self.start)   # Beginning time tuple
        et = time.localtime(self.stop)    # End time tuple
        begins = time.strftime('%a %b %d %H:%M', bt)
        starts = time.strftime('%H:%M', st)
        ends = time.strftime('%H:%M', et)
        overlaps = self.overlap and '*' or ' '
        try:
            channel_id = String(self.channel_id)
            title = String(self.title)
            s = '%s->%s (%s)%s %3s %s' % (begins, ends, starts, overlaps, channel_id, title)
        except UnicodeEncodeError: #just in case
            s = '%s->%s [%s]%s %3s %s' % (begins, ends, starts, overlaps, self.channel_id, self.title)
        return s


    def __repr__(self):
        bt = time.localtime(self.start)
        et = time.localtime(self.stop)
        return '<TvProgram %r %s->%s>' % (self.channel_id, time.strftime('%H:%M', bt), time.strftime('%H:%M', et))


    def __eq__(self, other):
        """ equality method """
        if not isinstance(other, TvProgram):
            return False
        return self.start == other.start \
            and self.stop == other.stop \
            and self.title == other.title \
            and self.channel_id == other.channel_id


    def __cmp__(self, other):
        """ compare function, return 0 if the objects are equal, <0 if less >0 if greater """
        if not isinstance(other, TvProgram):
            return 1
        if self.start != other.start:
            return self.start - other.start
        if self.stop != other.stop:
            return self.stop - other.stop
        if self.title != other.title:
            return self.title > other.title
        if self.channel_id != other.channel_id:
            return self.channel_id > other.channel_id
        return 0


    def getattr(self, attr):
        """
        return the specific attribute as string or an empty string
        """
        if attr == 'start':
            return Unicode(time.strftime(config.TV_TIME_FORMAT, time.localtime(self.start)))
        if attr == 'pdc_start':
            return Unicode(time.strftime(config.TV_TIME_FORMAT, time.localtime(self.pdc_start)))
        if attr == 'stop':
            return Unicode(time.strftime(config.TV_TIME_FORMAT, time.localtime(self.stop)))
        if attr == 'date':
            return Unicode(time.strftime(config.TV_DATE_FORMAT, time.localtime(self.start)))
        if attr == 'time':
            return self.getattr('start') + u' - ' + self.getattr('stop')
        if hasattr(self, attr):
            return getattr(self, attr)
        return ''


    def utf2str(self):
        """
        Decode all internal strings from Unicode to String
        """
        ret = copy.copy(self)
        for var in dir(ret):
            if not var.startswith('_') and isinstance(getattr(ret, var), unicode):
                setattr(ret, var, String(getattr(ret, var)))
        return ret


    def str2utf(self):
        """
        Encode all internal strings from String to Unicode
        """
        ret = copy.copy(self)
        for var in dir(ret):
            if not var.startswith('_') and isinstance(getattr(ret, var), str):
                setattr(ret, var, Unicode(getattr(ret, var)))
        return ret


class TvChannel:
    """
    """
    logo = None
    def __init__(self, id, displayname, tunerid, logo='', times=[], programs=[]):
        """ Copy the programs that are inside the indicated time bracket """
        self.id = id
        self.displayname = displayname
        self.tunerid = tunerid
        self.logo = logo
        self.times = times
        self.programs = programs


    def sort(self):
        # Sort the programs so that the earliest is first in the list
        f = lambda a, b: cmp(a.start, b.start)
        self.programs.sort(f)


    def __str__(self):
        s = 'CHANNEL ID   %-20s' % self.id
        if self.programs:
            s += '\n'
            for program in self.programs:
                s += '   ' + String(program) + '\n'
        else:
            s += '     NO DATA\n'
        return s


    def __repr__(self):
        return '<TvChannel %r>' % (self.id)



class TvGuide:
    """
    """
    chan_dict = None
    chan_list = None
    timestamp = 0.0

    def __init__(self):
        # These two types map to the same channel objects
        self.chan_dict = {}   # Channels mapped using the id
        self.chan_list = []   # Channels, ordered
        self.EPG_VERSION = EPG_VERSION


    def add_channel(self, channel):
        if not self.chan_dict.has_key(channel.id):
            # Add the channel to both the dictionary and the list. This works
            # well in Python since they will both point to the same object!
            self.chan_dict[channel.id] = channel
            self.chan_list += [channel]


    def add_program(self, program):
        # The channel must be present, or the program is
        # silently dropped
        if self.chan_dict.has_key(program.channel_id):
            p = self.chan_dict[program.channel_id].programs
            if len(p) and p[-1].start < program.stop and p[-1].stop > program.start:
                # the tv guide is corrupt, the last entry has a stop time higher than
                # the next start time. Correct that by reducing the stop time of
                # the last entry
                _debug_('wrong stop time: %s' % String(self.chan_dict[program.channel_id].programs[-1]))
                self.chan_dict[program.channel_id].programs[-1].stop = program.start

            if len(p) and p[-1].start == p[-1].stop:
                # Oops, something is broken here
                self.chan_dict[program.channel_id].programs = p[:-1]
            self.chan_dict[program.channel_id].programs += [program]


    def get_programs(self, start=0, stop=2147483647, chanids=None):
        """
        Get all programs that occur at least partially between the start and stop
        timeframe.
        
        @param start: is 0, get all programs from the start.
        @param stop: is 2147483647, get all programs until the end.
        @param chanids: can be used to select only certain channel id's, all channels are returned otherwise.
        @returns: a list of channels (TvChannel)
        """
        _debug_('get_programs(start=%r, stop=%r, chanids=%r)' % (time.strftime('%H:%M', time.localtime(start)),
            time.strftime('%H:%M', time.localtime(stop)), chanids))

        channels = []
        for chan in self.chan_list:
            if chanids and (not chan.id in chanids):
                continue

            c = TvChannel(chan.id, chan.displayname, chan.tunerid, chan.logo, chan.times)
            # Copy the programs that are inside the indicated time bracket
            f = lambda p, a=start, b=stop: not (p.start > b or p.stop < a)
            c.programs = filter(f, chan.programs)

            channels.append(c)

        _debug_('get_programs: channels=%r' % (channels,))
        return channels


    def sort(self):
        """ Sort all channel programs in time order """
        for chan in self.chan_list:
            chan.sort()


    def __str__(self):
        s = 'XML TV Guide\n'
        for chan in self.chan_list:
            s += String(chan)
        return s


    def __repr__(self):
        return '<TvGuide %r>' % (self.EPG_VERSION)
