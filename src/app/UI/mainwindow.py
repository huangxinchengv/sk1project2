# -*- coding: utf-8 -*-

# Copyright (C) 2003-2006 by Igor E. Novikov
# Copyright (C) 1997, 1998, 1999, 2000, 2001, 2002, 2003 by Bernhard Herzog
#
# This library is covered by GNU Library General Public License.
# For more info see COPYRIGHTS file in sK1 root directory.

import os, sys, string
from types import TupleType, ListType

from app.utils import os_utils
from app.events.warn import warn, warn_tb, INTERNAL, USER
from app import _, config, sKVersion
from app.plugins import plugins
from app.io import load
from app.conf import const
from app.utils import locale_utils
from app import Publisher, Point, EmptyFillStyle, EmptyLineStyle, dialogman, \
		EmptyPattern, Document, GuideLine, PostScriptDevice, SketchError, PolyBezier, CreatePath, Polar
import app
from app.Graphics import image, eps
import app.Scripting
from app.Graphics.color import rgb_to_tk
from app.managers.docmanager import DocumentManager 

from app.conf.const import DOCUMENT, CLIPBOARD, CLOSED, COLOR1, COLOR2
from app.conf.const import STATE, VIEW, MODE, CHANGED, SELECTION, POSITION, UNDO, EDITED, CURRENTINFO

from Tkinter import TclVersion, TkVersion, Frame, Scrollbar, Label, SW, StringVar
from Tkinter import X, BOTTOM, BOTH, TOP, HORIZONTAL, LEFT, Y, RIGHT
from Ttk import  TFrame, TScrollbar, TLabel, TButton
from widgets.doctabs import TabsPanel
from widgets.pager import Pager
import Tkinter
from tkext import AppendMenu, UpdatedLabel, UpdatedButton, CommandButton, ToolbarButton, \
				CommandCheckbutton, MakeCommand, MultiButton, \
			UpdatedRadiobutton, UpdatedCheckbutton, ToolsButton, ToolsCheckbutton, ToolbarCheckbutton, \
			UpdatedTButton
import tkext
from context import ctxPanel

from command import CommandClass, Keymap, Commands
from math import floor, ceil

from canvas import SketchCanvas
from ExportR import export_raster_more_interactive
import tkruler
from poslabel import PositionLabel
import palette, tooltips

import math, pathutils

import skpixmaps
pixmaps = skpixmaps.PixmapTk

from app import skapp
from dialogs.aboutdlg import aboutDialog
from pluginpanels.plugincontainer import PluginContainer


EXPORT_MODE=2
SAVE_AS_MODE=1
SAVE_MODE=0

command_list = []

def AddCmd(name, menu_name, method_name = None, **kw):
	kw['menu_name'] = menu_name
	if not method_name:
		method_name = name
	cmd = apply(CommandClass, (name, method_name), kw)
	command_list.append(cmd)

def AddDocCmd(name, menu_name, method_name = None, **kw):
	kw['menu_name'] = menu_name
	if not method_name:
		method_name = name
	method_name = ('document', method_name)
	for key in CommandClass.callable_attributes:
		if kw.has_key(key):
			value = kw[key]
			if type(value) == type(""):
				kw[key] = ('document', value)
	if not kw.has_key('subscribe_to'):
		kw['subscribe_to'] = SELECTION
	if not kw.has_key('sensitive_cb'):
		kw['sensitive_cb'] = ('document', 'HasSelection')
	cmd = apply(CommandClass, (name, method_name), kw)
	command_list.append(cmd)


class sK1MainWindow(Publisher):

	tk_basename = 'sk1'
	tk_class_name = 'sK1'

	def __init__(self, application, filename, run_script = None):    
		self.application = application
		self.counter=0
		self.root = application.root 
		self.filename = filename
		self.myWidth, self.myHeight = self.root.maxsize()       
		self.run_script = run_script
		self.canvas = None
		self.document = None
		self.commands = None
		self.tabspanel=None
		self.docmanager=DocumentManager(self)
		self.create_commands()
		self.build_window()
		self.build_menu()
		self.build_toolbar()
		self.build_tools()
		self.build_status_bar()
		self.__init_dlgs()
		self.document.Subscribe(SELECTION, self.refresh_buffer)

	def Run(self):
		if self.filename:
			if os.path.isdir(self.filename):
				filename = ''
				directory = self.filename
			else:
				filename = self.filename
				directory = ''
			self.LoadFromFile(filename, directory = directory)
			self.filename = ''
		if self.run_script:
			from app.Scripting.script import Context
			dict = {'context': Context()}
			try:
				execfile(self.run_script, dict)
			except:
				warn_tb(USER, _("Error running script `%s'"), self.run_script)

		self.application.Mainloop()

################### Window build ###############################
	def build_window(self):
		root = self.application.root
		
		p_frame = TFrame(root, style='FlatFrame', borderwidth=0)
		p_frame.pack(side = 'right', fill = Y)
		
		palette_frame = TFrame(p_frame, style='FlatFrame', borderwidth=2)
		palette_frame.pack(side = 'right', fill = Y)
		
		self.pc=PluginContainer(p_frame,self,style='RoundedFrame')
#		self.pc.pack(side = 'right', fill = Y)
		
		b = TLabel(root, style='VLine2')
		b.pack(side = 'right', fill = Y)

		# the menu
		self.mbar = TFrame(root, name = 'menubar', style='MenuBarFrame', borderwidth=2)
		self.mbar.pack(fill=X)

		# the toolbar
		self.tbar = TFrame(root, name = 'toolbar', style='ToolBarFrame', borderwidth=2)
		self.tbar.pack(fill=X)

		# the context panel
		self.ctxpanel=ctxPanel.ContexPanel(root, self)
		self.ctxpanel.panel.pack(fill=X)


		# the status bar
		self.status_bar = TFrame(root, name = 'statusbar', style='FlatFrame' )
		self.status_bar.pack(side = BOTTOM, fill=X)
		
		# the tools bar
		self.tframe = TFrame(root, name = 'tools_frame', style='FlatFrame', borderwidth=2)
		self.tframe.pack(side = LEFT, fill=Y)
		
		####################################
		# Drawing area creating 
		####################################
		base_frame = TFrame(root, name = 'drawing_area_frame', style='FlatFrame', borderwidth=0)
		base_frame.pack(side = LEFT, fill = BOTH, expand = 1)
		
		self.tabspanel = TabsPanel(base_frame, self)		
		self.tabspanel.pack(side = TOP, fill = X)
		self.docmanager.Activate(self.tabspanel)

		label=TLabel(base_frame,style='DrawingAreaBottom', image='space_5')
		label.pack(side = BOTTOM, fill = X)
				
		label=TLabel(base_frame,style='DrawingAreaLeft', image='space_5')
		label.pack(side = LEFT, fill = Y, expand = 1)
		
		label=TLabel(base_frame,style='DrawingAreaRight', image='space_5')
		label.pack(side = RIGHT, fill = Y, expand = 1)

		####################################
		frame = TFrame(base_frame, name = 'canvas_frame', style='FlatFrame', borderwidth=0)
		frame.pack(side = LEFT, fill = BOTH, expand = 1)

		vbar = TScrollbar(frame)
		vbar.grid(in_ = frame, column = 3, row = 1, sticky = 'ns')
		vbar.bind('<Button-4>', self.ScrollUpCanvas)
		vbar.bind('<Button-5>', self.ScrollDownCanvas)
		
		############Pager###################
		pframe = TFrame(frame, style='FlatFrame', borderwidth=0)
		pframe.grid(in_ = frame, column = 2, row = 2, sticky = 'ew')
		
		lab=Pager(pframe,self)
		lab.pack(side = LEFT, fill=Y)
		####################################
		hbar = TScrollbar(pframe, orient = HORIZONTAL)
