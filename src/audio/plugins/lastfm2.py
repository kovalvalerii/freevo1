# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
#
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


import sys, os, time
import md5, urllib, urllib2, httplib, re
from threading import Thread

import kaa
from kaa import Timer, OneShotTimer

import config
import plugin
import rc
import version, revision
from event import PLAY_END
from menu import MenuItem, Menu
from gui import AlertBox
from audio.audioitem import AudioItem
from audio.player import PlayerGUI
from util import feedparser
if sys.hexversion >= 0x2050000:
    from xml.etree.cElementTree import XML
else:
    try:
        from cElementTree import XML
    except ImportError:
        from elementtree.ElementTree import XML
from util.benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
benchmarkcall = config.DEBUG_BENCHMARKCALL
import pprint, traceback


class LastFMError(Exception):
    """
    An exception class for last.fm
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self, why):
        Exception.__init__(self)
        self.why = why

    def __str__(self):
        return self.why



class PluginInterface(plugin.MainMenuPlugin):
    """
    Last FM player client

    To activate this plugin, put the following in your local_conf.py:

    | plugin.activate('audio.lastfm')
    | LASTFM_USER = '<last fm user name>'
    | LASTFM_PASS = '<last fm password>'
    | LASTFM_LOCATIONS = [
    |     ('Last Fm - Neighbours', 'lastfm://user/%s/neighbours' % LASTFM_USER),
    |     ('Last FM - Jazz', 'lastfm://globaltags/jazz'),
    |     ('Last FM - Rock', 'lastfm://globaltags/rock'),
    |     ('Last FM - Oldies', 'lastfm://globaltags/oldies'),
    |     ('Last FM - Pop', 'lastfm://globaltags/pop'),
    |     ('Last FM - Norah Jones', 'lastfm://artist/norah jones')
    | ]

    Events sent to lastfm:

    | RIGHT - skip song
    | 1     - send to lastfm LOVE song
    | 9     - send to lastfm BAN song
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self):
        _debug_('PluginInterface.__init__()', 2)
        if not config.LASTFM_USER or not config.LASTFM_PASS:
            self.reason = 'LASTFM_USER or LASTFM_PASS not set'
            return
        plugin.MainMenuPlugin.__init__(self)
        self.menuitem = None
        if not os.path.isdir(config.LASTFM_DIR):
            os.makedirs(config.LASTFM_DIR, 0777)


    @benchmark(benchmarking, benchmarkcall)
    def config(self):
        """
        freevo plugins -i audio.freevo returns the info
        """
        _debug_('config()', 2)
        return [
            ('LASTFM_USER', None, 'User name for www.last.fm'),
            ('LASTFM_PASS', None, 'Password for www.last.fm'),
            ('LASTFM_LANG', 'en', 'Language of last fm metadata (cn,de,en,es,fr,it,jp,pl,ru,sv,tr)'),
            ('LASTFM_DIR', os.path.join(config.FREEVO_CACHEDIR, 'lastfm'), 'Directory to save lastfm files'),
            ('LASTFM_LOCATIONS', [], 'LastFM locations')
        ]


    @benchmark(benchmarking, benchmarkcall)
    def items(self, parent):
        _debug_('items(parent=%r)' % (parent,), 2)
        self.menuitem = LastFMMainMenuItem(parent)
        return [ self.menuitem ]


    @benchmark(benchmarking, benchmarkcall)
    def shutdown(self):
        print 'PluginInterface.shutdown'
        if self.menuitem is not None:
            self.menuitem.shutdown()



