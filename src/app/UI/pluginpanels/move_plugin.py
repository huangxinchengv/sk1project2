# -*- coding: utf-8 -*-

# Copyright (C) 2003-2006 by Igor E. Novikov
#
# This library is covered by GNU Library General Public License.
# For more info see COPYRIGHTS file in sK1 root directory.

from Ttk import TFrame, TLabel, TCheckbutton, TRadiobutton, TLabelframe
from Tkinter import Spinbox, DoubleVar, StringVar, BooleanVar, IntVar, StringVar
from Tkinter import RIGHT, BOTTOM, X, Y, W, E, BOTH, LEFT, TOP, GROOVE, E, DISABLED, NORMAL
from app.UI.tkext import UpdatedButton, UpdatedRadiobutton
from app.UI.ttk_ext import TSpinbox

from app.conf.const import SELECTION, CHANGED, EDITED

from app import _, config, Rect, Trafo
from app.conf import const
import app

from ppanel import PluginPanel

from app.UI.lengthvar import LengthVar

class MovePanel(PluginPanel):
	name='Move'
	title = _("Move")


	def init(self, master):
		PluginPanel.init(self, master)

		root=self.mw.root
		self.var_width_number=DoubleVar(root)
		self.var_height_number=DoubleVar(root)

		var_width_unit = StringVar(root)
		var_height_unit = StringVar(root)
		
		unit = config.preferences.default_unit
		self.var_width = LengthVar(10, unit, self.var_width_number, var_width_unit)
		self.var_height = LengthVar(10, unit,self.var_height_number,var_height_unit)
		
		jump=config.preferences.default_unit_jump
		self.var_width.set(0)
		self.var_height.set(0)
		
		self.var_position = StringVar(root)
		self.var_position.set('Аbsolute')
		
		self.var_basepoint = StringVar(root)
		self.var_basepoint.set('C')
		 
		#---------------------------------------------------------
		top = TFrame(self.panel, style='FlatFrame', borderwidth=5)
		top.pack(side = TOP, fill=BOTH)
		#---------------------------------------------------------
		# Horisontal size
		size_frameH = TFrame(top, style='FlatFrame', borderwidth=3)
		size_frameH.pack(side = TOP, fill = BOTH)
		
		label = TLabel(size_frameH, style='FlatLabel', text = _("H: "))
		label.pack(side = LEFT, padx=5)
		self.entry_width = TSpinbox(size_frameH,  var=0, vartype=1, textvariable = self.var_width_number, 
									min = -50000, max = 50000, step = jump, width = 10, command=self.apply_move)
		self.entry_width.pack(side = LEFT)

		self.labelwunit = TLabel(size_frameH, style='FlatLabel', text = self.var_width.unit)
		self.labelwunit.pack(side = LEFT, padx=5)
		#---------------------------------------------------------
		# Vertical 
		
		size_frameV = TFrame(top, style='FlatFrame', borderwidth=3)
		size_frameV.pack(side = TOP, fill = BOTH)
		label = TLabel(size_frameV, style='FlatLabel', text = _("V: "))
		label.pack(side = LEFT, padx=5)
		
		self.entry_height = TSpinbox(size_frameV, var=0, vartype=1, textvariable = self.var_height_number, 
									min = -50000, max = 50000, step = jump, width = 10, command=self.apply_move)
		self.entry_height.pack(side = LEFT)
		
		self.labelhunit = TLabel(size_frameV, style='FlatLabel', text = self.var_height.unit)
		self.labelhunit.pack(side = LEFT, padx=5)
		
		#---------------------------------------------------------
		# position chek
		
		self.position_check = TCheckbutton(top, text = _("Аbsolute Coordinates"), variable = self.var_position,
												onvalue='Аbsolute', offvalue='Relative', command = self.position)
		self.position_check.pack(side = TOP, anchor=W, padx=5,pady=5)

		
		
		#---------------------------------------------------------
		# Basepoint check
		# NW -- N -- NE
		# |     |     |
		# W  -- C --  E
		# |     |     |
		# SW -- S -- SE
		#
		# USER - bazepoint
		
		label = TLabel(top, style='FlatLabel', text = _("Basepoint:"))
		label.pack(side = TOP, fill = BOTH, padx=5)
		basepoint_frame=TLabelframe(top, labelwidget=label, style='Labelframe', borderwidth=4)
		basepoint_frame.pack(side = TOP, fill=X, padx=5, pady=2)
		
		frame=TFrame(basepoint_frame, style='FlatFrame')
		frame.pack(side = TOP, fill = BOTH, padx=5)
		
		radio = UpdatedRadiobutton(frame, value = 'NW', text = _(""), variable = self.var_basepoint, command = self.apply_basepoint)
		radio.pack(side=LEFT, anchor=W)
		radio = UpdatedRadiobutton(frame, value = 'N', text = _(""), variable = self.var_basepoint, command = self.apply_basepoint)
		radio.pack(side=LEFT, anchor=W)
		radio = UpdatedRadiobutton(frame, value = 'NE', text = _(""), variable = self.var_basepoint, command = self.apply_basepoint)
		radio.pack(side=LEFT, anchor=W)
		
		frame=TFrame(basepoint_frame, style='FlatFrame')
		frame.pack(side = TOP, fill = BOTH, padx=5)
		
		radio = UpdatedRadiobutton(frame, value = 'W', text = _(""), variable = self.var_basepoint, command = self.apply_basepoint)
		radio.pack(side=LEFT, anchor=W)
		radio = UpdatedRadiobutton(frame, value = 'C', text = _(""), variable = self.var_basepoint, command = self.apply_basepoint)
		radio.pack(side=LEFT, anchor=W)
		radio = UpdatedRadiobutton(frame, value = 'E', text = _(""), variable = self.var_basepoint, command = self.apply_basepoint)
		radio.pack(side=LEFT, anchor=W)
		
		frame=TFrame(basepoint_frame, style='FlatFrame')
		frame.pack(side = TOP, fill = BOTH, padx=5)
		
		radio = UpdatedRadiobutton(frame, value = 'SW', text = _(""), variable = self.var_basepoint, command = self.apply_basepoint)
		radio.pack(side=LEFT, anchor=W)
		radio = UpdatedRadiobutton(frame, value = 'S', text = _(""), variable = self.var_basepoint, command = self.apply_basepoint)
		radio.pack(side=LEFT, anchor=W)
		radio = UpdatedRadiobutton(frame, value = 'SE', text = _(""), variable = self.var_basepoint, command = self.apply_basepoint)
		radio.pack(side=LEFT, anchor=W)
		
		
		#---------------------------------------------------------
		# Button frame 
		
		button_frame = TFrame(top, style='FlatFrame', borderwidth=5)
		button_frame.pack(side = BOTTOM, fill = BOTH)

		self.update_buttons = []
		self.button = UpdatedButton(top, text = _("Apply"),
								command = self.apply_move)
		self.button.pack(in_ = button_frame, side = BOTTOM, expand = 1, fill = X, pady=3)

		self.button_copy = UpdatedButton(top, text = _("Apply to Copy"),
								command = self.apply_to_copy)
		self.button_copy.pack(in_ = button_frame, side = BOTTOM, expand = 1, fill = X)
		
		self.ReSubscribe()
		self.init_from_doc()