#		hbar.grid(in_ = frame, column = 2, row = 2, sticky = 'ew')
		hbar.pack(side = RIGHT, fill = X, expand = 1)
		hbar.bind('<Button-4>', self.ScrollLeftCanvas)
		hbar.bind('<Button-5>', self.ScrollRightCanvas)
		####################################
		#tempframe = Frame(root, name = 'temp_frame')
		
		hrule = tkruler.Ruler(frame, orient = tkruler.HORIZONTAL, 
							  bg=config.preferences.ruler_color, bd=0, highlightthickness=0, relief='flat') 
		
		hrule.grid(in_ = frame, column = 2, row = 0, sticky = 'nsew', columnspan = 2)
		hrule.bind('<Double-Button-1>', self.RulerDoublePressH)
		
		####################################

		vrule = tkruler.Ruler(frame, orient = tkruler.VERTICAL,
							  bg=config.preferences.ruler_color, bd=0, highlightthickness=0, relief='flat')
		
		vrule.grid(in_ = frame, column = 1, row = 1, sticky = 'nsew', rowspan = 2)
		vrule.bind('<Double-Button-1>', self.RulerDoublePressV)
		
		#ruler corner 
		b = TLabel(frame, style="FlatLabel", image="rulers_corner")
		#b = TButton(frame, command=self.GuideDialog, style="TCornerButton", image="icon_dlg_guides", takefocus=0)
		#b = TLabel(frame, style='FlatLabel')
		b.bind('<Button-1>', self.GuideDialog)
		tooltips.AddDescription(b, self.commands.CreateGuideDialog.menu_name)
		b.grid(column = 1, row = 0, sticky = 'news')
		#ruler corner  //
		
		resolution = config.preferences.screen_resolution
		self.canvas = SketchCanvas(root, toplevel = root, background = 'white', name = 'canvas',
				resolution = resolution, main_window = self, document = self.document)
		self.canvas.grid(in_ = frame, column = 2, row = 1, sticky = 'news')
		self.canvas.focus()
		self.canvas.SetScrollbars(hbar, vbar)
		self.canvas.SetRulers(hrule, vrule)
		
		vrule.SetCanvas(self.canvas)
		hrule.SetCanvas(self.canvas)

		frame.columnconfigure(0, weight = 0)
		frame.columnconfigure(1, weight = 0)
		frame.columnconfigure(2, weight = 1)
		frame.columnconfigure(3, weight = 0)
		frame.rowconfigure(0, weight = 0)
		frame.rowconfigure(1, weight = 1)
		frame.rowconfigure(2, weight = 0)
		hbar['command'] = self.canvas._w + ' xview'
		vbar['command'] = self.canvas._w + ' yview'

		# the palette

		pal = palette.GetStandardPalette()
		
		palette_trough = TFrame(palette_frame, style='FlatFrame', borderwidth=0)
		palette_container = TFrame(palette_trough, style='FlatFrame', borderwidth=0)
		
		self.palette = palette.PaletteWidget(palette_container)
		
		ScrollXUnits = self.palette.ScrollXUnits
		ScrollXPages = self.palette.ScrollXPages
		CanScrollLeft = self.palette.CanScrollLeft
		CanScrollRight = self.palette.CanScrollRight
		
		but1= UpdatedTButton(palette_frame, class_='Repeater', style='Pal2TopButton', image='pal_dbl_arrow_up',
					command = ScrollXPages, args =  -1, sensitivecb = CanScrollLeft)
		but1.pack(side = TOP)
		but2= UpdatedTButton(palette_frame, class_='Repeater', style='PalTopButton', image='pal_arrow_up',
					command = ScrollXUnits, args =  -1, sensitivecb = CanScrollLeft)
		but2.pack(side = TOP)
		
		palette_trough.pack(side = TOP, fill = Y, expand = 1)
		
		b = TLabel(palette_trough, style='PalLBorder')
		b.pack(side = LEFT, fill = Y)
		
		palette_container.pack(side = LEFT, fill = Y, expand = 1)
				
		but= UpdatedTButton(palette_container, style='PalNoColorButton', image='pal_no_color',
					command = self.no_pattern, args = 'fill', borderwidth=0)
		but.pack(side = TOP)
		but.bind('<ButtonPress-3>', self.no_pattern, 'line')
		tooltips.AddDescription(but, "No color")
		
		self.palette.pack(side = LEFT, fill = Y, expand = 1)
		
		b = TLabel(palette_trough, style='PalRBorder')
		b.pack(side = 'right', fill = Y)
		
		but3= UpdatedTButton(palette_frame, class_='Repeater', style='PalBottomButton', image='pal_arrow_down',
					command = ScrollXUnits, args =  +1, sensitivecb = CanScrollRight)
		but3.pack(side = TOP)
		but4= UpdatedTButton(palette_frame, class_='Repeater', style='Pal2BottomButton', image='pal_dbl_arrow_down',
					command = ScrollXPages, args =  +1, sensitivecb = CanScrollRight)
		but4.pack(side = TOP)

		self.palette.Subscribe(COLOR1, self.canvas.FillSolid)
		self.palette.Subscribe(COLOR2, self.canvas.LineColor)
		root.protocol('WM_DELETE_WINDOW', tkext.MakeMethodCommand(self.Exit))
		
		#Binding for mouse wheel
		self.palette.bind('<Button-4>', self.ScrollUpPallette)
		self.palette.bind('<Button-5>', self.ScrollDownPallette)
		self.canvas.bind('<Button-4>', self.ScrollUpCanvas)
		self.canvas.bind('<Button-5>', self.ScrollDownCanvas)
		self.canvas.bind('<Control-Button-4>', self.ScrollLeftCanvas)
		self.canvas.bind('<Control-Button-5>', self.ScrollRightCanvas)
		self.canvas.bind('<Shift-Button-4>', self.CanvasZoomingOut)
		self.canvas.bind('<Shift-Button-5>', self.CanvasZoomingIn)
		
	def build_toolbar(self):
		tbar = self.tbar
		canvas = self.canvas
		commands = self.commands
		
		label = TLabel(tbar, image = "toolbar_left")
		label.pack(side = LEFT)

		b = ToolbarButton(tbar, commands.NewDocument, image = "toolbar_new")
		tooltips.AddDescription(b, commands.NewDocument.menu_name)
		b.pack(side = LEFT)
		b = ToolbarButton(tbar, commands.LoadFromFile, image="toolbar_open")
		tooltips.AddDescription(b, commands.LoadFromFile.menu_name)
		b.pack(side = LEFT)
		
		label = TLabel(tbar, image = "toolbar_sep")
		label.pack(side = LEFT)
		
		b = ToolbarButton(tbar, commands.SaveToFile, image="toolbar_save")
		tooltips.AddDescription(b, commands.SaveToFile.menu_name)
		b.pack(side = LEFT)
		b = ToolbarButton(tbar, commands.SaveToFileAs, image="toolbar_saveas")
		tooltips.AddDescription(b, commands.SaveToFileAs.menu_name)
		b.pack(side = LEFT)

		
		label = TLabel(tbar, image = "toolbar_sep")
		label.pack(side = LEFT)
		
		b = ToolbarButton(tbar, commands.KPrinting, image="toolbar_print")
		tooltips.AddDescription(b, commands.KPrinting.menu_name)
		b.pack(side = LEFT)
		
		
		b = ToolbarButton(tbar, commands.PrintToPDF, image="print_tofile")
		tooltips.AddDescription(b, commands.PrintToPDF.menu_name)
		b.pack(side = LEFT)

		label = TLabel(tbar, image = "toolbar_sep")
		label.pack(side = LEFT)
		
		b = ToolbarButton(tbar, commands.CloseDoc, image="toolbar_fileclose")
		tooltips.AddDescription(b, commands.CloseDoc.menu_name)
		b.pack(side = LEFT)
		
		label = TLabel(tbar, image = "toolbar_sep")
		label.pack(side = LEFT)

		b = ToolbarButton(tbar, commands.Undo, image="toolbar_undo")
		tooltips.AddDescription(b, commands.Undo.menu_name)
		b.pack(side = LEFT)
		b = ToolbarButton(tbar, commands.Redo, image="toolbar_redo")
		tooltips.AddDescription(b, commands.Redo.menu_name)
		b.pack(side = LEFT)
		b = ToolbarButton(tbar, commands.RemoveSelected, image="toolbar_delete")
		tooltips.AddDescription(b, commands.RemoveSelected.menu_name)
		b.pack(side = LEFT)
		b = ToolbarButton(tbar, commands.CutSelected, image="toolbar_cut")
		tooltips.AddDescription(b, commands.CutSelected.menu_name)
		b.pack(side = LEFT)
		b = ToolbarButton(tbar, commands.CopySelected, image="toolbar_copy")
		tooltips.AddDescription(b, commands.CopySelected.menu_name)
		b.pack(side = LEFT)
		b = ToolbarButton(tbar, commands.PasteClipboard, image="toolbar_paste")
		tooltips.AddDescription(b, commands.PasteClipboard.menu_name)
		b.pack(side = LEFT)

		label = TLabel(tbar, image = "toolbar_sep")
		label.pack(side = LEFT)

		b = ToolbarButton(tbar, commands.InsertFile, image = "toolbar_iVector")
		tooltips.AddDescription(b, commands.InsertFile.menu_name)
		b.pack(side = LEFT)
		b = ToolbarButton(tbar, commands.CreateImage, image = "toolbar_iRaster")
		tooltips.AddDescription(b, commands.CreateImage.menu_name)
		b.pack(side = LEFT)

		label = TLabel(tbar, image = "toolbar_sep")
		label.pack(side = LEFT)

		b = ToolbarButton(tbar, commands.ExportAs, image = "toolbar_eVector")
		tooltips.AddDescription(b, commands.ExportAs.menu_name)
		b.pack(side = LEFT)
		b = ToolbarButton(tbar, commands.ExportRaster, image = "toolbar_eRaster")
		tooltips.AddDescription(b, commands.ExportRaster.menu_name)
		b.pack(side = LEFT)

		label = TLabel(tbar, image = "toolbar_sep")
		label.pack(side = LEFT)

		b = ToolbarButton(tbar, canvas.commands.FitPageToWindow, image = "toolbar_FitToPage")
		tooltips.AddDescription(b, canvas.commands.FitPageToWindow.menu_name)
		b.pack(side = LEFT)

		b = ToolbarButton(tbar, commands.FitToNat, image = "toolbar_FitToNative")
		tooltips.AddDescription(b, commands.FitToNat.menu_name)
		b.pack(side = LEFT)

		b = ToolbarButton(tbar, canvas.commands.FitSelectedToWindow, image = "toolbar_FitToSelected")
		tooltips.AddDescription(b, canvas.commands.FitSelectedToWindow.menu_name)
		b.pack(side = LEFT)

		b = ToolbarButton(tbar, canvas.commands.ZoomIn, image="toolbar_zoom+")
		tooltips.AddDescription(b, canvas.commands.ZoomIn.menu_name)
		b.pack(side = LEFT)

		b = ToolbarButton(tbar, canvas.commands.ZoomOut, image="toolbar_zoom-")
		tooltips.AddDescription(b, canvas.commands.ZoomOut.menu_name)
		b.pack(side = LEFT)
		
		label = TLabel(tbar, image = "toolbar_sep")
		label.pack(side = LEFT)
		#-----------------------------------            
		# Renderers
		#-----------------------------------
		b = ToolbarCheckbutton(tbar, canvas.commands.UseXlibRenderer, image='toolbar_xlib')
		b.pack(side = LEFT)
		tooltips.AddDescription(b, canvas.commands.UseXlibRenderer.menu_name)
		
		label = TLabel(tbar, image = "sb_sep")
		label.pack(side = LEFT)
		
		b = ToolbarCheckbutton(tbar, canvas.commands.UseCairoRenderer, image='toolbar_cairo')
		b.pack(side = LEFT)
		tooltips.AddDescription(b, canvas.commands.UseCairoRenderer.menu_name)
		
		label = TLabel(tbar, image = "sb_sep")
		label.pack(side = LEFT)
		
		#b = ToolbarCheckbuttoncommands, canvas.commands.AllowAlphaChannel, image='toolbar_alpha')
		#b.pack(side = LEFT)
		#tooltips.AddDescription(b, canvas.commands.AllowAlphaChannel.menu_name)

		
		b = ToolbarCheckbutton(tbar, canvas.commands.ToggleOutlineMode, image='toolbar_contour')
		b.pack(side = LEFT)
		tooltips.AddDescription(b, canvas.commands.ToggleOutlineMode.menu_name)
		
		label = TLabel(tbar, image = "toolbar_sep")
		label.pack(side = LEFT)
		
		b = ToolbarCheckbutton(tbar, canvas.commands.AllowCMS, image='enable_cms')
		b.pack(side = LEFT)
		tooltips.AddDescription(b, canvas.commands.AllowCMS.menu_name)
		
		label = TLabel(tbar, image = "sb_sep")
		label.pack(side = LEFT)
		
		b = ToolbarButton(tbar, commands.PCshowHide, image="show_side_panel")
		tooltips.AddDescription(b, commands.PCshowHide.menu_name)
		b.pack(side = LEFT)
		
	def build_tools(self):
		tframe = self.tframe
		canvas = self.canvas
		
		fr=TFrame(tframe, style='FlatFrame', borderwidth=12)
		fr.pack(side = TOP, fill = X)
		label = TLabel(fr, style='FlatLabel')
		label.pack(side = TOP, fill = X)
		
		label = TLabel(tframe, style='HLine')
		label.pack(side = TOP, fill = X)

		#Selection Mode Button
		b = ToolsCheckbutton(tframe, canvas.commands.SelectionMode, image='tools_pointer')
		b.pack(side = TOP)
		tooltips.AddDescription(b, canvas.commands.SelectionMode.menu_name)
		#CurveEdit Mode Button
		b = ToolsCheckbutton(tframe, canvas.commands.EditMode, image='tools_shaper')
		b.pack(side = TOP)
		tooltips.AddDescription(b, canvas.commands.EditMode.menu_name)
		#Zoom Mode Button
		b = ToolsCheckbutton(tframe, canvas.commands.ZoomMode, image='tools_zoom')
		b.pack(side = TOP)
		tooltips.AddDescription(b, canvas.commands.ZoomMode.menu_name)

		#PolyLine Mode Button
		b = ToolsCheckbutton(tframe, canvas.commands.CreatePolyLine, image='tools_pencil_line')
		b.pack(side = TOP)
		tooltips.AddDescription(b, canvas.commands.CreatePolyLine.menu_name)
		#PolyBezier Mode Button
		b = ToolsCheckbutton(tframe, canvas.commands.CreatePolyBezier, image='tools_pencil_curve')
		b.pack(side = TOP)
		tooltips.AddDescription(b, canvas.commands.CreatePolyBezier.menu_name)

		#Ellipse Mode Button
		b = ToolsCheckbutton(tframe, canvas.commands.CreateEllipse, image='tools_ellipse')
		b.pack(side = TOP)
		tooltips.AddDescription(b, canvas.commands.CreateEllipse.menu_name)
		
		#Rectangle Mode Button
		b = ToolsCheckbutton(tframe, canvas.commands.CreateRectangle, image='tools_rectangle')
		b.pack(side = TOP)
		tooltips.AddDescription(b, canvas.commands.CreateRectangle.menu_name)

		#SimpleText Mode Button
		b = ToolsCheckbutton(tframe, canvas.commands.CreateSimpleText, image='tools_text')
		b.pack(side = TOP)
		tooltips.AddDescription(b, canvas.commands.CreateSimpleText.menu_name)

		b = TLabel(tframe, style='HLine')
		b.pack(side = TOP, fill = X)

		#Outline Button
		b = ToolsButton(tframe, self.commands.CreateLineStyleDialog, image='tools_color_line')
		b.pack(side = TOP)
		tooltips.AddDescription(b, self.commands.CreateLineStyleDialog.menu_name)

		#Fill Button
		b = ToolsButton(tframe, self.commands.CreateFillStyleDialog, image='tools_color_fill')
		b.pack(side = TOP)
		tooltips.AddDescription(b, self.commands.CreateFillStyleDialog.menu_name)
		#Spacer
		b = TLabel(tframe, style='HLine')
		b.pack(side = TOP, fill = X)

		b = TLabel(tframe, style='HLine')
		b.pack(side = BOTTOM, fill = X)
		
		b = ToolbarButton(tframe, self.commands.MoveSelectedToBottom, image='tools_lower')
		b.pack(side =  BOTTOM, fill= X)
		b = ToolbarButton(tframe, self.commands.MoveSelectionDown, image='tools_backward')
		b.pack(side = BOTTOM, fill= X)
		b = ToolbarButton(tframe, self.commands.MoveSelectionUp, image='tools_forward')
		b.pack(side = BOTTOM, fill= X)
		b = ToolbarButton(tframe, self.commands.MoveSelectedToTop, image='tools_raise')
		b.pack(side =  BOTTOM, fill= X)				

	def build_status_bar(self):
		status_bar = self.status_bar
		canvas = self.canvas

		#Container
		sb1 = TFrame(status_bar, style="FlatFrame")
		sb1.pack(side = LEFT, fill = Y)
		#Position Info
		stat_pos = PositionLabel(sb1, name = 'position', text = '', anchor = 'center', width=20, updatecb = canvas.GetCurrentPos)
		stat_pos.pack(side = LEFT, fill = X)
		stat_pos.Update()
		canvas.Subscribe(POSITION, stat_pos.Update)


		sb_frame2 = TFrame(status_bar, style="RoundedSBFrame", borderwidth=2)
		sb_frame2.pack(side = LEFT, fill = BOTH)

		#OnGrid
		b = ToolbarCheckbutton(sb_frame2, canvas.commands.ToggleSnapToGrid, image='snap_to_grid')
		b.pack(side = LEFT)
		tooltips.AddDescription(b, canvas.commands.ToggleSnapToGrid.menu_name)
		
		label = TLabel(sb_frame2, image = "sb_sep")
		label.pack(side = LEFT)
		
		#OnGuide
		b = ToolbarCheckbutton(sb_frame2, canvas.commands.ToggleSnapToGuides, image='snap_to_guide')
		b.pack(side = LEFT)
		tooltips.AddDescription(b, canvas.commands.ToggleSnapToGuides.menu_name)
		
		label = TLabel(sb_frame2, image = "sb_sep")
		label.pack(side = LEFT)
		
		#OnObject
		b = ToolbarCheckbutton(sb_frame2, canvas.commands.ToggleSnapToObjects, image='snap_to_object')
		b.pack(side = LEFT)
		tooltips.AddDescription(b, canvas.commands.ToggleSnapToObjects.menu_name)

		
		label = TLabel(sb_frame2, image = "sb_sep")
		label.pack(side = LEFT)
		
		#ForceRedraw
		b = ToolbarButton(sb_frame2, canvas.commands.ForceRedraw, image='statusbar_refresh')
		b.pack(side = LEFT)
		tooltips.AddDescription(b, canvas.commands.ForceRedraw.menu_name)


		#Zoom Info
		#l=Label(status_bar, anchor=SW, text='    Zoom:')
		#l.pack(side='left')

		#stat_zoom = UpdatedLabel(status_bar, name = 'zoom', text = '', updatecb = canvas.ZoomInfoText)
		#stat_zoom.pack(side = 'left')
		#stat_zoom.Update()
		#canvas.Subscribe(VIEW, stat_zoom.Update)

		#stat_edited = UpdatedLabel(status_bar, name = 'edited', text = '',
		#                          updatecb = self.EditedInfoText)
		#stat_edited.pack(side = 'left')
		#stat_edited.Update()
		#self.Subscribe(UNDO, stat_edited.Update)

		#Selection Color switch
		def ColorInfo():
				if len(self.document.selection) != 1 or self.document.CanUngroup():
					fill_frame["style"]='ColorWatchDisabled'
					outline_frame["style"]='ColorWatchDisabled'
					fill_frame['background']=app.uimanager.currentColorTheme.bg
					outline_frame['background']=app.uimanager.currentColorTheme.bg
					return _("")
					
				properties = self.document.CurrentProperties()
				filltxt=''
				outlinetxt=''
				try:
					fill_frame["style"]='ColorWatchNormal'
					fillcolor=rgb_to_tk(properties.fill_pattern.Color().RGB())
					fill_frame["background"]=fillcolor
					filltxt='Fill: ' + properties.fill_pattern.Color().toString()
				except:
					fill_frame["style"]='ColorWatchTransp'
					filltxt='Fill: None'
					
				try:
					outline_frame["style"]='ColorWatchNormal'
					outline_frame["background"]=rgb_to_tk(properties.line_pattern.Color().RGB())
					outlinetxt='Outline: '+ str(math.ceil(math.floor(10**4*properties.line_width/2.83465)/10)/1000) +' mm' 
				except:
					outline_frame["style"]='ColorWatchTransp'
					outlinetxt='Outline: None'
					
				return _(filltxt + "\n" + outlinetxt)

		space = Frame(status_bar, relief='flat', borderwidth=0, width=5)
		space.pack(side = RIGHT, fill=Y)
		sb3f = Frame(status_bar, relief='flat', borderwidth=1, width=20, height=15)
		sb3f.pack(side = RIGHT)
		
		fill_frame = TLabel(sb3f, style='ColorWatchDisabled', image='space_12')           
		outline_frame = TLabel(sb3f,  style='ColorWatchDisabled', image='space_12')
		
		fill_frame.grid(row=0, column=0, sticky = 'EW')
		outline_frame.grid(row=1, column=0, sticky = 'EW', pady=1)

		l=UpdatedLabel(status_bar, name='colors', text='', justify = 'right', updatecb = ColorInfo)
		l.pack(side= RIGHT)
		l.Update()
		canvas.Subscribe(POSITION, l.Update)
		canvas.Subscribe(EDITED, l.Update)
		canvas.Subscribe(SELECTION, l.Update)

		#Object Info
		stat_sel = UpdatedLabel(status_bar, name = 'selection',  justify = 'center', anchor = 'center', text = '', updatecb = canvas.CurrentInfoText)
		stat_sel.pack(side = 'left', fill = X, expand = 1)
		stat_sel.Update()
		update = stat_sel.Update
		canvas.Subscribe(SELECTION, update)
		canvas.Subscribe(CURRENTINFO, update)
		canvas.Subscribe(EDITED, update)
				
