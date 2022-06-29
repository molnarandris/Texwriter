from gi.repository import Gtk
from .sourceview import TexwriterSource
from .pdfviewer import PdfViewer
from .logview import LogView

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/tabpage.ui')
class TabPage(Gtk.Widget):
    __gtype_name__ = 'TabPage'

    paned         = Gtk.Template.Child()
    pdfview       = Gtk.Template.Child()
    logview       = Gtk.Template.Child()
    sourceview    = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)

        # Making paned to change size when window is resized
        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)

        # do_dispose does not run
        self.connect("destroy", self.dispose_cb)
        self.connect("realize", self.realize_cb)

    def realize_cb(self, _):
        # hack: set first size
        self.paned.set_position(self.get_root().get_allocated_width() / 2)

    # do_dispose does not run
    def dispose_cb(self, _):
        self.paned.unparent()
