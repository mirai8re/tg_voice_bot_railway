import os
import asyncio
import logging
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
import openai
from aiogram.types import FSInputFile
from openai import OpenAI, OpenAIError

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")
bot = Bot(token=TELEGRAM_TOKEN)
router = Router()
client = OpenAI()

@router.message(CommandStart())
async def start_command_handler(message: Message):
    await message.reply("HI! 👋\n\nYou can send me voice messages, and I will transcribe them and respond!")

@router.message(F.voice)
async def voice_message_handler(message: Message):
    try:
        voice_file_id = message.voice.file_id
        file_info = await bot.get_file(voice_file_id)

        voice_file_path = f"{voice_file_id}.ogg"
        await bot.download_file(file_info.file_path, destination=voice_file_path)

        with open(voice_file_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(file=audio_file, model='whisper-1')

        user_text = transcription.text
        await message.reply(f"You said: {user_text}")

        assistant = await client.beta.assistants.create(
            name="Voice Assistant",
            instructions="You are a helpful assistant.",
            model="gpt-4o",
        )

        thread = await client.beta.threads.create()
        await client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_text
        )

        run = await client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        answer_text = ''
        if run.status == 'completed':
            messages = await client.beta.threads.messages.list(thread_id=thread.id)
            for message_block in messages:
                if message_block.role == 'assistant':
                    answer_text = message_block.content
                    break

            if not answer_text:
                answer_text = "I'm sorry, I didn't get a valid response."

            await message.reply(f"Assistant's response: {answer_text}")
        else:
            await message.reply("Error, please try again.")

        # Генерация аудио из текста
        try:
            with await client.audio.speech.with_streaming_response.create(
                    model='tts-1',
                    voice='onyx',
                    input=answer_text,
            ) as response:
                with open('response.mp3', 'wb') as f:
                    async for chunk in response.iter_bytes():
                        f.write(chunk)
        except OpenAIError as e:
            print(f"An error occurred while trying to fetch the audio stream: {e}")

        audio_file_path = 'response.mp3'

        try:
            audio_file = FSInputFile(audio_file_path)
            await message.answer_audio(audio=audio_file)
        except Exception as e:
            print(f"Error: {e}")
            await message.reply("An error occurred while sending the audio file")

        # Удаление временных файлов
        finally:
            if os.path.exists(voice_file_path):
                os.remove(voice_file_path)
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)

    except Exception as e:
        await message.reply("Error, please try again")
        print(f"Error: {e}")

async def main():
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
