# -*- coding: utf-8 -*-

# Copyright (C) 2003-2006 by Igor E. Novikov
#
# This library is covered by GNU Library General Public License.
# For more info see COPYRIGHTS file in sK1 root directory.

from Ttk import TFrame, TLabel, TCombobox
from Tkinter import RIGHT, BOTTOM, X, Y, BOTH, LEFT, TOP,W, E, DISABLED, NORMAL, StringVar, DoubleVar, IntVar
import PIL.Image

from app.X11.X import GXxor, ZPixmap

from colorsys import hsv_to_rgb, rgb_to_hsv

from app.conf.const import CHANGED, ConstraintMask

from app import _sketch
from app import  _, CreateRGBColor, StandardColors, Trafo, SketchError, Publisher
from app.Graphics import color

from app.UI.tkext import PyWidget

import string


xyramp_size = (140, 140)
zramp_size = (15, 140)



class ColorChooserWidget(TFrame):
	
	def __init__(self, parent, color=None, **kw):
		self.refcolor=color
		self.color=color
		self.parent=parent
		TFrame.__init__(self, parent, style='FlatFrame', **kw)

		frame = TFrame(self, style="RoundedFrame", borderwidth=5)
		frame.pack(side = LEFT)
		viewxy = ChooseRGBXY(frame, xyramp_size[0], xyramp_size[1], 0, 1)
		viewxy.pack(side = LEFT)

		frame = TFrame(self, style="RoundedFrame", borderwidth=5)
		frame.pack(side = LEFT)
		viewz = ChooseRGBZ(frame, zramp_size[0], zramp_size[1], 2)
		viewz.pack(side = LEFT)



class ImageView(PyWidget):

	# display a PIL Image

	def __init__(self, master, image, **kw):
		width, height = image.size
		if not kw.has_key('width'):
			kw["width"] = width
		if not kw.has_key('height'):
			kw["height"] = height
		apply(PyWidget.__init__, (self, master), kw)
		self.gc_initialized = 0
		self.image = image
		self.ximage = None

	def MapMethod(self):
		if not self.gc_initialized:
			self.init_gc()
			self.gc_initialized = 1

	def init_gc(self):
		self.gc = self.tkwin.GetGC()
		self.visual = color.skvisual
		w = self.tkwin
		width, height = self.image.size
		depth = self.visual.depth
		if depth > 16:
			bpl = 4 * width
		elif depth > 8:
			bpl = ((2 * width + 3) / 4) * 4
		elif depth == 8:
			bpl = ((width + 3) / 4) * 4
		else:
			raise SketchError('unsupported depth for images')
		self.ximage = w.CreateImage(depth, ZPixmap, 0, None, width, height,
									32, bpl)
		self.set_image(self.image)

	def set_image(self, image):
		self.image = image
		if self.ximage:
			ximage = self.ximage
			_sketch.copy_image_to_ximage(self.visual, image.im, ximage,
											0, 0, ximage.width, ximage.height)
			self.UpdateWhenIdle()

	def RedrawMethod(self, region = None):
		self.gc.PutImage(self.ximage, 0, 0, 0, 0,
							self.ximage.width, self.ximage.height)

	def ResizedMethod(self, width, height):
		pass

class ChooseComponent(ImageView, Publisher):

	def __init__(self, master, width, height, color = (0, 0, 0), **kw):
		image = PIL.Image.new('RGB', (width, height))
		apply(ImageView.__init__, (self, master, image), kw)
		self.set_color(color)
		self.drawn = 0
		self.dragging = 0
		self.drag_start = (0, 0, 0)
		self.update_pending = 1
		self.invgc = None
		self.bind('<ButtonPress>', self.ButtonPressEvent)
		self.bind('<Motion>', self.PointerMotionEvent)
		self.bind('<ButtonRelease>', self.ButtonReleaseEvent)

	def destroy(self):
		ImageView.destroy(self)
		Publisher.Destroy(self)

	def set_color(self, color):
		self.color = tuple(color)

	def init_gc(self):
		ImageView.init_gc(self)
		self.invgc = self.tkwin.GetGC(foreground = ~0,
										function = GXxor)
		self.tk.call(self._w, 'motionhints')
		self.show_mark()

	def ButtonPressEvent(self, event):
		if not self.dragging:
			self.drag_start = self.color
		self.dragging = self.dragging + 1
		self.move_to(self.win_to_color(event.x, event.y), event.state)

	def ButtonReleaseEvent(self, event):
		self.dragging = self.dragging - 1
		self.move_to(self.win_to_color(event.x, event.y), event.state)

	def PointerMotionEvent(self, event):
		if self.dragging:
			x, y = self.tkwin.QueryPointer()[4:6]
			self.move_to(self.win_to_color(x, y), event.state)

	#def moveto(self, x, y): #to be supplied by derived classes

	def hide_mark(self):
		if self.drawn:
			self.draw_mark()
			self.drawn = 0

	def show_mark(self):
		if not self.drawn and self.invgc:
			self.draw_mark()
			self.drawn = 1

	#def draw_mark(self):       # to be supplied by derived classes

	def UpdateWhenIdle(self):
		if not self.update_pending:
			self.update_pending = 1
			ImageView.UpdateWhenIdle(self)

	def RedrawMethod(self, region = None):
		if self.update_pending:
			self.update_ramp()
			self.update_pending = 0
		ImageView.RedrawMethod(self, region)
		if self.drawn:
			self.draw_mark()

	def RGBColor(self):
		return apply(CreateRGBColor, apply(hsv_to_rgb, self.color)).RGB()

