import re
from gi.repository import GObject, Gio

class LogProcessor(GObject.GObject):

    __gsignals__ = {
        'finished': (GObject.SIGNAL_RUN_LAST, None, ()),
    }

    # The regexps to look for in the log file
    badbox_re  = re.compile("^Overfull.* ([0-9]+)\-\-[0-9]+\n",re.MULTILINE)
    warning_re = re.compile("^LaTeX Warning: (Reference|Citation) `(.*)'.* ([0-9]*)\.\n",re.MULTILINE)
    error_re   = re.compile("^! (.*)\.\nl\.([0-9]*) (.*$)",re.MULTILINE)

    def __init__(self):
        super().__init__()
        self.file = None

    def set_log_path(self, path):
        self.file = Gio.File.new_for_path(path)

    def process(self):
        self.error_list = []
        self.warning_list = []
        self.badbox_list = []
        self.file.load_contents_async(None, self.load_cb, None)


    def load_cb(self,src,res,data):
        success, contents, etag = src.load_contents_finish(res)
        try:
            log = contents.decode("UTF-8")
        except UnicodeDecodeError:
            print("Error: Unknown character encoding of the log file. Expecting UTF-8")
            self.emit("finished")
            return

        for m in re.finditer(self.error_re, log):
            line   = int(m.group(2))-1
            detail = m.group(3)
            description = m.group(1)
            self.error_list.append((description,line,detail))

        for m in re.finditer(self.warning_re, log):
            line   = int(m.group(3))-1
            detail = m.group(2)
            msg = m.group(1)
            if msg == "Reference":
                detail = "\\ref{" + detail + "}"
            else:
                detail = "\\cite{" + detail + "}"
            self.warning_list.append((line, detail))

        for m in re.finditer(self.badbox_re, log):
            line   = int(m.group(1))-1
            detail = ""
            self.badbox_list.append((line, detail))

        self.emit('finished')

