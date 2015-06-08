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

import re, os

from colors import css_colors_low
from style import Value, zero

class Rect(object):

    def __init__(self, x=0.0, y=0.0, width=0.0, height=0.0):
        self.x      = x
        self.y      = y
        self.width  = width
        self.height = height

    def expanded_by(self, edge):
        return Rect (
            self.x - edge.left,
            self.y - edge.top,
            self.width + edge.left + edge.right,
            self.height + edge.top + edge.bottom)

    def __str__(self):
        return "%4.1fx%4.1f@%4.1f/%4.1f" % (self.width, self.height, self.x, self.y)

class EdgeSizes(object):

    def __init__(self, left=0.0, right=0.0, top=0.0, bottom=0.0):
        self.left   = left
        self.right  = right
        self.top    = top
        self.bottom = bottom

    def __str__(self):
        return "[%4.1f %4.1f %4.1f %4.1f]" % (self.left, self.right, self.top, self.bottom)

class Dimensions(object):

    def __init__(self):
        self.content = Rect()
        self.padding = EdgeSizes()
        self.border  = EdgeSizes()
        self.margin  = EdgeSizes()

    def padding_box(self):
        """ The area covered by the content area plus its padding. """
        return self.content.expanded_by(self.padding)
    
    def border_box(self):
        """ The area covered by the content area plus padding and borders. """
        return self.padding_box().expanded_by(self.border)
    
    def margin_box(self):
        """ The area covered by the content area plus padding, borders, and margin. """
        return self.border_box().expanded_by(self.margin)
    
class LayoutContext(object):

    def __init__(self, parent, containing_block_dim, text_alignment):

        self.parent         = parent

        self.containing_block_dim = containing_block_dim
        # The layout algorithm expects the container height to start at 0.
        self.height         = 0 

        # current line box
        self.line           = [] # for inline boxes
        self.line_width     = 0  # used for table rows as well as inline boxes
        self.line_height    = 0
        self.text_alignment = text_alignment

        # table layout context
        self.table_colw     = None
        self.table_colw_sum = 0
        self.table_coli     = 0
        self.table_colf     = 1.0 # column width scaling factor

    def get_table_context(self):
        if self.table_colw:
            return self
        return self.parent.get_table_context()

    def __str__(self):
        return "LayoutContext (height=%4.1f, line_height=%4.1f)" % (self.height, self.line_height)

    def line_wrap(self):

        # adjust current line horizontally:
        xoffset = 0
        if self.text_alignment == 'center':
            xoffset = (self.containing_block_dim.content.width - self.line_width) / 2
        elif self.text_alignment == 'right':
            xoffset = (self.containing_block_dim.content.width - self.line_width) 

        if xoffset>0:
            for box in self.line:
                box.move (xoffset, 0)

        # wrap to next line 
        self.height      += self.line_height
        self.line         = [] # for inline boxes
        self.line_width   = 0
        self.line_height  = 0

