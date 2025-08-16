# streaming_latency_test.py (Version 4 - Final Fix & Heavily Commented)

# === Imports ===
# os: Used to interact with the operating system, specifically to get environment variables.
import os
# asyncio: The library for writing asynchronous code (coroutines), which is essential for handling
# real-time, non-blocking operations like a live audio stream.
import asyncio
# time: A simple library to get the current time, which we use to measure latency.
import time
# dotenv: A library to load environment variables from a `.env` file into the system's environment.
# This is how we keep our secret API keys out of the code.
from dotenv import load_dotenv
# deepgram: The official Deepgram Python SDK. We import the specific classes we need.
from deepgram import (
    DeepgramClient,           # The main client for interacting with the API.
    LiveTranscriptionEvents,  # An enumeration of events we can listen for (e.g., Transcript received).
    LiveOptions,              # An object to configure the live transcription options (e.g., model, language).
)

# === Configuration ===
# This function call finds a `.env` file in our project directory and loads all the
# key-value pairs defined in it as environment variables.
load_dotenv()

# We retrieve the API keys from the environment variables. os.getenv() is a safe way
# to get them; it will return `None` if the key isn't found instead of crashing.
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# This is the audio file we will use to simulate a person talking.
AUDIO_FILE_PATH = "test_question.mp3"

# === Transcript Collector Class ===
# We create a helper class to manage the state of our transcript. Because the transcript
# will arrive in multiple small pieces (segments) via the callback, we need a place
# to store these pieces and assemble them at the end.
class TranscriptCollector:
    def __init__(self):
        """This is the constructor, called when we create an instance of the class."""
        # We initialize an empty list to hold all the final transcript segments we receive.
        self.segments = []

    # FIX: The callback function must be an 'async' function.
    # The Deepgram SDK's event handler is asynchronous, so it needs to be able to 'await'
    # the callbacks we provide. Making this an 'async def' turns it into a coroutine.
    async def on_message(self, _, result, **kwargs):
        """
        This function is our event handler. It gets called automatically every time
        the Deepgram SDK receives a 'Transcript' event from the WebSocket.
        """
        # The 'result' object contains the transcription data.
        # 'is_final' is a boolean that is True when Deepgram has detected the end of an
        # utterance (e.g., after a pause). This is a confirmed, final transcript segment.
        if result.is_final and result.channel.alternatives[0].transcript != '':
            # We extract the actual text from the result object.
            transcript_segment = result.channel.alternatives[0].transcript
            # We add this confirmed segment to our list.
            self.segments.append(transcript_segment)

    def get_full_transcript(self):
        """A simple helper method to join all the collected segments into one string."""
        return " ".join(self.segments)

# === Main Asynchronous Function ===
# We put our main logic in an 'async' function so we can use 'await' for non-blocking operations.
async def main():
    try:
        # Initialize the Deepgram Client with our API key.
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Create the WebSocket connection object. This doesn't connect yet; it just prepares the object.
        # We use 'asyncwebsocket' as it's the latest, recommended method.
        dg_connection = deepgram.listen.asyncwebsocket.v("1")
        print("--- Starting Chatur Streaming Latency Test (Final Version) ---")
        
        # Create an instance of our helper class to store the transcript.
        transcript_collector = TranscriptCollector()
        
        # This is the crucial wiring step. We are "subscribing" our 'on_message' function
        # to the 'Transcript' event. Now, whenever Deepgram sends a transcript, our
        # 'on_message' function will be automatically called with the data.
        dg_connection.on(LiveTranscriptionEvents.Transcript, transcript_collector.on_message)

        # Configure the options for our live transcription.
        options = LiveOptions(
            model="nova-2",      # The model we want to use. Nova-2 is fast and accurate.
            language="en-US",    # The language of the audio.
            smart_format=True,   # Adds punctuation, capitalization, etc.
        )
        
        # This is the line that actually opens the secure WebSocket connection to Deepgram's servers.
        # 'await' means our program will pause here until the connection is successfully established.
        await dg_connection.start(options)
        print("1. Streaming audio from file...")

        # We open our local audio file in binary read mode ('rb').
        with open(AUDIO_FILE_PATH, "rb") as audio_file:
            # This loop reads the audio file in small chunks to simulate a real-time stream.
            while True:
                chunk = audio_file.read(4096)  # Read 4KB of audio data at a time.
                if not chunk:
                    # If the chunk is empty, we've reached the end of the file.
                    break
                
                # Send the audio chunk over the live WebSocket connection.
                await dg_connection.send(chunk)
                # We add a tiny, non-blocking sleep. This simulates a real-time audio
                # source (like a microphone buffer) and prevents us from overwhelming
                # the connection by sending the whole file in a fraction of a second.
                # await asyncio.sleep(0.01)

        print("2. Finished streaming. Closing connection and waiting for final transcript...")
        
        # We start our latency timer *after* the last piece of audio has been sent.
        latency_start_time = time.time()
        
        # This command sends a special message to Deepgram telling it that we are done
        # sending audio. 'await' makes our script pause here and wait until the server
        # has processed all the audio and sent back all the final transcript messages.
        await dg_connection.finish()
        
        # Once 'finish()' is done, we can be sure we've received all transcript segments.
        # We now call our helper method to assemble the complete text.
        full_transcript = transcript_collector.get_full_transcript()
        
        # We stop the timer immediately after getting the full transcript.
        latency_end_time = time.time()
        
        # The final latency is the difference. This number represents the time from
        # the moment the user stopped talking to the moment the app has the full transcript.
        final_latency = latency_end_time - latency_start_time

        print(f"   -> Final Transcript received: '{full_transcript}'")
        
        print("\n--- TEST COMPLETE ---")
        print("This latency measures the time from the end of speech to the final transcript reception.")
        print(f"✅ Real-Time STT Latency: {final_latency:.4f} seconds")

    except Exception as e:
        # A general error handler to catch any problems that might occur.
        print(f"An error occurred: {e}")

# === Script Execution ===
# This is a standard Python construct. The code inside this 'if' statement will only run
# when you execute the script directly (e.g., 'python3 streaming_latency_test.py').
if __name__ == "__main__":
    # 'asyncio.run()' is the entry point that starts the asyncio event loop and runs
    # our main asynchronous function until it's complete.
    asyncio.run(main())