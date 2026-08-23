"""Structured run-progress markers for the octopus CLI.

The pentest pipeline streams loguru lines to stdout; the CLI can't reliably turn those into a
phase tree. So we also emit tiny machine-readable markers on their own lines:

    ##OCTO## <kind>|<k=v>|<k=v>

The CLI (cli/src/ui/Repl.tsx) parses these into a live phase/step view and filters them out of the
visible log tail. Emission is BEST-EFFORT: any failure here must never affect a pentest run.

Markers carry phase/step/task boundaries, the agent's BELIEF information-state (the POMDP posterior
over the hidden state S — legitimately shown to the user, the thesis point), the policy decision, and
transient LLM-wait status. They NEVER carry the hidden true state S itself.
"""
import sys

_PREFIX = "##OCTO##"


def _clean(v) -> str:
    # Keep markers single-line and delimiter-safe.
    return str(v).replace("|", "/").replace("\n", " ").replace("\r", " ").strip()


def emit(kind: str, **fields) -> None:
    try:
        parts = [_PREFIX, _clean(kind)]
        for k, v in fields.items():
            parts.append(f"{k}={_clean(v)}")
        sys.stdout.write("|".join(parts) + "\n")
        sys.stdout.flush()
    except Exception:
        pass
