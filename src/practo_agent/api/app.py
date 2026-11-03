"""FastAPI interface for session-based Practo support conversations."""

from typing import Annotated

from fastapi import FastAPI, Path, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from starlette.concurrency import run_in_threadpool

from practo_agent.memory import ConversationMemory
from practo_agent.schemas import AgentResponse


QueryText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100_000),
]
SessionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]


class QueryPayload(BaseModel):
    """Validated request body shared by HTTP and WebSocket requests."""

    model_config = ConfigDict(extra="forbid")

    query: QueryText


class QueryRequest(QueryPayload):
    """HTTP request body with an explicit conversation session."""

    session_id: SessionId


class SessionRequest(BaseModel):
    """Validated WebSocket session identifier."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId


class HealthResponse(BaseModel):
    """Liveness response for the API process."""

    status: str = Field(pattern="^ok$")


def create_app(
    conversations: ConversationMemory | None = None,
) -> FastAPI:
    """Create the API and its process-local conversation manager."""

    app = FastAPI(
        title="Practo Healthcare Support API",
        description=(
            "Administrative support through structured HTTP and "
            "session-based WebSocket conversations."
        ),
    )
    app.state.conversations = (
        conversations if conversations is not None else ConversationMemory()
    )

    @app.get("/health", response_model=HealthResponse)
    def health_check() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/query", response_model=AgentResponse)
    def query(request: QueryRequest) -> AgentResponse:
        return app.state.conversations.run_turn(
            request.query,
            session_id=request.session_id,
        )

    @app.websocket("/ws/{session_id}")
    async def conversation_socket(
        websocket: WebSocket,
        session_id: Annotated[str, Path()],
    ) -> None:
        try:
            validated_session = SessionRequest(session_id=session_id)
        except ValidationError:
            await websocket.accept()
            await websocket.send_json(
                {
                    "error": {
                        "code": "invalid_session",
                        "message": "Session ID must contain 1 to 128 characters.",
                    }
                }
            )
            await websocket.close(code=1008)
            return

        await websocket.accept()
        while True:
            try:
                message = await websocket.receive_text()
            except WebSocketDisconnect:
                return

            try:
                request = QueryPayload.model_validate_json(message)
            except ValidationError:
                await websocket.send_json(
                    {
                        "error": {
                            "code": "invalid_request",
                            "message": (
                                "Send a JSON object with a non-empty "
                                "query string."
                            ),
                        }
                    }
                )
                continue

            response = await run_in_threadpool(
                app.state.conversations.run_turn,
                request.query,
                session_id=validated_session.session_id,
            )
            await websocket.send_json(response.model_dump(mode="json"))

    return app


app = create_app()
