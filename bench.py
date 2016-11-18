#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#
# Copyright 2016 Guenter Bartsch
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
# simple benchmark app for robinson tuning
#

import sys
import numpy as np
import os
import logging
import pstats, cProfile

from time import time

import robinson

ITERATIONS = 10

logging.basicConfig(level=logging.DEBUG)

class DummyContext(object):

    def select_font_face(self, face):
        pass
    def set_font_size(self, size):
        pass
    def text_extents (self, txt):
        # x_bearing, y_bearing, width, height, x_advance, y_advance
        return 1,1,10,10,10,10
    def font_extents(self):
        # ascent, descent, height, max_x_advance, max_y_advance
        return 1,1, 10, 20, 10
    def set_source_rgba(self, r,g,b,a):
        pass
    def set_source_surface(self, surface, x=0, y=0):
        pass
    def set_line_width(self, w):
        pass
    def move_to(self, x, y):
        pass
    def show_text(self, txt):
        pass
    def fill(self):
        pass
    def paint(self):
        pass
    def rectangle(self, x, y, w, h):
        pass

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

def run_benchmark (htmlfn, cssfn, pngfn) :

    print "starting benchmark, %d iterations..." % ITERATIONS

    with open(htmlfn) as f:
        html = f.read()
    with open(cssfn) as f:
        css = f.read()

    WIDTH, HEIGHT = 1024, 576

    ctx = DummyContext()

    for i in range(ITERATIONS):
        rob = robinson.html (html, css, WIDTH, load_resourcefn, text_extents, font_extents, ctx)
        rob.render(ctx)

#
# init
#

reload(sys)
sys.setdefaultencoding('utf-8')
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

#
# main
#

start_time = time()

cProfile.runctx("run_benchmark ('test/weather.html', 'test/weather.css', 'weather.png')", globals(), locals(), "Profile.prof")

end_time = time()

logging.debug("robinson delay=%f" % (end_time - start_time))

# s = pstats.Stats("Profile.prof")
# s.strip_dirs().sort_stats("time").print_stats()

