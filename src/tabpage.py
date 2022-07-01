from gi.repository import Gtk, Gio, GObject, Adw
from .sourceview import TexwriterSource
from .pdfviewer import PdfViewer
from .logview import LogView
from .logprocessor import LogProcessor

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/tabpage.ui')
class TabPage(Gtk.Widget):
    __gtype_name__ = 'TabPage'

    paned         = Gtk.Template.Child()
    pdfview       = Gtk.Template.Child()
    logview       = Gtk.Template.Child()
    sourceview    = Gtk.Template.Child()
    pdfstack      = Gtk.Template.Child()
    errorlist     = Gtk.Template.Child()

    busy = GObject.Property(type=bool, default=False)

    __gsignals__ = {
        'compiled': (GObject.SIGNAL_RUN_LAST, None, (bool,)),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)

        self.to_compile = False

        # Making paned to change size when window is resized
        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)

        # do_dispose does not run
        self.connect("destroy", self.dispose_cb)
        self.connect("realize", self.realize_cb)

        self.sourceview.connect("saved", self.saved_cb)
        self.sourceview.connect("opened", self.tex_opened_cb)
        self.logview.connect("loaded", self.log_loaded_cb)

        self.logprocessor = LogProcessor()
        self.logprocessor.connect("finished", self.log_processed_cb)

    def log_processed_cb(self, logprocessor):
        for e in logprocessor.error_list:
            row = Adw.ActionRow.new()
            row.set_activatable(True)
            row.data = e
            row.set_title(f"{e[0]}: \"{e[2]}\" on line {e[1]}")
            self.errorlist.append(row)
            row.connect("activated", self.error_activated)

    def error_activated(self, row):
        print("yea")
        buffer = self.sourceview.sourceview.get_buffer()
        it = buffer.highlight("Error", row.data[1], row.data[2])
        self.sourceview.sourceview.scroll_to_iter(it, 0.3, False, 0, 0)
        buffer.place_cursor(it)
        self.sourceview.sourceview.grab_focus()

    def tex_opened_cb(self, sender, success):
        if success:
            self.pdfview.load(self.sourceview.file.get_pdf_path())
            self.logprocessor.set_log_path(self.sourceview.file.get_log_path())
        else:
            print("File loading error")

    def log_loaded_cb(self, sender):
        self.set_property("busy", False)

    def realize_cb(self, _):
        # hack: set first size
        self.paned.set_position(self.get_root().get_allocated_width() / 2)

    # do_dispose does not run
    def dispose_cb(self, _):
        self.paned.unparent()

    def on_compile_finished(self, proc, result, data):
        self.to_compile = False
        if not proc.get_successful():
            print("Compile failed")
            self.pdfstack.set_visible_child_name("error")
            self.logprocessor.process()
            return
        self.set_property("busy", False)
        self.pdfstack.set_visible_child_name("pdfview")
        self.pdfview.load(self.sourceview.file.get_pdf_path())
        self.emit("compiled", proc.get_successful())

    def clear_error_list(self):
        c = self.errorlist.get_first_child()
        while c:
            self.errorlist.remove(c)
            c = self.errorlist.get_first_child()


    def compile(self, save = True):
        self.clear_error_list()
        if self.sourceview.file is None:
            return
        self.set_property("busy", True)
        if save and self.sourceview.modified:
            self.to_compile = True
            self.sourceview.save()
            return  # we have to wait for the saving to finish
        self.to_compile = False
        self.sourceview.clear_tags()
        path = self.sourceview.file.get_tex_path()
        directory = self.sourceview.file.get_dir()
        cmd = ['flatpak-spawn', '--host', 'latexmk', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', '-halt-on-error', "--output-directory="+ directory, path]
        print(path)
        proc = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE)
        proc.communicate_utf8_async(None, None, self.on_compile_finished, None)

    def saved_cb(self, widget, success):
        if not success:
            if self.to_compile:
                self.to_compile = False
                self.emit("compiled", False)
                self.set_property("busy", False)
        if self.to_compile:
            self.compile(False)
