#if 0
# -----------------------------------------------------------------------
# area.py - An area for the Freevo skin
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
#
# This is the main class for all area. Right now it's working, but
# some things are not very good. Maybe someone can create a new
# Skin_Area with a different behaviour.
#
# My first draft was an area which redraws only the needed parts and
# blits it onto the surface.. But there are some problems with that,
# which makes this a little bit difficult. This version redraws too
# much, but blits only the needed parts on the screen.
#
# If you want to create a new Skin_Area, please keep my problems in mind:
#
#
# 1. Not all areas are visible at the same time, some areas may change
#    the settings and others don't
# 2. The listing and the view area can overlap, at the next item the image
#    may be gone
# 3. alpha layers are slow to blit on a non alpha surface.
# 4. the blue_round1 draws two alpha masks, one for the listing, one
#    for the view area. They overlap, but the overlapping area
#    shouldn't be an addition of the transparent value
# 5. If you drop an alpha layer on the screen, you can't get the original
#    background back by making a reverse alpha layer.
#
# For more informations contact me (dmeyer@tzi.de)
#
#
# Todo: make it faster :-)
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.8  2003/03/02 19:31:35  dischi
# split the draw function in two parts
#
# Revision 1.7  2003/03/02 15:04:08  dischi
# Added forced_redraw after Clear()
#
# Revision 1.6  2003/03/01 00:12:17  dischi
# Some bug fixes, some speed-ups. blue_round2 has a correct main menu,
# but on the main menu the idle bar still flickers (stupid watermarks),
# on other menus it's ok.
#
# Revision 1.5  2003/02/27 22:39:49  dischi
# The view area is working, still no extended menu/info area. The
# blue_round1 skin looks like with the old skin, blue_round2 is the
# beginning of recreating aubin_round1. tv and music player aren't
# implemented yet.
#
# Revision 1.4  2003/02/26 19:59:25  dischi
# title area in area visible=(yes|no) is working
#
# Revision 1.3  2003/02/26 19:18:52  dischi
# Added blue1_small and changed the coordinates. Now there is no overscan
# inside the skin, it's only done via config.OVERSCAN_[XY]. The background
# images for the screen area should have a label "background" to override
# the OVERSCAN resizes.
#
# Revision 1.2  2003/02/25 23:27:36  dischi
# changed max usage
#
# Revision 1.1  2003/02/25 22:56:00  dischi
# New version of the new skin. It still looks the same (except that icons
# are working now), but the internal structure has changed. Now it will
# be easier to do the next steps.
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
# -----------------------------------------------------------------------
#endif


import copy
import pygame

import osd
import config
import objectcache

import xml_skin


# Create the OSD object
osd = osd.get_singleton()

# Set to 1 for debug output
DEBUG = 1

TRUE = 1
FALSE = 0


background = None
alpha = None


class Screen:
    """
    this call is a set of surfaces for the area to do it's job
    """

    def __init__(self):
        self.background  = pygame.Surface((osd.width, osd.height), 1, 32)
        self.alpha       = self.background.convert_alpha()
        self.alpha.fill((0,0,0,0))
        self.alpha_bg    = self.background.convert()
        
    def clear(self):
        self.alpha.fill((0,0,0,0))


	
