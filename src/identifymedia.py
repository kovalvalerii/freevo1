#if 0 /*
# -----------------------------------------------------------------------
# identifymedia.py - the Freevo identifymedia/automount module
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.24  2003/04/12 18:27:29  dischi
# special video item handling
#
# Revision 1.23  2003/04/06 21:12:54  dischi
# o Switched to the new main skin
# o some cleanups (removed unneeded inports)
#
# Revision 1.22  2003/03/24 19:42:20  dischi
# fixed cd id search
#
# Revision 1.21  2003/03/15 17:13:22  dischi
# store rom drive type in media
#
# Revision 1.20  2003/03/11 19:40:33  dischi
# bugfix
#
# Revision 1.19  2003/03/10 07:09:48  outlyer
# Added an uppercase /VIDEO_TS/ for DVDs in identifymedia. I couldn't verify
# this works since I lack a cdrom drive.
#
# Revision 1.18  2003/02/25 05:31:47  krister
# Made CD audio playing use -cdrom-device for mplayer.
#
# Revision 1.17  2003/02/19 06:42:57  krister
# Thomas Schuppels latest CDDA fixes. I changed some info formatting, made it possible to play unknown disks, added MPlayer 1MB caching (important) of CD tracks.
#
# Revision 1.16  2003/02/17 21:14:02  dischi
# Bugfix. CD detection now works again
#
# Revision 1.15  2003/02/17 06:03:58  krister
# Disable CDDB is the runtime is used, there's some problem with that right now.
#
# Revision 1.14  2003/02/17 03:27:10  outlyer
# Added Thomas' CDDB support patch. I don't have a CD-rom drive in my machine,
# so I can't verify it works; code looks good though.
#
# I only had to make one change from the original submitted patch, which was
# to make sure we don't crash in audiodiskitem if the system lacks CDDB, the
# check was already performed in identifymedia.
#
# Revision 1.13  2003/02/15 04:03:02  krister
# Joakim Berglunds patch for finding music/movie cover pics.
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

import time, os
from fcntl import ioctl
import re
import threading
import config
import util
import rc
import string
import copy

from audio.audiodiskitem import AudioDiskItem
from video.videoitem import VideoItem

# CDDB Stuff
try:
    import DiscID, CDDB
except:
    print "CDDB not installed."
    pass

from video import xml_parser, videoitem
from mediamenu import DirItem

DEBUG = config.DEBUG   # 1 = regular debug, 2 = more verbose

LABEL_REGEXP = re.compile("^(.*[^ ]) *$").match


# taken from cdrom.py so we don't need to import cdrom.py
CDROM_DRIVE_STATUS=0x5326
CDSL_CURRENT=( (int ) ( ~ 0 >> 1 ) )
CDS_DISC_OK=4
CDROM_DISC_STATUS=0x5327
CDS_AUDIO=100
CDROM_SELECT_SPEED=0x5322


