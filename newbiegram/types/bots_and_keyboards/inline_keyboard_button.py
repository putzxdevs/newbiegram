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

from typing import Any

import newbiegram
from newbiegram import raw, types
from newbiegram.types.object import Object

# Layer 225+ colored button styles. A string here is resolved to the matching
# KeyboardButtonStyle flag; a raw KeyboardButtonStyle object is passed through.
_STYLE_COLORS = {"primary": "bg_primary", "danger": "bg_danger", "success": "bg_success"}


def _build_style(
    style: str | raw.types.KeyboardButtonStyle | None,
    icon: int | None,
) -> raw.types.KeyboardButtonStyle | None:
    """Resolve a high-level style spec into a raw KeyboardButtonStyle constructor."""
    if style is None and icon is None:
        return None

    if isinstance(style, raw.types.KeyboardButtonStyle):
        return style

    kwargs: dict[str, Any] = {}
    if isinstance(style, str):
        flag = _STYLE_COLORS.get(style.lower())
        if flag is None:
            raise ValueError(
                f"Invalid button style {style!r}. Expected one of: {', '.join(_STYLE_COLORS)}."
            )
        kwargs[flag] = True
    elif style is not None:
        raise TypeError(
            "style must be a string ('primary' | 'danger' | 'success') "
            "or a raw.types.KeyboardButtonStyle."
        )

    if icon is not None:
        kwargs["icon"] = icon

    return raw.types.KeyboardButtonStyle(**kwargs) if kwargs else None


