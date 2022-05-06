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

import os
import gi
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, GObject, GtkSource, Gio, GLib


@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    GObject.type_register(GtkSource.View)
    paned        = Gtk.Template.Child()
    sourceview   = Gtk.Template.Child()
    header_bar   = Gtk.Template.Child()

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
        ]

        for a in actions: self.create_action(*a)

        manager = GtkSource.LanguageManager()
        language = manager.get_language("latex")
        self.sourceview.get_buffer().set_language(language)

        self.file = None
        self.title = Gtk.Label(label = "Texwriter rocks")
        self.header_bar.set_title_widget(self.title)

    def open_file(self,file):

        def load_finish_cb(loader, result):
            success = loader.load_finish(result)
            path = loader.get_location().get_path()
            if success:
                self.file = file # when we call this fcn, file is the right thing
                print(self.file)
                self.title.set_label(path)
            else:
                print("Could not load file: " + path)
            return success

        buffer = self.sourceview.get_buffer()
        loader = GtkSource.FileLoader.new(buffer, file)
        loader.load_async(io_priority=GLib.PRIORITY_DEFAULT, callback = load_finish_cb)
        path, _ = os.path.splitext(file.get_location().get_path())
        path = path + '.pdf'
        #self.pdfview.open_file(path)


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
            print(path)
            if success:
                pass
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
        print("compiling")

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
