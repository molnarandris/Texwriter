from gi.repository import Gtk, GObject
from .pdfviewer import PdfViewer
from .logprocessor import LogProcessor

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/viewer_page.ui')
class ViewerPage(Gtk.Widget):
    __gtype_name__ = "ViewerPage"

    def __init__(self):
        super().__init__()



