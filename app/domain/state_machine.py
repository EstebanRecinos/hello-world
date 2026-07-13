"""Explicit state machine for the payload manifest lifecycle.

The manifest is the central domain object: it travels intact through every
stage and, in future phases, will extend to physical custody and orbital
transfer. All lifecycle rules live in this single transition table — never
in scattered ifs.
"""

from enum import StrEnum


class ManifestState(StrEnum):
    DRAFT = "draft"
    QUOTED = "quoted"
    BOOKED = "booked"
    INTEGRATED = "integrated"
    LAUNCHED = "launched"
    DEPLOYED = "deployed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


# QUOTED -> QUOTED allows re-quoting against a different launch window before
# booking. CANCELLED is reachable from every state prior to INTEGRATED: once a
# payload is physically integrated into the vehicle there is no unilateral
# cancellation.
TRANSITIONS: dict[ManifestState, frozenset[ManifestState]] = {
    ManifestState.DRAFT: frozenset({ManifestState.QUOTED, ManifestState.CANCELLED}),
    ManifestState.QUOTED: frozenset(
        {ManifestState.QUOTED, ManifestState.BOOKED, ManifestState.CANCELLED}
    ),
    ManifestState.BOOKED: frozenset({ManifestState.INTEGRATED, ManifestState.CANCELLED}),
    ManifestState.INTEGRATED: frozenset({ManifestState.LAUNCHED}),
    ManifestState.LAUNCHED: frozenset({ManifestState.DEPLOYED}),
    ManifestState.DEPLOYED: frozenset({ManifestState.CLOSED}),
    ManifestState.CLOSED: frozenset(),
    ManifestState.CANCELLED: frozenset(),
}

TERMINAL_STATES = frozenset({ManifestState.CLOSED, ManifestState.CANCELLED})


class InvalidTransitionError(Exception):
    def __init__(self, from_state: ManifestState, to_state: ManifestState) -> None:
        self.from_state = from_state
        self.to_state = to_state
        allowed = sorted(TRANSITIONS[from_state])
        super().__init__(
            f"Invalid manifest transition {from_state.value!r} -> {to_state.value!r}; "
            f"allowed from {from_state.value!r}: {[s.value for s in allowed] or 'none (terminal state)'}"
        )


def validate_transition(from_state: ManifestState, to_state: ManifestState) -> None:
    """Raise InvalidTransitionError unless from_state -> to_state is allowed."""
    if to_state not in TRANSITIONS[from_state]:
        raise InvalidTransitionError(from_state, to_state)
