from gi.repository import Gtk, Gio, GObject
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

    def tex_opened_cb(self, sender, success):
        if success:
            self.pdfview.load(self.sourceview.file.get_pdf_path())
        else:
            print("File loading error")

    def realize_cb(self, _):
        # hack: set first size
        self.paned.set_position(self.get_root().get_allocated_width() / 2)

    # do_dispose does not run
    def dispose_cb(self, _):
        self.paned.unparent()

    def on_compile_finished(self, proc, result, data):
        self.to_compile = False
        if not proc.get_successful():
            self.logprocessor.run()
        self.set_property("busy", False)
        self.pdfview.load(self.sourceview.file.get_pdf_path())
        self.emit("compiled", proc.get_successful())

    def compile(self, save = True):
        if self.sourceview.file is None:
            return
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
        self.set_property("busy", True)
        proc.communicate_utf8_async(None, None, self.on_compile_finished, None)

    def saved_cb(self, widget, success):
        if not success:
            if self.to_compile:
                self.to_compile = False
                self.emit("compiled", False)
        if self.to_compile:
            self.compile(False)
