import logging
from dataclasses import dataclass
from typing import Optional
import random

from dotenv import load_dotenv

from livekit import api
from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    metrics,
)
from livekit.agents.job import get_job_context
from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
#from livekit.plugins import deepgram, openai, silero
from plugins import deepgram, openai, silero

#from livekit.agents.tts import openai
#from livekit.agents.stt import deepgram
#from livekit.agents.vad import silero

logger = logging.getLogger("classroom-agent")

load_dotenv()

common_instructions = (
    "You are participating in a classroom presentation session. "
    "The user is giving a presentation, and you should actively listen and engage but be to the point "
    "Be respectful and constructive in your interactions."
)


@dataclass
class PresentationData:
    # Shared data used by all agents
    topic: Optional[str] = None
    presenter_name: Optional[str] = None
    presentation_started: bool = False
    current_agent: Optional[str] = None  # Track which agent should speak next
    question_count: int = 0
    feedback_given: bool = False


class ModeratorAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=f"{common_instructions} You are the classroom moderator. "
            "Your role is to welcome the presenter, understand what topic they'll be presenting on, "
            "get their name, and then introduce them to the class. "
            "Once you have the necessary information, start the presentation session with the two other agents. "
            "Keep your introduction brief and short.",
        )

    async def on_enter(self):
        self.session.generate_reply()

    @function_tool
    async def start_presentation(
        self,
        context: RunContext[PresentationData],
        presenter_name: str,
        topic: str,
    ):
        """Called when the presenter has provided their name and topic, ready to start.

        Args:
            presenter_name: The name of the presenter
            topic: The topic they will be presenting on
        """
        context.userdata.presenter_name = presenter_name
        context.userdata.topic = topic
        context.userdata.presentation_started = True
        context.userdata.current_agent = "expert"

        # Create the presentation agent that will manage the two classroom agents
        presentation_agent = PresentationAgent(presenter_name, topic)
        
        logger.info(
            "Starting presentation session - Presenter: %s, Topic: %s", 
            presenter_name, topic
        )
        return presentation_agent, f"Thank you {presenter_name}! Please begin your presentation on {topic}."


class PresentationAgent(Agent):
    def __init__(self, presenter_name: str, topic: str, *, chat_ctx: Optional[ChatContext] = None) -> None:
        super().__init__(
            instructions=f"{common_instructions} You are managing a classroom presentation session. "
            f"The presenter {presenter_name} is giving a presentation on '{topic}'. "
            "You have two roles to play alternately: "
            "1. EXPERT MODE: Act as an expert in the topic. Ask insightful, challenging questions, "
            "provide constructive feedback, suggest improvements, and share advanced insights. "
            "Be encouraging but intellectually rigorous. "
            "2. BEGINNER MODE: Act as someone new to the topic. Ask basic questions for clarification, "
            "express confusion about complex concepts, ask for examples, and show enthusiasm for learning. "
            "Be curious and humble. "
            "Switch between these roles naturally. Wait for the presenter to speak, then respond appropriately. "
            "Occasionally provide feedback on presentation style, clarity, and engagement.",
            llm=openai.realtime.RealtimeModel(voice="echo"),
            tts=None,
            chat_ctx=chat_ctx,
        )
        self.presenter_name = presenter_name
        self.topic = topic
        self.is_expert_turn = True  # Start with expert

    async def on_enter(self):
        # Give initial encouragement to start
        self.session.generate_reply()

    @function_tool
    async def switch_agent_role(self, context: RunContext[PresentationData]):
        """Switch between expert and beginner agent roles to create variety in the interaction."""
        self.is_expert_turn = not self.is_expert_turn
        context.userdata.current_agent = "expert" if self.is_expert_turn else "beginner"
        
        role = "expert" if self.is_expert_turn else "beginner"
        logger.info(f"Switching to {role} mode")
        
        # Update instructions based on current role
        if self.is_expert_turn:
            current_instructions = f"You are now in EXPERT MODE for the topic '{self.topic}'. " \
                "Ask challenging questions, provide expert insights, suggest improvements, " \
                "and give constructive feedback. Be intellectually rigorous but supportive."
        else:
            current_instructions = f"You are now in BEGINNER MODE for the topic '{self.topic}'. " \
                "Ask basic questions, seek clarification on complex points, request examples, " \
                "and show curiosity and enthusiasm for learning."
        
        return current_instructions

    @function_tool
    async def ask_expert_question(self, context: RunContext[PresentationData]):
        """Generate an expert-level question or provide expert feedback."""
        context.userdata.question_count += 1
        return f"Speaking as an expert in {self.topic}, I'd like to engage with your presentation."

    @function_tool
    async def ask_beginner_question(self, context: RunContext[PresentationData]):
        """Generate a beginner-level question or seek clarification."""
        context.userdata.question_count += 1
        return f"As someone new to {self.topic}, I have a question about what you just presented."

    @function_tool
    async def provide_presentation_feedback(self, context: RunContext[PresentationData]):
        """Provide feedback on presentation style, clarity, and delivery."""
        context.userdata.feedback_given = True
        return "I'd like to provide some feedback on your presentation style and delivery."

    @function_tool
    async def end_presentation(self, context: RunContext[PresentationData]):
        """Called when the presentation session should end."""
        self.session.interrupt()

        await self.session.generate_reply(
            instructions=f"Thank {context.userdata.presenter_name} for their presentation on {context.userdata.topic}. "
            "Provide encouraging closing remarks and mention what was learned. Keep it brief and positive.",
            allow_interruptions=False
        )

        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(api.DeleteRoomRequest(room=job_ctx.room.name))

    @function_tool
    async def request_clarification(self, context: RunContext[PresentationData]):
        """Ask the presenter to clarify or elaborate on a point."""
        return "Could you elaborate on that point? I'd like to understand it better."

    @function_tool
    async def share_related_insight(self, context: RunContext[PresentationData]):
        """Share a related insight or connect to broader concepts (expert mode)."""
        return f"That connects to some broader concepts in {self.topic}. Let me share a related insight."


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    session = AgentSession[PresentationData](
        vad=ctx.proc.userdata["vad"],
        llm=openai.LLM(model="gpt-4o-mini"),
        stt=deepgram.STT(model="nova-3"),
        tts=openai.TTS(voice="echo"),
        userdata=PresentationData(),
    )

    # Log metrics as they are emitted
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")  
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=ModeratorAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
