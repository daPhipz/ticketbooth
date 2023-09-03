# Copyright (C) 2023 Alessandro Iepure
#
# SPDX-License-Identifier: GPL-3.0-or-later

import glob
import os
from gettext import gettext as _

from gi.repository import Adw, Gio, GLib, Gtk

from . import shared  # type: ignore
from .dialogs.add_manual_dialog import AddManualDialog
from .dialogs.add_tmdb_dialog import AddTMDBDialog
from .views.first_run_view import FirstRunView
from .views.main_view import MainView


@Gtk.Template(resource_path=shared.PREFIX + '/ui/window.ui')
class TicketboothWindow(Adw.ApplicationWindow):
    """
    This class reppresents the main application window.

    Properties:
        None

    Methods:
        None

    Signals:
        None
    """

    __gtype_name__ = 'TicketboothWindow'

    _win_stack = Gtk.Template.Child()

    def _sort_on_changed(self, new_state: str, source: Gtk.Widget) -> None:
        """
        Callback for the win.view-sorting action

        Args:
            new_state (str): new selected state
            source (Gtk.Widget): widget that caused the activation

        Returns:
            None
        """

        self.set_state(new_state)
        shared.schema.set_string('view-sorting', str(new_state)[1:-1])

    def _add_tmdb(self, new_state: None, source: Gtk.Widget) -> None:
        """
        Callback for the win.add-tmdb action

        Args:
            new_state (None): stateless action, always None
            source (Gtk.Widget): widget that caused the activation

        Returns:
            None
        """

        dialog = AddTMDBDialog(source)
        dialog.present()

    def _add_manual(self, new_state: None, source: Gtk.Widget) -> None:
        """
        Callback for the win.add-manual action

        Args:
            new_state (None): stateless action, always None
            source (Gtk.Widget): widget that caused the activation

        Returns:
            None
        """

        dialog = AddManualDialog(source)
        dialog.present()

    def _refresh(self, new_state: None, source: Gtk.Widget) -> None:
        """
        Callback for the win.refresh action

        Args:
            new_state (None): stateless action, always None
            source (Gtk.Widget): widget that caused the activation

        Returns:
            None
        """

        source._win_stack.get_child_by_name('main').refresh()

    _actions = {
        ('view-sorting', None, 's', f"'{shared.schema.get_string('view-sorting')}'", _sort_on_changed),
        ('add-tmdb', _add_tmdb),
        ('add-manual', _add_manual),
        ('refresh', _refresh),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_action_entries(self._actions, self)
        self._restore_state()

        if shared.DEBUG:
            self.add_css_class('devel')

        shared.schema.bind('offline-mode', self.lookup_action('add-tmdb'),
                           'enabled', Gio.SettingsBindFlags.INVERT_BOOLEAN)
        Gio.NetworkMonitor.get_default().connect('network-changed', self._on_network_changed)

    @Gtk.Template.Callback('_on_close_request')
    def _on_close_request(self, user_data: object | None) -> bool:
        """
        Callback for "close-request" signal.
        Checks for background activities to prevent quiting and corruption, deletes cached data if enabled in settings.

        Args:
            user_data (object or None): additional data passed to the callback

        Returns:
            True to block quiting, Flase to allow it
        """

        # Background activities
        if self._win_stack.get_child_by_name('main').is_spinner_visible():
            dialog = Adw.MessageDialog.new(self, _('Background Activies Running'),
                                           _('There are some activities running in the background that need to be completed before exiting. A spinning indicator in the headerbar is visible while they are running.'))
            dialog.add_response('ok', _('Ok'))
            dialog.show()
            return True

        # Cache
        if shared.schema.get_boolean('exit-remove-cache'):
            files = glob.glob('*.jpg', root_dir=shared.cache_dir)
            for file in files:
                os.remove(shared.cache_dir / file)

        return False

    @Gtk.Template.Callback('_on_map')
    def _on_map(self, widget: Gtk.Widget) -> None:
        """
        Callback for the "map" signal. Determines what view to show on startup.

        Args:
            widget (Gtk.Widget): the object which received the signal

        Returns:
            None
        """

        if not shared.schema.get_boolean('first-run'):
            self._win_stack.add_named(child=MainView(), name='main')
            self._win_stack.set_visible_child_name('main')
            return

        self.first_run_view = FirstRunView()
        self._win_stack.add_named(child=self.first_run_view, name='first-run')
        self._win_stack.set_visible_child_name('first-run')
        self.first_run_view.connect('exit', self._on_first_run_exit)

    def _on_network_changed(self, network_monitor: Gio.NetworkMonitor, network_available: bool) -> None:
        """
        Callback for "network-changed" signal.
        If no network is available, it turns on offline mode.

        Args:
            network_monitor (Gio.NetworkMonitor): the NetworkMonitor in use
            network_available (bool): whether or not the network is available

        Returns:
            None
        """

        shared.schema.set_boolean('offline-mode', GLib.Variant.new_boolean(not network_available))

    def _on_first_run_exit(self, source: Gtk.Widget) -> None:
        """
        Callback for the "exit" signal. Changes the visible view.

        Args:
            None

        Returns:
            None
        """

        self._win_stack.add_named(child=MainView(), name='main')
        self._win_stack.set_visible_child_name('main')

    def _restore_state(self) -> None:
        """
        Restores the last known state of the window between runs.

        Args:
            None

        Returns:
            None
        """

        shared.schema.bind('win-width', self, 'default-width', Gio.SettingsBindFlags.DEFAULT)
        shared.schema.bind('win-height', self, 'default-height', Gio.SettingsBindFlags.DEFAULT)
        shared.schema.bind('win-maximized', self, 'maximized', Gio.SettingsBindFlags.DEFAULT)
