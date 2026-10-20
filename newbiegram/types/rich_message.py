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

import newbiegram
from newbiegram import raw, types
from newbiegram.types.object import Object

# Rich button styles (Layer 225+). Resolved to a raw RichButtonStyle.
_RICH_STYLES = {"primary": "bg_primary", "danger": "bg_danger", "success": "bg_success", "link": "link"}


def _build_rich_button_style(
    style: str | raw.types.RichButtonStyle | None,
) -> raw.types.RichButtonStyle | None:
    if style is None:
        return None
    if isinstance(style, raw.types.RichButtonStyle):
        return style
    if not isinstance(style, str):
        raise TypeError("style must be a string ('primary' | 'danger' | 'success' | 'link') or a raw RichButtonStyle.")
    flag = _RICH_STYLES.get(style.lower())
    if flag is None:
        raise ValueError(f"Invalid rich button style {style!r}. Expected one of: {', '.join(_RICH_STYLES)}.")
    return raw.types.RichButtonStyle(**{flag: True})


class RichMessage(Object):
    """A Rich Message (Bot API 10.3 / Layer 225+).

    Rich messages support structured content (blocks), inline buttons, embedded media and rich text —
    a superset of plain text messages. Pass exactly one of ``html``, ``markdown`` or ``blocks``.

    Parameters:
        html (``str``, *optional*):
            HTML source of the rich message. The server parses it into blocks.

        markdown (``str``, *optional*):
            Markdown source of the rich message. The server parses it into blocks.

        blocks (List of :obj:`~newbiegram.raw.base.PageBlock`, *optional*):
            Pre-structured blocks (paragraph, heading, list, table, quotation, etc.). Use the raw
            ``pageBlock*`` constructors directly for full control.

        files (List of :obj:`~newbiegram.raw.base.InputRichFile`, *optional*):
            Media referenced from the HTML/Markdown source by id.

        photos (List of :obj:`~newbiegram.raw.types.InputPhoto`, *optional*):
            Photos referenced from blocks.

        documents (List of :obj:`~newbiegram.raw.types.InputDocument`, *optional*):
            Documents referenced from blocks.

        users (List of ``int`` | ``str`` | :obj:`~newbiegram.raw.types.InputUser`, *optional*):
            Users referenced from blocks (mentions). Int/str ids are resolved to InputUser.

        rtl (``bool``, *optional*):
            Right-to-left layout.

        noautolink (``bool``, *optional*):
            Disable automatic link detection in plain text.
    """

    def __init__(
        self,
        *,
        html: str | None = None,
        markdown: str | None = None,
        blocks: list | None = None,
        files: list | None = None,
        photos: list | None = None,
        documents: list | None = None,
        users: list[int | str | raw.base.InputUser] | None = None,
        rtl: bool | None = None,
        noautolink: bool | None = None,
    ):
        super().__init__()

        modes = [v for v in (html, markdown, blocks) if v is not None]
        if len(modes) != 1:
            raise ValueError("RichMessage requires exactly one of: html, markdown, blocks.")

        self.html = html
        self.markdown = markdown
        self.blocks = blocks
        self.files = files
        self.photos = photos
        self.documents = documents
        self.users = users
        self.rtl = rtl
        self.noautolink = noautolink

    async def write(self, client: newbiegram.Client):
        rtl = self.rtl or None
        noautolink = self.noautolink or None

        if self.html is not None:
            return raw.types.InputRichMessageHTML(
                html=self.html,
                files=self.files or None,
                rtl=rtl,
                noautolink=noautolink,
            )

        if self.markdown is not None:
            return raw.types.InputRichMessageMarkdown(
                markdown=self.markdown,
                files=self.files or None,
                rtl=rtl,
                noautolink=noautolink,
            )

        # blocks mode: resolve users to InputUser
        resolved_users = None
        if self.users:
            resolved_users = [
                u if isinstance(u, raw.base.InputUser) else await client.resolve_peer(u)
                for u in self.users
            ]

        return raw.types.InputRichMessage(
            blocks=self.blocks or [],
            photos=self.photos or None,
            documents=self.documents or None,
            users=resolved_users or None,
            rtl=rtl,
            noautolink=noautolink,
        )


class RichMessageButton(Object):
    """A colored button embedded inside a rich message (Layer 225+).

    Used inside the rich text of a block. Maps to the ``textButton`` constructor: its label is rich text,
    its action is an ``InlineButtonType`` (same set as inline keyboard buttons), and it can be colored via
    ``richButtonStyle`` (primary/danger/success/link).

    Parameters:
        text (``str`` | :obj:`~newbiegram.raw.base.RichText`):
            Button label. A plain string is wrapped in plain text; pass a raw RichText for styled labels.

        callback_data (``str`` | ``bytes``, *optional*):
            Callback payload sent to the bot on press.

        url (``str``, *optional*):
            HTTP URL opened on press.

        web_app (:obj:`~newbiegram.types.WebAppInfo`, *optional*):
            Web App launched on press.

        copy_text (``str``, *optional*):
            Text copied to clipboard on press.

        disabled (``bool``, *optional*):
            Render the button disabled (not tappable).

        login_url (:obj:`~newbiegram.types.LoginUrl`, *optional*):
            Login URL action.

        user_id (``int``, *optional*):
            User profile action.

        style (``str``, *optional*):
            ``"primary"`` | ``"danger"`` | ``"success"`` | ``"link"``.
    """

    def __init__(
        self,
        text: str | raw.base.RichText,
        *,
        callback_data: str | bytes | None = None,
        url: str | None = None,
        web_app: types.WebAppInfo = None,
        copy_text: str | None = None,
        disabled: bool | None = None,
        login_url: types.LoginUrl = None,
        user_id: int | None = None,
        style: str | raw.types.RichButtonStyle | None = None,
    ):
        super().__init__()

        self.text = text
        self.callback_data = callback_data
        self.url = url
        self.web_app = web_app
        self.copy_text = copy_text
        self.disabled = disabled
        self.login_url = login_url
        self.user_id = user_id
        self.style = style

    async def write(self, client: newbiegram.Client) -> raw.types.TextButton:
        # Reuse the high-level inline button to build the correct InlineButtonType for the action,
        # then lift its `type` into a TextButton with a rich-text label.
        inline = await types.InlineKeyboardButton(
            text=str(self.text) if isinstance(self.text, str) else "",
            callback_data=self.callback_data,
            url=self.url,
            web_app=self.web_app,
            copy_text=self.copy_text,
            disabled=self.disabled,
            login_url=self.login_url,
            user_id=self.user_id,
        ).write(client)

        label = (
            self.text
            if not isinstance(self.text, str)
            else raw.types.TextPlain(text=self.text)
        )

        return raw.types.TextButton(
            text=label,
            type=inline.type,
            style=_build_rich_button_style(self.style),
        )
