import tkinter as tki
import tkinter.ttk as ttk

class ScrollableFrame( object):
    def __init__( self, root, canvas_w, canvas_h, use_horiz_scrolling = False):
        self.root = root
        self.canvasframe = ttk.Frame(self.root)
        self.graphcanvas = tki.Canvas(self.canvasframe)
        self.scrollbar_v = ttk.Scrollbar(self.canvasframe, orient="vertical", command=self.graphcanvas.yview)
        if use_horiz_scrolling:
            self.scrollbar_h = ttk.Scrollbar(self.canvasframe, orient="horizontal", command=self.graphcanvas.xview)
        self.scrollframe = ttk.Frame(self.graphcanvas)
        self.graphcanvas.create_window((0, 0), window=self.scrollframe, anchor="nw")
        self.graphcanvas.configure(yscrollcommand=self.scrollbar_v.set)
        if use_horiz_scrolling:
            self.graphcanvas.configure(xscrollcommand=self.scrollbar_h.set)
        self.graphcanvas.config(width=canvas_w,height=canvas_h)
        self.graphcanvas.pack(side="left", fill="both", expand=True)
        self.scrollbar_v.pack(side="right", fill="y")
        if use_horiz_scrolling:
            self.scrollbar_h.pack(side="bottom", fill="x")

        self.scrollframe.bind('<Configure>', lambda e: self.graphcanvas.configure(scrollregion=self.graphcanvas.bbox("all") ) )

    def pack( self, *args, **kwargs ):
        self.canvasframe.pack( *args, **kwargs )

    def grid( self, *args, **kwargs ):
        self.canvasframe.grid( *args, **kwargs )

    def getFrame( self ):
        return self.scrollframe
        
