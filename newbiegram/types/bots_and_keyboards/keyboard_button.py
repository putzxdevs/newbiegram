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

from __future__ import annotations

from typing import Any

from newbiegram import raw, types
from newbiegram.types.bots_and_keyboards.inline_keyboard_button import _build_style
from newbiegram.types.object import Object


class KeyboardButton(Object):
    """One button of the reply keyboard.
    For simple text buttons String can be used instead of this object to specify text of the button.
    Optional fields are mutually exclusive.

    Parameters:
        text (``str``):
            Text of the button. If none of the optional fields are used, it will be sent as a message when
            the button is pressed.

        request_contact (``bool``, *optional*):
            If True, the user's phone number will be sent as a contact when the button is pressed.
            Available in private chats only.

        request_location (``bool``, *optional*):
            If True, the user's current location will be sent when the button is pressed.
            Available in private chats only.

        request_poll (``bool`` | ``str``, *optional*):
            If True, the user will be asked to create a poll and send it to the bot. Pass ``"quiz"`` to
            request a quiz poll. Available in private chats only.

        web_app (:obj:`~newbiegram.types.WebAppInfo`, *optional*):
            If specified, the described `Web App <https://core.telegram.org/bots/webapps>`_ will be launched when the
            button is pressed. The Web App will be able to send a "web_app_data" service message. Available in private
            chats only.

        style (``str`` | :obj:`~newbiegram.raw.types.KeyboardButtonStyle`, *optional*):
            New (Layer 225+). Colored button background: ``"primary"`` | ``"danger"`` | ``"success"``.

        icon (``int``, *optional*):
            New (Layer 225+). Custom emoji ID to display before the label.
    """

    def __init__(
        self,
        text: str | Any,
        request_contact: bool | None = None,
        request_location: bool | None = None,
        request_poll: bool | str | None = None,
        web_app: types.WebAppInfo = None,
        style: str | raw.types.KeyboardButtonStyle | None = None,
        icon: int | None = None,
    ):
        super().__init__()

        self.text = text if isinstance(text, str) else str(text)
        self.request_contact = request_contact
        self.request_location = request_location
        self.request_poll = request_poll
        self.web_app = web_app
        self.style = style
        self.icon = icon

    @staticmethod
    def read(b: raw.types.KeyboardButton):
        # Layer 225+ buttons are polymorphic: the concrete kind lives in b.type.
        raw_style = b.style
        style = raw_style if isinstance(raw_style, raw.types.KeyboardButtonStyle) else None
        t = b.type

        if isinstance(t, raw.types.ButtonTypeRequestPhone):
            return KeyboardButton(text=b.text, request_contact=True, style=style)

        if isinstance(t, raw.types.ButtonTypeRequestGeoLocation):
            return KeyboardButton(text=b.text, request_location=True, style=style)

        if isinstance(t, raw.types.ButtonTypeRequestPoll):
            return KeyboardButton(
                text=b.text,
                request_poll="quiz" if getattr(t, "quiz", None) is True else True,
                style=style,
            )

        if isinstance(t, raw.types.ButtonTypeSimpleWebView):
            return KeyboardButton(text=b.text, web_app=types.WebAppInfo(url=t.url), style=style)

        # ButtonTypeDefault (plain text button) and anything else
        return KeyboardButton(text=b.text, style=style)

    def write(self):
        style = _build_style(self.style, self.icon)

        if self.request_contact:
            button_type = raw.types.ButtonTypeRequestPhone()
        elif self.request_location:
            button_type = raw.types.ButtonTypeRequestGeoLocation()
        elif self.request_poll is not None:
            button_type = raw.types.ButtonTypeRequestPoll(
                quiz=True if str(self.request_poll).lower() == "quiz" else None
            )
        elif self.web_app:
            button_type = raw.types.ButtonTypeSimpleWebView(url=self.web_app.url)
        else:
            button_type = raw.types.ButtonTypeDefault()

        return raw.types.KeyboardButton(text=self.text, type=button_type, style=style)