################### Document managment #########################
	def Document(self): 
		return self.document

	def NewDocument(self): 
		self.docmanager.NewDocument()
		
	def LoadFromFile(self, filename = None, directory = None):
		self.docmanager.OpenDocument(filename, directory)
		
	def SaveToFileInteractive(self, use_dialog = SAVE_MODE):
		self.docmanager.SaveDocument(self.document, use_dialog)
		self.tabspanel.updateTabNames()
		
	def SaveAllDocuments(self):
		self.tabspanel.saveAll()
		self.tabspanel.updateTabNames()
		
	def InsertFile(self, filename = None):
		self.docmanager.ImportVector(filename)
		
	def PrintToPDF(self):
		self.docmanager.PrintDocument(self.document, 1)

	def CloseCurrentDocument(self):
		self.tabspanel.closeActiveTab()
		
	def CloseAllDocuments(self):
		self.tabspanel.closeAll()

	def Exit(self):
		if not self.tabspanel.closeAll(exit=1)== tkext.Cancel:
			self.commands = None
			self.application.Exit()
			
################### Pages managment #########################
	def InsertPage(self):
		from dialogs.insertpagedlg import insertpgDialog
		insertpgDialog(self.root)
		import time
		time.sleep(.1)
		self.document.SelectNone()
		self.canvas.ForceRedraw()
		
	def NextPage(self):
		from dialogs.insertpagedlg import insertpgDialog
		if self.document.active_page < len(self.document.pages)-1:
			self.document.GoToPage(self.document.active_page+1)
		else:
			insertpgDialog(self.root)
		self.document.SelectNone()
		self.canvas.ForceRedraw()
	
	def PreviousPage(self):
		from dialogs.insertpagedlg import insertpgDialog
		if self.document.active_page > 0:
			self.document.GoToPage(self.document.active_page-1)	
		else:
			insertpgDialog(self.root, 1)
		self.document.SelectNone()			
		self.canvas.ForceRedraw()

	def DeletePage(self):
		from dialogs.deletepagedlg import deletepgDialog
		deletepgDialog(self.root)
		import time
		time.sleep(.1)
		self.document.SelectNone()
		self.canvas.ForceRedraw()
		
	def GotoPage(self):
		from dialogs.gotopagedlg import gotopgDialog
		gotopgDialog(self.root)
		import time
		time.sleep(.1)
		self.document.SelectNone()
		self.canvas.ForceRedraw()		
		
			
