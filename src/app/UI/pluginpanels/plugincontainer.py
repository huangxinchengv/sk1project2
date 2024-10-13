# -*- coding: utf-8 -*-

# Copyright (C) 2003-2008 by Igor E. Novikov
#
# This library is covered by GNU Library General Public License.
# For more info see COPYRIGHTS file in sK1 root directory.

from Ttk import TFrame, TLabel
from Tkinter import TOP,LEFT,RIGHT,BOTTOM,X,Y,BOTH,W,S,N,E,NORMAL,DISABLED,END
from app import Publisher
from app.conf.const import DOCUMENT, SELECTION, MODE
from app.UI.widgets.resframe import ResizableTFrame
import app

from pbrowser import PluginBrowser

class PluginContainer(ResizableTFrame):
	
	visible=0
	loaded=[]
	activated=[]
	rborder=None
	
	def __init__(self, master, mw, cnf={}, **kw):
		self.mw=mw
		self.master=master
		ResizableTFrame.__init__(self, master, mw, size=180, orient=LEFT, min=100, max=300)
		self.browserframe=ResizableTFrame(self.panel, mw, size=10, orient=BOTTOM, min=10, max=500)
		self.browserframe.pack(side=TOP, fill=X)
		
		self.pbrowser=PluginBrowser()
				
		
		
	def showHide(self):
		if not self.pbrowser.activated:
			self.pbrowser.init(self.browserframe.panel, self)
			self.pbrowser.forget()
			self.pbrowser.pack(side=TOP, fill=BOTH, expand=1)
			
		if not self.visible:
			self.visible=1
			self.rborder.pack(side=RIGHT, fill=Y)
			self.pack(side=RIGHT, fill=Y)						
		else:
			self.visible=0
			self.rborder.forget()
			self.forget()
			
		