import asyncio
import websockets
import os
import json
from dotenv import load_dotenv
from groq import Groq
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
except Exception as e:
    print(f"Error initializing API clients: {e}")
    exit()

async def get_groq_suggestion(text):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an AI assistant for a product manager in a live interview. Your response MUST be extremely concise. Provide a maximum of 3 short bullet points. Each bullet point MUST be under 10 words. Do NOT write explanations. Do NOT write paragraphs. For example: '- Clarify the core problem - Use STAR framework - Focus on user impact'."},
                {"role": "user", "content": text}
            ],
            model="llama3-8b-8192",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error getting suggestion from Groq: {e}")
        return "Error: Could not get suggestion."

async def handle_client(websocket, path):
    print("Client connected.")
    
    try:
        dg_connection = deepgram_client.listen.asynclive.v("1")

        async def on_message(self, result, **kwargs):
            if result.is_final and result.channel.alternatives[0].transcript != '':
                transcript = result.channel.alternatives[0].transcript
                print(f"Final transcript received: {transcript}")
                
                suggestion = await get_groq_suggestion(transcript)
                
                response = {
                    "type": "final_result",
                    "transcribed_text": transcript,
                    "llm_suggestion": suggestion
                }
                await websocket.send(json.dumps(response))

        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)

        options = LiveOptions(
            model="nova-2",
            language="en-US",
            smart_format=True,
            encoding="linear16",
            sample_rate=44100 # This needs to match the sample rate from the Swift app
        )

        await dg_connection.start(options)

        async for message in websocket:
            await dg_connection.send(message)

    except websockets.exceptions.ConnectionClosedOK:
        print("Client disconnected normally.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'dg_connection' in locals() and dg_connection:
            await dg_connection.finish()
        print("Connection closed.")

async def main():
    print("Starting WebSocket server on ws://localhost:8765")
    async with websockets.serve(handle_client, "localhost", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())