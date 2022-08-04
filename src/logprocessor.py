import re
from gi.repository import GObject, Gio

# The regexps to look for in the log file

re_file = re.compile("(\\((?P<file>[^ \n\t(){}]*)|\\))")
re_badbox = re.compile(r"(Ov|Und)erfull \\[hv]box ")
re_line = re.compile(r"(l\.(?P<line>[0-9]+)( (?P<code>.*))?$|<\*>)")
re_cseq = re.compile(r".*(?P<seq>(\\|\.\.\.)[^ ]*) ?$")
re_macro = re.compile(r"^(?P<macro>\\.*) ->")
re_atline = re.compile(
"( detected| in paragraph)? at lines? (?P<line>[0-9]*)(--(?P<last>[0-9]*))?")
re_reference = re.compile("LaTeX Warning: Reference `(?P<ref>.*)' \
on page [0-9]* undefined on input line (?P<line>[0-9]*)\\.$")
re_label = re.compile("LaTeX Warning: (?P<text>Label .*)$")
re_warning = re.compile(
"(LaTeX|Package)( (?P<pkg>.*))? Warning: (?P<text>.*)$")
re_online = re.compile("(; reported)? on input line (?P<line>[0-9]*)")
re_ignored = re.compile("; all text was ignored after line (?P<line>[0-9]*).$")


class LogProcessor(GObject.GObject):

    def __init__(self):
        super().__init__()
        self.file = None
        self.lines = []
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
            self.lines = log.splitlines()
            for elem in self.parse():
                if elem["kind"] == "error":
                    self.error_list.append(elem)
                if elem["kind"] == "warning" or elem["kind"] == "ref":
                    self.warning_list.append(elem)
                if elem["kind"] == "badbox":
                    self.badbox_list.append(elem)
                print(elem)
            print(self.badbox_list)
        finally:
            callback()

    def continued (self, line):
        """
        Check if a line in the log is continued on the next line. This is
        needed because TeX breaks messages at 79 characters per line. We make
        this into a method because the test is slightly different in Metapost.
        """
        return len(line) == 79

    def parse (self):
        """
        Parse the log file for relevant information.
        The function returns a generator. Each generated item is a dictionary
        that contains (some of) the following entries:
        - kind: the kind of information ("error", "box", "ref", "warning")
        - text: the text of the error or warning
        - code: the piece of code that caused an error
        - file, line, last, pkg: as used by Message.format_pos.
        """
        if not self.lines:
            return
        files = []         # The currently opened files
        parsing = False    # True if we are parsing an error's text
        skipping = False   # True if we are skipping text until an empty line
        prefix = None  # the prefix for warning messages from packages
        accu = ""      # accumulated text from the previous line
        macro = None   # the macro in which the error occurs
        cseqs = {}     # undefined control sequences so far
        for line in self.lines:

            # TeX breaks messages at 79 characters, just to make parsing
            # trickier...

            if not parsing and self.continued(line):
                accu += line
                continue
            line = accu + line
            accu = ""

            # Text that should be skipped (from bad box messages)

            if prefix is None and line == "":
                skipping = False
                continue

            if skipping:
                continue

            # Errors (including aborted compilation)

            if parsing:
                if error == "Undefined control sequence.":
                    # This is a special case in order to report which control
                    # sequence is undefined.
                    m = re_cseq.match(line)
                    if m:
                        seq = m.group("seq")
                        if cseqs.has_key(seq):
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
                    skipping = True
                    pdfTeX = line.find("pdfTeX warning") != -1
                    if error is not None and (pdfTeX or (not pdfTeX)):
                        if pdfTeX:
                            d = {
                                "kind": "warning",
                                "pkg": "pdfTeX",
                                "text": error[error.find(":")+2:]
                            }
                        else:
                            d =    {
                                "kind": "error",
                                "text": error
                            }
                        d.update( m.groupdict() )
                        m = re_ignored.search(error)
                        if m:
                            d["file"] = files[-1]
                            if d.has_key("code"):
                                del d["code"]
                            d.update( m.groupdict() )
                        elif files[-1] is None:
                            d["file"] = files[-1]
                        else:
                            d["file"] = files[-1]
                        if macro is not None:
                            d["macro"] = macro
                            macro = None
                        yield d
                elif line[0] == "!":
                    error = line[2:]
                elif line[0:3] == "***":
                    parsing = False
                    skipping = True
                    yield    {
                        "kind": "abort",
                        "text": error,
                        "why" : line[4:],
                        "file": files[-1]
                        }
                continue

            if len(line) > 0 and line[0] == "!":
                error = line[2:]
                parsing = True
                continue

            if line == "Runaway argument?":
                error = line
                parsing = True
                continue

            # Long warnings

            if prefix is not None:
                if line[:len(prefix)] == prefix:
                    text.append(line[len(prefix):].strip())
                else:
                    text = " ".join(text)
                    m = re_online.search(text)
                    if m:
                        info["line"] = m.group("line")
                        text = text[:m.start()] + text[m.end():]
                    info["text"] = text
                    d = { "kind": "warning" }
                    d.update( info )
                    yield d
                    prefix = None
                continue

            # Undefined references

            m = re_reference.match(line)
            if m:
                d =    {
                    "kind": "warning",
                    "text": f"Reference `{m.group('ref')}' undefined.",
                    "file": files[-1]
                    }
                d.update( m.groupdict() )
                yield d
                continue

            m = re_label.match(line)
            if m:
                d =    {
                    "kind": "warning",
                    "file": files[-1]
                    }
                d.update( m.groupdict() )
                yield d
                continue

            # Other warnings

            if line.find("Warning") != -1:
                m = re_warning.match(line)
                if m:
                    info = m.groupdict()
                    info["file"] = files[-1]
                    if info["pkg"] is None:
                        del info["pkg"]
                        prefix = ""
                    else:
                        prefix = ("(%s)" % info["pkg"])
                    prefix = prefix.ljust(m.start("text"))
                    text = [info["text"]]
                continue

            # Bad box messages

            m = re_badbox.match(line)
            if m:
                mpos = { "file": files[-1] }
                m = re_atline.search(line)
                if m:
                    md = m.groupdict()
                    for key in "line", "last":
                        if md[key]: mpos[key] = md[key]
                    line = line[:m.start()]
                d =    {
                    "kind": "warning",
                    "text": line
                    }
                d.update( mpos )
                yield d
                skipping = True
                continue

            # If there is no message, track source names

            self.update_file(line, files)

    def update_file (self, line, stack):
        """
        Parse the given line of log file for file openings and closings and
        update the list `stack'. Newly opened files are at the end, therefore
        stack[1] is the main source while stack[-1] is the current one. The
        first element, stack[0], contains the value None for errors that may
        happen outside the source.
        """
        m = re_file.search(line)
        while m:
            if line[m.start()] == '(':
                stack.append(m.group("file"))
            else:
                del stack[-1]
            line = line[m.end():]
            m = re_file.search(line)