###############################################################################

	def ReSubscribe(self):
		self.document.Subscribe(SELECTION, self.init_from_doc)
		self.document.Subscribe(EDITED, self.Update)
		config.preferences.Subscribe(CHANGED, self.update_pref)
		
	def init_from_doc(self, *arg):
		if self.is_selection():
			self.entry_width.set_state(NORMAL)
			self.entry_height.set_state(NORMAL)
			self.position_check['state']=NORMAL
			self.button['state']=NORMAL
			self.button_copy['state']=NORMAL
		else:
			self.entry_width.set_state(DISABLED)
			self.entry_height.set_state(DISABLED)
			self.position_check['state']=DISABLED
			self.button['state']=DISABLED
			self.button_copy['state']=DISABLED
##			self.var_width.set(0)
##			self.var_height.set(0)
			
		self.update_pref()

	def apply_basepoint(self):
		self.Update()

	def position(self):
		if self.var_position.get()=='Аbsolute' and self.var_basepoint.get()=='USER':
			self.var_basepoint.set('C')
		self.Update()

	def apply_move(self, *arg):
		if self.button["state"]==DISABLED:
			return
		try:
				x=self.var_width.get()
				y=self.var_height.get()
		except:
				return
		br=self.document.selection.coord_rect
		x, y = self.coordinates(self.var_position.get(), self.var_basepoint.get())
		var_x, var_y = self.var_width.get(), self.var_height.get()