################### Window comands #############################	
	AddCmd('NewDocument', _("New"), image = 'menu_file_new', key_stroke = ('Ctrl+N', 'Ctrl+n', 'Ctrl+t'))
	AddCmd('OpenNewDocument', _("New Drawing Window"), image ='no_image')
	AddCmd('LoadFromFile', _("Open..."), image = 'menu_file_open',  key_stroke = ('Ctrl+O', 'Ctrl+o',))	
	AddCmd('LoadMRU0', '', 'LoadFromFile', image = 'menu_mru_1', args = 0, key_stroke = 'Alt+1', name_cb = lambda: os.path.split(config.preferences.mru_files[0])[1])
	AddCmd('LoadMRU1', '', 'LoadFromFile', image = 'menu_mru_2', args = 1, key_stroke = 'Alt+2', name_cb = lambda: os.path.split(config.preferences.mru_files[1])[1])
	AddCmd('LoadMRU2', '', 'LoadFromFile', image = 'menu_mru_3', args = 2, key_stroke = 'Alt+3', name_cb = lambda: os.path.split(config.preferences.mru_files[2])[1])
	AddCmd('LoadMRU3', '', 'LoadFromFile', image = 'menu_mru_4', args = 3, key_stroke = 'Alt+4', name_cb = lambda: os.path.split(config.preferences.mru_files[3])[1])
	AddCmd('SaveToFile', _("Save"), 'SaveToFileInteractive', image = 'menu_file_save', subscribe_to = UNDO, sensitive_cb = ('document', 'WasEdited'), key_stroke = ('Ctrl+S', 'Ctrl+s'))
	AddCmd('SaveToFileAs', _("Save As..."), 'SaveToFileInteractive', image = 'menu_file_saveas', args = 1)
	AddCmd('SaveAll', _("Save All"), 'SaveAllDocuments')
	AddCmd('ExportAs', _("Export As..."), 'SaveToFileInteractive', args = 2)		
	AddCmd('CloseDoc', _("Close"), 'CloseCurrentDocument', image = 'menu_file_close')	
	AddCmd('CloseAll', _("Close All"), 'CloseAllDocuments')
	AddCmd('InsertFile', _("Import vector..."))
	AddCmd('SetOptions', _("Options..."), image = 'menu_file_configure')
	AddCmd('Exit', _("Exit"), image = 'menu_file_exit', key_stroke = ('Alt+F4'))
	
	AddCmd('ProjectSite', _("Project web site..."))
	AddCmd('AboutBox', _("About sK1..."))
	AddCmd('PCshowHide', _("Sidebar"))
	
	
	AddCmd('InsertPage', _("Insert Page..."), 'InsertPage')
	AddCmd('DeletePage', _("Delete Page..."), 'DeletePage', subscribe_to = UNDO, sensitive_cb = ('document','CanBePageDeleting'))
	AddCmd('NextPage', _("Next Page"), 'NextPage', key_stroke = ('PgDn', 'Next', 'KP_Next'))
	AddCmd('PreviousPage', _("Previous Page"), 'PreviousPage', key_stroke = ('PgUp', 'Prior', 'KP_Prior'))
	AddCmd('GotoPage', _("Go to Page..."), 'GotoPage')
	
	AddCmd('AddHorizGuideLine', _("Add Horizontal Guide Line"), 'AddGuideLine', args = 1)
	AddCmd('AddVertGuideLine', _("Add Vertical Guide Line"), 'AddGuideLine', args = 0)
	
	AddCmd('FitToNat', _("Zoom 1:1"), 'FitToNat')
	AddCmd('CopySelected', _("Copy"), 'CutCopySelected',args= ('CopyForClipboard',), subscribe_to = SELECTION, image = 'menu_edit_copy',
			key_stroke = ('Ctrl+C', 'Ctrl+c'), sensitive_cb = ('document', 'HasSelection'))
			
	AddCmd('CopyPaste', _("Copy&Paste"), 'CopyPasteSelected', args= ('CopyForClipboard',), subscribe_to = SELECTION, key_stroke = 'F6',
			sensitive_cb = ('document', 'HasSelection'))
	
	AddCmd('CutSelected', _("Cut"), 'CutCopySelected', args= ('CutForClipboard',), subscribe_to = SELECTION, image = 'menu_edit_cut', 
			key_stroke = ('Ctrl+X', 'Ctrl+x'), sensitive_cb = ('document', 'HasSelection'))
			
	AddCmd('PasteClipboard', _("Paste"), image = 'menu_edit_paste', key_stroke = ('Ctrl+V', 'Ctrl+v'),
			subscribe_to = ('application', CLIPBOARD), sensitive_cb = ('application', 'ClipboardContainsData'))
			
	AddCmd('ExportRaster', _("Export Bitmap..."), 'ExportRaster')
	
			
	AddCmd('CreateLayerDialog', _("Layers..."), 'CreateDialog', args = ('dlg_layer', 'LayerPanel'), key_stroke = 'F5')
	AddCmd('CreateAlignDialog', _("Align to ..."), 'CreateDialog', args = ('dlg_align', 'AlignPanel'), key_stroke = ('Ctrl+A', 'Ctrl+a'))
	AddCmd('CreateGridDialog', _("Grid Setup..."), 'CreateDialog', args = ('dlg_grid', 'GridPanel'))
	AddCmd('CreateLineStyleDialog', _("Outline..."), 'CreateDialog', args = ('dlg_line', 'LinePanel'), key_stroke = 'F12')
	AddCmd('CreateFillStyleDialog', _("Fill..."), 'CreateDialog', args = ('filldlg', 'FillPanel'), key_stroke = 'F11')
	AddCmd('CreateFontDialog', _("Fonts..."), 'CreateDialog', args = ('fontdlg', 'FontPanel'), key_stroke = 'Ctrl+f')
	AddCmd('CreateStyleDialog', _("Styles..."), 'CreateDialog', args = ('styledlg', 'StylePanel'))
	AddCmd('CreateBlendDialog', _("Blend..."), 'CreateDialog', args = ('dlg_blend', 'BlendPanel'), key_stroke = ('Ctrl+B', 'Ctrl+b'))
	AddCmd('CreateLayoutDialog', _("Page Setup..."), 'CreateDialog', args = ('dlg_layout', 'LayoutPanel'))
	#AddCmd('CreateExportDialog', 'Export...', 'CreateDialog', args = ('export', 'ExportPanel'))
	AddCmd('CreateCurveDialog', _("Curve Commands..."), 'CreateDialog', args = ('dlg_curve', 'CurvePanel'))
	AddCmd('CreateGuideDialog', _("Guides Setup..."), 'CreateDialog', args = ('dlg_guide', 'GuidePanel'))
	AddCmd('KPrinting', _("Print..."), 'KPrinting', image = 'menu_file_print', key_stroke = ('Ctrl+P', 'Ctrl+p'), sensitive_cb ='HasKPrinter')
	AddCmd('PrintToPDF', _("Print to PDF..."), 'PrintToPDF', image = 'menu_file_pdf')
