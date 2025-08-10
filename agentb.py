import asyncio

from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli

load_dotenv()


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    print("[assistant-b] joined:", ctx.room.name)
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    opts = WorkerOptions(entrypoint_fnc=entrypoint, agent_name="assistant-b")
    cli.run_app(opts)