class LayoutBox(object):

    def __init__(self, html, parent, box_type, node, style, text=None):

        #print "Creating LayoutBox of type %s, node %s" % (box_type, node)

        self.dimensions = Dimensions ()
        self.html       = html
        self.parent     = parent
        self.box_type   = box_type
        self.children   = []
        self.node       = node
        self.style      = style
        self.text       = text 
        self.img        = None

    def __str__(self):

        if self.node is None:
            return "LayoutBox@%s(%s)" % (id(self), self.text)

        return "LayoutBox@%s(%s %s)" % (id(self), self.node.tag, self.text)

    def move (self, xoffset, yoffset):
        self.dimensions.content.x += xoffset
        self.dimensions.content.y += yoffset
        for child in self.children:
            child.move (xoffset, yoffset)

    def get_style (self, key, fallback_key, default, inherit=False):

        if not self.style:
            if inherit and self.parent is not None:
                return self.parent.get_style (key, fallback_key, default, inherit)
            return default

        if key in self.style:
            return self.style[key][1]
        elif fallback_key in self.style:
            return self.style[fallback_key][1]
        
        if inherit and self.parent is not None:
            return self.parent.get_style (key, fallback_key, default, inherit)
        return default

    def get_color (self, key, inherit=False):
        color = self.get_style (key, None, None, inherit)
        if color is None:
            return None

        #print "Got color: %s -> %s" % (color, repr(color.to_rgb()))

        return color.to_rgb()

    def get_inline_container (self):
        """Where a new inline child should go."""

        if self.box_type == 'inline' or self.box_type == 'anonymous':
            return self

        # If we've just generated an anonymous block box, keep using it.
        # Otherwise, create a new one.

        if len(self.children)==0 or self.children[-1].box_type != 'anonymous':
            self.children.append(LayoutBox(self.html, self, 'anonymous', None, None))

        return self.children[-1]

    def layout(self, lc):
        """Lay out a box and its descendants."""
        if self.box_type == 'block' or self.box_type == 'anonymous':
            self.layout_block(lc)
        elif self.box_type == 'inline' :
            self.layout_inline(lc)
        elif self.box_type == 'table' :
            self.layout_table(lc)
        elif self.box_type == 'tr' :
            self.layout_table_row(lc)
        elif self.box_type == 'td' :
            self.layout_table_cell(lc)
        elif self.box_type == 'img' :
            self.layout_image(lc)
        else:
            # TODO
            pass

    def layout_image (self, lc):
        """Lay out an image element."""

        # similar to inline layout but no descendants

        # compute width and height of this image incl border/margin/padding
        self.calculate_image_width_height()

        # Determine where the box is located within its container.
        self.calculate_inline_position(lc)

        # adjust line height
        mb = self.dimensions.margin_box()
        if lc.line_height < mb.height:
            lc.line_height = mb.height

    def calculate_image_width_height(self):
        # margin, border, and padding have initial value 0.

        margin_left = self.get_style("margin-left", "margin", zero)
        margin_right = self.get_style("margin-right", "margin", zero)
        margin_top = self.get_style("margin-top", "margin", zero)
        margin_bottom = self.get_style("margin-bottom", "margin", zero)

        border_left = self.get_style("border-left-width", "border-width", zero)
        border_right = self.get_style("border-right-width", "border-width", zero)
        border_top = self.get_style("border-top-width", "border-width", zero)
        border_bottom = self.get_style("border-bottom-width", "border-width", zero)

        padding_left = self.get_style("padding-left", "padding", zero)
        padding_right = self.get_style("padding-right", "padding", zero)
        padding_top = self.get_style("padding-top", "padding", zero)
        padding_bottom = self.get_style("padding-bottom", "padding", zero)

        # get image size

        imagefn  = self.node.get('src')
        self.img = self.html.load_image(imagefn)
        width    = self.img.get_width()
        height   = self.img.get_height()

        d = self.dimensions
        d.content.width  = width
        d.content.height = height

        d.padding.left = padding_left.to_px()
        d.padding.right = padding_right.to_px()
        d.padding.top = padding_top.to_px()
        d.padding.bottom = padding_bottom.to_px()

        d.border.left = border_left.to_px()
        d.border.right = border_right.to_px()
        d.border.top = border_top.to_px()
        d.border.bottom = border_bottom.to_px()

        d.margin.left = margin_left.to_px()
        d.margin.right = margin_right.to_px()
        d.margin.top = margin_top.to_px()
        d.margin.bottom = margin_bottom.to_px()

    def layout_table (self, lc):
        """ Very simple table layout support at this point. """

        d = self.dimensions
        align = self.get_style("text-align", None, Value ('IDENT', 'left'), inherit=True)

        #
        # ask children about their widths to determine column widths 
        #
        lc.table_colw = []
        for tpart in self.children:
            #print "layout_table:   tpart=%s" % tpart
            for tr in tpart.children:
                #print "layout_table:      tr=%s" % tr
                col_i = 0
                for td in tr.children:
                    #print "layout_table:         td=%s" % td
                    if len(lc.table_colw) <= col_i:
                        lc.table_colw.append(0.0)

                    td.calculate_inline_width_height()

                    mb = td.dimensions.margin_box()

                    if mb.width > lc.table_colw[col_i]:
                        lc.table_colw[col_i] = mb.width
                    col_i += 1

        lc.table_colw_sum = reduce (lambda x, y: x+y, lc.table_colw, 0.0)
        #print "layout_table: colw=%s sum=%f" % (repr(lc.table_colw), lc.table_colw_sum)

        #
        # continue with regular block layout for now
        # (tds will use lc table info further down in the tree)
        #

        self.layout_block(lc)

    def layout_table_row (self, lc):
        """Lay out a table row and its descendants."""

        # very similar to block layout, except:
        # - reset lc.table_coli / line_width
        # - compute scaling factor for columns
        # - our content height := max(child.content.height)

        tlc = lc.get_table_context()
        tlc.table_coli = 0
        tlc.line_width = 0

        # Child width can depend on parent width, so we need to calculate this box's width before
        # laying out its children.
        self.calculate_block_width(lc)

        tlc.table_colf = self.dimensions.content.width / tlc.table_colw_sum

        # Determine where the box is located within its container.
        self.calculate_block_position(lc)

        # Recursively lay out the children of this box.
        clc = self.layout_block_children(lc)

        # our content height := max(child.content.height)
        h = 0
        for child in self.children:
            ch = child.dimensions.margin_box().height
            if ch > h:
                h = ch
        self.dimensions.content.height = h
        # make all cells of this row equal height:
        for child in self.children:
            child.dimensions.content.height += h - child.dimensions.margin_box().height

        # Increment the container's height so each child is laid out below the previous one.
        lc.height = lc.height + self.dimensions.margin_box().height


    def layout_table_cell (self, lc):
        """Lay out a table cell element and its descendants."""

        # we're basically doing block layout here, but within a fake context
        # tailored to our place in the table

        align = self.get_style("text-align", None, Value ('IDENT', 'left'), inherit=True)

        # fake dimensions for this table cell

        tlc = lc.get_table_context()

        d = lc.containing_block_dim

        fake_dim = Dimensions()
        fake_dim.content.x      = d.content.x + tlc.line_width
        fake_dim.content.y      = d.content.y + lc.height

        w = tlc.table_colw[tlc.table_coli] * tlc.table_colf

        fake_dim.content.width  = w
        fake_dim.content.height = 0

        #print "layout_table_cell: fake_dim.content: %s" % fake_dim.content

        fake_lc = LayoutContext(lc, fake_dim, align.to_str())

        self.layout_block(fake_lc)
        
        tlc.line_width += w
        tlc.table_coli += 1


    def layout_inline (self, lc):
        """Lay out a inline-level element and its descendants."""

        #print "layout_inline: %s %s" % (self, lc)

        # compute width and height of this box and all descendants
        self.calculate_inline_width_height()

        # Determine where the box is located within its container.
        self.calculate_inline_position(lc)

        # Recursively lay out the children of this box.
        self.layout_inline_children(lc)

        # adjust line height
        mb = self.dimensions.margin_box()
        if lc.line_height < mb.height:
            lc.line_height = mb.height

        #print "layout_inline done: %s %s" % (self, lc)

    def calculate_inline_width_height(self):
        #print "calculate_inline_width_height: %s" % (self)

        # margin, border, and padding have initial value 0.

        margin_left = self.get_style("margin-left", "margin", zero)
        margin_right = self.get_style("margin-right", "margin", zero)
        margin_top = self.get_style("margin-top", "margin", zero)
        margin_bottom = self.get_style("margin-bottom", "margin", zero)

        border_left = self.get_style("border-left-width", "border-width", zero)
        border_right = self.get_style("border-right-width", "border-width", zero)
        border_top = self.get_style("border-top-width", "border-width", zero)
        border_bottom = self.get_style("border-bottom-width", "border-width", zero)

        padding_left = self.get_style("padding-left", "padding", zero)
        padding_right = self.get_style("padding-right", "padding", zero)
        padding_top = self.get_style("padding-top", "padding", zero)
        padding_bottom = self.get_style("padding-bottom", "padding", zero)

        # calculate text size

        font_family = self.get_style("font-family", None, "Monospace", inherit=True)
        font_size   = self.get_style("font-size", None, 16, inherit=True)
        if self.text is not None:
            xtents = self.html.text_extents(font_family.to_str(), font_size.to_px(), self.text)
            width  = xtents[4]
            xtents = self.html.font_extents(font_family.to_str(), font_size.to_px())
            height = xtents[2]
        else:
            width  = 0
            height = 0

        # make room for children, if any

        for child in self.children:
            if child.box_type == 'img':
                child.calculate_image_width_height()

                #print "MAKING ROOM FOR IMAGE CHILD width=%f" % child.dimensions.content.width

            else:
                child.calculate_inline_width_height()

            cb = child.dimensions.margin_box()

            if cb.width > width:
                width = cb.width
            if cb.height > height:
                height = cb.height

        d = self.dimensions
        d.content.width  = width
        d.content.height = height

        d.padding.left = padding_left.to_px()
        d.padding.right = padding_right.to_px()
        d.padding.top = padding_top.to_px()
        d.padding.bottom = padding_bottom.to_px()

        d.border.left = border_left.to_px()
        d.border.right = border_right.to_px()
        d.border.top = border_top.to_px()
        d.border.bottom = border_bottom.to_px()

        d.margin.left = margin_left.to_px()
        d.margin.right = margin_right.to_px()
        d.margin.top = margin_top.to_px()
        d.margin.bottom = margin_bottom.to_px()

        #print "DONE calculate_inline_width_height: %s" % (self)
        #print "   d.content: %s" % d.content
        #print "   d.padding: %s" % d.padding
        #print "   d.border : %s" % d.border  
        #print "   d.margin : %s" % d.margin 

    def calculate_inline_position (self, lc):
        """Finish calculating the block's edge sizes, and position it within its containing block."""
        """http://www.w3.org/TR/CSS2/visudet.html#normal-block"""
        """Sets the vertical margin/padding/border dimensions, and the `x`, `y` values."""

        #print "calculate_inline_position: %s lc=%s" % (self, lc)

        d = self.dimensions

        # Position the box left to last inline box or wrap to next line

        nw = lc.line_width + d.content.width + d.margin.left + d.border.left + d.padding.left + d.margin.right + d.border.right + d.padding.right
        if nw > lc.containing_block_dim.content.width:
            lc.line_wrap()

        d.content.x = lc.containing_block_dim.content.x + d.margin.left + d.border.left + d.padding.left + lc.line_width
        d.content.y = lc.containing_block_dim.content.y + d.margin.top  + d.border.top  + d.padding.top + lc.height
        
        # advance cursor, add box to current line for alignment
        lc.line_width += d.content.width + d.margin.left + d.border.left + d.padding.left + d.margin.right + d.border.right + d.padding.right
        lc.line.append(self)
        #print "   d.content: %s" % d.content
        #print "   d.padding: %s" % d.padding
        #print "   d.border : %s" % d.border  
        #print "   d.margin : %s" % d.margin 

    def layout_inline_children(self, lc):
        align = self.get_style("text-align", None, Value ('IDENT', 'left'), inherit=True)

        clc = LayoutContext(lc, self.dimensions, align.to_str())
        for child in self.children:
            child.layout(clc)

        # finish + align last line
        clc.line_wrap()

        if clc.height > self.dimensions.content.height:
            self.dimensions.content.height = clc.height


    def layout_block (self, lc):
        """Lay out a block-level element and its descendants."""

        # Child width can depend on parent width, so we need to calculate this box's width before
        # laying out its children.
        self.calculate_block_width(lc)

        # Determine where the box is located within its container.
        self.calculate_block_position(lc)

        # Recursively lay out the children of this box.
        clc = self.layout_block_children(lc)

        # Parent height can depend on child height, so `calculate_height` must be called after the
        # children are laid out.
        self.calculate_block_height(clc)
    
        # Increment the height so each child is laid out below the previous one.
        #print "layout_block: %s complete height is %f, lc is %s" % (self, self.dimensions.margin_box().height, id(lc))
        lc.height = lc.height + self.dimensions.margin_box().height

    def calculate_block_width(self, lc):
        """Calculate the width of a block-level non-replaced element in normal flow."""     
        """http://www.w3.org/TR/CSS2/visudet.html#blockwidth"""
        """Sets the horizontal margin/padding/border dimensions, and the `width`."""

        #print "calculate_block_width: %s" % (self)

        # `width` has initial value `auto`.
        auto = Value('IDENT', 'auto')
        width = self.get_style ('width', None, auto)

        # margin, border, and padding have initial value 0.

        zero = Value ('DIMENSION', 0.0, 'px')

        margin_left = self.get_style("margin-left", "margin", zero)
        margin_right = self.get_style("margin-right", "margin", zero)

        border_left = self.get_style("border-left-width", "border-width", zero)
        border_right = self.get_style("border-right-width", "border-width", zero)

        padding_left = self.get_style("padding-left", "padding", zero)
        padding_right = self.get_style("padding-right", "padding", zero)
 
        total = reduce(lambda x, y: x+y, 
                           map(lambda x: 0.0 if x.is_auto() else x.to_px(), 
                               [margin_left, margin_right, border_left, border_right,
                                padding_left, padding_right, width]))

        #print "   margin: %s, %s;\n   border: %s, %s;\n   padding: %s, %s;\n   total: %s" % (margin_left, margin_right, border_left, border_right, padding_left, padding_right, total)
 
        # If width is not auto and the total is wider than the container, treat auto margins as 0.
        if not width.is_auto() and total > lc.containing_block_dim.content.width:
            if margin_left.is_auto():
                margin_left = zero
            
            if margin_right.is_auto():
                margin_right = zero
            

        # Adjust used values so that the above sum equals `lc.containing_block_dim.width`.
        # Each arm of the `match` should increase the total width by exactly `underflow`,
        # and afterward all values should be absolute lengths in px.
        underflow = lc.containing_block_dim.content.width - total

        #print "   underflow: %f" % underflow

        # If the values are overconstrained, calculate margin_right.
        if not width.is_auto() and not margin_left.is_auto() and not margin_right.is_auto():
            margin_right = Value.length(margin_right.to_px() + underflow, 'px')

        # If exactly one size is auto, its used value follows from the equality.
        elif not width.is_auto() and not margin_left.is_auto() and margin_right.is_auto():
            margin_right = Value.length(underflow, 'px')
        elif not width.is_auto() and margin_left.is_auto() and not margin_right.is_auto():
            margin_right = Value.length(underflow, 'px')

        # If width is set to auto, any other auto values become 0.
        elif width.is_auto() :
            if margin_left.is_auto():
                margin_left = Value.length(0.0, 'px')
            if margin_right.is_auto():
                margin_right = Value.length(0.0, 'px')

            if underflow >= 0.0:
                # Expand width to fill the underflow.
                width = Value.length(underflow, 'px')
            else:
                # Width can't be negative. Adjust the right margin instead.
                width = Value.length(0.0, 'px')
                margin_right = Value.length(margin_right.to_px() + underflow, 'px')

        # If margin-left and margin-right are both auto, their used values are equal.
        elif not width.is_auto() and margin_left.is_auto() and margin_right.is_auto():
            margin_left = Value.length(underflow / 2.0, 'px');
            margin_right = Value.length(underflow / 2.0, 'px');


        d = self.dimensions
        d.content.width = width.to_px()

        d.padding.left = padding_left.to_px()
        d.padding.right = padding_right.to_px()

        d.border.left = border_left.to_px()
        d.border.right = border_right.to_px()

        d.margin.left = margin_left.to_px()
        d.margin.right = margin_right.to_px()

        #print "   d.content: %s" % d.content
        #print "   d.padding: %s" % d.padding
        #print "   d.border : %s" % d.border  
        #print "   d.margin : %s" % d.margin 

 
    def calculate_block_position (self, lc):
        """Finish calculating the block's edge sizes, and position it within its containing block."""
        """http://www.w3.org/TR/CSS2/visudet.html#normal-block"""
        """Sets the vertical margin/padding/border dimensions, and the `x`, `y` values."""

        #print "calculate_block_position: %s" % self

        d = self.dimensions

        # margin, border, and padding have initial value 0.
        zero = Value ('DIMENSION', 0.0, 'px')

        # If margin-top or margin-bottom is `auto`, the used value is zero.
        d.margin.top = self.get_style("margin-top", "margin", zero).to_px()
        d.margin.bottom = self.get_style("margin-bottom", "margin", zero).to_px()

        d.border.top = self.get_style("border-top-width", "border-width", zero).to_px()
        d.border.bottom = self.get_style("border-bottom-width", "border-width", zero).to_px()

        d.padding.top = self.get_style("padding-top", "padding", zero).to_px()
        d.padding.bottom = self.get_style("padding-bottom", "padding", zero).to_px()

        d.content.x = lc.containing_block_dim.content.x + d.margin.left + d.border.left + d.padding.left

        # Position the box below all the previous boxes in the container.
        d.content.y = lc.height + lc.containing_block_dim.content.y + d.margin.top + d.border.top + d.padding.top
    
        #print "   d.content: %s" % d.content
        #print "   d.padding: %s" % d.padding
        #print "   d.border : %s" % d.border  
        #print "   d.margin : %s" % d.margin 

    def layout_block_children(self, lc):

        align = self.get_style("text-align", None, Value ('IDENT', 'left'), inherit=True)

        clc = LayoutContext(lc, self.dimensions, align.to_str())
        for child in self.children:
            child.layout(clc)

        # finish + align last line
        clc.line_wrap()

        return clc

    def calculate_block_height(self, lc):
        """Height of a block-level non-replaced element in normal flow with overflow visible."""

        # If the height is set to an explicit length, use that exact length.
        # Otherwise, just keep the value set by `layout_block_children`.

        if self.style is not None and 'height' in self.style:
            self.dimensions.content.height = self.get_style("height", None, None).to_px()
        else:
            self.dimensions.content.height = lc.height + lc.line_height

    def render (self, ctx):

        self.render_background(ctx)
        self.render_borders(ctx)
        self.render_text(ctx)
        self.render_image(ctx)

        for child in self.children:
            child.render (ctx)

    def render_background (self, ctx):

        color = self.get_color ('background')
        if color is None:
            return
        ctx.set_source_rgba(color[0], color[1], color[2], 1.0)

        rect = self.dimensions.border_box() 
        ctx.rectangle (rect.x, rect.y, rect.width, rect.height)
        ctx.fill()

    def render_borders (self, ctx):
        color = self.get_color ('border-color')
        if color is None:
            return
        ctx.set_source_rgba(color[0], color[1], color[2], 1.0)

        d = self.dimensions
        border_box = d.border_box()

        # Left border
        width = self.get_style ('border-left-width', 'border-width', zero).to_px()
        ctx.set_line_width(width) 
        ctx.rectangle (border_box.x, border_box.y, d.border.left, border_box.height)
        ctx.fill()

        # Right border
        width = self.get_style ('border-right-width', 'border-width', zero).to_px()
        ctx.set_line_width(width) 
        ctx.rectangle (border_box.x + border_box.width - d.border.right, border_box.y, d.border.right, border_box.height)
        ctx.fill()

        # Top border
        width = self.get_style ('border-top-width', 'border-width', zero).to_px()
        ctx.set_line_width(width) 
        ctx.rectangle (border_box.x, border_box.y, border_box.width, d.border.top)
        ctx.fill()

        # Bottom border
        width = self.get_style ('border-bottom-width', 'border-width', zero).to_px()
        ctx.set_line_width(width) 
        ctx.rectangle (border_box.x, border_box.y + border_box.height - d.border.bottom, border_box.width, d.border.bottom)
        ctx.fill()


    def render_text (self, ctx):
       
        if not self.text:
            return

        ctx.set_source_rgba(255, 255, 255, 1.0)

        font_family = self.get_style("font-family", None, "Monospace", inherit=True).to_str()
        font_size   = self.get_style("font-size", None, 16, inherit=True).to_px()

        color = self.get_color ('color', inherit=True)
        if color is None:
            return

        #print "Rendering text: %s %s " % (self.text, repr(color))

        ctx.set_source_rgba   (color[0], color[1], color[2], 1.0)
        ctx.select_font_face  (font_family)
        ctx.set_font_size     (font_size)
        xt = ctx.font_extents ()
        ctx.move_to           (self.dimensions.content.x, self.dimensions.content.y + xt[0])
        ctx.show_text         (self.text)

    def render_image (self, ctx):
       
        if not self.img:
            return

        d = self.dimensions

        ctx.set_source_surface(self.img, d.content.x, d.content.y)
        ctx.rectangle (d.content.x, d.content.y, self.img.get_width(), self.img.get_height())
        ctx.fill ()

