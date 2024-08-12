import os
import asyncio
import logging
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
import openai
from gtts import gTTS
from aiogram.types import FSInputFile


load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
openai.api_key = os.getenv("OPENAI_API_KEY")
router = Router()

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
            transcription = openai.Audio.transcribe("whisper-1", audio_file)

        user_text = transcription["text"]
        await message.reply(f"You said: {user_text}")

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_text}]
        )

        answer_text = response['choices'][0]['message']['content']
        await message.reply(f"Answer: {answer_text}")

        audio_file_path = "response.mp3"
        tts = gTTS(text=answer_text, lang='en')
        tts.save(audio_file_path)

        try:
            audio_file = FSInputFile(audio_file_path)
            await message.answer_audio(audio=audio_file)

        except Exception as e:
            print(f"Error: {e}")
            await message.reply("An error occurred while sending the audio file")

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