class Skin_Area:
    """
    the base call for all areas. Each child needs two functions:

    def update_content_needed
    def update_content
    """

    def __init__(self, name, screen):
        self.area_name = name
        self.area_val  = None
        self.redraw    = TRUE
        self.depends   = ()
        self.layout    = None
        self.name      = name
        
        self.background = screen.background
        self.alpha = screen.alpha
        self.alpha_bg = screen.alpha_bg

        self.redraw_background  = []
        self.redraw_alpha       = []
        self.content_alpha      = []

        self._write_text   = []
        self._draw_image   = []

        self.imagecache = objectcache.ObjectCache(5, desc='%s_image' % self.name)

    def prepare(self, settings, menuw, force_redraw):
        """
        this is the first part of main draw function. This function draws the
        background, checks if redraws are needed and calls the two update functions
        for the different types of areas
        """
        
        menu = menuw.menustack[-1]

        self.menu = menu
        
        self.redraw = force_redraw
        self.mode = 0                   # start draw
        
        area = self.area_val

        if area:
            visible = area.visible
        else:
            visible = FALSE
            
        self.redraw = self.init_vars(settings, menu.item_types)

        if area and area != self.area_val:
            self.redraw_alpha += [ (area.x, area.y, area.width, area.height) ]
            old_area = area
        else:
            old_area = None
            
        area = self.area_val

        # maybe we are NOW invisible
        if visible and not area.visible:
            for rect in self.content_alpha:
                self.alpha_bg.blit(self.background, (rect[0], rect[1]), rect)
                self.alpha_bg.blit(self.alpha, (rect[0], rect[1]), rect)
            self.content_alpha = []
            osd.screen.blit(self.alpha_bg, (area.x, area.y),
                            (area.x, area.y, area.width, area.height))

        if not area.visible:
            return
        
        self.draw_background()

        # dependencies haven't changed
        if not self.redraw:
            # no update needed: return
            if not self.update_content_needed(settings, menuw):
                return

        self.redraw_alpha += self.content_alpha

        self.content_alpha = []

        self.mode = 1                   # draw alpha stuff
        self.update_content(settings, menuw)

        for rect in self.redraw_background:
            # redraw background
            self.alpha_bg.blit(self.background, rect[:2], rect)

        if self.redraw_alpha:
            # redraw alpha means to create a new merge of background
            # and alpha on alpha_bg and blit it into osd.screen
            x0 = osd.width
            y0 = osd.height
            x1 = 0
            y1 = 0
            
            for rect in self.redraw_alpha:
                x0 = min(x0, rect[0])
                y0 = min(y0, rect[1])
                x1 = max(x1, rect[0] + rect[2])
                y1 = max(y1, rect[1] + rect[3])
            self.alpha_bg.blit(self.background, (x0, y0), (x0, y0, x1-x0, y1-y0))
            self.alpha_bg.blit(self.alpha, (x0, y0), (x0, y0, x1-x0, y1-y0))

        self.redraw_alpha = []
        self.redraw_background = []

        # now blit the alpha_bg on the osd.screen
        if old_area:
            osd.screen.blit(self.alpha_bg, old_area.pos(self.name),
                            old_area.rect(self.name))


        # FIXME: at this point with blue_round2 we blit the hole screen,
        osd.screen.blit(self.alpha_bg, area.pos(self.name), area.rect(self.name))

        
    def draw(self):
        """
        this is the second part of main draw function. This function draws the
        content (text and images)
        """

        for t in self._write_text:
            ( text, font, x, y, width, height, align_h, align_v, mode, ellipses ) = t
            if font.shadow.visible:
                osd.drawstringframed(text, x+font.shadow.x, y+font.shadow.y,
                                     width, height, font.shadow.color, None,
                                     font=font.name, ptsize=font.size,
                                     align_h = align_h, align_v = align_v,
                                     mode=mode, ellipses=ellipses)
            osd.drawstringframed(text, x, y, width, height, font.color, None,
                                 font=font.name, ptsize=font.size,
                                 align_h = align_h, align_v = align_v,
                                 mode=mode, ellipses=ellipses)

        for i in self._draw_image:
            osd.screen.blit(i[0], i[1])

        self._write_text = []
        self._draw_image = []




    def calc_geometry(self, object, copy_object=0):
        """
        calculate the real values of the object (e.g. content) based
        on the geometry of the area
        """
        if copy_object:
            object = copy.deepcopy(object)

        MAX = self.area_val.width
        object.width = eval('%s' % object.width)

        MAX = self.area_val.height
        object.height = eval('%s' % object.height)

        object.x += self.area_val.x
        object.y += self.area_val.y
        
        if not object.width:
            object.width = self.area_val.width

        if not object.height:
            object.height = self.area_val.height

        if object.width + object.x > self.area_val.width + self.area_val.x:
            object.width = self.area_val.width - object.x

        if object.height + object.y > self.area_val.height + self.area_val.y:
            object.height = self.area_val.height - object.y

        return object

        
    def get_item_rectangle(self, rectangle, item_w, item_h):
        """
        calculates the values for a rectangle inside the item tag
        """
        r = copy.copy(rectangle)
        
        if not r.width:
            r.width = item_w

        if not r.height:
            r.height = item_h

        MAX = item_w
        r.x = int(eval('%s' % r.x))
        r.width = int(eval('%s' % r.width))
            
        MAX = item_h
        r.y = int(eval('%s' % r.y))
        r.height = int(eval('%s' % r.height))

        if r.x < 0:
            item_w -= r.x

        if r.y < 0:
            item_h -= r.y

        return max(item_w, r.width), max(item_h, r.height), r
    


    def init_vars(self, settings, display_type):
        """
        check which layout is used and set variables for the object
        """
        redraw = self.redraw
        
        if settings.menu.has_key(display_type):
            area = settings.menu[display_type][0]
        else:
            area = settings.menu['default'][0]

        area = eval('area.%s' % self.area_name)
        
        if (not self.area_val) or area != self.area_val:
            self.area_val = area
            redraw = TRUE
            
        if not settings.layout.has_key(area.layout):
            print '*** layout <%s> not found' % area.layout
            return FALSE

        old_layout = self.layout
        self.layout = settings.layout[area.layout]

        if old_layout and old_layout != self.layout:
            redraw = TRUE

        area.r = (area.x, area.y, area.width, area.height)

        return redraw
        


    def draw_background(self):
        """
        draw the <background> of the area
        """
        area = self.area_val

        redraw_watermark = self.redraw
        last_watermark = None

        if hasattr(self, 'watermark') and self.watermark:
            last_watermark = self.watermark[4]
            if self.menu.selected.image != self.watermark[4]:
                self.redraw_background += [ self.watermark[:4] ]
                self.watermark = None
                redraw_watermark = TRUE
            
        for bg in copy.deepcopy(self.layout.background):
            if isinstance(bg, xml_skin.XML_image):
                self.calc_geometry(bg)
                imagefile = ''
                
                # if this is the real background image, ignore the
                # OVERSCAN to fill the whole screen
                if bg.label == 'background':
                    bg.x -= config.OVERSCAN_X
                    bg.y -= config.OVERSCAN_Y
                    bg.width  += 2 * config.OVERSCAN_X
                    bg.height += 2 * config.OVERSCAN_Y

                if bg.label == 'watermark' and self.menu.selected.image:
                    imagefile = self.menu.selected.image
                    if last_watermark != imagefile:
                        self.redraw = TRUE
                        redraw_watermark = TRUE
                    self.watermark = (bg.x, bg.y, bg.width, bg.height, imagefile)
                else:
                    imagefile = bg.filename

                if self.name == 'screen':
                    bg.label = 'background'
                    
                if imagefile:
                    cname = '%s-%s-%s' % (imagefile, bg.width, bg.height)
                    image = self.imagecache[cname]
                    if not image:
                        image = osd.loadbitmap(imagefile)
                        if image:
                            image = pygame.transform.scale(image,(bg.width,bg.height))
                            self.imagecache[cname] = image
                    if image:
                        self.draw_image(image, bg, redraw=redraw_watermark)
                            
            elif isinstance(bg, xml_skin.XML_rectangle):
                self.calc_geometry(bg)
                self.drawroundbox(bg.x, bg.y, bg.width, bg.height, bg, redraw=self.redraw)

        if redraw_watermark:
            self.redraw = TRUE
            

    def drawroundbox(self, x, y, width, height, rect, redraw=TRUE):
        """
        draw a round box
        """
        # only call this function in mode 0 and mode 1
        if self.mode > 1:
            return

        area = self.area_val
        osd.drawroundbox(x, y, x+width, y+height,
                         color = rect.bgcolor, border_size=rect.size,
                         border_color=rect.color, radius=rect.radius, layer=self.alpha)
        if redraw:
            self.redraw_alpha  += [ (x, y, width, height) ]

        if self.mode == 1:
            self.content_alpha += [ (x, y, width, height) ]

            
    # Draws a text inside a frame based on the settings in the XML file
    def write_text(self, text, font, content, x=-1, y=-1, width=None, height=None,
                   align_h = None, align_v = None, mode='hard', ellipses='...'):
        """
        writes a text ... or better stores the information about this call
        in a variable. The real drawing is done inside draw()
        """
        if x == -1: x = content.x
        if y == -1: y = content.y

        if width == None:
            width  = content.width
        if height == None:
            height = content.height

        if not align_h:
            align_h = content.align
            if not align_h:
                align_h = 'left'
                
        if not align_v:
            align_v = content.valign
            if not align_v:
                align_v = 'top'

        self._write_text += [ ( text, font, x, y, width, height, align_h,
                                align_v, mode, ellipses ) ]



    def draw_image(self, image, val, redraw=TRUE):
        """
        draws an image ... or better stores the information about this call
        in a variable. The real drawing is done inside draw()
        """
        if isinstance(val, tuple):
            self._draw_image += [ ( image, val ) ]
            
            
        elif hasattr(val, 'label') and val.label == 'background':
            if redraw:
                self.background.blit(image, (val.x, val.y))
                # really redraw or is this a watermark problem?
                if self.redraw:
                    self.redraw_background += [ (val.x, val.y, val.width, val.height) ]
        else:
            self._draw_image += [ ( image, (val.x, val.y)) ]
            
