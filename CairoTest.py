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

def render_image (htmlfn, cssfn, pngfn) :

    with open(htmlfn) as f:
        html = f.read()
    with open(cssfn) as f:
        css = f.read()

    WIDTH, HEIGHT = 1024, 576

    surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    ctx = cairo.Context (surface)

    rob = robinson.html (html, css, WIDTH, load_resourcefn, text_extents, font_extents, ctx)

    rob.render(ctx)

    surface.write_to_png (pngfn)

render_image ('test/splash.html', 'test/splash.css', 'splash.png')
render_image ('test/weather.html', 'test/weather.css', 'weather.png')


