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

import newbiegram
from newbiegram import enums, raw, types, utils


class SendRichMessage:
    async def send_rich_message(
        self: newbiegram.Client,
        chat_id: int | str,
        rich_message: types.RichMessage,
        *,
        message_thread_id: int | None = None,
        disable_notification: bool | None = None,
        reply_to_message_id: int | None = None,
        schedule_date=None,
        protect_content: bool | None = None,
        reply_markup: types.InlineKeyboardMarkup
        | types.ReplyKeyboardMarkup
        | types.ReplyKeyboardRemove
        | types.ForceReply = None,
    ) -> types.Message | None:
        """Send a rich message (Bot API 10.3 / Layer 225+).

        Rich messages support structured blocks, embedded buttons, media and rich text — a superset of
        plain text messages. Build the rich message with :obj:`~newbiegram.types.RichMessage` (HTML, Markdown
        or structured blocks) and pass it here.

        .. include:: /_includes/usable-by/bots.rst

        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier or username of the target chat.

            rich_message (:obj:`~newbiegram.types.RichMessage`):
                The rich message to send.

            message_thread_id (``int``, *optional*):
                Forum topic identifier.

            disable_notification (``bool``, *optional*):
                Send silently (no sound).

            reply_to_message_id (``int``, *optional*):
                ID of the original message this replies to.

            schedule_date (:py:obj:`~datetime.datetime`, *optional*):
                When the message will be auto-sent.

            protect_content (``bool``, *optional*):
                Protect from forwarding/saving.

            reply_markup (..., *optional*):
                Inline keyboard, custom reply keyboard, reply keyboard remove or force reply.

        Returns:
            :obj:`~newbiegram.types.Message` | ``None``: The sent message on success.

        Example:
            .. code-block:: python

                from newbiegram import types

                rich = types.RichMessage(html="<b>Hello</b> from a rich message!")
                await app.send_rich_message(chat_id, rich)
        """

        reply_to = utils.get_reply_head_fm(message_thread_id, reply_to_message_id)

        r = await self.invoke(
            raw.functions.messages.SendMessage(
                peer=await self.resolve_peer(chat_id),
                no_webpage=True,
                silent=disable_notification or None,
                reply_to=reply_to,
                random_id=self.rnd_id(),
                schedule_date=utils.datetime_to_timestamp(schedule_date),
                reply_markup=await reply_markup.write(self) if reply_markup else None,
                message="",
                rich_message=await rich_message.write(self),
                noforwards=protect_content,
            )
        )

        if isinstance(r, raw.types.UpdateShortSentMessage):
            peer = await self.resolve_peer(chat_id)
            peer_id = peer.user_id if isinstance(peer, raw.types.InputPeerUser) else -peer.chat_id

            return types.Message(
                id=r.id,
                chat=types.Chat(id=peer_id, type=enums.ChatType.PRIVATE, client=self),
                text="",
                date=utils.timestamp_to_datetime(r.date),
                outgoing=r.out,
                reply_markup=reply_markup,
                client=self,
            )

        for i in r.updates:
            if isinstance(
                i,
                (
                    raw.types.UpdateNewMessage,
                    raw.types.UpdateNewChannelMessage,
                    raw.types.UpdateNewScheduledMessage,
                ),
            ):
                return await types.Message._parse(
                    client=self,
                    message=i.message,
                    users={u.id: u for u in r.users},
                    chats={c.id: c for c in r.chats},
                    is_scheduled=isinstance(i, raw.types.UpdateNewScheduledMessage),
                )
        return None
