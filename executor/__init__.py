"""Multi-channel Kali execution layer (R3).

`Executor.run(action) -> Observation` behind one interface; each channel (SSH / msfrpc /
flag-gated MCP) is a pluggable `Channel` adapter, chosen by a router. See `docs/EXECUTOR.md`.
Offensive tooling lives only in the Kali container; this package is a router/normalizer and
holds no exploits.
"""
from executor.base import Channel, Executor, ChannelError

__all__ = ["Channel", "Executor", "ChannelError"]
