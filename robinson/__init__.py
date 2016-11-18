#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#
# Copyright 2015, 2016 Guenter Bartsch
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# tiny html+css renderer, based on mbrubeck's rendering engine 
# with some enhancements:
#
# - uses lxml + tinycss for parsing
# - uses cssselect for css selector handling
# - some support for inline and table layout
# - support for text and fonts including word wrapping and alignment
#

import re, os
from StringIO import StringIO

from lxml import etree
import tinycss
import cssselect
import cairo
import traceback
import time
import cProfile, pstats

from style import Value, get_style_string
from layout import Dimensions, LayoutBox, LayoutContext

VERBOSE = False

img_cache       = {}

#
# helper / debug functions
#

def pprint_ltree (box, indent):

    print "LTREE: ",
    for i in range(indent):
        print ' ',

    print box.box_type, box.node.tag if box.node is not None else 'NONE', repr(box.text), box.dimensions.content, id(box)

    for child in box.children:
        pprint_ltree (child, indent+1)

def speci2prio(speci):
    return speci[0] * 10000 + speci[1] * 100 + speci[2]

#
# main robinson html render class
#

class html(object):

    def _build_text_boxes (self, root, text):
        """ create text box if we have text """

        if text is None:
            return
        
        txt1 = text.lstrip().rstrip()
        if len(txt1) == 0:
            return

        # collapse whitespace
        txt = ''
        ws = True
        for c in txt1:
            if c.isspace():
                if ws:
                    continue
                ws = True
                txt += ' '
            else:
                ws = False
                txt += c

        # split
        parts = txt.split(' ')

        ic = root.get_inline_container()
        for part in parts:
            b = LayoutBox (self, ic, 'inline', None, None, part+' ') 
            ic.children.append (b)


    def _build_layout_tree (self, parent, node, style_map):
        """ Build the tree of LayoutBoxes, but don't perform any layout calculations yet. """

        #print "layout_tree: working on %s %s text:%s tail:%s" % (node.tag, node.attrib, repr(node.text), repr(node.tail))

        # Create the root box.

        style = style_map[node]

        display = get_style_string (u'display', style, 'block')
        if display != 'none':
            box_type = display
        else:
            raise Exception ('Root node has display: none.')

        root = LayoutBox (self, parent, box_type, node, style) 
        self._build_text_boxes (root, node.text)

        # Create the descendant boxes.

        for child in node:
            
            display = get_style_string (u'display', style_map[child], 'block')

            if display == 'none':
                # Don't lay out nodes with `display: none;`
                pass
            elif display == 'inline' or display == 'img':
                ic = root.get_inline_container()
                ic.children.append (self._build_layout_tree(ic, child, style_map))
            else:
                root.children.append (self._build_layout_tree(root, child, style_map))

            # create text box if we have tail text
            self._build_text_boxes (root, child.tail)

        return root

    def _layout_tree (self, root, style_map, containing_block_dim):
        """Transform a lxml node tree into a layout tree"""

        root_box = self._build_layout_tree(None, root, style_map)
        #pprint_ltree (root_box, 0)

        lc = LayoutContext (None, containing_block_dim, 'left')
        root_box.layout (lc)

        return root_box

    def load_image (self, imagefn):

        global img_cache

        if VERBOSE:
            print "robinson: load_image(%s)..." % imagefn

        if not imagefn in img_cache:

            if VERBOSE:
                print "robinson: load_image CACHE MISS" 

            pngstr = self.load_resourcefn (imagefn)

            sio = StringIO (pngstr)
            try:
                img_cache[imagefn] = cairo.ImageSurface.create_from_png(sio)
            except:
                traceback.print_exc()
                img_cache[imagefn] = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
                
            sio.close()

        return img_cache[imagefn]

    def render (self, ctx):

        color = self.ltree.get_color ('background')
        if color is not None:
            ctx.set_source_rgba(color[0], color[1], color[2], 1.0)
            ctx.paint()

        self.ltree.render(ctx)

    def __init__(self, html, css, width, load_resourcefn, text_extents, font_extents, user_data):

        self.text_extents    = text_extents
        self.font_extents    = font_extents
        self.load_resourcefn = load_resourcefn
        self.user_data       = user_data

        if VERBOSE:
            start = time.clock()
            end   = time.clock()
            print "robinson: %8.3fs lxml parsing..." % (end-start)

            pr = cProfile.Profile()

        root = etree.fromstring(html)
        document = etree.ElementTree(root)

        if VERBOSE:
            end   = time.clock()

            print repr(root), root.__class__
            print document, repr(document), document.__class__
            print etree.tostring(document.getroot())

            print "robinson: %8.3fs tinycss.css21.CSS21Parser()..." % (end-start)

        cssparser = tinycss.css21.CSS21Parser()

        stylesheet = cssparser.parse_stylesheet(css)
        
        if VERBOSE:
            end   = time.clock()
            print "robinson: %8.3fs style mapping..." % (end-start)

        style_map = {}

        sel_to_xpath = cssselect.xpath.HTMLTranslator().selector_to_xpath
        for rule in stylesheet.rules:
            if not isinstance (rule, tinycss.css21.RuleSet):
                continue

            sel_css = rule.selector.as_css()
            sels    = cssselect.parse (sel_css)

            #print "CSS Ruleset: %s" % (rule.selector.as_css())

            for sel in sels:
                speci = sel.specificity()
                prio  = speci2prio (speci)
                #print "   selector: %s, specificity: %s (%06d)" % (repr(sel), sel.specificity(), prio)

                xpath = sel_to_xpath (sel)
                #print "   xpath: %s" % repr(xpath)

                for item in document.xpath(xpath):
                    #print "     matched item: %s" % repr(item.tag)

                    if not item in style_map:
                        style_map[item] = {}

                    for decl in rule.declarations:
                        #print "       declaration: %s: %s" % (decl.name, decl.value)

                        if not decl.name in style_map[item]:
                            style_map[item][decl.name] = (prio, Value.from_token(decl.value))
                        else:
                            if prio > style_map[item][decl.name][0]:
                                style_map[item][decl.name] = (prio, Value.from_token(decl.value))
         
        #print "Style map done."
        #print repr(style_map)

        if VERBOSE:
            end   = time.clock()
            print "robinson: %8.3fs building layout tree..." % (end-start)
            pr.enable()

        viewport = Dimensions ()
        viewport.content.width  = width
        self.ltree = self._layout_tree (document.getroot(), style_map, viewport)

        if VERBOSE:
            end   = time.clock()
            print "robinson: %8.3fs __init__ done." % (end-start)

            # pr.disable()
            # s = StringIO()
            # sortby = 'cumulative'
            # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            # ps.print_stats()
            # print s.getvalue()

        #pprint_ltree (self.ltree, 0)

