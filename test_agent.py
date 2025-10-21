import os
import requests
import time
import threading
from deepgram import DeepgramClient
from deepgram.clients.agent.v1.websocket import AgentWebSocketEvents
from deepgram.clients.agent.v1.websocket.messages import AgentKeepAlive
from deepgram.clients.agent.v1.websocket.options import SettingsOptions

# Load keys from env
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not DEEPGRAM_API_KEY or not OPENROUTER_API_KEY:
    print("Error: Missing DEEPGRAM_API_KEY or OPENROUTER_API_KEY in env vars.")
    exit(1)

deepgram = DeepgramClient(DEEPGRAM_API_KEY, {"keepalive": "true"})
connection = deepgram.agent.v1.connect()

# Configure settings (SIP-compatible: mulaw/8kHz)
options = SettingsOptions()
options.audio.input.encoding = "mulaw"
options.audio.input.sample_rate = 8000
options.audio.output.encoding = "mulaw"
options.audio.output.sample_rate = 8000
options.audio.output.container = "none"
options.agent.language = "en"
options.agent.listen.provider.type = "deepgram"
options.agent.listen.provider.model = "nova-3"
# OpenRouter as custom OpenAI-compatible LLM
options.agent.think.provider.type = "open_ai"
options.agent.think.provider.model = "anthropic/claude-3.5-sonnet"  # Your flexible model
options.agent.think.endpoint = "https://openrouter.ai/api/v1/chat/completions"  # Custom endpoint
options.agent.think.headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
options.agent.think.prompt = "You are a friendly phone assistant. Respond concisely and naturally to voice queries."
options.agent.speak.provider.type = "deepgram"
options.agent.speak.provider.model = "aura-2-thalia-en"
options.agent.greeting = "Hello! This is a Deepgram test. I'll respond to what you say."

# Keep-alive thread
def send_keep_alive():
    while True:
        time.sleep(5)
        print("Sending keep-alive...")
        connection.send(str(AgentKeepAlive()))

keep_alive_thread = threading.Thread(target=send_keep_alive, daemon=True)
keep_alive_thread.start()

# Event handlers (logs to console)
def on_audio_data(_, data, **kwargs):
    print(f"AI speaking: {len(data)} bytes of TTS audio received!")

def on_conversation_text(_, text, **kwargs):
    print(f"Chat transcript: {text}")

def on_user_started_speaking(_, **kwargs):
    print("User started speaking—listening!")

def on_error(_, error, **kwargs):
    print(f"Error: {error}")

def on_close(_, **kwargs):
    print("Connection closed.")

# Register events
connection.on(AgentWebSocketEvents.AudioData, on_audio_data)
connection.on(AgentWebSocketEvents.ConversationText, on_conversation_text)
connection.on(AgentWebSocketEvents.UserStartedSpeaking, on_user_started_speaking)
connection.on(AgentWebSocketEvents.Error, on_error)
connection.on(AgentWebSocketEvents.Close, on_close)

# Start connection with options
if not connection.start(options):
    print("Failed to start connection—check keys/config.")
    exit(1)

print("Agent started successfully! Streaming sample audio...")

# Stream sample (Apollo 11 WAV as "caller input")
sample_url = "https://static.deepgram.com/samples/apollo_11.wav"
response = requests.get(sample_url, stream=True)
if response.status_code != 200:
    print("Failed to fetch sample.")
    exit(1)

# Skip WAV header (44 bytes)
response.raw.read(44)
chunk_size = 512  # Small for real-time
for chunk in response.iter_content(chunk_size=chunk_size):
    if chunk:
        print(f"Sending {len(chunk)} bytes...")
        connection.send(chunk)
        time.sleep(0.02)  # Pace like RTP stream

print("Sample sent—waiting for AI response (30s)...")
time.sleep(30)

connection.finish()
print("Test complete! Check logs for events (STT, LLM response, TTS).")