#	AddCmd('CreatePrintDialog', _("LPR printing..."), 'CreateDialog', args = ('printdlg', 'PrintPanel'))
	AddCmd('CreateMoveDialog', _("Move..."), 'CreateDialog', args = ('dlg_move', 'MovePanel'), key_stroke = 'Alt+F9')
	AddCmd('CreateRotateDialog', _("Rotate..."), 'CreateDialog', args = ('dlg_rotate', 'RotatePanel'))
	AddCmd('CreateSizeDialog', _("Resize..."), 'CreateDialog', args = ('dlg_size', 'SizePanel'))
	AddCmd('CreateReloadPanel', _("Reload Module..."), 'CreateDialog', args = ('reloaddlg', 'ReloadPanel'))
	AddCmd('HideDialogs', _("Hide Dialogs"))
	AddCmd('ShowDialogs', _("Show Dialogs"))
	
	AddCmd('LoadPalette', _("Load Palette..."))	
	AddCmd('InsertFile', _("Import vector..."))
	AddCmd('CreateImage', _("Import bitmap..."), subscribe_to = None)
	AddCmd('DocumentInfo', "Document Info...")	
	AddCmd('CreateStyleFromSelection', _("Name Style..."), sensitive_cb = ('document', 'CanCreateStyle'), subscribe_to = SELECTION)	
	
