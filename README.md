# Multiagent Classroom MVP

A real-time, voice-based multi-agent AI system that simulates an interactive classroom presentation environment. Built on the **LiveKit Agents** framework, it orchestrates multiple AI agents that engage a live presenter — alternating between an expert critic and a curious beginner.


## How It Works

The system runs two sequential agents within a single LiveKit session, sharing state via a typed `PresentationData` dataclass.

### Agent Pipeline

```
User joins room
      │
      ▼
┌─────────────────┐
│  ModeratorAgent │  ← Greets presenter, collects name + topic
└────────┬────────┘
         │  start_presentation() tool call
         ▼
┌──────────────────────┐
│  PresentationAgent   │  ← Engages presenter in dual roles
│  ┌────────────────┐  │
│  │  EXPERT MODE   │  │  Challenging questions, expert feedback
│  ├────────────────┤  │
│  │  BEGINNER MODE │  │  Basic questions, clarification, curiosity
│  └────────────────┘  │
└──────────────────────┘
         │  end_presentation() tool call
         ▼
    Room deleted via LiveKit API
```

### Agents

**`ModeratorAgent`**
- Welcomes the presenter, collects their name and topic via natural conversation
- Calls the `start_presentation` function tool, which instantiates `PresentationAgent` and hands off the session
- Uses `gpt-4o-mini` + Deepgram STT + OpenAI TTS

**`PresentationAgent`**
- Dynamically switches between two personas using `switch_agent_role()`:
  - **Expert mode** — asks rigorous, domain-specific questions; provides feedback on content and delivery
  - **Beginner mode** — asks for clarification, examples, and simpler explanations
- Exposes function tools: `ask_expert_question`, `ask_beginner_question`, `provide_presentation_feedback`, `request_clarification`, `share_related_insight`, `end_presentation`
- Uses the **OpenAI Realtime API** (`echo` voice) for low-latency voice interaction

### Shared State

All agents read and write to a typed `PresentationData` dataclass via `RunContext.userdata`:

```python
@dataclass
class PresentationData:
    topic: Optional[str] = None
    presenter_name: Optional[str] = None
    presentation_started: bool = False
    current_agent: Optional[str] = None
    question_count: int = 0
    feedback_given: bool = False
```

## Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | LiveKit Agents `~1.0` |
| LLM (Moderator) | OpenAI `gpt-4o-mini` |
| LLM (Presentation) | OpenAI Realtime API |
| Speech-to-Text | Deepgram `nova-3` |
| Text-to-Speech | OpenAI TTS (`echo`) |
| Voice Activity Detection | Silero VAD |
| Real-time Transport | LiveKit |
| Package Manager | `uv` |
| Python | `>=3.10` |


## Setup

### 1. Install `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install dependencies

```bash
uv pip install --requirements pyproject.toml
```

### 3. Configure environment variables

Create a `.env` file in the root:

```env
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
```

### 4. Install the LiveKit CLI

```bash
curl -sSL https://get.livekit.io/cli | bash
```

### 5. Generate a participant token

```bash
lk token create \
  --join \
  --room classroom-test \
  --identity user \
  --url $LIVEKIT_URL \
  --api-key $LIVEKIT_API_KEY \
  --api-secret $LIVEKIT_API_SECRET
```

Use this token to connect via the [LiveKit Playground](https://playground.livekit.io) or any LiveKit client SDK.

### 6. Start the agent worker

```bash
uv run src/agent.py connect --room classroom-test
```

## Project Structure

```
multiagent-mvp/
├── src/
│   └── agent.py          # All agent definitions and entrypoint
├── pyproject.toml        # Project metadata and dependencies
├── .python-version       # Pinned Python version
├── Procfile              # Process definition (for deployment)
└── .env                  # Environment variables (not committed)
```

## Metrics & Observability

The session collects token and latency metrics via LiveKit's `UsageCollector`, logged on worker shutdown:

```python
@session.on("metrics_collected")
def _on_metrics_collected(ev: MetricsCollectedEvent):
    metrics.log_metrics(ev.metrics)
    usage_collector.collect(ev.metrics)
```

## Deployment

A `Procfile` is included for Heroku/Railway-style deployments:

```
worker: python src/agent.py start
```
