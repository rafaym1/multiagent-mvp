# Multi-agent DEMO


## Setup

1. Install Astral.sh Uv
   - Follow the instructions at
     [https://github.com/astral-sh/uv](UV)
2. Install dependencies
    ```bash
    uv pip install --requirements pyproject.toml
    ```
3. Create a `.env` file in the root directory with the following content:
    ```env
    DEEPGRAM_API_KEY=your_deepgram_api_key
    OPENAI_API_KEY=your_openai_api_key
    CARTESIA_API_KEY=your_cartesia_api_key
    LIVEKIT_URL=wss://your_livekit_url
    LIVEKIT_API_KEY=your_livekit_api_key
    LIVEKIT_API_SECRET=your_livekit_api_secret
    ```
4. Install livekit CLI:
    ```bash
    curl -sSL https://get.livekit.io/cli | bash
    ```

5. Generate the livekit URL and livekit Token:
    ```bash
    lk token create --join --room classroom-test --identity user --url URL_FROM_.ENV --api-key LIVEKIT_API_KEY_IN.ENV --api-secret LIVEKIT_API_SECRET_IN.ENV
    ```

6. Start the server with UV env activated
    ```bash
    uv run src/agent.py connect --room classroom-test
    ```