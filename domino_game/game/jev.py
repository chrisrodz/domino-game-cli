"""Bounded Jev move selection through the official TypeSafe SDK."""

from typesafe_sdk import (
    RetryPolicy,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPIResponseValidationError,
    TypeSafeClient,
    TypeSafeError,
)

from domino_game.game.move_evaluation import JudgmentError, MoveDecision, build_questions, certain_move, select_move
from domino_game.game.observation import TurnObservation


class AIConfigurationError(RuntimeError):
    """Jev cannot run with the supplied credentials or request configuration."""


class JevUnavailableError(RuntimeError):
    """A turn may safely continue with the local strategy."""


class JevStrategy:
    def __init__(self, client: TypeSafeClient):
        self.client = client
        self.last_decision: MoveDecision | None = None

    @classmethod
    def from_environment(cls) -> JevStrategy:
        try:
            client = TypeSafeClient(timeout=2.0, retry=RetryPolicy(max_retries=0, timeout=2.0))
        except TypeSafeError:
            raise AIConfigurationError("Medium and Hard require a valid TYPESAFE_API_KEY environment variable.") from None
        return cls(client)

    def choose_move(self, observation: TurnObservation) -> str:
        self.last_decision = None
        certain = certain_move(observation)
        if certain is not None:
            return certain
        plan = build_questions(observation)
        try:
            response = self.client.system_one(
                state=observation.state,
                questions=plan.questions,
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
        try:
            self.last_decision = select_move(observation, plan, response)
        except JudgmentError:
            raise JevUnavailableError("Jev returned missing or invalid tactical judgments") from None
        return self.last_decision.move_id

    def close(self) -> None:
        self.client.close()
