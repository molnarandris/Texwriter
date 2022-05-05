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

import gi
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, GObject, GtkSource, Gio


@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    GObject.type_register(GtkSource.View)
    paned = Gtk.Template.Child()

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