################### Document comands ############################	
	AddDocCmd('SelectAll', _("Select All"), sensitive_cb = 'IsSelectionMode', subscribe_to = MODE)
	AddDocCmd('SelectNextObject', _("Select Next"), key_stroke = 'Alt+Right')
	AddDocCmd('SelectPreviousObject', _("Select Previous"), key_stroke = 'Alt+Left')
	AddDocCmd('SelectFirstChild', _("Select First Child"), key_stroke = 'Alt+Down')
	AddDocCmd('SelectParent', _("Select Parent"), key_stroke = 'Alt+Up')

	AddDocCmd('MoveUp', _("Move Up"), 'HandleMoveSelected', args=(0,1), key_stroke = ('Up', 'KP_Up'))        
	AddDocCmd('MoveDown', _("Move Down"), 'HandleMoveSelected', args=(0,-1), key_stroke = ('Down', 'KP_Down'))
	AddDocCmd('MoveRight', _("Move Right"), 'HandleMoveSelected', args=(1,0), key_stroke = ('Right', 'KP_Right'))
	AddDocCmd('MoveLeft', _("Move Left"), 'HandleMoveSelected', args=(-1,0), key_stroke = ('Left', 'KP_Left'))

	AddDocCmd('RemoveSelected', _("Delete"), key_stroke = ('Del', 'Delete', 'KP_Delete'), image = 'menu_edit_delete')

	AddDocCmd('MoveSelectedToTop', _("Move to Top"), key_stroke = ('Shift+PgUp', 'Shift+Prior', 'Shift+KP_Prior'))
	AddDocCmd('MoveSelectedToBottom', _("Move to Bottom"), key_stroke = ('Shift+PgDown', 'Shift+Next', 'Shift+KP_Next'))

	AddDocCmd('MoveSelectionUp', _("Move One Up"), key_stroke = ('Ctrl+PgUp', 'Ctrl+Prior', 'Ctrl+KP_Prior'))
	AddDocCmd('MoveSelectionDown', _("Move One Down"), key_stroke = ('Ctrl+PgDown', 'Ctrl+Next', 'Ctrl+KP_Next'))

	AddDocCmd('ApplyToDuplicate', _("Duplicate0"))
	AddDocCmd('DuplicateSelected', _("Duplicate"), key_stroke = ('Ctrl+D', 'Ctrl+d'))
	AddDocCmd('GroupSelected', _("Group selected objects"), sensitive_cb = 'CanGroup', key_stroke = ('Ctrl+G', 'Ctrl+g'))
	AddDocCmd('UngroupSelected', _("Ungroup selection"), sensitive_cb = 'CanUngroup', key_stroke = ('Ctrl+U', 'Ctrl+u'))
	AddDocCmd('ConvertToCurve', _("Convert To Curve"), sensitive_cb = 'CanConvertToCurve', key_stroke = ('Ctrl+Q', 'Ctrl+q'))
	AddDocCmd('CombineBeziers', _("Combine Beziers"), sensitive_cb = 'CanCombineBeziers', key_stroke = ('Ctrl+L','Ctrl+l'))
	AddDocCmd('SplitBeziers', _("Split Beziers"), sensitive_cb = 'CanSplitBeziers', key_stroke = ('Ctrl+K', 'Ctrl+k'))

	AddDocCmd('AbutHorizontal', _("Abut Horizontal"))
	AddDocCmd('AbutVertical', _("Abut Vertical"))

	AddDocCmd('FlipHorizontal', _("Flip Horizontal"), 'FlipSelected', args = (1, 0))
	AddDocCmd('FlipVertical', _("Flip Vertical"), 'FlipSelected', args = (0, 1))

	AddDocCmd('CancelBlend', _("Cancel Blend"), sensitive_cb = 'CanCancelBlend')
	AddDocCmd('RemoveTransformation', _("Remove Transformation"))
	AddDocCmd('CreateMaskGroup', _("Create Mask Group"), sensitive_cb = 'CanCreateMaskGroup')
	AddDocCmd('CreatePathText', _("Create Path Text"), sensitive_cb = 'CanCreatePathText')
	AddDocCmd('CreateClone', _("Create Clone"), sensitive_cb = 'CanCreateClone')
	
	AddDocCmd('RotLeft', _("Rotate Left 90"), 'RotateSelected', args=(90))
	AddDocCmd('Rot180', _("Rotate 180"), 'RotateSelected', args=(180))
	AddDocCmd('RotRight', _("Rotate Right 90"), 'RotateSelected', args=(-90))
	AddDocCmd('UngrAll', _("Ungroup All"), 'UngroupAllSelected', sensitive_cb = 'CanUngroupAll')

	AddDocCmd('Undo', _("Undo"), subscribe_to = UNDO, sensitive_cb = 'CanUndo', image = 'menu_edit_undo', name_cb = 'UndoMenuText', key_stroke = ('Ctrl+Z', 'Ctrl+z'))
	AddDocCmd('Redo', _("Redo"), subscribe_to = UNDO, sensitive_cb = 'CanRedo', name_cb = 'RedoMenuText', image = 'menu_edit_redo', key_stroke = ('Ctrl+Shift+Z', 'Ctrl+Z'))
	AddDocCmd('ResetUndo', _("Discard Undo History"), subscribe_to = None, sensitive_cb = None)

	AddDocCmd('FillNone', _("No Fill"), 'AddStyle', args = EmptyFillStyle)
	AddDocCmd('LineNone', _("No Line"), 'AddStyle', args = EmptyLineStyle)
	AddDocCmd('UpdateStyle', _("Update Style"), 'UpdateDynamicStyleSel')
	
################### Menu build ############################	
	def build_menu(self):
		mbar = self.mbar
		self.file_menu = AppendMenu(mbar, _("File"), self.make_file_menu(), 0)
		AppendMenu(mbar, _("Edit"), self.make_edit_menu(), 0)
		AppendMenu(mbar, _("View"), self.make_view_menu(), 0)
		AppendMenu(mbar, _("Layout"), self.make_layout_menu(), 0)
		AppendMenu(mbar, _("Arrange"), self.make_arrange_menu(), 0)
		AppendMenu(mbar, _("Effects"), self.make_effects_menu(), 4)
#		AppendMenu(mbar, _("Curve"), self.make_curve_menu(), 1)
		AppendMenu(mbar, _("Style"), self.make_style_menu(), 1)
