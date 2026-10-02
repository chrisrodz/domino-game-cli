"""Bounded Jev move selection through the official TypeSafe SDK."""

from typesafe_sdk import (
    Choice,
    RetryPolicy,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPIResponseValidationError,
    TypeSafeClient,
    TypeSafeError,
)

from domino_game.game.observation import TurnObservation


class AIConfigurationError(RuntimeError):
    """Jev cannot run with the supplied credentials or request configuration."""


class JevUnavailableError(RuntimeError):
    """A turn may safely continue with the local strategy."""


class JevStrategy:
    def __init__(self, client: TypeSafeClient):
        self.client = client

    @classmethod
    def from_environment(cls) -> JevStrategy:
        try:
            client = TypeSafeClient(timeout=2.0, retry=RetryPolicy(max_retries=0, timeout=2.0))
        except TypeSafeError:
            raise AIConfigurationError("Medium and Hard require a valid TYPESAFE_API_KEY environment variable.") from None
        return cls(client)

    def choose_move(self, observation: TurnObservation) -> str:
        criteria = {candidate.move_id: candidate.to_option() for candidate in observation.candidates}
        try:
            response = self.client.system_one(
                state=observation.state,
                questions={
                    "move": Choice(
                        instructions=(
                            "Which supplied legal move best advances the acting player's team toward winning this round "
                            "and match under `rules`? Weigh going out, partner support, opponent pressure, remaining "
                            "hand connections and pip exposure. Use the exact resulting ends and hand facts in each "
                            "option. Other players' tiles are unknown. If public history is supplied, use it as evidence; "
                            "pass deductions apply only in the current round. Playable tiles after this move describe "
                            "the immediate board, not a guarantee about the player's next turn. Select one option."
                        ),
                        criteria=criteria,
                    )
                },
            )
        except TypeSafeAPIConnectionError:
            raise JevUnavailableError("Jev could not connect or timed out") from None
        except TypeSafeAPIResponseValidationError:
            raise JevUnavailableError("Jev returned an invalid response") from None
        except TypeSafeAPIError as error:
            if error.status in (400, 401, 403, 404, 422):
                raise AIConfigurationError(
                    f"Jev rejected the request (HTTP {error.status}). Check TYPESAFE_API_KEY and TypeSafe model configuration."
                ) from None
            raise JevUnavailableError(f"Jev is unavailable (HTTP {error.status})") from None
        answer = response.choices.get("move")
        if answer is None or answer.choice not in criteria:
            raise JevUnavailableError("Jev did not select one of the supplied legal moves")
        return answer.choice

    def close(self) -> None:
        self.client.close()
