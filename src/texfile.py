from gi.repository import GObject
import os

"""
  Keeps name of the opened tex file, its root tex document
  Helps to find the log files, etc.
"""

class TexFile(GObject.Object):
    __gtype_name__ = "TexFile"

    def __init__(self):
        super().__init__()
        self._root_base = ""
        self._tex_path = ""

    @GObject.Property(type=str)
    def tex_path(self):
        return self._tex_path

    @tex_path.setter
    def tex_path(self, path):
        self._tex_path = path
        self._root_base = os.path.splitext(path)[0]

    @property
    def pdf_path(self):
        return self._root_base + ".pdf"

    @property
    def log_path(self):
        return self._root_base + ".log"

    @property
    def root_dir(self):
        return os.path.dirname(self._root_base)

    @GObject.Property
    def title(self):
        path = os.path.basename(self._tex_path)
        return os.path.splitext(path)[0]
