import pytest

from app.domain.state_machine import (
    TRANSITIONS,
    InvalidTransitionError,
    ManifestState,
    validate_transition,
)

HAPPY_PATH = [
    (ManifestState.DRAFT, ManifestState.QUOTED),
    (ManifestState.QUOTED, ManifestState.BOOKED),
    (ManifestState.BOOKED, ManifestState.INTEGRATED),
    (ManifestState.INTEGRATED, ManifestState.LAUNCHED),
    (ManifestState.LAUNCHED, ManifestState.DEPLOYED),
    (ManifestState.DEPLOYED, ManifestState.CLOSED),
]


@pytest.mark.parametrize("from_state,to_state", HAPPY_PATH)
def test_happy_path_transitions_are_valid(from_state, to_state):
    validate_transition(from_state, to_state)  # must not raise


def test_requote_is_allowed():
    validate_transition(ManifestState.QUOTED, ManifestState.QUOTED)


@pytest.mark.parametrize(
    "from_state",
    [ManifestState.DRAFT, ManifestState.QUOTED, ManifestState.BOOKED],
)
def test_cancel_allowed_before_integration(from_state):
    validate_transition(from_state, ManifestState.CANCELLED)


@pytest.mark.parametrize(
    "from_state",
    [
        ManifestState.INTEGRATED,
        ManifestState.LAUNCHED,
        ManifestState.DEPLOYED,
        ManifestState.CLOSED,
        ManifestState.CANCELLED,
    ],
)
def test_cancel_rejected_from_integration_onwards(from_state):
    with pytest.raises(InvalidTransitionError):
        validate_transition(from_state, ManifestState.CANCELLED)


@pytest.mark.parametrize(
    "from_state,to_state",
    [
        (ManifestState.DRAFT, ManifestState.BOOKED),  # cannot skip quoting
        (ManifestState.DRAFT, ManifestState.LAUNCHED),
        (ManifestState.QUOTED, ManifestState.INTEGRATED),
        (ManifestState.BOOKED, ManifestState.LAUNCHED),  # cannot skip integration
        (ManifestState.LAUNCHED, ManifestState.BOOKED),  # no going backwards
        (ManifestState.CLOSED, ManifestState.DRAFT),
        (ManifestState.CANCELLED, ManifestState.QUOTED),
    ],
)
def test_invalid_transitions_raise_explicit_error(from_state, to_state):
    with pytest.raises(InvalidTransitionError) as exc_info:
        validate_transition(from_state, to_state)
    assert from_state.value in str(exc_info.value)
    assert to_state.value in str(exc_info.value)


def test_terminal_states_have_no_exits():
    assert TRANSITIONS[ManifestState.CLOSED] == frozenset()
    assert TRANSITIONS[ManifestState.CANCELLED] == frozenset()


def test_every_state_appears_in_transition_table():
    assert set(TRANSITIONS) == set(ManifestState)
