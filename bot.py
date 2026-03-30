import logging
import random
import string
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- SOZLAMALAR ---
API_TOKEN = '8691633617:AAF3iwi_HsGRFdioZiEE97DsEAcWwzvLuiE'
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

# Ma'lumotlarni saqlash (Oddiy holatda lug'atdan foydalanamiz, 7/24 uchun DB kerak bo'ladi)
tests_db = {} 

class TestStates(StatesGroup):
    choosing_action = State()
    writing_question = State()
    writing_options = State()
    setting_time = State()
    solving_test = State()

# --- KLAVIATURA ---
main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Test yaratish"), KeyboardButton(text="Test yechish")]
], resize_keyboard=True)

finish_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Testni yakunlash")]
], resize_keyboard=True)

# --- FUNKSIYALAR ---
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def send_results_to_owner(owner_id, test_code):
    test = tests_db.get(test_code)
    if test:
        results = "\n".join([f"Foydalanuvchi {r['user']}: {r['score']} ball" for r in test['results']])
        await bot.send_message(owner_id, f"🕒 Vaqt tugadi! '{test_code}' kodi ostidagi test natijalari:\n\n{results if results else 'Hech kim yechmadi.'}")

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Assalomu alaykum! Tanlang:", reply_markup=main_menu)

@dp.message(F.text == "Test yaratish")
async def create_test(message: types.Message, state: FSMContext):
    await state.set_state(TestStates.writing_question)
    await state.update_data(questions=[], owner_id=message.from_user.id)
    await message.answer("Test uchun savolni kiriting:", reply_markup=finish_kb)

@dp.message(TestStates.writing_question)
async def get_question(message: types.Message, state: FSMContext):
    if message.text == "Testni yakunlash":
        data = await state.get_data()
        if not data['questions']:
            await message.answer("Kamida bitta savol kiriting!")
            return
        await state.set_state(TestStates.setting_time)
        await message.answer("Natijalar necha daqiqadan keyin sizga kelsin? (Masalan: 5)")
        return
    
    await state.update_data(current_q=message.text)
    await state.set_state(TestStates.writing_options)
    await message.answer("Variantlarni kiriting (masalan: A, B, C, D) va to'g'risini birinchi yozing:")

@dp.message(TestStates.writing_options)
async def get_options(message: types.Message, state: FSMContext):
    options = [opt.strip() for opt in message.text.split(',')]
    data = await state.get_data()
    questions = data['questions']
    questions.append({'question': data['current_q'], 'options': options, 'correct': options[0]})
    
    await state.update_data(questions=questions)
    await state.set_state(TestStates.writing_question)
    await message.answer("Savol saqlandi. Keyingi savolni yuboring yoki 'Testni yakunlash' tugmasini bosing.", reply_markup=finish_kb)

@dp.message(TestStates.setting_time)
async def set_time(message: types.Message, state: FSMContext):
    try:
        minutes = int(message.text)
        data = await state.get_data()
        code = generate_code()
        
        tests_db[code] = {
            'owner': data['owner_id'],
            'questions': data['questions'],
            'results': []
        }
        
        # Taymerni yoqish
        run_at = datetime.now() + timedelta(minutes=minutes)
        scheduler.add_job(send_results_to_owner, 'date', run_date=run_at, args=[data['owner_id'], code])
        
        await message.answer(f"✅ Test tayyor!\nKod: `{code}`\nNatijalar {minutes} daqiqadan keyin yuboriladi.", parse_mode="Markdown", reply_markup=main_menu)
        await state.clear()
    except:
        await message.answer("Iltimos, faqat raqam kiriting (daqiqalarda).")

@dp.message(F.text == "Test yechish")
async def solve_start(message: types.Message, state: FSMContext):
    await state.set_state(TestStates.solving_test)
    await message.answer("Test kodini kiriting:")

@dp.message(TestStates.solving_test)
async def process_solving(message: types.Message, state: FSMContext):
    code = message.text.upper()
    if code in tests_db:
        test = tests_db[code]
        score = 0
        # Sodda bo'lishi uchun bu yerda barcha savollarni birdaniga yuboramiz
        text = f"Test: {code}\n\n"
        for i, q in enumerate(test['questions'], 1):
            text += f"{i}. {q['question']}\nVariantlar: {', '.join(q['options'])}\n\n"
        
        # Haqiqiy botda bu yerda Inline tugmalar bilan bittadan savol beriladi
        # Hozircha foydalanuvchi yechdi deb hisoblaymiz (namuna uchun)
        test['results'].append({'user': message.from_user.full_name, 'score': 'Yechildi'})
        await message.answer(text + "\nSiz testni qabul qildingiz!")
        await state.clear()
    else:
        await message.answer("Kod noto'g'ri!")

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())