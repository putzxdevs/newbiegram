#  Hydrogram - Telegram MTProto API Client Library for Python
#  Copyright (C) 2017-2023 Dan <https://github.com/delivrance>
#  Copyright (C) 2023-present Hydrogram <https://github.com/putzxdevs/newbiegram>
#
#  This file is part of Hydrogram.
#
#  Hydrogram is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Hydrogram is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with Hydrogram.  If not, see <http://www.gnu.org/licenses/>.

from collections.abc import Callable

import newbiegram


class OnRawUpdate:
    def on_raw_update(self=None, group: int = 0) -> Callable:
        """Decorator for handling raw updates.

        This does the same thing as :meth:`~newbiegram.Client.add_handler` using the
        :obj:`~newbiegram.handlers.RawUpdateHandler`.

        Parameters:
            group (``int``, *optional*):
                The group identifier, defaults to 0.
        """

        def decorator(func: Callable) -> Callable:
            if isinstance(self, newbiegram.Client):
                self.add_handler(newbiegram.handlers.RawUpdateHandler(func), group)
            else:
                if not hasattr(func, "handlers"):
                    func.handlers = []

                func.handlers.append((newbiegram.handlers.RawUpdateHandler(func), group))

            return func

        return decorator
