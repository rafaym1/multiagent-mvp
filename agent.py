import asyncio

from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli

load_dotenv()


async def entrypoint(ctx: JobContext):
    # join the room as this agent
    await ctx.connect()
    print("[assistant-a] joined:", ctx.room.name)
    # stay alive until shutdown
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    opts = WorkerOptions(entrypoint_fnc=entrypoint, agent_name="assistant-a")
    cli.run_app(opts)  # `python agent_a.py dev` in dev mode
