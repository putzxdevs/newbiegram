#  NewbieGram - Telegram MTProto API Client Library for Python
#  Copyright (C) 2020-present Cezar H. <https://github.com/usernein>
#  Copyright (C) 2023-present NewbieGram contributors <https://github.com/putzxdevs/newbiegram>
#
#  This file is part of NewbieGram, a fork of Hydrogram.
#
#  NewbieGram is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  NewbieGram is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with Hydrogram.  If not, see <http://www.gnu.org/licenses/>.

from asyncio import Future
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .identifier import Identifier
from .listener_types import ListenerTypes

if TYPE_CHECKING:
    import newbiegram


@dataclass
class Listener:
    listener_type: ListenerTypes
    filters: "newbiegram.filters.Filter"
    unallowed_click_alert: bool
    identifier: Identifier
    future: Future = None
    callback: Callable = None