class LastFMMainMenuItem(MenuItem):
    """
    This is the item for the main menu and creates the list of commands in a
    submenu.
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self, parent):
        _debug_('LastFMMainMenuItem.__init__(parent=%r)' % (parent,), 2)
        MenuItem.__init__(self, parent, arg='audio', skin_type='radio')
        self.name = _('Last FM')
        self.webservices = LastFMWebServices()


    @benchmark(benchmarking, benchmarkcall)
    def actions(self):
        """return a list of actions for this item"""
        _debug_('actions()', 2)
        return [ (self.create_stations_menu, 'stations') ]


    @benchmark(benchmarking, benchmarkcall)
    def create_stations_menu(self, arg=None, menuw=None):
        _debug_('create_stations_menu(arg=%r, menuw=%r)' % (arg, menuw), 2)
        lfm_items = []
        self.webservices._login()
        for lfm_station in config.LASTFM_LOCATIONS:
            name, station = lfm_station
            lfm_item = LastFMItem(self, name, station, self.webservices)
            lfm_items += [ lfm_item ]
        if not lfm_items:
            lfm_items += [MenuItem(_('Invalid LastFM Session!'), menuw.goto_prev_page, 0)]
        lfm_menu = Menu(_('Last FM'), lfm_items)
        #rc.app(None)
        menuw.pushmenu(lfm_menu)
        menuw.refresh()


    @benchmark(benchmarking, benchmarkcall)
    def shutdown(self):
        print 'LastFMMainMenuItem.shutdown'
        if self.webservices is not None:
            self.webservices.shutdown()



class LastFMItem(AudioItem):
    """
    This is the class that actually runs the commands. Eventually
    hope to add actions for different ways of running commands
    and for displaying stdout and stderr of last command run.
    """
    poll_interval = 4
    poll_interval = 1
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self, parent, name, station, webservices):
        _debug_('LastFMItem.__init__(parent=%r, name=%r, station=%r, webservices=%r)' % \
            (parent, name, station, webservices), 1)
        AudioItem.__init__(self, station, parent, name)
        self.station_url = urllib.quote_plus(station)
        self.station_name = name
        self.webservices = webservices
        self.xspf = None
        self.feed = None
        self.entry = None
        self.timer = None
        self.player = None
        self.arg = None
        self.menuw = None


    @benchmark(benchmarking, benchmarkcall)
    def actions(self):
        """
        return a list of actions for this item
        """
        _debug_('LastFMItem.actions()', 1)
        #self.genre = self.station_name
        self.stream_name = self.station_name
        self.webservices.adjust_station(self.station_url)
        self.xspf = LastFMXSPF()
        self.feed = None
        self.entry = 0
        items = [ (self.play, _('Listen to LastFM Station')) ]
        return items


    @benchmark(benchmarking, True) #benchmarkcall)
    def eventhandler(self, event, menuw=None):
        _debug_('LastFMItem.eventhandler(event=%s, menuw=%r)' % (event, menuw), 2)
        if event == 'STOP':
            self.stop(self.arg, self.menuw)
            return
        if event == 'PLAYLIST_NEXT':
            self.skip()
            return True
        elif event == 'LANG': # Love
            self.ban()
            return True
        elif event == 'SUBTITLE': # bAn
            self.love()
            return True
        return False


    @benchmark(benchmarking, benchmarkcall)
    def play(self, arg=None, menuw=None):
        """
        Play the current playing
        """
        _debug_('LastFMItem.play(arg=%r, menuw=%r)' % (arg, menuw), 1)
        self.arg = arg
        if self.menuw is None:
            self.menuw = menuw

        if self.feed is None or self.entry >= len(self.feed.entries):
            try:
                for i in range(3):
                    xspf = self.webservices.request_xspf()
                    if xspf != 'No recs :(':
                        break
                    time.sleep(2)
                else:
                    if menuw:
                        AlertBox(text='No recs :(').show()
                    rc.post_event(PLAY_END)
                    return

                self.feed = self.xspf.parse(xspf)
                if self.feed is None:
                    if menuw:
                        AlertBox(text=_('Cannot get XSFP')).show()
                    rc.post_event(PLAY_END)
                    return
            except LastFMError, why:
                _debug_(why, DWARNING)
                if menuw:
                    AlertBox(text=str(why)).show()
                rc.post_event(PLAY_END)
            self.entry = 0

        entry = self.feed.entries[self.entry]
        self.stream_name = urllib.unquote_plus(self.feed.feed.title)
        self.album = entry.album
        self.artist = entry.artist
        self.title = entry.title
        self.location_url = entry.location_url
        self.length = entry.duration
        basename = entry.artist + '-' + entry.album + '-' + entry.title
        self.basename = basename.lower().replace(' ', '_').replace('.', '').replace('\'', '').replace(':', '')
        self.url = os.path.join(config.LASTFM_DIR, self.basename + os.path.splitext(entry.location_url)[1])
        self.trackpath = os.path.join(config.LASTFM_DIR, self.basename + os.path.splitext(entry.location_url)[1])
        self.image = os.path.join(config.LASTFM_DIR, self.basename + os.path.splitext(entry.image_url)[1])
        self.image_downloader = self.webservices.download(entry.image_url, self.image)
        self.track_downloader = self.webservices.download(self.location_url, self.trackpath, istrack=True)
        #self.is_playlist = True
        # Wait for a bit of the file to be downloaded
        while self.track_downloader.filesize() < 1024 * 20:
            if not self.track_downloader.isrunning():
                rc.post_event(PLAY_END)
                return
            time.sleep(0.1)
        # Wait for the image to be downloaded
        for i in range(30):
            if not self.image_downloader.isrunning():
                break
            time.sleep(0.1)
        self.player = PlayerGUI(self, menuw)
        if self.timer is not None and self.timer.active():
            self.timer.stop()
        self.timer = kaa.OneShotTimer(self.timerhandler)
        self.timer.start(entry.duration)
        error = self.player.play()
        if error:
            _debug_('player play error=%r' % (error,), DWARNING)
            if menuw:
                AlertBox(text=error).show()
            rc.post_event(PLAY_END)


    @benchmark(benchmarking, benchmarkcall)
    def timerhandler(self):
        """
        Handle the timer event when at the end of a track
        """
        if self.timer is None:
            _debug_('timer is not running', DINFO)
            return
        if self.track_downloader is None:
            _debug_('downloader is not running', DERROR)
            return
        if self.track_downloader.isrunning():
            _debug_('still playing', DINFO)
            self.timer.start(LastFMItem.poll_interval)
        else:
            self.entry += 1
            self.play(self.arg, self.menuw)


    @benchmark(benchmarking, benchmarkcall)
    def stop(self, arg=None, menuw=None):
        """
        Stop the current playing
        """
        _debug_('LastFMItem.stop(arg=%r, menuw=%r)' % (arg, menuw), 1)
        if self.timer is not None and self.timer.active():
            self.timer.stop()
        self.timer = None


    @benchmark(benchmarking, benchmarkcall)
    def skip(self):
        """Skip song"""
        _debug_('skip()', 1)
        self.entry += 1
        if self.timer is not None and self.timer.active():
            self.timer.stop()
        self.timer = None
        self.play(self.arg, self.menuw)


    @benchmark(benchmarking, benchmarkcall)
    def love(self):
        """Send "Love" information to audioscrobbler"""
        _debug_('love()', 1)
        self.webservices.love()


    @benchmark(benchmarking, benchmarkcall)
    def ban(self):
        """Send "Ban" information to audioscrobbler"""
        _debug_('ban()', 1)
        self.webservices.ban()




class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        #print 'DJW:http_error_301'
        result = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        result.status = code
        return result

    def http_error_302(self, req, fp, code, msg, headers):
        #print 'DJW:http_error_302'
        result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        result.status = code
        return result



class LastFMDownloader(Thread):
    """
    Download the stream to a file

    There is a bad bug im mplayer that corrupts the url passed, so we have to
    download it to a file and then play it
    """
    def __init__(self, url, filename, headers=None):
        Thread.__init__(self)
        self.url = url
        self.filename = filename
        self.headers = headers
        self.running = True
        self.size = 0


    def run(self):
        """
        Execute a download operation. Stop when finished downloading or
        requested to stop.
        """
        #print 'DJW:self.url:', self.url, 'self.headers:', self.headers
        request = urllib2.Request(self.url, headers=self.headers)
        opener = urllib2.build_opener(SmartRedirectHandler())
        try:
            f = opener.open(request)
            fd = open(self.filename, 'wb')
            while self.running:
                reply = f.read(1024 * 100)
                fd.write(reply)
                if len(reply) == 0:
                    self.running = False
                    _debug_('%s downloaded' % self.filename)
                    #print 'DJW:downloaded %s' % self.filename
                    # what we could do now is to add tags to track
                    break
                self.size += len(reply)
            else:
                _debug_('%s aborted' % self.filename)
            fd.close()
            f.close()
        except ValueError, why:
            _debug_('%s: %s' % (self.filename, why), DWARNING)
        except urllib2.HTTPError, why:
            _debug_('%s: %s' % (self.filename, why), DWARNING)


    def stop(self):
        """
        Stop the download thead running
        """
        # this does not stop the download thread
        self.running = False


    def filesize(self):
        """
        Get the downloaded file size
        """
        return self.size


    def isrunning(self):
        """
        See if the thread running
        """
        return self.running



class LastFMWebServices:
    """
    Interface to LastFM web-services
    """
    _version = '1.1.2'
    headers = {
        'User-agent': 'Freevo-%s (r%s)' % (version.__version__, revision.__revision__)
    }

    @benchmark(benchmarking, benchmarkcall)
    def __init__(self):
        _debug_('LastFMWebServices.__init__()', 2)
        self.logincachefilename = os.path.join(config.FREEVO_CACHEDIR, 'lastfm.session')
        try:
            self.cachefd = open(self.logincachefilename, 'r')
            self.session = self.cachefd.readline().strip('\n')
            self.stream_url = self.cachefd.readline().strip('\n')
            self.base_url = self.cachefd.readline().strip('\n')
            self.base_path = self.cachefd.readline().strip('\n')
            self.downloader = None
        except IOError, why:
            self._login()


    @benchmark(benchmarking, benchmarkcall)
    def shutdown(self):
        """
        Shutdown the lasf.fm webservices
        """
        print 'LastFMWebServices.shutdown'
        if self.downloader is not None:
            self.downloader.stop()


    @benchmark(benchmarking, benchmarkcall)
    def _urlopen(self, url, data=None, lines=True):
        """
        Wrapper to see what is sent and received
        When lines is true then the reply is returned as a list of lines,
        otherwise it is returned as a block.

        @param url: Is the URL to read.
        @param data: Is the POST data.
        @param lines: return a list of lines, otherwise data block.
        @returns: reply from request
        """
        _debug_('url=%r, data=%r' % (url, data), 1)
        request = urllib2.Request(url, headers=LastFMWebServices.headers)
        opener = urllib2.build_opener(SmartRedirectHandler())
        if lines:
            reply = []
            try:
                f = opener.open(request)
                lines = f.readlines()
                if lines is None:
                    return []
                for line in lines:
                    reply.append(line.strip('\n'))
            except httplib.BadStatusLine, why:
                print 'BadStatusLine:', why
                reply = None
            except AttributeError, why:
                reply = None
            except Exception, why:
                _debug_('%s: %s' % (url, why), DWARNING)
                raise
            _debug_('reply=%r' % (reply,), 1)
            return reply
        else:
            reply = ''
            try:
                f = opener.open(request)
                reply = f.read()
            except Exception, why:
                _debug_('%s: %s' % (url, why), DWARNING)
                raise
            _debug_('len(reply)=%r' % (len(reply),), 1)
            return reply


    @benchmark(benchmarking, benchmarkcall)
    def _login(self, arg=None):
        """Read session and stream url from ws.audioscrobbler.com"""
        _debug_('login(arg=%r)' % (arg,), 2)
        username = config.LASTFM_USER
        password_txt = config.LASTFM_PASS
        password = md5.new(config.LASTFM_PASS)
        login_url='http://ws.audioscrobbler.com/radio/handshake.php' + \
            '?version=%s&platform=linux' % (LastFMWebServices._version) + \
            '&username=%s&passwordmd5=%s' % (config.LASTFM_USER, password.hexdigest()) + \
            '&debug=0&language=%s' % (config.LASTFM_LANG)
        stream_url = ''

        try:
            lines = self._urlopen(login_url)
            for line in lines:
                # this is a bit dangerous if a variable clashes
                exec('self.%s = "%s"' % tuple(line.split('=', 1)))
            # Save the lastfm session information
            fd = open(self.logincachefilename, 'w')
            print >>fd, self.session
            print >>fd, self.stream_url
            print >>fd, self.base_url
            print >>fd, self.base_path
            fd.close()
        except IOError, why:
            self.session = ''
            self.stream_url = ''
            self.base_url = ''
            self.base_path = ''


    @benchmark(benchmarking, benchmarkcall)
    def request_xspf(self):
        """Request a XSPF (XML Shareable Playlist File)"""
        _debug_('LastFMWebServices.request_xspf()', 1)
        if not self.session:
            self._login()
        #request_url = 'http://%s%s/xspf.php?sk=%s&discovery=0&desktop=%s' % \
        request_url = 'http://%s%s/xspf.php?sk=%s&discovery=1&desktop=%s' % \
            (self.base_url, self.base_path, self.session, LastFMWebServices._version)
        return self._urlopen(request_url, lines=False)


    @benchmark(benchmarking, benchmarkcall)
    def adjust_station(self, station_url):
        """Change Last FM Station"""
        _debug_('adjust_station(station_url=%r)' % (station_url,), 2)
        if not self.session:
            self._login()
        tune_url = 'http://ws.audioscrobbler.com/radio/adjust.php?session=%s&url=%s&lang=%s&debug=0' % \
            (self.session, station_url, config.LASTFM_LANG)
        try:
            for line in self._urlopen(tune_url):
                if re.search('response=OK', line):
                    return True
            return False
        except AttributeError, why:
            return None
        except IOError, why:
            return None


    @benchmark(benchmarking, benchmarkcall)
    def now_playing(self):
        """
        Return Song Info and album Cover
        """
        _debug_('now_playing()', 2)
        if not self.session:
            self._login()
        info_url = 'http://ws.audioscrobbler.com/radio/np.php?session=%s&debug=0' % (self.session,)
        reply = self._urlopen(info_url)
        if not reply or reply[0] == 'streaming=false':
            return None
        return reply


    @benchmark(benchmarking, benchmarkcall)
    def download(self, url, filename, istrack=False):
        """
        Download album cover or track to last.fm directory.

        Add the session as a cookie to the request

        @param url: location of item to download
        @param filename: path to downloaded file
        """
        _debug_('download(url=%r, filename=%r)' % (url, filename), 1)
        if not self.session:
            self._login()
        headers = {
            'Cookie': 'Session=%s' % self.session,
            'User-agent': 'Freevo-%s (r%s)' % (version.__version__, revision.__revision__)
        }
        if istrack:
            headers.update({'Host': 'play.last.fm'})
        self.downloader = LastFMDownloader(url, filename, headers)
        self.downloader.start()
        return self.downloader


    @benchmark(benchmarking, benchmarkcall)
    def skip(self):
        """Skip song"""
        _debug_('skip()', 2)
        if not self.session:
            self._login
        skip_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=skip&debug=0' % \
            (self.session)
        return self._urlopen(skip_url)


    @benchmark(benchmarking, benchmarkcall)
    def love(self):
        """Send "Love" information to audioscrobbler"""
        _debug_('love()', 2)
        if not self.session:
            self._login
        love_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=love&debug=0' % \
            (self.session)
        return self._urlopen(love_url)


    @benchmark(benchmarking, benchmarkcall)
    def ban(self):
        """Send "Ban" information to audioscrobbler"""
        _debug_('ban()', 2)
        if not self.session:
            self._login
        ban_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=ban&debug=0' % \
            (self.session)
        return self._urlopen(ban_url)


    @benchmark(benchmarking, benchmarkcall)
    def test_user_pass(self):
        """
        Test User/Pass

        This way you can check, whether a user/pass is valid.

        http://ws.audioscrobbler.com/ass/pwcheck.php?
            time=[TS]&username=[USER]&auth=[AUTH1]&auth2=[AUTH2]&defaultplayer=[PLAYER]

        Variables:

        * TS: Unix timestamp of the current time.
        * USER: Username.
        * AUTH1: md5( md5(password) + Timestamp), An md5 sum of an md5 sum of the password, plus the timestamp as salt.
        * AUTH2: Second possible Password. The client uses md5( md5(toLower(password)) + Timestamp)
        * PLAYER: See Appendix
        """
        timestamp = time.strftime('%s', time.gmtime(time.time()))
        username = config.LASTFM_USER
        password = config.LASTFM_PASS
        auth = md5.new(md5.new(password).hexdigest()+timestamp).hexdigest()
        auth2 = md5.new(md5.new(password.lower()).hexdigest()+timestamp).hexdigest()
        url = 'http://ws.audioscrobbler.com//ass/pwcheck.php?' + \
            'time=%s&' % timestamp + \
            'username=%s&' % username + \
            'auth=%s&' % auth + \
            'auth2=%s&' % auth2 + \
            'defaultplayer=fvo'
        return self._urlopen(url)



class LastFMXSPF:
    """
    Analyse the XSPF (spiff) XML Sharable Playlist File feed using ElementTree

    XSPF is documented at U{http://www.xspf.org/quickstart/}
    """
    _LASTFM_NS = 'http://www.audioscrobbler.net/dtd/xspf-lastfm'

    @benchmark(benchmarking, benchmarkcall)
    def __init__(self):
        self.entries = []
        self.feed = feedparser.FeedParserDict()


    @benchmark(benchmarking, benchmarkcall)
    def parse(self, xml):
        """
        Parse the XML feed
        """
        try:
            tree = XML(xml)
        except SyntaxError:
            raise LastFMError(xml)
        title = tree.find('title')
        self.feed.title = title is not None and title.text or u''
        for link_elem in tree.findall('link'):
            for k, v in link_elem.items():
                if k == 'rel' and v == 'http://www.last.fm/skipsLeft':
                    self.feed.skips_left = int(link_elem.text)
        tracklist = tree.find('trackList')
        if tracklist:
            for track_elem in tracklist.findall('track'):
                track = feedparser.FeedParserDict()
                track_map = dict((c, p) for p in track_elem.getiterator() for c in p)
                title = track_elem.find('title')
                track.title = title is not None and title.text or u''
                album = track_elem.find('album')
                track.album = album is not None and album.text or u''
                artist = track_elem.find('creator')
                track.artist = artist is not None and artist.text or u''
                location_url = track_elem.find('location')
                track.location_url = location_url is not None and location_url.text or u''
                image_url = track_elem.find('image')
                track.image_url = image_url is not None and image_url.text or u''
                duration_ms = track_elem.find('duration')
                track.duration = duration_ms is not None and int(float(duration_ms.text)/1000.0+0.5) or 0
                trackauth = track_elem.find('{%s}trackauth' % LastFMXSPF._LASTFM_NS)
                track.trackauth = trackauth is not None and trackauth.text or u''
                self.entries.append(track)
        return self



if __name__ == '__main__':
    """
    To run this test harness need to have defined in local_conf.py:

        - LASTFM_USER
        - LASTFM_PASS
        - LASTFM_LANG
    """

    station = 'lastfm://globaltags/jazz'
    station_url = urllib.quote_plus(station)
    webservices = LastFMWebServices()
    print webservices.test_user_pass()
    print webservices._login()
    print webservices.adjust_station(station_url)
    print webservices.request_xspf()
    print 'sleep(10)'
    time.sleep(10)
    for i in range(3):
        xspf = self.webservices.request_xspf()
        print xspf
        if xspf != 'No recs :(':
            break
        time.sleep(2)
    else:
        print 'Failed to get second playlist'
