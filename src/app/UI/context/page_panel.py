# -*- coding: utf-8 -*-

# Copyright (C) 2008 by Igor E. Novikov
#
# This library is covered by GNU Library General Public License.
# For more info see COPYRIGHTS file in sK1 root directory.

from sk1sdk.libttk import TCombobox, TLabel,TCheckbutton
from app.UI.ttk_ext import TSpinbox
from app.conf.const import CHANGED
from sk1sdk.libtk.Tkinter import LEFT, RIGHT, DoubleVar, StringVar, NORMAL, DISABLED
from sk1sdk.libttk import tooltips
from subpanel import CtxSubPanel
from app import  _, config
from math import floor, ceil
from app.Graphics.papersize import Papersize, PapersizesList
from app.UI.lengthvar import LengthVar
from app.Graphics.pagelayout import PageLayout

USER_SPECIFIC = _('<Custom Size>')

class PagePanel(CtxSubPanel):
	
	name='PagePanel'
	
	def __init__(self, parent):
		CtxSubPanel.__init__(self, parent)		
		
		root=self.mw.root
		self.var_format_name = StringVar(root)
		self.var_format_name.set(config.preferences.default_paper_format)
		self.page_orientation=config.preferences.default_page_orientation
		
		label = TLabel(self.panel, text=_("Page:"))
		label.pack(side = LEFT, padx=5)
		self.page_formats = TCombobox(self.panel, state='readonly', postcommand = self.set_format, 
									 values=self.make_formats(), width=17, style='ComboNormal',
									 textvariable=self.var_format_name)
		tooltips.AddDescription(self.page_formats, _("Page formats"))
		self.page_formats.pack(side = LEFT, padx=5)
		
		
		var_width_number = DoubleVar(root)
		var_height_number = DoubleVar(root)
		var_width_unit = StringVar(root)
		var_height_unit = StringVar(root)
		unit = config.preferences.default_unit
		self.var_width = LengthVar(10, unit, var_width_number, var_width_unit)
		self.var_height = LengthVar(10, unit,var_height_number,var_height_unit)
		jump=config.preferences.default_unit_jump
		
		label = TLabel(self.panel, text=_("H:"))
		label.pack(side = LEFT)
		self.widthentry = TSpinbox(self.panel, textvariable = var_width_number, command = self.applyResize,
								vartype=1, min = 5, max = 50000, step = jump, width = 7)
		tooltips.AddDescription(self.widthentry, _("Width of paper"))
		self.widthentry.pack(side = LEFT, padx=5)
		
		label = TLabel(self.panel, text=_("V:"))
		label.pack(side = LEFT)		
		self.heightentry = TSpinbox(self.panel, textvariable =var_height_number, command = self.applyResize,
		 						vartype=1, min = 5, max = 50000, step = jump, width = 7)
		tooltips.AddDescription(self.heightentry, _("Height of paper"))
		self.heightentry.pack(side = LEFT, padx=5)
		
		self.portrait_val= StringVar(root)
		self.landscape_val = StringVar(root)
		
		self.portrait=TCheckbutton(self.panel, image='context_portrait', variable =self.portrait_val, 
								   command = self.set_portrait, style='ToolBarCheckButton')
		tooltips.AddDescription(self.portrait, _("page layout to Portrait"))
		self.portrait.pack(side = LEFT)
		self.landscape=TCheckbutton(self.panel, image='context_landscape', variable =self.landscape_val, 
									command = self.set_landscape, style='ToolBarCheckButton')	
		tooltips.AddDescription(self.landscape, _("page layout to Landscape"))
		self.landscape.pack(side = LEFT)
		config.preferences.Subscribe(CHANGED, self.update_pref)

		
	def init_from_doc(self):
		self.page_orientation=self.doc.Layout().Orientation()
		
		formatname=self.doc.Layout().FormatName()
		if formatname=='':
			formatname=USER_SPECIFIC
			width, height = self.doc.PageSize()
			if width <= height:
				self.page_orientation=0
			else:
				self.page_orientation=1
			self.update_size(width, height)

		self.var_format_name.set(formatname)
		self.update()
	
	def ReSubscribe(self):
		self.init_from_doc()
	
	def make_formats(self):
		formats=()
		for format in PapersizesList:
			formats+=(format[0],)
		formats+=(USER_SPECIFIC,)
		return formats
	
	def set_portrait(self):
		self.page_orientation=0
		width =min(self.var_width.get(),self.var_height.get())
		height=max(self.var_width.get(),self.var_height.get())
		self.update_size(width, height)
		self.set_size()
		
	def set_landscape(self):
		self.page_orientation=1
		width =max(self.var_width.get(),self.var_height.get())
		height=min(self.var_width.get(),self.var_height.get())
		self.update_size(width, height)
		self.set_size()
			
	def set_size(self):
		self.var_width.UpdateNumber()
		self.var_height.UpdateNumber()
		self.update()
		self.apply_settings()
				
	def set_format(self):		
		self.set_size()

	def update_pref(self, *arg):
		self.var_width.unit=config.preferences.default_unit
		self.var_height.unit=config.preferences.default_unit
		width, height = self.doc.PageSize()
		self.update_size(width, height)

	def update(self):		
		self.set_entry_sensitivity()
		self.update_size_from_name(self.var_format_name.get())
		if self.page_orientation:
			self.portrait_val.set('')
			self.landscape_val.set('1')
		else:
			self.portrait_val.set('1')
			self.landscape_val.set('')
		
	def set_entry_sensitivity(self):
		formatname = self.var_format_name.get()
		if formatname != USER_SPECIFIC:
			self.widthentry.set_state(DISABLED)
			self.heightentry.set_state(DISABLED)
		else:
			self.widthentry.set_state(NORMAL)
			self.heightentry.set_state(NORMAL)
			
	def update_size(self, width, height):
		self.var_width.set(width)
		self.var_height.set(height)
			
	def update_size_from_name(self, formatname):
		if not formatname == USER_SPECIFIC:
			width, height = Papersize[formatname]
			if self.page_orientation:
				width, height = height, width
			self.update_size(width, height)

	def applyResize (self, event):
		try:
			width=self.var_width.get()
			height=self.var_height.get()
			if width <= height:
				self.set_portrait()
			else:
				self.set_landscape()
		except:
			return
		
	def apply_settings(self):
		formatname = self.var_format_name.get()
		if formatname == USER_SPECIFIC:
			layout = PageLayout(width = self.var_width.get(),
								height = self.var_height.get(),
								orientation = 0)
		else:
			layout = PageLayout(formatname,
								orientation = self.page_orientation)
		self.mw.canvas.bitmap_buffer=None
		self.doc.SetLayout(layout)