"""Voice - Neuro Voice Chat API."""

# Programmed by CoolCat467

from __future__ import annotations

# Voice - Neuro Voice Chat API
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

__title__ = "voice"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"


import struct
from abc import abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeAlias, override
from urllib.parse import quote

from neuro_api import voice_commands
from neuro_api.client import AbstractNeuroAPIClient
from neuro_api.command import check_typed_dict

if TYPE_CHECKING:
    from collections.abc import Iterable


def derive_voice_url(base_url: str, game: str) -> str:
    """Return voice endpoint from the main websocket URL and the game name.

    `.../game/<name>` becomes `.../game/<name>/voice`, `.../game` gets
    the game name inserted, and any other path (e.g. a bare host) gets
    `/game/<name>/voice` appended.

    Query parameters (e.g. `?session=`) are kept.
    """
    if not base_url or not game:
        return ""

    # Extract query parameters
    query = ""
    query_index = base_url.find("?")
    if query_index >= 0:
        url, query = base_url[:query_index], base_url[query_index:]
    else:
        url = base_url

    # Remove trailing slashes
    url = url.rstrip("/")
    encoded_game = quote(game, safe="")

    # Determine the path
    game_index = url.rfind("/game/")

    if url.endswith("/game"):
        path = f"{url}/{encoded_game}/voice"
    elif game_index >= 0 and url.find("/", game_index + len("/game/")) < 0:
        # Already .../game/<name>, reuse the existing name segment.
        path = f"{url}/voice"
    else:
        path = f"{url}/game/{encoded_game}/voice"

    return path + query


try:
    import numpy as np

    SampleFormat: TypeAlias = (
        Sequence[float] | np.ndarray[tuple[int], np.dtype[np.float32]]
    )

    def to_wire_format(
        samples: SampleFormat,
        sample_rate: int,
        channels: int,
        wire_sample_rate: int,
    ) -> SampleFormat:
        """Return samples converted to wire format.

        Convert given samples at given sample rate and number of channels to
        mono at given wire sample rate.
        """
        if channels < 1 or sample_rate < 1:
            return np.zeros(0, dtype=np.float32)

        mono: Sequence[float] | np.ndarray[tuple[int], np.dtype[np.float32]]
        if channels > 1:
            frames = len(samples) // channels
            mono = np.zeros(frames, dtype=np.float32)
            for i in range(frames):
                mono[i] = np.mean(samples[i * channels : (i + 1) * channels])
        else:
            mono = samples

        if sample_rate == wire_sample_rate:
            return mono

        out_length = int(len(mono) * wire_sample_rate / sample_rate)
        if out_length <= 0:
            return np.zeros(0, dtype=np.float32)

        resampled = np.zeros(out_length, dtype=np.float32)
        step = sample_rate / wire_sample_rate
        for i in range(out_length):
            pos = i * step
            i0 = int(pos)
            i1 = min(i0 + 1, len(mono) - 1)
            frac = pos - i0
            resampled[i] = mono[i0] + (mono[i1] - mono[i0]) * frac

        return resampled
except ImportError:

    def to_wire_format(
        samples: SampleFormat,
        sample_rate: int,
        channels: int,
        wire_sample_rate: int,
    ) -> SampleFormat:
        """Return samples converted to wire format.

        Convert given samples at given sample rate and number of channels to
        mono at given wire sample rate.
        """
        if channels < 1 or sample_rate < 1:
            return []

        mono = samples
        if channels > 1:
            frames = len(samples) // channels
            mono = [0.0] * frames
            for i in range(frames):
                sum_val = 0.0
                for c in range(channels):
                    sum_val += samples[i * channels + c]
                mono[i] = sum_val / channels

        if sample_rate == wire_sample_rate:
            return mono

        out_length = int(len(mono) * wire_sample_rate / sample_rate)
        if out_length <= 0:
            return []

        resampled = [0.0] * out_length
        step = sample_rate / wire_sample_rate
        for i in range(out_length):
            pos = i * step
            i0 = int(pos)
            i1 = min(i0 + 1, len(mono) - 1)
            frac = pos - i0
            resampled[i] = mono[i0] + (mono[i1] - mono[i0]) * frac

        return resampled


def sample_array_to_bytes(samples: SampleFormat) -> bytes:
    """Return sample array as bytes."""
    return b"".join(struct.pack("<f", sample) for sample in samples)


