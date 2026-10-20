#  NewbieGram - Telegram MTProto API Client Library for Python
#  Copyright (C) 2017-2023 Dan <https://github.com/delivrance>
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

from .object import Object


class List(list):
    __slots__ = []

    def __str__(self):
        return Object.__str__(self)

    def __repr__(self):
        return f"newbiegram.types.List([{','.join(Object.__repr__(i) for i in self)}])"
