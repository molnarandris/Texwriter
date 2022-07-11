from gi.repository import Gtk, GObject, Adw
from .pdfviewer import PdfViewer
from .logprocessor import LogProcessor

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/viewer_page.ui')
class ViewerPage(Gtk.Widget):
    __gtype_name__ = "ViewerPage"

    pdfviewer     = Gtk.Template.Child()
    main_stack    = Gtk.Template.Child()
    errorlist     = Gtk.Template.Child()
    warninglist   = Gtk.Template.Child()
    badboxlist    = Gtk.Template.Child()
    warning_label = Gtk.Template.Child()
    badbox_label  = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        self.logprocessor = LogProcessor()

    def load_pdf(self, path):
        self.pdfviewer.load(path)
        self.main_stack.set_visible_child_name("pdfview")

    def load_log(self, path):
        for lst in [self.errorlist, self.warninglist, self.badboxlist]:
            c = lst.get_first_child()
            while c:
                lst.remove(c)
                c = lst.get_first_child()
        self.logprocessor.set_log_path(path)
        self.logprocessor.process(self.load_log_finish)

    def load_log_finish(self):
        for e in self.logprocessor.error_list:
            row = Adw.ActionRow.new()
            row.set_activatable(True)
            row.data = e
            row.set_title(f"{e[0]}: \"{e[2]}\" on line {e[1]}")
            self.errorlist.append(row)
            row.connect("activated", self.error_row_activated)
        for e in self.logprocessor.warning_list:
            row = Adw.ActionRow.new()
            row.set_activatable(True)
            row.data = e
            row.set_title(f"{e[0]}: \"{e[2]}\" on line {e[1]}")
            self.warninglist.append(row)
            row.connect("activated", self.error_row_activated)
        for e in self.logprocessor.badbox_list:
            row = Adw.ActionRow.new()
            row.set_activatable(True)
            row.data = e
            row.set_title(f"{e[0]}: \"{e[2]}\" on line {e[1]}")
            self.badboxlist.append(row)
            row.connect("activated", self.error_row_activated)

        if self.logprocessor.error_list:
            self.main_stack.set_visible_child_name("errorview")
        if self.logprocessor.warning_list:
            self.warning_label.set_visible(True)
            self.warninglist.set_visible(True)
        else:
            self.warning_label.set_visible(False)
            self.warninglist.set_visible(False)
        if self.logprocessor.badbox_list:
            self.badbox_label.set_visible(True)
            self.badboxlist.set_visible(True)
        else:
            self.badbox_label.set_visible(False)
            self.badboxlist.set_visible(False)
        
    def error_row_activated(self, row):
        path = self.pdfviewer.path[:-3]+ "tex"
        context = row.data[2]
        if context.startswith("..."):
            context = context[3:]
        self.get_root().goto_tex(path, row.data[1], context, -1)
        
