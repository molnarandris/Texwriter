from gi.repository import Gtk, GObject, Adw
from .pdfviewer import PdfViewer
from .logprocessor import LogProcessor

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/viewer_page.ui')
class ViewerPage(Gtk.Widget):
    __gtype_name__ = "ViewerPage"

    pdfviewer     = Gtk.Template.Child()
    main_stack    = Gtk.Template.Child()
    errorlist     = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        self.logprocessor = LogProcessor()
        self.logprocessor.connect("finished", self.load_error_finish)

    def load_pdf(self, path):
        self.pdfviewer.load(path)
        self.main_stack.set_visible_child_name("pdfview")

    def clear_error_list(self):
        c = self.errorlist.get_first_child()
        while c:
            self.errorlist.remove(c)
            c = self.errorlist.get_first_child()


    def load_error(self, path):
        self.clear_error_list()
        self.logprocessor.set_log_path(path)
        self.logprocessor.process()

    def load_error_finish(self, sender):
        for e in self.logprocessor.error_list:
            row = Adw.ActionRow.new()
            row.set_activatable(True)
            row.data = e
            row.set_title(f"{e[0]}: \"{e[2]}\" on line {e[1]}")
            self.errorlist.append(row)
            row.connect("activated", self.error_row_activated)
        self.main_stack.set_visible_child_name("errorview")
        
    def error_row_activated(self, row):
        path = self.pdfviewer.path[:-3]+ "tex"
        context = row.data[2]
        if context.startswith("..."):
            context = context[3:]
        self.get_root().goto_tex(path, row.data[1], context, -1)
        
