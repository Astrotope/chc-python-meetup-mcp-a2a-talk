"""
Chess Agent Executor for A2A Protocol.

Based on currency-agent executor pattern from Google ADK examples.
"""
from collections.abc import AsyncGenerator
import logging

from google.adk import Runner
from google.adk.events import Event
from google.genai import types

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    FilePart,
    FileWithBytes,
    FileWithUri,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def convert_genai_parts_to_a2a(genai_parts: list) -> list[Part]:
    """Convert GenAI parts to A2A format."""
    parts = []
    for genai_part in genai_parts:
        if hasattr(genai_part, 'text') and genai_part.text is not None:
            text_part = TextPart(text=genai_part.text)
            part = Part(root=text_part)
            parts.append(part)
        elif isinstance(genai_part, str):
            text_part = TextPart(text=genai_part)
            part = Part(root=text_part)
            parts.append(part)
        # Skip parts with None or empty text
    return parts


def convert_a2a_part_to_genai(part: Part) -> types.Part:
    """Convert a single A2A part to GenAI format."""
    logger.debug(f"Converting part: {part}")
    logger.debug(f"Part root: {getattr(part, 'root', 'No root attribute')}")
    logger.debug(f"Part dict: {part.model_dump() if hasattr(part, 'model_dump') else 'No model_dump'}")
    
    # Try to get the actual data from the Part object
    part_data = part.root if hasattr(part, 'root') else part
    
    # Handle different part structures
    if hasattr(part_data, 'text') and part_data.text is not None:
        logger.debug(f"Converting text part: {part_data.text}")
        return types.Part(text=part_data.text)
    elif hasattr(part, 'text') and part.text is not None:
        logger.debug(f"Converting text part directly: {part.text}")
        return types.Part(text=part.text)
    elif isinstance(part_data, str):
        logger.debug(f"Converting string part: {part_data}")
        return types.Part(text=part_data)
    elif isinstance(part_data, dict) and 'text' in part_data:
        logger.debug(f"Converting dict text part: {part_data['text']}")
        return types.Part(text=part_data['text'])
    else:
        # Try to extract text from the part structure
        try:
            part_dump = part.model_dump()
            if 'text' in part_dump:
                return types.Part(text=part_dump['text'])
            elif isinstance(part_dump, dict) and len(part_dump) == 1:
                # Single key-value pair, might be the content
                key, value = next(iter(part_dump.items()))
                if isinstance(value, str):
                    return types.Part(text=value)
        except Exception as e:
            logger.debug(f"Failed to extract from model_dump: {e}")
            
        raise ValueError(f"Could not extract text from part: {part} (type: {type(part)})")

def convert_a2a_parts_to_genai(parts: list[Part]) -> list[types.Part]:
    """Convert A2A parts to GenAI format."""
    return [convert_a2a_part_to_genai(part) for part in parts]


class ChessAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs a chess agent."""

    def __init__(self, runner: Runner, card: AgentCard):
        self.runner = runner
        self._card = card

    def _run_agent(
        self, session_id: str, new_message: types.UserContent
    ) -> AsyncGenerator[Event, None]:
        return self.runner.run_async(
            session_id=session_id, user_id="self", new_message=new_message
        )

    async def _process_request(
        self,
        new_message: types.UserContent,
        session_id: str,
        task_updater: TaskUpdater,
    ) -> None:
        session = await self._upsert_session(session_id)
        session_id = session.id
        async for event in self._run_agent(session_id, new_message):
            if event.is_final_response():
                parts = convert_genai_parts_to_a2a(event.content.parts)
                logger.debug("✅ Yielding final chess response: %s", parts)
                await task_updater.add_artifact(parts)
                await task_updater.complete()
                break
            if not event.get_function_calls():
                # Not a function call event - just a text response
                parts = convert_genai_parts_to_a2a(event.content.parts)
                logger.debug("📝 Yielding chess text response: %s", parts)
                await task_updater.add_artifact(parts)

    async def _upsert_session(self, session_id: str):
        """Upsert a session."""
        return await self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id="self", session_id=session_id
        ) or await self.runner.session_service.create_session(
            app_name=self.runner.app_name, user_id="self", session_id=session_id
        )

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the chess agent request."""
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        try:
            await self._process_request(
                types.UserContent(
                    parts=convert_a2a_parts_to_genai(context.message.parts),
                ),
                context.context_id,
                updater
            )
        except Exception as e:
            logger.exception("Error processing chess request")
            error_parts = [TextPart(text=f"Error generating chess move: {str(e)}")]
            await updater.add_artifact(error_parts)
            await updater.complete()

    async def cancel(
        self, 
        context: RequestContext, 
        event_queue: EventQueue
    ) -> None:
        """Cancel the chess agent request."""
        raise ServerError(error=UnsupportedOperationError())