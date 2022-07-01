import os, re
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
        self.logprocessor = LogProcessor(buffer)
        self.logprocessor.connect('finished',self.on_log_finished)



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
                self.logprocessor.run()

        self.buffer.clear_tags()
        tex = self.file.get_location().get_path()
        directory = os.path.dirname(tex)
        cmd = ['flatpak-spawn', '--host', '/usr/bin/latexmk', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', '-halt-on-error', '-output-directory=' + directory, tex]
        proc = ProcessRunner(cmd)
        self.cancellable = proc.cancellable
        proc.connect('finished', on_compile_finished)

    def cancel(self):
        self.cancellable.cancel()

    def on_log_finished(self, logproc):
        self.emit("compiled", False)

    def synctex_fwd(self, sender, _):
        def on_synctex_finished(sender):
            result = re.search("Page:(.*)", sender.stdout)
            page = int(result.group(1))
            result = re.search("x:(.*)", sender.stdout)
            x = float(result.group(1))
            result = re.search("y:(.*)", sender.stdout)
            y = float(result.group(1))
            result = re.search("h:(.*)", sender.stdout)
            h = float(result.group(1))
            result = re.search("v:(.*)", sender.stdout)
            v = float(result.group(1))
            result = re.search("H:(.*)", sender.stdout)
            H = float(result.group(1))
            result = re.search("W:(.*)", sender.stdout)
            W = float(result.group(1))
            self.pdfview.synctex_fwd(page,x,y,h,v,H,W)

        buf = self.sourceview.get_buffer()
        it = buf.get_iter_at_mark(buf.get_insert())
        path = self.docmanager.file.get_location().get_path()
        pos = str(it.get_line()) + ":" + str(it.get_line_offset()) + ":" + path
        path = os.path.splitext(path)[0] + '.pdf'
        cmd = ['flatpak-spawn', '--host', 'synctex', 'view', '-i', pos, '-o', path]
        proc = ProcessRunner(cmd)
        proc.connect('finished', on_synctex_finished)



