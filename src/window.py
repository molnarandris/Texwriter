# window.py
#
# Copyright 2022 András Molnár
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, re, gi
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, GObject, GtkSource, Gio, GLib, Gdk
from .pdfviewer import PdfViewer
from .utilities import ProcessRunner

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    GObject.type_register(GtkSource.View)
    paned        = Gtk.Template.Child()
    sourceview   = Gtk.Template.Child()
    header_bar   = Gtk.Template.Child()
    pdfview      = Gtk.Template.Child()
    title        = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Save and restore window geometry
        settings = Gio.Settings.new(
            "com.github.molnarandris.texwriter"
        )
        settings.bind("width", self, "default-width", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("height", self, "default-height", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("maximized", self, "maximized", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("paned-position", self.paned, "position", Gio.SettingsBindFlags.DEFAULT)

        # Making paned to change size when window is resized
        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)

        actions = [
            ('open', self.on_open_action, ['<primary>o']),
            ('close', self.on_close_action, ['<primary>w']),
            ('save', self.on_save_action, ['<primary>s']),
            ('compile', self.on_compile_action, ['F5']),
            ('synctex-fwd', self.synctex_fwd, ['F7']),
        ]

        for a in actions: self.create_action(*a)

        manager = GtkSource.LanguageManager()
        language = manager.get_language("latex")
        buffer = self.sourceview.get_buffer()
        buffer.set_language(language)
        buffer.connect("changed", lambda _: self.title.set_saved(False))

        self.file = None
        self.to_compile = False

        self.pdfview.connect("synctex-bck", self.synctex_bck)

    def synctex_bck(self,sender, line):
        buf = self.sourceview.get_buffer()
        _, it = buf.get_iter_at_line_offset(line-1,0)
        buf.place_cursor(it)
        self.sourceview.scroll_to_iter(it,0,True, 0, 0.382)

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
        pos = str(it.get_line()) + ":" + str(it.get_line_offset()) + ":" + self.file.get_location().get_path()
        path, _ = os.path.splitext(self.file.get_location().get_path())
        path = path + '.pdf'
        cmd = ['flatpak-spawn', '--host', 'synctex', 'view', '-i', pos, '-o', path]
        proc = ProcessRunner(cmd)
        proc.connect('finished', on_synctex_finished)

    def open_file(self,file):

        def load_finish_cb(loader, result):
            success = loader.load_finish(result)
            path = loader.get_location().get_path()
            if success:
                self.file = file # when we call this fcn, file is the right thing
                self.title.set_saved(True)
                s,t = os.path.split(path)
                self.title.set_title_string(t)
                self.title.set_subtitle_string(s)
            else:
                print("Could not load file: " + path)
            return success

        buffer = self.sourceview.get_buffer()
        loader = GtkSource.FileLoader.new(buffer, file)
        loader.load_async(io_priority=GLib.PRIORITY_DEFAULT, callback = load_finish_cb)
        path, _ = os.path.splitext(file.get_location().get_path())
        path = path + '.pdf'
        self.pdfview.open_file(path)


    def on_open_action(self, widget, _):

        # Extra reference to dialog to prevent garbage collection
        def dialog_response(dialog, response, _dialog):
            if response == Gtk.ResponseType.ACCEPT:
                file = GtkSource.File.new()
                file.set_location(dialog.get_file())
                self.open_file(file)

        dialog = Gtk.FileChooserNative.new( "Open file", self, Gtk.FileChooserAction.OPEN, None, None)
        dialog.connect("response", dialog_response, dialog)

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

        dialog.show()

    def save_file(self, buffer, file):

        def save_finish_cb(saver, result):
            success = saver.save_finish(result)
            path = saver.get_location().get_path()
            if success:
                self.title.set_saved(True)
                if self.to_compile:
                    self.compile()
            else:
                print("Could not save file: " + path)
            return success

        saver = GtkSource.FileSaver.new(buffer = buffer, file = file)
        saver.save_async(io_priority = GLib.PRIORITY_DEFAULT, callback = save_finish_cb)

    def on_save_action(self, widget, _):

        def dialog_response(self, dialog, response, _dialog):
            if response == Gtk.ResponseType.ACCEPT:
                file = GtkSource.File.new()
                file.set_location(dialog.get_file())
                self.save_file(file)

        if self.file is not None:
            buffer = self.sourceview.get_buffer()
            self.save_file(buffer, self.file)
            return
        dialog = Gtk.FileChooserNative.new( "Save file", self, Gtk.FileChooserAction.SAVE, None, None)
        dialog.connect("response", dialog_response, dialog)

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

        dialog.show()

    def on_close_action(self, widget, _):
        print("close file")

    def on_compile_action(self, widget, _):
        self.to_compile = True
        self.activate_action("win.save")

    def compile(self):
        def on_compile_finished(sender):
            if sender.result == 0:
                # Compilation was successful
                tex = self.file.get_location().get_path()
                pdf,_  = os.path.splitext(tex)
                self.pdfview.open_file(pdf + ".pdf")
                self.activate_action("win.synctex-fwd", None)
                self.to_compile = False
            else:
                # Compilation failed
                print("Compile failed")

        tex = self.file.get_location().get_path()
        directory = os.path.dirname(tex)
        cmd = ['flatpak-spawn', '--host', '/usr/bin/latexmk', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', '-halt-on-error', '-output-directory=' + directory, tex]
        proc = ProcessRunner(cmd)
        proc.connect('finished', on_compile_finished)

    def create_action(self, name, callback, shortcuts=None):
        """Add a window action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.get_application().set_accels_for_action(f"win.{name}", shortcuts)


class TitleWidget(Gtk.Box):
    __gtype_name__ = "TitleWidget"

    def __init__(self):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_valign(Gtk.Align.CENTER)
        self.title = Gtk.Label()
        self.subtitle = Gtk.Label()
        self.saved = True
        self.set_title_string("New Document")
        self.set_subtitle_string("path")

        self.append(self.title)
        self.append(self.subtitle)


    def set_title_string(self,s):
        self.title_string = s
        if self.saved:
            self.title.set_markup("<b>" + s + "</b>")
        else:
            self.title.set_markup("<it><b>" + s + "</b></it>")

    def set_subtitle_string(self,s):
        self.subtitle_string = s
        self.subtitle.set_markup("<small>" + s + "</small>")

    def set_saved(self,b):
        self.saved = b
        if self.saved:
            self.title.set_markup("<b>" + self.title_string + "</b>")
        else:
            self.title.set_markup("<i><b>" + self.title_string + "</b></i>")

class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self)
        self.props.program_name = 'texwriter'
        self.props.version = "0.1.0"
        self.props.authors = ['András Molnár']
        self.props.copyright = '2022 András Molnár'
        self.props.logo_icon_name = 'com.github.molnarandris.texwriter'
        self.props.modal = True
        self.set_transient_for(parent)