class Identify_Thread(threading.Thread):

    # magic!
    # Try to find out as much as possible about the disc in the
    # rom drive: title, image, play options, ...
    def identify(self, media):

        # Check drive status (tray pos, disc ready)
        try:
            fd = os.open(media.devicename, os.O_RDONLY | os.O_NONBLOCK)
            s = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT)
        except:
            # maybe we need to close the fd if ioctl fails, maybe
            # open fails and there is no fd
            try:
                os.close(fd)
            except:
                pass
            media.drive_status = None
            return

        # Same as last time? If so we're done
        if s == media.drive_status:
            os.close(fd)
            return

        media.drive_status = s

        media.id        = ''
        media.label     = ''
        media.type      = 'empty_cdrom'
        media.info      = None
        media.videoinfo = None

        # Is there a disc present?
        if s != CDS_DISC_OK:
            os.close(fd)
            return

        # Check media type (data, audio)
        s = ioctl(fd, CDROM_DISC_STATUS)
        if s == CDS_AUDIO:
            os.close(fd)
            media.type  = 'audiocd'
            try:
                cdrom = DiscID.open(media.devicename)
                disc_id = DiscID.disc_id(cdrom)
                media.info = AudioDiskItem(disc_id, parent=None, name='',
                                           devicename=media.devicename,
                                           display_type='audio')
                (query_stat, query_info) = CDDB.query(disc_id)

                media.info.handle_type = 'audio'
                if query_stat == 200:
                    media.info.title = query_info['title']

                elif query_stat == 210 or query_stat == 211:
                    print "multiple matches found! Matches are:"
                    for i in query_info:
                        print "ID: %s Category: %s Title: %s" % \
                              (i['disc_id'], i['category'], i['title'])
                else:
                    print "failure getting disc info, status %i" % query_stat
                    media.info.title = 'Unknown CD Album'
            except:
                pass
            return

        # try to set the speed
        if config.ROM_SPEED:
            try:
                ioctl(fd, CDROM_SELECT_SPEED, config.ROM_SPEED)
            except:
                pass
            
        mediatypes = [('VCD', '/mpegav/', 'vcd'), ('SVCD','/SVCD/', 'vcd'), 
                      ('SVCD','/svcd/', 'vcd'), ('DVD', '/video_ts/', 'dvd'),
		      ('DVD','/VIDEO_TS/','dvd')]

        image = title = movie_info = None

        # Read the volume label directly from the ISO9660 file system
        
        os.close(fd)
        try:
            img = open(media.devicename)
            img.seek(0x0000832d)
            id = img.read(16)
            img.seek(32808, 0)
            label = img.read(32)
            m = LABEL_REGEXP(label)
            if m:
                label = m.group(1)
            img.close()
        except IOError:
            print 'I/O error on disc %s' % media.devicename
            return

        media.id    = id+label
        media.label = ''
        media.type  = 'cdrom'
        
        # is the id in the database?
        if id+label in config.MOVIE_INFORMATIONS_ID:
            movie_info = config.MOVIE_INFORMATIONS_ID[id+label]
            if movie_info:
                title = movie_info.name
            
        # no? Maybe we can find a label regexp match
        else:
            for (re_label, movie_info_t) in config.MOVIE_INFORMATIONS_LABEL:
                if re_label.match(label):
                    movie_info = movie_info_t
                    if movie_info_t.name:
                        title = movie_info.name
                        m = re_label.match(label).groups()
                        re_count = 1

                        # found, now change the title with the regexp. E.g.:
                        # label is "bla_2", the label regexp "bla_[0-9]" and the title
                        # is "Something \1", the \1 will be replaced with the first item
                        # in the regexp group, here 2. The title is now "Something 2"
                        for g in m:
                            title=string.replace(title, '\\%s' % re_count, g)
                            re_count += 1
                        break
                
        if movie_info:
            image = movie_info.image
                        
        # Disc is data of some sort. Mount it to get the file info
        util.mount(media.mountdir)

        # Check for DVD/VCD/SVCD
        for mediatype in mediatypes:
            if os.path.exists(media.mountdir + mediatype[1]):
                util.umount(media.mountdir)

                if not title:
                    title = '%s [%s]' % (mediatype[0], label)

                if movie_info:
                    media.info = copy.copy(movie_info)
                else:
                    media.info = videoitem.VideoItem('0', None)

                media.info.label = label
                media.info.name = title
                media.info.mode = mediatype[2]
                media.info.media = media

                media.type  = mediatype[2]

                if os.path.isfile(config.COVER_DIR+label+'.jpg'):
                    media.info.image = config.COVER_DIR+label+'.jpg'
                return
        
        # Check for movies/audio/images on the disc
        mplayer_files = util.match_files(media.mountdir, config.SUFFIX_VIDEO_FILES)
        mp3_files = util.match_files(media.mountdir, config.SUFFIX_AUDIO_FILES)
        image_files = util.match_files(media.mountdir, config.SUFFIX_IMAGE_FILES)

        util.umount(media.mountdir)

        if DEBUG:
            print 'identifymedia: mplayer = "%s"' % mplayer_files
            print 'identifymedia: mp3="%s"' % mp3_files
            print 'identifymedia: image="%s"' % image_files
            
        media.info = DirItem(media.mountdir, None)
        
        # Is this a movie disc?
        if mplayer_files and not mp3_files:
            media.info.handle_type = 'video'

            # try to find out if it is a series cd
            if not title:
                show_name = ""
                the_same  = 1
                volumes   = ''
                for movie in mplayer_files:
                    if config.TV_SHOW_REGEXP_MATCH(movie):
                        show = config.TV_SHOW_REGEXP_SPLIT(os.path.basename(movie))

                        if show_name and show_name != show[0]: the_same = 0
                        if not show_name: show_name = show[0]
                        if volumes: volumes += ', '
                        volumes += show[1] + "x" + show[2]

                if show_name and the_same:
                    if os.path.isfile((config.TV_SHOW_IMAGES + show_name + ".png").lower()):
                        image = (config.TV_SHOW_IMAGES + show_name + ".png").lower()
                    elif os.path.isfile((config.TV_SHOW_IMAGES + show_name + ".jpg").lower()):
                        image = (config.TV_SHOW_IMAGES + show_name + ".jpg").lower()
                    title = show_name + ' ('+ volumes + ')'
                elif not show_name:
                    if os.path.isfile(config.COVER_DIR+\
                                      os.path.splitext(os.path.basename(movie))[0]+'.png'):
                        image = config.COVER_DIR+\
                                os.path.splitext(os.path.basename(movie))[0]+'.png'
                    elif os.path.isfile(config.COVER_DIR+\
                                        os.path.splitext(os.path.basename(movie))[0]+'.jpg'):
                        image = config.COVER_DIR+\
                                os.path.splitext(os.path.basename(movie))[0]+'.jpg'
                    title = os.path.splitext(os.path.basename(movie))[0]
            # nothing found, give up: return the label
            if not title:
                title = label


        # XXX add more intelligence to cds with audio files
        elif (not mplayer_files) and mp3_files:
            media.info.handle_type = 'audio'
            title = '%s [%s]' % (media.drivename, label)

        # XXX add more intelligence to cds with image files
        elif (not mplayer_files) and (not mp3_files) and image_files:
            media.info.handle_type = 'image'
            title = '%s [%s]' % (media.drivename, label)

        # Mixed media?
        elif mplayer_files or image_files or mp3_files:
            media.info.handle_type = None
            title = '%s [%s]' % (media.drivename, label)
        
        # Strange, no useable files
        else:
            media.info.handle_type = None
            title = '%s [%s]' % (media.drivename, label)


        if movie_info:
            media.info.copy(movie_info)
        if title:
            media.info.name = title
        if image:
            media.info.image = image

        if len(mplayer_files) == 1:
            media.videoinfo = VideoItem(mplayer_files[0], None)
            media.videoinfo.media = media
            
            if movie_info:
                media.videoinfo.copy(movie_info)
            if title:
                media.videoinfo.name = title
            if image:
                media.videoinfo.image = image
            
        media.info.media = media
        return


    def check_all(self):
        rclient = rc.get_singleton()
        
        for media in config.REMOVABLE_MEDIA:
            last_status = media.drive_status
            self.identify(media)

            if last_status != media.drive_status:
                if DEBUG:
                    print 'MEDIA: Status=%s' % media.drive_status
                    print 'Posting IDENTIFY_MEDIA event'
                if last_status:
                    self.last_media = media
                rclient.post_event(rclient.IDENTIFY_MEDIA)
            else:
                if DEBUG > 1:
                    print 'MEDIA: Status=%s' % media.drive_status

                
    def __init__(self):
        threading.Thread.__init__(self)
        self.last_media = None          # last changed media

        
    def run(self):
        # Make sure the movie database is rebuilt at startup
        os.system('touch /tmp/freevo-rebuild-database')
        while 1:
            # Check if we need to update the database
            # This is a simple way for external apps to signal changes
            if os.path.exists("/tmp/freevo-rebuild-database"):
                xml_parser.hash_xml_database()
                for media in config.REMOVABLE_MEDIA:
                    media.drive_status = None

            self.check_all()
            time.sleep(2)

