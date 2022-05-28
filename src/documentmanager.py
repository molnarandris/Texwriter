import os
from gi.repository import GObject, GtkSource, GLib, Gio
from .utilities import  ProcessRunner


class DocumentManager(GObject.GObject):

    __gsignals__ = {
        'open-success': (GObject.SIGNAL_RUN_LAST, None, (str,)),
        'save-success': (GObject.SIGNAL_RUN_LAST, None, ()),
        'open-pdf': (GObject.SIGNAL_RUN_LAST, None, (str,)),
        'compiled': (GObject.SIGNAL_RUN_LAST, None, (bool,)),
    }

    def __init__(self,buffer):
        super().__init__()

        self.buffer = buffer
        self.file = None
        self.to_compile = False
        self.cancellable = None

    def open_file(self,file):

        def load_finish_cb(loader, result):
            success = loader.load_finish(result)
            path = loader.get_location().get_path()
            if success:
                self.file = file # when we call this fcn, file is the right thing
                self.emit("open-success", path)
            else:
                print("Could not load file: " + path)
            return success

        loader = GtkSource.FileLoader.new(self.buffer, file)
        self.cancellable = Gio.Cancellable.new()
        loader.load_async(io_priority=GLib.PRIORITY_DEFAULT, callback = load_finish_cb, cancellable = self.cancellable)

    def save_file(self):

        def save_finish_cb(saver, result):
            success = saver.save_finish(result)
            path = saver.get_location().get_path()
            if success:
                self.emit("save-success")
                if self.to_compile:
                    self.compile()
            else:
                print("Could not save file: " + path)
            return success

        saver = GtkSource.FileSaver.new(self.buffer, self.file)
        self.cancellable = Gio.Cancellable.new()
        saver.save_async(io_priority = GLib.PRIORITY_DEFAULT, callback = save_finish_cb, cancellable = self.cancellable)

    def compile(self):
        def on_compile_finished(sender):
            if sender.result == 0:
                # Compilation was successful
                tex = self.file.get_location().get_path()
                pdf = os.path.splitext(tex)[0] + ".pdf"
                self.emit("open-pdf", pdf)
                self.emit("compiled", True)
                self.to_compile = False
            else:
                # Compilation failed
                self.emit("compiled", False)

        tex = self.file.get_location().get_path()
        directory = os.path.dirname(tex)
        cmd = ['flatpak-spawn', '--host', '/usr/bin/latexmk', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', '-halt-on-error', '-output-directory=' + directory, tex]
        proc = ProcessRunner(cmd)
        self.cancellable = proc.cancellable
        proc.connect('finished', on_compile_finished)

    def cancel(self):
        self.cancellable.cancel()

