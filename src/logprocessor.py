import re
from gi.repository import GObject, Gio

# The regexps to look for in the log file

re_file = re.compile("(\\((?P<file>[^ \n\t(){}]*)|\\))")
re_badbox = re.compile(r"(Ov|Und)erfull \\[hv]box ")
re_line = re.compile(r"(l\.(?P<line>[0-9]+)( (?P<code>.*))?$|<\*>)")
re_cseq = re.compile(r".*(?P<seq>(\\|\.\.\.)[^ ]*) ?$")
re_macro = re.compile(r"^(?P<macro>\\.*) ->")
re_atline = re.compile("( detected| in paragraph)? at lines? (?P<line>[0-9]*)(--(?P<last>[0-9]*))?")
re_reference = re.compile("LaTeX Warning: Reference `(?P<ref>.*)' on page [0-9]* undefined on input line (?P<line>[0-9]*)\\.$")
re_label = re.compile("LaTeX Warning: (?P<text>Label .*)$")
re_warning = re.compile("(LaTeX|Package)( (?P<pkg>.*))? Warning: (?P<msg>.*)$")
re_online = re.compile("(; reported)? on input line (?P<line>[0-9]*)")
re_ignored = re.compile("; all text was ignored after line (?P<line>[0-9]*).$")


class LogProcessor(GObject.GObject):

    def __init__(self):
        super().__init__()
        self.file = None
        self.line_iter = None
        self.error_list = []
        self.warning_list = []
        self.badbox_list = []

    def set_log_path(self, path):
        self.file = Gio.File.new_for_path(path)

    def process(self, callback):
        self.error_list = []
        self.warning_list = []
        self.badbox_list = []
        self.file.load_contents_async(None, self.load_cb, callback)


    def load_cb(self, src, result, callback):
        success, contents, etag = src.load_contents_finish(result)
        try:
            log = contents.decode("UTF-8")
        except UnicodeDecodeError:
            print("Error: Unknown character encoding of the log file. Expecting UTF-8")
        else:
            self.line_iter = iter(log.splitlines())
            for elem in self.parse():
                if elem["type"] == "error":
                    self.error_list.append(elem)
                if elem["type"] == "warning" or elem["type"] == "reference":
                    self.warning_list.append(elem)
                if elem["type"] == "badbox":
                    self.badbox_list.append(elem)
                print(elem)
        finally:
            callback()

    def continued (self, line):
        """
        Check if a line in the log is continued on the next line. This is
        needed because TeX breaks messages at 79 characters per line. We make
        this into a method because the test is slightly different in Metapost.
        """
        return len(line) == 79

    def line_generator(self):
        """
            The generator used to get the lines of the log file. It concatenates
            lines that are cut at 79 characters and skips empty lines.
        """
        while True:
            try:
                line = next(self.line_iter)
                L = len(line)
                while L == 79:
                    txt = next(self.line_iter)
                    L = len(txt)
                    line = line + txt
                if len(line) == 0:
                    continue
                else:
                    yield line
            except StopIteration:
                return

    def parse (self):
        """
        Parse the log file for relevant information.
        The function returns a generator. Each generated item is a dictionary
        that contains (some of) the following entries:
        - type: the type of information ("error", "box", "ref", "warning")
        - msg:  the error or warning message
        - context: the piece of code that caused an error or warning
        - file: the file in which the error occured
        - line: the line that caused the error or warning
        - lastline: the last line that caused the error or warning
        """
        files = []         # The currently opened files
        parsing = False    # True if we are parsing an error's text
        prefix = None  # the prefix for warning messages from packages
        macro = None   # the macro in which the error occurs
        cseqs = {}     # undefined control sequences so far

        lines = self.line_generator()

        for line in lines:

            d = dict()
            if len(files)>0:
                d["file"] = files[-1]

            # Errors
            d["type"] = "error"

            if line[0] == "!":
                error = line[2:]
                parsing = True
                continue

            if line == "Runaway argument?":
                error = line
                parsing = True
                continue


            # Errors (including aborted compilation)
            while parsing:
                if error == "Undefined control sequence.":
                    # This is a special case in order to report which control
                    # sequence is undefined.
                    m = re_cseq.match(line)
                    if m:
                        seq = m.group("seq")
                        if seq in cseqs:
                            error = None
                        else:
                            cseqs[seq] = None
                            error = f"Undefined control sequence {m.group('seq')}."
                m = re_macro.match(line)
                if m:
                    macro = m.group("macro")
                m = re_line.match(line)
                if m:
                    parsing = False
                    pdfTeX = line.find("pdfTeX warning") != -1
                    if error is not None and (pdfTeX or (not pdfTeX)):
                        if pdfTeX:
                            d["type"] = "warning"
                            d["msg"] = error[error.find(":")+2:]
                        else:
                            d["msg"] = error
                        m = re_ignored.search(error)
                        if m:
                            if "code" in d:
                                del d["code"]
                            d.update( m.groupdict() )
                        if macro is not None:
                            d["macro"] = macro
                            macro = None
                        yield d
                elif line[0] == "!":
                    error = line[2:]
                elif line[0:3] == "***":
                    parsing = False
                    d["msg"] = error
                    yield d
                line = next(lines)

            # End of parsing



            # Warnings
            d["type"] = "warning"

            # Long warnings
            if prefix is not None:
                if line[:len(prefix)] == prefix:
                    text.append(line[len(prefix):].strip())
                else:
                    text = " ".join(text)
                    m = re_online.search(text)
                    if m:
                        d["line"] = m.group("line")
                        text = text[:m.start()] + text[m.end():]
                    d["msg"] = text
                    yield d
                    prefix = None
                continue

            # Undefined references
            d["type"] = "reference"

            m = re_reference.match(line)
            if m:
                d["msg"] = f"Reference `{m.group('ref')}' undefined."
                yield d
                continue

            m = re_label.match(line)
            if m:
                yield d
                continue

            # Other warning
            if line.find("Warning") != -1:
                m = re_warning.match(line)
                if m:
                    info = m.groupdict()
                    if info["pkg"] is None:
                        del info["pkg"]
                        prefix = ""
                    else:
                        prefix = ("(%s)" % info["pkg"])
                    prefix = prefix.ljust(m.start("msg"))
                    text = [info["msg"]]
                continue

            # Bad box messages
            d["type"] = "badbox"

            m = re_badbox.match(line)
            if m:
                m = re_atline.search(line)
                if m:
                    md = m.groupdict()
                    for key in "line", "last":
                        if md[key]: d[key] = md[key]
                    line = line[:m.start()]
                d["msg"] = line
                yield d
                continue

            # If there is no message, track source names
            m = re_file.search(line)
            while m:
                if line[m.start()] == '(':
                    files.append(m.group("file"))
                else:
                    del files[-1]
                line = line[m.end():]
                m = re_file.search(line)

