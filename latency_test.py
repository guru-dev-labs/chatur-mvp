# latency_test.py (Version 2 with detailed timing)

import time
import os
from groq import Groq
from deepgram import DeepgramClient, PrerecordedOptions
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

AUDIO_FILE_PATH = "test_question.mp3" # Using your .mp3 file

try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
except Exception as e:
    print("Error initializing API clients. Make sure your API keys are set correctly in the .env file.")
    print(e)
    exit()

def run_latency_test():
    try:
        print("--- Starting Chatur Latency Test (Deepgram + Groq) ---")
        
        # --- NEW: Initialize individual timers ---
        stt_latency = 0
        llm_latency = 0
        
        total_start_time = time.time()

        # --- STAGE A: SPEECH-TO-TEXT (Deepgram) ---
        print("1. Transcribing audio with Deepgram...")
        stt_start_time = time.time() # Start STT timer
        
        with open(AUDIO_FILE_PATH, 'rb') as audio_file:
            buffer_data = audio_file.read()
            payload = {'buffer': buffer_data}
            options = PrerecordedOptions(model="nova-2", smart_format=True)
            response = deepgram_client.listen.rest.v("1").transcribe_file(payload, options)
            transcribed_text = response['results']['channels'][0]['alternatives'][0]['transcript']
        
        stt_end_time = time.time() # End STT timer
        stt_latency = stt_end_time - stt_start_time # Calculate STT duration
        
        if not transcribed_text:
            print("Error: Transcription failed.")
            return

        print(f"   -> Transcribed Text: '{transcribed_text}'")

        # --- STAGE B: AI SUGGESTION (Groq) ---
        print("\n2. Getting suggestions from Groq...")
        llm_start_time = time.time() # Start LLM timer

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an AI assistant for a product manager in a live interview. Your response MUST be extremely concise. Provide a maximum of 3 short bullet points. Each bullet point MUST be under 10 words. Do NOT write explanations. Do NOT write paragraphs. For example: '- Clarify the core problem - Use STAR framework - Focus on user impact'." },
                {"role": "user", "content": transcribed_text}
            ],
            model="llama3-8b-8192",
        )
        llm_suggestion = chat_completion.choices[0].message.content
        
        llm_end_time = time.time() # End LLM timer
        llm_latency = llm_end_time - llm_start_time # Calculate LLM duration
        
        print(f"   -> LLM Suggestion:\n{llm_suggestion}")

        total_end_time = time.time()
        total_latency = total_end_time - total_start_time

        # --- 3. THE FINAL RESULT (Now with details) ---
        print("\n--- TEST COMPLETE: LATENCY BREAKDOWN ---")
        print(f"   - Deepgram STT Latency: {stt_latency:.2f} seconds")
        print(f"   - Groq LLM Latency:     {llm_latency:.2f} seconds")
        print("   ------------------------------------")
        print(f"✅ Total End-to-End Latency: {total_latency:.2f} seconds")

    except FileNotFoundError:
        print(f"Error: The audio file was not found. Make sure a file named '{AUDIO_FILE_PATH}' is in the folder.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    run_latency_test()