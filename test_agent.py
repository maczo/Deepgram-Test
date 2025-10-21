# Adapted from Deepgram Voice Agent docs example (v5 SDK)
# Simplified for console test: Stream sample, log events, no file writes

import os
import requests
import time
import threading
from deepgram import DeepgramClient, AgentWebSocketEvents, AgentKeepAlive
from deepgram.clients.agent.v1.websocket.options import SettingsOptions

def main():
    try:
        # Load keys
        api_key = os.getenv("DEEPGRAM_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key or not openrouter_key:
            raise ValueError("Missing DEEPGRAM_API_KEY or OPENROUTER_API_KEY env vars")

        # Initialize client
        deepgram = DeepgramClient(api_key, {"keepalive": "true"})
        connection = deepgram.agent.v1.connect()
        print("WebSocket connection created.")

        # Configure options (SIP-friendly mulaw/8kHz; docs use linear16/24kHz, but adaptable)
        options = SettingsOptions()
        options.audio.input.encoding = "mulaw"  # For telephony RTP
        options.audio.input.sample_rate = 8000
        options.audio.output.encoding = "mulaw"
        options.audio.output.sample_rate = 8000
        options.audio.output.container = "none"  # Stream, no container for test
        options.agent.language = "en"
        options.agent.listen.provider.type = "deepgram"
        options.agent.listen.provider.model = "nova-3"
        # OpenRouter as custom OpenAI-compatible
        options.agent.think.provider.type = "open_ai"
        options.agent.think.provider.model = "anthropic/claude-3.5-sonnet"
        options.agent.think.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        options.agent.think.headers = {"Authorization": f"Bearer {openrouter_key}"}
        options.agent.think.prompt = "You are a friendly phone assistant. Respond concisely and naturally to voice queries."
        options.agent.speak.provider.type = "deepgram"
        options.agent.speak.provider.model = "aura-2-thalia-en"
        options.agent.greeting = "Hello! This is a Deepgram test. I'll respond to what you say."

        # Keep-alive thread (docs recommend every 5s)
        def send_keep_alive():
            while True:
                time.sleep(5)
                print("Sending keep-alive...")
                connection.send(str(AgentKeepAlive()))

        keep_alive_thread = threading.Thread(target=send_keep_alive, daemon=True)
        keep_alive_thread.start()

        # Event handlers (simplified from docs: log to console)
        def on_audio_data(_, data, **kwargs):
            print(f"Received audio data from agent: {len(data)} bytes")

        def on_agent_audio_done(_, agent_audio_done, **kwargs):
            print(f"Agent audio done: {agent_audio_done}")

        def on_conversation_text(_, conversation_text, **kwargs):
            print(f"Conversation text: {conversation_text}")

        def on_welcome(_, welcome, **kwargs):
            print(f"Welcome: {welcome}")

        def on_settings_applied(_, settings_applied, **kwargs):
            print(f"Settings applied: {settings_applied}")

        def on_user_started_speaking(_, user_started_speaking, **kwargs):
            print(f"User started speaking: {user_started_speaking}")

        def on_agent_thinking(_, agent_thinking, **kwargs):
            print(f"Agent thinking: {agent_thinking}")

        def on_agent_started_speaking(_, agent_started_speaking, **kwargs):
            print(f"Agent started speaking: {agent_started_speaking}")

        def on_close(_, close, **kwargs):
            print(f"Connection closed: {close}")

        def on_error(_, error, **kwargs):
            print(f"Error: {error}")

        def on_unhandled(_, unhandled, **kwargs):
            print(f"Unhandled event: {unhandled}")

        # Register handlers (docs list: AudioData, AgentAudioDone, ConversationText, etc.)
        connection.on(AgentWebSocketEvents.AudioData, on_audio_data)
        connection.on(AgentWebSocketEvents.AgentAudioDone, on_agent_audio_done)
        connection.on(AgentWebSocketEvents.ConversationText, on_conversation_text)
        connection.on(AgentWebSocketEvents.Welcome, on_welcome)
        connection.on(AgentWebSocketEvents.SettingsApplied, on_settings_applied)
        connection.on(AgentWebSocketEvents.UserStartedSpeaking, on_user_started_speaking)
        connection.on(AgentWebSocketEvents.AgentThinking, on_agent_thinking)
        connection.on(AgentWebSocketEvents.AgentStartedSpeaking, on_agent_started_speaking)
        connection.on(AgentWebSocketEvents.Close, on_close)
        connection.on(AgentWebSocketEvents.Error, on_error)
        connection.on(AgentWebSocketEvents.Unhandled, on_unhandled)
        print("Event handlers registered.")

        # Start connection
        print("Starting WebSocket...")
        if not connection.start(options):
            print("Failed to start—check API key/config.")
            return
        print("WebSocket started successfully!")

        # Stream sample audio (docs use spacewalk.wav; Apollo 11 for fun)
        print("Streaming sample audio...")
        sample_url = "https://static.deepgram.com/samples/apollo_11.wav"
        response = requests.get(sample_url, stream=True)
        if response.status_code != 200:
            print("Failed to fetch sample.")
            return

        # Skip WAV header (44 bytes, per docs)
        header = response.raw.read(44)
        chunk_size = 8192
        chunk_count = 0
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                print(f"Sending chunk {chunk_count}: {len(chunk)} bytes")
                connection.send(chunk)
                chunk_count += 1
                time.sleep(0.1)  # Delay for real-time simulation

        print(f"Sample sent ({chunk_count} chunks)—waiting for response (30s)...")
        time.sleep(30)

        connection.finish()
        print("Test complete! Review logs for events.")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
