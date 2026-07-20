# Copyright (C) 2026 Meld authors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from gi.repository import GObject


class ReviewComments(GObject.GObject):
    """In-RAM store of code-review comments, keyed by file and line.

    Comments live only for the lifetime of the process and are shared
    across every comparison tab, so the whole review can be copied to the
    clipboard at once. Line numbers are 1-based and captured at the moment
    the comment is made.
    """

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__()
        # Absolute directory roots used to derive relative paths.
        self.roots = []
        # abspath -> {line: text}
        self._by_file = {}

    def set_roots(self, roots):
        self.roots = [
            os.path.abspath(r) for r in roots if r
        ]

    def relpath(self, abspath):
        """Path relative to the first matching registered root.

        Falls back to the basename when the file is under no known root.
        """
        for root in self.roots:
            try:
                if os.path.commonpath([root, abspath]) == root:
                    return os.path.relpath(abspath, root)
            except ValueError:
                # Paths on different drives (Windows) can't be compared
                continue
        return os.path.basename(abspath)

    def set_comment(self, abspath, line, text):
        text = (text or '').strip()
        if not text:
            self._delete(abspath, line)
            return
        self._by_file.setdefault(abspath, {})[line] = text
        self.emit('changed')

    def _delete(self, abspath, line):
        lines = self._by_file.get(abspath)
        if not lines or line not in lines:
            return
        del lines[line]
        if not lines:
            del self._by_file[abspath]
        self.emit('changed')

    def get_comment(self, abspath, line):
        return self._by_file.get(abspath, {}).get(line, '')

    def lines_for(self, abspath):
        return set(self._by_file.get(abspath, {}).keys())

    def count(self):
        return sum(len(lines) for lines in self._by_file.values())

    def clear(self):
        if not self._by_file:
            return
        self._by_file = {}
        self.emit('changed')

    def as_text(self):
        """Render every comment as ``relative/path:line: text`` lines.

        Sorted by relative path then line number, one comment per line.
        """
        entries = []
        for abspath, lines in self._by_file.items():
            relpath = self.relpath(abspath)
            for line, text in lines.items():
                # Keep each comment on a single output line.
                oneline = ' '.join(text.split())
                entries.append((relpath, line, oneline))
        entries.sort(key=lambda e: (e[0], e[1]))
        return '\n'.join(
            '{}:{}: {}'.format(relpath, line, text)
            for relpath, line, text in entries
        )


# Process-wide singleton shared by every comparison tab and the main window.
review_comments = ReviewComments()
