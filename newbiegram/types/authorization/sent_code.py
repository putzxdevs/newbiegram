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

from __future__ import annotations

from newbiegram import enums, raw
from newbiegram.types.object import Object


class SentCode(Object):
    """Contains info on a sent confirmation code.

    Parameters:
        type (:obj:`~newbiegram.enums.SentCodeType`):
            Type of the current sent code.

        phone_code_hash (``str``):
            Confirmation code identifier useful for the next authorization steps (either
            :meth:`~newbiegram.Client.sign_in` or :meth:`~newbiegram.Client.sign_up`).

        next_type (:obj:`~newbiegram.enums.NextCodeType`, *optional*):
            Type of the next code to be sent with :meth:`~newbiegram.Client.resend_code`.

        timeout (``int``, *optional*):
            Delay in seconds before calling :meth:`~newbiegram.Client.resend_code`.
    """

    def __init__(
        self,
        *,
        type: enums.SentCodeType,
        phone_code_hash: str,
        next_type: enums.NextCodeType = None,
        timeout: int | None = None,
    ):
        super().__init__()

        self.type = type
        self.phone_code_hash = phone_code_hash
        self.next_type = next_type
        self.timeout = timeout

    @staticmethod
    def _parse(sent_code: raw.types.auth.SentCode) -> SentCode:
        return SentCode(
            type=enums.SentCodeType(type(sent_code.type)),
            phone_code_hash=sent_code.phone_code_hash,
            next_type=enums.NextCodeType(type(sent_code.next_type))
            if sent_code.next_type
            else None,
            timeout=sent_code.timeout,
        )
