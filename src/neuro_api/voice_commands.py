"""Voice Commands - Neuro API voice chat control commands."""

# Programmed by CoolCat467

from __future__ import annotations

# Voice Commands - Neuro API voice chat control commands
# Copyright (C) 2026  CoolCat467
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__title__ = "voice_commands"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"


from typing import TYPE_CHECKING, NotRequired, TypedDict

from neuro_api.command import format_command

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def voice_start_command(game: str) -> bytes:
    """Return formatted voice/start command.

    Client to Server command.

    Should be sent immediately after socket connection succeeds.

    Args:
        game (str): Game title to initialize voice chat for.

    """
    return format_command("voice/start", game)


def voice_speakers_register_command(
    game: str,
    speakers: Iterable[tuple[int, str]],
) -> bytes:
    """Return formatted voice/speakers/register command.

    Client to Server command.

    Register or rename speaker id and name pair.

    Args:
        game (str): Game title speakers are being registered for
        speakers (Iterable[tuple[int, str]]):
            Sequence of tuples of uint16 speaker id and display title strings.
            Speaker id numbers should be chosen by the game and unique per socket.
            Display titles are directly received by Neuro.

    """
    return format_command(
        "voice/speakers/register",
        game,
        {
            "speakers": [
                {"id": id_ & 0xFFFF, "name": name} for id_, name in speakers
            ],
        },
    )


def voice_speakers_unregister_command(
    game: str,
    ids: Sequence[int],
) -> bytes:
    """Return formatted voice/speakers/unregister command.

    Client to Server command.

    Removes specified speaker ids (e.g. player has left the lobby)

    Args:
        game (str): Game title speakers are being unregistered for
        ids (Sequence[int]): uint16 speaker ids being unregistered

    """
    return format_command(
        "voice/speakers/unregister",
        game,
        {
            "ids": ids,
        },
    )


def voice_stop_command(game: str) -> bytes:
    """Return formatted voice/stop command.

    Client to Server command.

    Ends the voice session but keeps the socket usable for a fresh
    voice/start (leave and rejoin a VC lobby in one play session).

    Closing the socket also ends the session.
    """
    return format_command("voice/stop", game)


class IncomingVoiceReadySchema(TypedDict):
    """Schema for incoming `voice/ready` commands.

    Attributes:
        sample_rate (int): Sample rate for voice data
        channels (int): Number of audio channels

    """

    sample_rate: int
    channels: int


class IncomingVoiceUnavailableSchema(TypedDict):
    """Schema for incoming `voice/unavailable` commands.

    Attributes:
        reason (str): Optional reason why voice is unavailable.

    """

    reason: NotRequired[str]


class IncomingVoiceSpeakingSchema(TypedDict):
    """Schema for incoming `voice/speaking` commands.

    Attributes:
        speaking (bool): Neuro speech status for push to talk.

    """

    speaking: bool
