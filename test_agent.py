import os
import requests
import time
from deepgram import DeepgramClient
from deepgram.core.events import EventType  # For general events like MESSAGE, ERROR
from deepgram.extensions.types.sockets import (
    AgentV1SettingsMessage,
    AgentV1Agent,
    AgentV1AudioConfig,
    AgentV1AudioInput,
    AgentV1AudioOutput,
    AgentV1Listen,
    AgentV1ListenProvider,
    AgentV1Think,
    AgentV1OpenAiThinkProvider,
    AgentV1Speak,
    AgentV1DeepgramSpeakProvider
)

# Load keys (from Coolify env)
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not DEEPGRAM_API_KEY or not OPENROUTER_API_KEY:
    print("Error: Missing DEEPGRAM_API_KEY or OPENROUTER_API_KEY in env vars.")
    exit(1)

client = DeepgramClient(DEEPGRAM_API_KEY)

# Connect to agent
with client.agent.v1.connect() as connection:
    # Configure settings (SIP-friendly: mulaw/8kHz)
    settings = AgentV1SettingsMessage(
        audio=AgentV1AudioConfig(
            input=AgentV1AudioInput(encoding="mulaw", sample_rate=8000),
            output=AgentV1AudioOutput(encoding="mulaw", sample_rate=8000, container="none")
        ),
        agent=AgentV1Agent(
            language="en",
            listen=AgentV1Listen(
                provider=AgentV1ListenProvider(type="deepgram", model="nova-3")
            ),
            think=AgentV1Think(
                provider=AgentV1OpenAiThinkProvider(
                    type="open_ai",
                    model="anthropic/claude-3.5-sonnet",  # Your flexible model
                    endpoint="https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
                ),
                prompt="You are a friendly phone assistant. Respond concisely and naturally to voice queries."
            ),
            speak=AgentV1Speak(
                provider=AgentV1DeepgramSpeakProvider(type="deepgram", model="aura-2-thalia-en")
            ),
            greeting="Hello! This is a Deepgram test. I'll respond to what you say."
        )
    )

    # Send settings to start
    connection.send(str(settings))
    print("Agent settings sent—connection active!")

    # Event handlers (logs to console)
    def on_message(_, message, **kwargs):
        print(f"Received event: {message.type} - {message}")

    def on_error(_, error, **kwargs):
        print(f"Error: {error}")

    connection.on(EventType.MESSAGE, on_message)
    connection.on(EventType.ERROR, on_error)

    # Simulate caller: Stream sample WAV (Neil Armstrong quote)
    print("Streaming sample audio...")
    sample_url = "https://static.deepgram.com/samples/apollo_11.wav"
    response = requests.get(sample_url, stream=True)
    if response.status_code != 200:
        print("Failed to fetch sample.")
        exit(1)
    # Skip WAV header (44 bytes)
    header = response.raw.read(44)
    for chunk in response.iter_content(chunk_size=512):
        if chunk:
            connection.send(chunk)
            time.sleep(0.02)  # Real-time pacing

    # Run for 30s to see responses
    time.sleep(30)
    print("Test complete—check logs for STT/LLM/TTS interaction!")