##		if self.var_position.get()=='Relative':
##			if x!=None or y!=None:
##				if round(x,3)!=var_x or round(y,3)!=var_y:
##					self.var_basepoint.set('USER')

		if self.var_position.get()=='Relative':
			x,y = var_x, var_y
		else:
			x,y = var_x-x, var_y-y

		self.document.MoveSelected(x, y)


	def apply_to_copy(self):
		if self.button["state"]==DISABLED:
			return
		self.document.ApplyToDuplicate()
		self.apply_move()


	def coordinates(self, position, anchor ='C'):
		br=self.document.selection.coord_rect
		hor_sel=br.right - br.left
		ver_sel=br.top - br.bottom
		
		if position == 'Relative':
			left, bottom = -hor_sel/2, -ver_sel/2
		else:
			left, bottom = br.left, br.bottom
		# NW -- N -- NE
		# |     |     |
		# W  -- C --  E
		# |     |     |
		# SW -- S -- SE
		if anchor == 'NW':
			cnt_x=left
			cnt_y=ver_sel+bottom
		elif anchor == 'N':
			cnt_x=hor_sel/2+left
			cnt_y=ver_sel+bottom
		elif anchor == 'NE':
			cnt_x=hor_sel+left
			cnt_y=ver_sel+bottom
		elif anchor == 'W':
			cnt_x=left
			cnt_y=ver_sel/2+bottom
		elif anchor == 'E':
			cnt_x=hor_sel+left
			cnt_y=ver_sel/2+bottom
		elif anchor == 'SW':
			cnt_x=left
			cnt_y=bottom
		elif anchor == 'S':
			cnt_x=hor_sel/2+left
			cnt_y=bottom
		elif anchor == 'SE':
			cnt_x=hor_sel+left
			cnt_y=bottom
		elif anchor == 'C':
			cnt_x=hor_sel/2+left
			cnt_y=ver_sel/2+bottom
		else:
			cnt_x=None
			cnt_y=None
		
		if position == 'Relative' and cnt_x!=None:
			return cnt_x*2, cnt_y*2
		else:
			return cnt_x, cnt_y

	def update_pref(self, *arg):
		self.labelwunit['text']=config.preferences.default_unit
		self.labelhunit['text']=config.preferences.default_unit
		self.var_width.unit=config.preferences.default_unit
		self.var_height.unit=config.preferences.default_unit
		self.entry_width.step=config.preferences.default_unit_jump
		self.entry_height.step=config.preferences.default_unit_jump
		self.Update()

	def Update(self, *arg):
		if len(self.document.selection.GetInfo()):
			self.update_value()

	def is_selection(self):
		return (len(self.document.selection) > 0)

	def update_value(self):
		x, y = self.coordinates(self.var_position.get(), self.var_basepoint.get())
		if x == None:
			x=self.var_width.get()
		if y == None:
			y=self.var_height.get()
		
		self.var_width.set(x)
		self.var_height.set(y)


instance=MovePanel()
app.transform_plugins.append(instance)