class InlineKeyboardButton(Object):
    """One button of an inline keyboard.

    You must use exactly one of the optional fields.

    Parameters:
        text (``str``):
            Label text on the button.

        callback_data (``str`` | ``bytes``, *optional*):
            Data to be sent in a callback query to the bot when button is pressed, 1-64 bytes.

        url (``str``, *optional*):
            HTTP url to be opened when button is pressed.

        web_app (:obj:`~newbiegram.types.WebAppInfo`, *optional*):
            Description of the `Web App <https://core.telegram.org/bots/webapps>`_ that will be launched when the user
            presses the button. The Web App will be able to send an arbitrary message on behalf of the user using the
            method :meth:`~newbiegram.Client.answer_web_app_query`. Available only in private chats between a user and the
            bot.

        login_url (:obj:`~newbiegram.types.LoginUrl`, *optional*):
             An HTTP URL used to automatically authorize the user. Can be used as a replacement for
             the `Telegram Login Widget <https://core.telegram.org/widgets/login>`_.

        user_id (``int``, *optional*):
            User id, for links to the user profile.

        switch_inline_query (``str``, *optional*):
            If set, pressing the button will prompt the user to select one of their chats, open that chat and insert
            the bot's username and the specified inline query in the input field.

        switch_inline_query_current_chat (``str``, *optional*):
            If set, pressing the button will insert the bot's username and the specified inline query in the current
            chat's input field.

        callback_game (:obj:`~newbiegram.types.CallbackGame`, *optional*):
            Description of the game that will be launched when the user presses the button.
            **NOTE**: This type of button **must** always be the first button in the first row.

        copy_text (``str``, *optional*):
            New (Layer 225+). Text that will be copied to the clipboard when the button is pressed.

        disabled (``bool``, *optional*):
            New (Bot API 10.3). When True, the button is rendered disabled (not tappable).

        style (``str`` | :obj:`~newbiegram.raw.types.KeyboardButtonStyle`, *optional*):
            New (Layer 225+). Colored button background. One of ``"primary"`` (dark blue, main actions),
            ``"danger"`` (red, destructive actions), ``"success"`` (green, positive actions).
            Only one color may be set at a time. Pass a raw ``KeyboardButtonStyle`` for full control.

        icon (``int``, *optional*):
            New (Layer 225+). A custom emoji ID to display before the button label. May be used with or without
            a background color. Requires the bot to own custom emoji usernames on Fragment or an active Premium owner.
    """

    def __init__(
        self,
        text: str | Any,
        callback_data: str | bytes | None = None,
        url: str | None = None,
        web_app: types.WebAppInfo = None,
        login_url: types.LoginUrl = None,
        user_id: int | None = None,
        switch_inline_query: str | None = None,
        switch_inline_query_current_chat: str | None = None,
        callback_game: types.CallbackGame = None,
        copy_text: str | None = None,
        disabled: bool | None = None,
        style: str | raw.types.KeyboardButtonStyle | None = None,
        icon: int | None = None,
    ):
        super().__init__()

        self.text = text if isinstance(text, str) else str(text)
        self.callback_data = callback_data
        self.url = url
        self.web_app = web_app
        self.login_url = login_url
        self.user_id = user_id
        self.switch_inline_query = switch_inline_query
        self.switch_inline_query_current_chat = switch_inline_query_current_chat
        self.callback_game = callback_game
        self.copy_text = copy_text
        self.disabled = disabled
        self.style = style
        self.icon = icon

    @staticmethod
    def read(b: raw.types.KeyboardInlineButton):
        # Layer 225+ buttons are polymorphic: the concrete kind lives in b.type.
        raw_style = b.style
        style = raw_style if isinstance(raw_style, raw.types.KeyboardButtonStyle) else None

        t = b.type

        if isinstance(t, raw.types.InlineButtonTypeCallback):
            try:
                data = t.data.decode()
            except UnicodeDecodeError:
                data = t.data
            return InlineKeyboardButton(text=b.text, callback_data=data, style=style)

        if isinstance(t, raw.types.InlineButtonTypeUrl):
            return InlineKeyboardButton(text=b.text, url=t.url, style=style)

        if isinstance(t, raw.types.InlineButtonTypeUrlAuth):
            return InlineKeyboardButton(
                text=b.text,
                login_url=types.LoginUrl(
                    url=t.url, forward_text=t.fwd_text, button_id=t.button_id
                ),
                style=style,
            )

        if isinstance(t, raw.types.InlineButtonTypeUserProfile):
            return InlineKeyboardButton(text=b.text, user_id=t.user_id, style=style)

        if isinstance(t, raw.types.InlineButtonTypeSwitchInline):
            if t.same_peer:
                return InlineKeyboardButton(
                    text=b.text, switch_inline_query_current_chat=t.query, style=style
                )
            return InlineKeyboardButton(text=b.text, switch_inline_query=t.query, style=style)

        if isinstance(t, raw.types.InlineButtonTypeGame):
            return InlineKeyboardButton(text=b.text, callback_game=types.CallbackGame(), style=style)

        if isinstance(t, raw.types.InlineButtonTypeWebView):
            return InlineKeyboardButton(text=b.text, web_app=types.WebAppInfo(url=t.url), style=style)

        if isinstance(t, raw.types.InlineButtonTypeCopy):
            return InlineKeyboardButton(text=b.text, copy_text=t.copy_text, style=style)

        if isinstance(t, raw.types.InlineButtonTypeDisabled):
            return InlineKeyboardButton(text=b.text, disabled=True, style=style)

        return None

    async def write(self, client: newbiegram.Client):
        style = _build_style(self.style, self.icon)

        if self.callback_data is not None:
            # Telegram only wants bytes, but we are allowed to pass strings too, for convenience.
            data = (
                bytes(self.callback_data, "utf-8")
                if isinstance(self.callback_data, str)
                else self.callback_data
            )
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InlineButtonTypeCallback(data=data),
                style=style,
            )

        if self.url is not None:
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InlineButtonTypeUrl(url=self.url),
                style=style,
            )

        if self.login_url is not None:
            bot = await client.resolve_peer(self.login_url.bot_username or "self")
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InputInlineButtonTypeUrlAuth(
                    url=self.login_url.url,
                    fwd_text=self.login_url.forward_text,
                    request_write_access=self.login_url.request_write_access,
                    bot=bot,
                ),
                style=style,
            )

        if self.user_id is not None:
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InputInlineButtonTypeUserProfile(
                    user_id=await client.resolve_peer(self.user_id)
                ),
                style=style,
            )

        if self.switch_inline_query is not None:
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InlineButtonTypeSwitchInline(query=self.switch_inline_query),
                style=style,
            )

        if self.switch_inline_query_current_chat is not None:
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InlineButtonTypeSwitchInline(
                    query=self.switch_inline_query_current_chat,
                    same_peer=True,
                ),
                style=style,
            )

        if self.callback_game is not None:
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InlineButtonTypeGame(),
                style=style,
            )

        if self.web_app is not None:
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InlineButtonTypeWebView(url=self.web_app.url),
                style=style,
            )

        if self.copy_text is not None:
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InlineButtonTypeCopy(copy_text=self.copy_text),
                style=style,
            )

        if self.disabled:
            return raw.types.KeyboardInlineButton(
                text=self.text,
                type=raw.types.InlineButtonTypeDisabled(),
                style=style,
            )

        return None
