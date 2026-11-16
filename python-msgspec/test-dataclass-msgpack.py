# SPDX-License-Identifier: MulanPSL-2.0
# SPDX-FileCopyrightText: (C) 2026 openRuyi Project Contributors

from dataclasses import dataclass

import msgspec


@dataclass
class Addresses:
    inputs: list[str]
    outputs: list[str]
    coordinator: str | None = None


@dataclass
class Handshake:
    addresses: Addresses
    parallel_config: dict[str, int | str | list[int]]


value = Handshake(Addresses(["in"], ["out"]), {"rank": 0, "ranks": [0, 1]})
payload = msgspec.msgpack.encode(value)
assert msgspec.msgpack.decode(payload, type=Handshake) == value
