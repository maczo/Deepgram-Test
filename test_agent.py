import os
import requests
import time
from deepgram import DeepgramClient, AgentWebSocketEvents
from deepgram.clients.agent.v1.websocket.options import SettingsOptions

# Load keys (will come from Coolify env)
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not DEEPGRAM_API_KEY or not OPENROUTER_API_KEY:
    print("Error: Missing keys—add to env vars.")
    exit(1)

deepgram = DeepgramClient(DEEPGRAM_API_KEY)
connection = deepgram.agent.v1.connect()

# Configure for telephony (mulaw/8kHz like SIP)
options = SettingsOptions()
options.audio.input = type('Input', (), {'encoding': 'mulaw', 'sample_rate': 8000})()  # Simplified for test
options.audio.output = type('Output', (), {'encoding': 'mulaw', 'sample_rate': 8000, 'container': 'none'})()
options.agent.language = 'en'
options.agent.listen = type('Listen', (), {'provider': type('Provider', (), {'type': 'deepgram', 'model': 'nova-3'}())}())
# OpenRouter for LLM
options.agent.think = type('Think', (), {
    'provider': type('Provider', (), {
        'type': 'open_ai',
        'model': 'anthropic/claude-3.5-sonnet',  # Swap to your fave, e.g., 'meta-llama/llama-3.1-8b-instruct'
        'endpoint': 'https://openrouter.ai/api/v1/chat/completions',
        'headers': {'Authorization': f'Bearer {OPENROUTER_API_KEY}'}
    })(),
    'prompt': 'You are a friendly phone assistant. Respond concisely and naturally to voice queries.'
})()
options.agent.speak = type('Speak', (), {'provider': type('Provider', (), {'type': 'deepgram', 'model': 'aura-2-thalia-en'}())}())
options.agent.greeting = "Hello! This is a Deepgram test. I'll respond to what you say."

# Event handlers (logs to console)
def on_audio_data(_, data, **kwargs):
    print(f"AI speaking: {len(data)} bytes of audio generated!")  # In full: Save to WAV

def on_conversation_text(_, text, **kwargs):
    print(f"Full chat so far: {text}")

def on_user_started_speaking(_, **kwargs):
    print("Detected user speech—listening!")

def on_error(_, error, **kwargs):
    print(f"Error: {error}")

connection.on(AgentWebSocketEvents.AudioData, on_audio_data)
connection.on(AgentWebSocketEvents.ConversationText, on_conversation_text)
connection.on(AgentWebSocketEvents.UserStartedSpeaking, on_user_started_speaking)
connection.on(AgentWebSocketEvents.Error, on_error)

# Start the agent
if not connection.start(options):
    print("Failed to start agent—check keys.")
    exit(1)

print("Agent connected! Streaming sample audio...")

# Simulate caller: Stream Deepgram's Apollo 11 sample (famous "small step" quote)
sample_url = "https://static.deepgram.com/samples/apollo_11.wav"
response = requests.get(sample_url, stream=True)
if response.status_code != 200:
    print("Failed to fetch sample—check connection.")
    exit(1)
header = response.raw.read(44)  # Skip WAV header
for chunk in response.iter_content(chunk_size=512):  # Small chunks for real-time feel
    if chunk:
        connection.send(chunk)
        time.sleep(0.02)  # Simulate stream rate

# Keep running for responses (30s test)
time.sleep(30)
connection.finish()
print("Test complete—review logs above for AI interaction!")
