#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#
# Copyright 2015 Guenter Bartsch
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
# generate some test rendering images to show off some of robinson's
# rendering capabilities
#

import os
import math
import robinson
import cairo
import traceback

def load_resourcefn (fn):
    res = None
    with open(fn, 'rb') as f:
        res = f.read()
    return res

def text_extents(ctx, font_face, font_size, text):
    ctx.select_font_face (font_face)
    ctx.set_font_size (font_size)
    return ctx.text_extents (text)

def font_extents(ctx, font_face, font_size):
    ctx.select_font_face (font_face)
    ctx.set_font_size (font_size)
    return ctx.font_extents ()

def render_pdf (htmlfn, cssfn, pdffn) :

    with open(htmlfn) as f:
        html = f.read()
    with open(cssfn) as f:
        css = f.read()

    # For PDF files, width and height are in "point" units (1/72 of an inch)
    WIDTH, HEIGHT = 14*72, 8.5*72

    surface = cairo.PDFSurface (pdffn,WIDTH, HEIGHT)
    ctx = cairo.Context (surface)

    rob = robinson.html (html, css, WIDTH, load_resourcefn, text_extents, font_extents, ctx)

    rob.render(ctx)

    surface.show_page()

render_pdf ('test/splash.html', 'test/splash.css', 'splash.pdf')
render_pdf ('test/weather.html', 'test/weather.css', 'weather.pdf')