#		AppendMenu(mbar, _("Script"), self.make_script_menu(), 0)
#		AppendMenu(mbar, _("Windows"), self.make_window_menu(), 0)
		AppendMenu(mbar, _("Help"), self.make_help_menu(), 0 )

		if config.preferences.show_special_menu:
			AppendMenu(mbar, _("Special"), self.make_special_menu())
		self.update_mru_files()
		self.file_menu.RebuildMenu()
		
	def add_mru_file(self, filename):
		if filename:
			config.add_mru_file(filename)
			self.update_mru_files()

	def remove_mru_file(self, filename):
		if filename:
			config.remove_mru_file(filename)
			self.update_mru_files()

	def update_mru_files(self):
		self.commands.LoadMRU0.Update()
		self.commands.LoadMRU1.Update()
		self.commands.LoadMRU2.Update()
		self.commands.LoadMRU3.Update()
		self.file_menu.RebuildMenu()
	
	def make_file_menu(self):
		cmds = self.commands
		return map(MakeCommand,
					[cmds.NewDocument,
					cmds.LoadFromFile,
					None,
					cmds.SaveToFile,
					cmds.SaveToFileAs,
					cmds.SaveAll,
					None,
					cmds.CloseDoc,
					cmds.CloseAll,
					None,
					cmds.CreateImage,
					cmds.InsertFile,
					cmds.ExportAs,
					cmds.ExportRaster, #cmds.SavePS,
					#cmds.export_bitmap,
					None,
					cmds.KPrinting,
					cmds.PrintToPDF, #cmds.CreatePrintDialog,
					None,
					#cmds.CreateExportDialog,
					#None,
#					cmds.SetOptions,
#					None,
#					cmds.DocumentInfo,
					None,
					cmds.LoadMRU0,
					cmds.LoadMRU1,
					cmds.LoadMRU2,
					cmds.LoadMRU3,
					None,
					cmds.Exit])
		
	def make_edit_menu(self):
		cmds = self.canvas.commands
		return map(MakeCommand,
					[self.commands.Undo,
					self.commands.Redo,
					self.commands.ResetUndo,
					None,
					self.commands.CutSelected,
					self.commands.CopySelected,
					self.commands.PasteClipboard,
					None,
					self.commands.RemoveSelected,
					self.commands.DuplicateSelected,
					self.commands.SelectAll,
#                                       None,
#                                       [(_("Create"), {'auto_rebuild':self.creation_entries}),
#                                               []],
					None,
					cmds.SelectionMode,
					cmds.EditMode,
					])
		
	def make_view_menu(self):
		def MakeEntry(scale, call = self.canvas.SetScale):
			percent = int(100 * scale)
			return (('%3d%%' % percent), call, scale)
		def Make11(scale, call = self.canvas.SetScale):
			percent = int(100 * scale)
			return (("Zoom 1:1"), call, scale)
		cmds = self.canvas.commands
		scale = map(MakeEntry, [ 0.125, 0.25, 0.5, 1, 2, 4, 8])
		return map(MakeCommand,
					[Make11(1.16),
					[_("Zoom")] + scale,
					cmds.ZoomIn,
					cmds.ZoomOut,
					cmds.ZoomMode,
					None,
					cmds.FitToWindow,
					cmds.FitSelectedToWindow,
					cmds.FitPageToWindow,
					cmds.RestoreViewport,
					None,
					cmds.ForceRedraw,
					None,
					cmds.ToggleOutlineMode,
					cmds.TogglePageOutlineMode,
					None,
					cmds.ToggleCrosshairs,
					None,
					self.commands.LoadPalette
					])				

	def make_layout_menu(self):
		return map(MakeCommand,
					[self.commands.InsertPage,
					self.commands.DeletePage,
					self.commands.GotoPage,
					self.commands.NextPage,
					self.commands.PreviousPage,
					None,
					self.commands.CreateLayoutDialog,
					self.commands.CreateGridDialog,
					self.commands.CreateGuideDialog,
					None,
					self.commands.AddHorizGuideLine,
					self.commands.AddVertGuideLine,
					None,
					self.canvas.commands.ToggleSnapToGrid,
					self.canvas.commands.ToggleSnapToGuides,
					self.canvas.commands.ToggleSnapToObjects
					#None,
					#self.canvas.commands.ToggleSnapMoveRelative,
					#self.canvas.commands.ToggleSnapBoundingRect
					])
		
	def make_arrange_menu(self):
		commands = [self.commands.CreateAlignDialog,
					None,
					self.commands.MoveSelectedToTop,
					self.commands.MoveSelectedToBottom,
					self.commands.MoveSelectionUp,
					self.commands.MoveSelectionDown,
					None,
					self.commands.AbutHorizontal,
					self.commands.AbutVertical,
					None,
					self.commands.GroupSelected,
					self.commands.UngroupSelected,
					None,
					self.commands.ConvertToCurve
					]
		if config.preferences.show_advanced_snap_commands:
			commands.append(None)
			commands.append(self.canvas.commands.ToggleSnapMoveRelative)
			commands.append(self.canvas.commands.ToggleSnapBoundingRect)
		#commands = commands + [None,
			#                     self.commands.CreateLayoutDialog
			#                    ]
		return map(MakeCommand, commands)

	def make_effects_menu(self):
		return map(MakeCommand,
					[self.commands.CreateMoveDialog,
					self.commands.CreateSizeDialog,
					self.commands.CreateRotateDialog,
					None,
					self.commands.FlipHorizontal,
					self.commands.FlipVertical,
					None,
					self.commands.RemoveTransformation,
					None,
					self.commands.CreateBlendDialog,
					self.commands.CancelBlend,
					None,
					self.commands.CreateMaskGroup,
					self.commands.CreatePathText
					])	

	def make_curve_menu(self):
		canvas = self.canvas
		cmds = self.canvas.commands.PolyBezierEditor
		return map(MakeCommand,
					[cmds.ContAngle,
					cmds.ContSmooth,
					cmds.ContSymmetrical,
					cmds.SegmentsToLines,
					cmds.SegmentsToCurve,
					cmds.SelectAllNodes,
					None,
					cmds.DeleteNodes,
					cmds.InsertNodes,
					None,
					cmds.CloseNodes,
					cmds.OpenNodes,
					None,
					self.commands.CombineBeziers,
					self.commands.SplitBeziers,
					None,
					self.commands.ConvertToCurve])
	
	def make_style_menu(self):
		return map(MakeCommand,
					[self.commands.FillNone,
					self.commands.CreateFillStyleDialog,
					self.canvas.commands.FillSolid,
					None,
					self.commands.LineNone,
					self.commands.CreateLineStyleDialog,
					None,
					self.commands.CreateStyleFromSelection,
					self.commands.CreateStyleDialog,
					self.commands.UpdateStyle# ,
#                                       None,
#                                       self.commands.CreateFontDialog
					])

	def make_script_menu(self):
		tree = app.Scripting.Registry.MenuTree()
		cmdlist = self.convert_menu_tree(tree)
		return map(MakeCommand, cmdlist)			

	def make_window_menu(self):
		cmds = self.commands
		return map(MakeCommand,
					[cmds.HideDialogs,
					cmds.ShowDialogs,
					None,
					cmds.CreateLayerDialog,
					cmds.CreateAlignDialog,
					cmds.CreateGridDialog,
					None,
					cmds.CreateLineStyleDialog,
					cmds.CreateFillStyleDialog,
					cmds.CreateFontDialog,
					cmds.CreateStyleDialog,
					None,
					cmds.CreateLayoutDialog,
					None,
					cmds.CreateBlendDialog,
					cmds.CreateCurveDialog
					])

	def make_help_menu(self):
		return map(MakeCommand,
					[self.commands.ProjectSite,
					None,
					self.commands.AboutBox
					])

	def make_special_menu(self):
		cmdlist = [self.commands.python_prompt,
					self.commands.CreateReloadPanel,
					self.commands.DocumentInfo,
					None,
					self.commands.DumpXImage,
					self.commands.CreateClone,
					#self.commands.export_bitmap,
					]
		app.Issue(None, const.ADD_TO_SPECIAL_MENU, cmdlist)
		return map(MakeCommand, cmdlist)		
																				
################### Utilite methods ############################
		
	def issue_document(self):
		self.issue(DOCUMENT, self.document)
		
	def refresh_buffer(self):
		if self.canvas:
			self.canvas.bitmap_buffer=None
	
	def HasKPrinter(self):
		return dialogman.is_kprinter
	
	def PCshowHide(self):
		self.pc.showHide()

	def create_commands(self):
		cmds = Commands()
		keymap = Keymap()
		for cmd_class in command_list:
			cmd = cmd_class.InstantiateFor(self)
			setattr(cmds, cmd.name, cmd)
			keymap.AddCommand(cmd)
		self.commands = cmds
		self.commands.Update()
		self.keymap = keymap

	def MapKeystroke(self, stroke):
		return self.keymap.MapKeystroke(stroke)

	def LoadPalette(self, filename = None):
		if not filename:
			directory = config.user_palettes
			if not directory:
				directory = os_utils.gethome()
				
			filename, sysfilename=dialogman.getGenericOpenFilename(_("Load Palette"),
																   app.managers.dialogmanager.palette_types,
																   initialdir = directory, initialfile = filename)
			if not filename:
				return

		pal = palette.LoadPalette(filename)
		if not pal:
			self.application.MessageBox(title = _("Load Palette"),
								message = _("\nCannot load palette %(filename)s!\n") % {'filename': filename})
		else:
			self.palette.SetPalette(pal)
			config.preferences.palette = filename

	def __init_dlgs(self):
		self.dialogs = {}

	def CreateDialog(self, module, dlgname):
		if self.dialogs.has_key(dlgname):
			dialog = self.dialogs[dlgname]
			dialog.deiconify_and_raise()
		else:
			exec "from %s import %s" % (module, dlgname)
			dlgclass = locals()[dlgname]
			dialog = dlgclass(self.root, self, self.document)
			dialog.Subscribe(CLOSED, self.__dlg_closed, dlgname)
			self.dialogs[dlgname] = dialog

	def HideDialogs(self):
		for dialog in self.dialogs.values():
			dialog.withdraw()


	def ShowDialogs(self):
		for dialog in self.dialogs.values():
			dialog.deiconify_and_raise()


	def __dlg_closed(self, dialog, name):
		try:
			del self.dialogs[name]
		except:
			# This might happen if the dialog is buggy...
			warn(INTERNAL, 'dialog %s alread removed from dialog list', name)

	def KGetOpenFilename(self,title="sK1", filetypes = None, initialdir = '', initialfile = ''):
		self.root.update()
		winid=str(self.root.winfo_id())
		from_K = os.popen('kdialog --caption \''+title+'\' --embed \''+winid+'\' --getopenfilename \''+initialdir+'\''+ filetypes)
		file=from_K.readline()
		file=locale_utils.strip_line(file)
		from_K.close()
		file=locale_utils.locale_to_utf(file)
		return file

	def KPrinting(self):
		self.docmanager.PrintDocument(self.document)
		self.root.update()

	def CreatePluginDialog(self, info):
		if info.HasCustomDialog():
			dialog = info.CreateCustomDialog(self.root, self, self.document)
		else:
			from plugindlg import PluginPanel
			dialog = PluginPanel(self.root, self, self.document, info)
		dialog.Subscribe(CLOSED, self.__dlg_closed, info.class_name)
		self.dialogs[info.class_name] = dialog


	def SetOptions(self):
		import optiondlg
		optiondlg.OptionDialog(self.root, self.canvas)


	def UpdateCommands(self):
		self.canvas.UpdateCommands()

	def creation_entries(self):
		cmds = self.canvas.commands
		entries = [cmds.CreateRectangle,
					cmds.CreateEllipse,
					cmds.CreatePolyBezier,
					cmds.CreatePolyLine,
					cmds.CreateSimpleText,
					self.commands.CreateImage,
					None]
		items = plugins.object_plugins.items()
		items.sort()
		place = self.place_plugin_object
		dialog = self.CreatePluginDialog
		group = self.create_plugin_group
		for name, plugin in items:
			if plugin.UsesSelection():
				entries.append((plugin.menu_text, group, plugin))
			elif plugin.HasParameters() or plugin.HasCustomDialog():
				entries.append((plugin.menu_text + '...', dialog, plugin))
			else:
				entries.append((plugin.menu_text, place, plugin))
		return map(MakeCommand, entries)

	def place_plugin_object(self, info):
		self.canvas.PlaceObject(info())

	def create_plugin_group(self, info):
		self.document.group_selected(info.menu_text, info.CallFactory)

	def PlaceObject(self, object):
		self.canvas.PlaceObject(object)

	def convert_menu_tree(self, tree):
		result = []
		for title, item in tree:
			if type(item) == ListType:
				result.append([title] + self.convert_menu_tree(item))
			else:
				result.append((title, item.Execute))
		return result

	def EditedInfoText(self):
		if self.document.WasEdited():
			return _("modified")
		return _("unmodified")

