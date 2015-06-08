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
# tiny html+css renderer, based on mbrubeck's rendering engine 
# with some enhancements:
#
# - uses html5lib + tinycss for parsing
# - uses cssselect for css selector handling
# - some support for inline and table layout
# - support for text and fonts including word wrapping and alignment
#

import re, os

from colors import css_colors_low

def hash_to_rgb (h):

    r = h >> 16
    g = (h >> 8) & 0xFF
    b = h & 0xFF

    return (r / 255.0, g / 255.0, b / 255.0)

#
# CSS helpers (pretty crude)
#

class Value (object):
    
    def __init__(self, type, value, unit = None):

        self.type  = type
        self.value = value
        self.unit  = unit

    @classmethod
    def from_token(cls, token):
        # FIXME: create multiple tokens
        t = token[0]
        return cls(t.type, t.value, t.unit)

    @classmethod
    def length(cls, value, unit):
        return cls('DIMENSION', value, unit)

    def to_px (self):
        if self.type == 'INTEGER' or self.type == 'NUMBER':
            return float(self.value)
        elif self.type == 'DIMENSION':
            # FIXME: take unit into account!
            return float(self.value)
        elif self.is_auto():
            return 0.0
        else:
            raise Exception ("Value: %s to_px: Unknown token type! " % self)

    def to_str (self):
        if self.type == 'IDENT' or self.type == 'STRING':
            return self.value
        else:
            raise Exception ("Value: to_str: Unknown token type! %s" % self.type)

    def is_auto (self):
        if self.type != 'IDENT':
            return False

        return self.value == 'auto'

    def to_rgb (self):

        if self.type == 'IDENT':
            cname = self.value.lower() # case-insensitive
            if cname in css_colors_low:
                return hash_to_rgb(css_colors_low[cname])
        elif self.type == 'HASH':
            return hash_to_rgb (int(self.value[1:], 16))

        return None

    def __str__ (self):
        return 'Value(%s, %s, %s)' % (self.type, repr(self.value), repr(self.unit))

# we need this in all sorts of places
zero = Value ('DIMENSION', 0.0, 'px')

def get_style_string (key, styles, default = ''):

    if not key in styles:
        return default

    return styles[key][1].to_str()