class ChooseRGBXY(ChooseComponent):

	def __init__(self, master, width, height, xcomp = 0, ycomp = 1,
					color = (0, 0, 0), **kw):
		self.xcomp = xcomp
		self.ycomp = ycomp
		self.win_to_color = Trafo(1 / float(width - 1), 0,
									0, -1 / float(height - 1),
									0, 1)
		self.color_to_win = self.win_to_color.inverse()
		apply(ChooseComponent.__init__, (self, master, width, height, color),
				kw)

	def SetColor(self, color):
		color = apply(rgb_to_hsv, tuple(color))
		otheridx = 3 - self.xcomp - self.ycomp
		if color[otheridx] != self.color[otheridx]:
			self.UpdateWhenIdle()
		self.hide_mark()
		self.color = color
		self.show_mark()

	def update_ramp(self):
		_sketch.fill_hsv_xy(self.image.im, self.xcomp, self.ycomp, self.color)
		self.set_image(self.image)

	def move_to(self, p, state):
		x, y = p
		if state & ConstraintMask:
			sx = self.drag_start[self.xcomp]
			sy = self.drag_start[self.ycomp]
			if abs(sx - x) < abs(sy - y):
				x = sx
			else:
				y = sy
		if x < 0:       x = 0
		elif x >= 1.0:  x = 1.0
		if y < 0:       y = 0
		elif y >= 1.0:  y = 1.0

		color = list(self.color)
		color[self.xcomp] = x
		color[self.ycomp] = y
		self.hide_mark()
		self.color = tuple(color)
		self.show_mark()
		self.issue(CHANGED, self.RGBColor())

	def draw_mark(self):
		color = self.color
		w, h = self.image.size
		x, y = self.color_to_win(color[self.xcomp], color[self.ycomp])
		x = int(x)
		y = int(y)
		self.invgc.DrawLine(x, 0, x, h)
		self.invgc.DrawLine(0, y, w, y)


class ChooseRGBZ(ChooseComponent):

	def __init__(self, master, width, height, comp = 1, color = (0, 0, 0),
					**kw):
		self.comp = comp
		self.win_to_color = Trafo(1, 0, 0, -1 / float(height - 1), 0, 1)
		self.color_to_win = self.win_to_color.inverse()
		apply(ChooseComponent.__init__, (self, master, width, height, color),
				kw)

	def SetColor(self, color):
		c = self.color;
		color = apply(rgb_to_hsv, tuple(color))
		if ((self.comp == 0 and (color[1] != c[1] or color[2] != c[2]))
			or (self.comp == 1 and (color[0] != c[0] or color[2] != c[2]))
			or (self.comp == 2 and (color[0] != c[0] or color[1] != c[1]))):
			self.hide_mark()
			self.color = color
			self.show_mark()
			self.UpdateWhenIdle()

	def update_ramp(self):
		_sketch.fill_hsv_z(self.image.im, self.comp, self.color)
		self.set_image(self.image)

	def move_to(self, p, state):
		y = p.y
		if y < 0:       y = 0
		elif y >= 1.0:  y = 1.0

		color = list(self.color)
		color[self.comp] = y
		self.hide_mark()
		self.color = tuple(color)
		self.show_mark()
		self.issue(CHANGED, self.RGBColor())

	def draw_mark(self):
		w, h = self.image.size
		x, y = self.color_to_win(0, self.color[self.comp])
		x = int(x)
		y = int(y)
		self.invgc.DrawLine(0, y, w, y)