#Pallette Scrolling
	def ScrollUpPallette(self, delta):
			self.palette.ScrollXUnits(-1)
	def ScrollDownPallette(self, delta):
			self.palette.ScrollXUnits(1)

	def ScrollUpCanvas(self, delta):
			self.canvas.ScrollYUnits(-1)
	def ScrollDownCanvas(self, delta):
			self.canvas.ScrollYUnits(1)
	def ScrollLeftCanvas(self, delta):
			self.canvas.ScrollXUnits(-1)
	def ScrollRightCanvas(self, delta):
			self.canvas.ScrollXUnits(1)
	def CanvasZoomingOut(self, delta):
			self.canvas.ZoomFactor(0.75)
	def CanvasZoomingIn(self, delta):
			self.canvas.ZoomFactor(1.5)

	def RulerDoublePressH(self, event):
			self.root.bell()
			self.CreateDialog('dlg_grid', 'GridPanel')
	def RulerDoublePressV(self, event):
			self.CreateDialog('dlg_layer', 'LayerPanel')

	def GuideDialog(self, action=None):
			self.CreateDialog('dlg_guide', 'GuidePanel')
			
	def ProjectSite(self):
		dialogman.launchBrowserURL('http://sk1project.org')

	def AboutBox(self):
		aboutDialog(self.root)
		
#		abouttext = _("sK1 (%(version)s) - A Python&Tcl/Tk -based vector graphics editor for printing industry.\n "
#						"(c) 2003-2006 by Igor E. Novikov\n\n"
#						"This program is free software under the terms of "
#						"the GNU LGPL v.2.0. For more info - COPYRIGHTS file in sK1 root directory.\n\n"
#						"Libraries versions:\n"
#						"Python:\t%(py)s\t\nTcl:\t%(tcl)s\n"
#						"Tkinter:\t%(tkinter)s\t\nTk:\t%(tk)s") \
#					% {'version':sKVersion,
#						'py':string.split(sys.version)[0],
#						'tcl':TclVersion,
#						'tkinter':string.split(Tkinter.__version__)[1],
#						'tk':TkVersion}
#
#		self.application.MessageBox(title = _("About sK1"), message = abouttext, icon = 'construct')



	def DocumentInfo(self):
		text = self.document.DocumentInfo()

		from app import _sketch
		meminfo = '\nMemory:\n'\
					'# Bezier Paths:\t\t%d\n'\
					'# RGBColors:\t\t%d\n' \
					'# Rects:\t\t%d\n'\
					'# Trafos:\t\t%d\n'\
					'# Points:\t\t%d' % (_sketch.num_allocated(),
										_sketch.colors_allocated(),
										_sketch.rects_allocated(),
										_sketch.trafos_allocted(),
										_sketch.points_allocated())
		text = '\n' + text + '\n\n' + meminfo+ '\n\n'

		self.application.MessageBox(title = 'Document Info', message = text, icon = 'construct')

	AddCmd('DumpXImage', 'Dump XImage')
	def DumpXImage(self):
		gc = self.canvas.gc
		if gc.ximage:
			gc.ximage.dump_data("~/.sK1/ximage.dat")



#     AddCmd('export_bitmap', 'Export Bitmap')
#     def export_bitmap(self):
#       import export
#       export.export_bitmap(self.document)

	AddCmd('python_prompt', 'Python Prompt')
	def python_prompt(self):
		if config.preferences.show_special_menu:
			import prompt
			prompt.PythonPrompt()


	#
	#       Create Image
	#

	def GetOpenImageFilename(self, title = None, initialdir = '', initialfile = '', no_eps = 0):
		if title is None:
			title = _("to load image - sK1")
		if no_eps:
			filetypes = skapp.imagefiletypes()
		else:
			filetypes = skapp.imagefiletypes()
		filename = self.KGetOpenFilename(title = title,
													filetypes = filetypes,
													initialdir = initialdir,
													initialfile = initialfile)
		return filename


	def CreateImage(self, sysfilename = None):
		if not sysfilename:
			filename, sysfilename=dialogman.getImportBMFilename(initialdir = config.preferences.dir_for_bitmap_import, initialfile = '')

		if sysfilename:
			try:
				self.canvas.commands.ForceRedraw
				file = open(sysfilename, 'r')
				is_eps = eps.IsEpsFileStart(file.read(256))
				file.close()
				dir, name = os.path.split(filename)
				config.preferences.image_dir = dir
				if is_eps:
					imageobj = eps.EpsImage(filename = sysfilename)
				else:
					imageobj = image.Image(imagefile = sysfilename)
				self.canvas.PlaceObject(imageobj)
			except IOError, value:
				if type(value) == TupleType:
					value = value[1]
				self.application.MessageBox(title = _("Load Image"),
								message = _("Cannot load %(filename)s:\n"
											"%(message)s") \
								% {'filename':`os.path.split(filename)[1]`,
									'message':value})

	def AddGuideLine(self, horizontal = 1):
		self.canvas.PlaceObject(GuideLine(Point(0, 0), horizontal))

	def CreateStyleFromSelection(self):
		import styledlg
		doc = self.document
		object = doc.CurrentObject()
		style_names = doc.GetStyleNames()
		if object:
			name = styledlg.GetStyleName(self.root, object, style_names)
			if name:
				name, which_properties = name
				doc.CreateStyleFromSelection(name, which_properties)

	def no_pattern(self, category):
		import styledlg
		if category == 'fill':
			title = _("No Fill")
			prop = 'fill_pattern'
		else:
			title = _("No Line")
			prop = 'line_pattern'
		styledlg.set_properties(self.root, self.document, title, category,
								{prop: EmptyPattern})

	#
	#       Cut/Paste
	#

	def CutCopySelected(self, method):
		objects = getattr(self.document, method)()
		if objects is not None:
			self.application.SetClipboard(objects)

	def CopyPasteSelected(self,method):
		objects = getattr(self.document, method)()
		if objects is not None:
			self.application.SetClipboard(objects)
			if self.application.ClipboardContainsData():
					obj = self.application.GetClipboard().Object()
					copies=self.document.copy_objects(self.application.GetClipboard())
					self.document.Insert(copies, undo_text=_("Paste"))
#					obj = obj.Duplicate()
#					self.canvas.PlaceObject(obj)

	def PasteClipboard(self):
		if self.application.ClipboardContainsData():
			obj = self.document.copy_objects(self.application.GetClipboard().Object())
			if config.preferences.insertion_mode:
				self.canvas.PlaceObject(obj)
			else:
				self.document.Insert(obj, undo_text=_("Paste"))


	def FitToNat (self):
		hp=float(self.canvas.winfo_screenheight())
		hm=float(self.canvas.winfo_screenmmheight())
		self.canvas.SetScale(1.07+hm/hp)

	def ExportRaster(self):
			export_raster_more_interactive(self)



	
