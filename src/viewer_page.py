from gi.repository import Gtk, GObject
from .pdfviewer import PdfViewer
from .logprocessor import LogProcessor

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/viewer_page.ui')
class ViewerPage(Gtk.Widget):
    __gtype_name__ = "ViewerPage"

    pdfviewer     = Gtk.Template.Child()
    main_stack    = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)


    def load(self,file):
        self.pdfviewer.load(file)
        self.main_stack.set_visible_child(self.pdfviewer)



