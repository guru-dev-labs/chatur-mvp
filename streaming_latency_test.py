# streaming_latency_test.py (Version 6 - With LLM call and JSON output)

import os
import asyncio
import sys
import json # Import the JSON library
from dotenv import load_dotenv
from groq import Groq # Import Groq
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # Get the Groq key

class TranscriptCollector:
    def __init__(self):
        self.segments = []

    async def on_message(self, _, result, **kwargs):
        if result.is_final and result.channel.alternatives[0].transcript != '':
            transcript_segment = result.channel.alternatives[0].transcript
            self.segments.append(transcript_segment)

    def get_full_transcript(self):
        return " ".join(self.segments)

def create_json_output(type, data):
    """Helper function to create and print a JSON object."""
    # We use json.dumps to convert a Python dictionary to a JSON string.
    # We add a newline character `\n` so the Swift app can easily read one line at a time.
    print(json.dumps({"type": type, "data": data}) + "\n")


async def main():
    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        groq_client = Groq(api_key=GROQ_API_KEY) # Initialize Groq client
        dg_connection = deepgram.listen.asyncwebsocket.v("1")
        
        transcript_collector = TranscriptCollector()
        dg_connection.on(LiveTranscriptionEvents.Transcript, transcript_collector.on_message)

        options = LiveOptions(model="nova-2", language="en-US", smart_format=True)
        await dg_connection.start(options)
        
        # --- Reading from stdin (no change here) ---
        while True:
            chunk = sys.stdin.buffer.read(4096)
            if not chunk:
                break
            await dg_connection.send(chunk)
        
        await dg_connection.finish()
        full_transcript = transcript_collector.get_full_transcript()
        
        # --- KEY CHANGE: Call LLM and print JSON ---
        if full_transcript:
            # 1. Send the final transcript back to Swift as JSON
            create_json_output("final_transcript", full_transcript)
            
            # 2. Call the Groq LLM for suggestions
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant for a product manager in a live interview. Your response MUST be extremely concise. Provide a maximum of 3 short bullet points. Each bullet point MUST be under 10 words. Do NOT write explanations. Do NOT write paragraphs. For example: '- Clarify the core problem - Use STAR framework - Focus on user impact'."
                    },
                    {
                        "role": "user",
                        "content": full_transcript
                    }
                ],
                model="llama3-8b-8192",
            )
            llm_suggestion = chat_completion.choices[0].message.content
            
            # 3. Send the AI suggestion back to Swift as JSON
            create_json_output("suggestion", llm_suggestion)

    except Exception as e:
        error_message = {"type": "error", "data": str(e)}
        print(json.dumps(error_message) + "\n", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())