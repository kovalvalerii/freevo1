#!/usr/bin/env python
#if 0 /*
# -----------------------------------------------------------------------
# install.py - install external plugins or themes into Freevo
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.1  2003/10/28 21:26:10  dischi
# make install a helper to make it also work for non installed versions
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


import sys
import os

import config
import util.fileops

if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
    is_local = False
    tgz = os.path.abspath(sys.argv[1])

    # check if we use an installed version of python or not
    src = os.environ['FREEVO_PYTHON'].rfind('src')
    if src >= 0 and os.environ['FREEVO_PYTHON'][src:] == 'src':
        # local version, chdir to freevo working directory
        is_local = True
        os.chdir(os.path.join(os.environ['FREEVO_PYTHON'], '..'))

    # create tmp directory
    if os.path.isdir('tmp'):
        print 'directory tmp exists, please remove it'
        sys.exit(1)
    os.mkdir('tmp')

    # unpack
    os.system('tar -zxf %s -C tmp' % tgz)

    if is_local:
        # move all files from src, share and i18n into the Freevo tree
        all_files = []
        os.path.walk('tmp', util.fileops.match_files_recursively_helper, all_files)
        for file in all_files:
            new_file = file[file[4:].find('/')+5:]
            if os.path.isfile(file) and (new_file.find('share') == 0 or
                                         new_file.find('src') == 0 or
                                         new_file.find('i18n') == 0):
                print 'installing %s' % new_file
                os.rename(file, new_file)
    else:
        # check package
        d = util.fileops.getdirnames('tmp')
        if len(d) != 1:
            print 'package is not a freevo theme or plugin, please contact the author'
        else:
            # chdir into plugin main directory and run setup.py
            cur = os.getcwd()
            os.chdir(d[0])

            sys.argv = ['setup.py', 'install']
            execfile('setup.py')

            os.chdir(cur)

    # remove tmp directory
    util.fileops.rmrf('tmp')
    
else:
    print 'freevo install helper to install external plugins or themes into Freevo'
    print
    print 'usage freevo install file'
    print 'File needs to be a tgz containing a setup.py and the Freevo file structure'
    print
