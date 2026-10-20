#  Hydrogram - Telegram MTProto API Client Library for Python
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
from newbiegram.filters import Filter


class OnError:
    def on_error(self=None, errors=None) -> Callable:
        """Decorator for handling new errors.

        This does the same thing as :meth:`~newbiegram.Client.add_handler` using the
        :obj:`~newbiegram.handlers.MessageHandler`.

        Parameters:
            errors (:obj:`~Exception`, *optional*):
                Pass one or more errors to allow only a subset of errors to be passed
                in your function.
        """

        def decorator(func: Callable) -> Callable:
            if isinstance(self, newbiegram.Client):
                self.add_handler(newbiegram.handlers.ErrorHandler(func, errors), 0)
            elif isinstance(self, Filter) or self is None:
                if not hasattr(func, "handlers"):
                    func.handlers = []

                func.handlers.append((newbiegram.handlers.ErrorHandler(func, self), 0))

            return func

        return decorator