class AbstractNeuroVoiceAPI(AbstractNeuroAPIClient):
    """Abstract class for interacting with the Neuro voice chat API."""

    __slots__ = ("channels", "game_title", "sample_rate", "server_accepted")

    def __init__(
        self,
        game_title: str,
    ) -> None:
        """Initialize AbstractNeuroVoiceAPI."""
        self.game_title = game_title

        self.sample_rate = 48000
        self.channels = 1

        self.server_accepted = False

    async def send_voice_start_command(self) -> None:
        """Send voice start command.

        Should be sent immediately after socket connection succeeds.
        """
        await self.send_command_data(
            voice_commands.voice_start_command(self.game_title),
        )

    async def send_voice_stop_command(self) -> None:
        """Send voice stop command.

        Ends the voice session but keeps the socket usable for a fresh
        voice/start (leave and rejoin a VC lobby in one play session).
        """
        await self.send_command_data(
            voice_commands.voice_stop_command(self.game_title),
        )

    async def send_voice_speakers_register_command(
        self,
        speakers: Iterable[tuple[int, str]],
    ) -> None:
        """Send voice speaker register command.

        Register or rename speaker id and name pair.

        Args:
            speakers (Iterable[tuple[int, str]]):
                Sequence of tuples of uint16 speaker id and display title strings.
                Speaker id numbers should be chosen by the game and unique per socket.
                Display titles are directly received by Neuro.

        """
        await self.send_command_data(
            voice_commands.voice_speakers_register_command(
                self.game_title,
                speakers,
            ),
        )

    async def send_voice_speakers_unregister_command(
        self,
        ids: Sequence[int],
    ) -> None:
        """Send voice speaker unregister command.

        Removes specified speaker ids (e.g. player has left the lobby)

        Args:
            ids (Sequence[int]): uint16 speaker ids being unregistered

        """
        await self.send_command_data(
            voice_commands.voice_speakers_unregister_command(
                self.game_title,
                ids,
            ),
        )

    @abstractmethod
    async def raw_read_from_websocket(
        self,
    ) -> bytes | bytearray | memoryview | str:
        """Abstract method to read a raw message from the websocket.

        This method must be implemented by subclasses to define
        the specific mechanism for receiving data from a websocket.

        Returns:
            bytes | bytearray | memoryview | str: The message
            received from the websocket, both string control messages and binary raw PCM f32le audio.

        """

    @override
    async def read_from_websocket(self) -> str:
        """Return a control message data from websocket.

        Any received binary messages are sent to `handle_binary_frame`.
        """
        while True:
            frame = await self.raw_read_from_websocket()
            if not isinstance(frame, str):
                await self.handle_pcm_data(frame)
                continue
            return frame

    @override
    @abstractmethod
    async def write_to_websocket(self, data: str | bytes) -> None: ...

    async def send_pcm_voice_data(
        self,
        speaker_id: int,
        samples: bytes | bytearray | memoryview,
    ) -> None:
        """Send PCM samples for given speaker id to server.

        Important: Samples should be headerless mono Float32 PCM at
        `self.sample_rate`, which is 48k kHz on default.

        If your samples are not in this format, do

        >>> sample_array_to_bytes(to_wire_format(your_samples, your_sample_rate, your_channels, self.sample_rate))

        or some other equivalent resampling from your favorite audio
        library.
        """
        protocol_version = 1
        flags = 0
        await self.write_to_websocket(
            struct.pack(
                "BBH",
                protocol_version,
                flags,
                speaker_id,
            )
            + samples,
        )

    async def handle_voice_ready(self) -> None:
        """Handle voice ready."""

    async def handle_voice_unavailable(self, reason: str | None) -> None:
        """Handle voice unavailable.

        Args:
            reason (str | None): Optional reason server says voice is unavailable.

        Note that if server does not support voice this will never be
        called, have a timeout or something after you call
        `self.send_voice_start_command`.

        """

    async def handle_pcm_data(
        self,
        frame: bytes | bytearray | memoryview,
    ) -> None:
        """Handle headerless Float32 little-endian PCM data from Neuro.

        Sample rate is from `self.sample_rate` and number of channels is
        from `self.channels`.

        Should be mono 48k kHz on default.
        """

    async def handle_voice_speaking(self, speaking: bool) -> None:
        """Handle voice speaking state changes.

        Use to key push-to-talk.
        """

    async def handle_voice_cancelled(self) -> None:
        """Handle voice cancelled.

        Neuro's speech was interrupted. Immediately discard any buffered
        downstream audio and release push to talk.

        Default implementation calls `handle_voice_speaking(False)`.
        """
        await self.handle_voice_speaking(False)

    async def read_message(self) -> None:
        """Read message from Neuro voice chat websocket.

        You should call this function in a loop as long as the websocket
        is still connected and `self.server_accepted` is True after
        calling `self.send_voice_start_command`

        Calls ``handle_voice_ready`` for `voice/ready` commands.

        Calls ``handle_voice_unavailable`` for `voice/unavailable` commands.

        Calls ``handle_voice_speaking`` for `voice/speaking` commands.

        Calls ``handle_voice_cancelled`` for `voice/cancelled` commands.

        Calls ``handle_unknown_command`` for any other command.
        """
        # Read message from server
        command_type, data = await self.read_raw_server_message()
        if command_type == "voice/ready":
            assert data is not None
            voice_ready = check_typed_dict(
                data,
                voice_commands.IncomingVoiceReadySchema,
            )

            self.sample_rate = voice_ready["sample_rate"]
            self.channels = voice_ready["channels"]

            self.server_accepted = True

            await self.handle_voice_ready()
        elif command_type == "voice/unavailable":
            assert data is not None

            voice_unavailable = check_typed_dict(
                data,
                voice_commands.IncomingVoiceUnavailableSchema,
            )

            reason = voice_unavailable.get("reason")

            self.server_accepted = False

            await self.handle_voice_unavailable(reason)
        elif command_type == "voice/speaking":
            assert data is not None
            speaking_data = check_typed_dict(
                data,
                voice_commands.IncomingVoiceSpeakingSchema,
            )

            await self.handle_voice_speaking(speaking_data["speaking"])
        elif command_type == "voice/cancelled":
            await self.handle_voice_cancelled()
        else:
            await self.handle_unknown_command(command_type, data)
