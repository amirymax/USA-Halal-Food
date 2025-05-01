import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from api_token import BOT_TOKEN
from admin import admin_router, ADMIN_IDS
# Включаем логирование
logging.basicConfig(
    level=logging.INFO, 
    filename="bot.log",  
    filemode="a",  # a - append
    format="%(asctime)s - %(levelname)s - %(message)s"
)



bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# Загружаем JSON с ресторанами
def load_restaurants():
    global restaurants_data
    try:
        with open("restaurants.json", "r", encoding="utf-8") as file:
            restaurants_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        restaurants_data = {}

# 📍 Приветственное сообщение
WELCOME_MESSAGE = '''
👋 <b>Welcome!</b>  

🍽 <i>Find the best fast food & restaurants near you!</i>  

🌍 <b>Languages:</b>  
🇺🇿 <b>Sizga yaqin joylashgan</b> – Tezkor oziq-ovqat va restoran qidiruvi.  
🇺🇸 <b>Fast food & restaurant search</b> – Find the best places nearby.  
🇷🇺 <b>Быстрый поиск еды</b> – Рестораны и кафе рядом с вами.  

🍕 Bon Appétit! 🚀
'''

def create_states_keyboard():
    buttons = [KeyboardButton(text=state) for state in restaurants_data.keys()]
    keyboard = ReplyKeyboardMarkup(keyboard=[buttons[i:i+3] for i in range(0, len(buttons), 3)], resize_keyboard=True)
    return keyboard

CHANNEL_ID = -1002616983549
CHANNEL_LINK = "https://t.me/halal_cafe_usa"

def create_subscription_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Присоединиться к группе", url=CHANNEL_LINK)],  # Первая строка
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]  # Вторая строка
    ])
    return keyboard
# 🔹 Функция проверки подписки
async def check_subscription(user_id: int, bot: Bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except TelegramBadRequest as e:
        logging.error(f"❌ Ошибка при проверке подписки {user_id}: {e}")
        return False

# 🔹 Обработчик команды /start
@router.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    load_restaurants()
    if message.chat.id != CHANNEL_ID:

        if not await check_subscription(message.from_user.id, bot):
            await message.answer(
                "🔹 Для использования бота присоединяйтесь в группу и нажмите «Я подписался» после этого:",
                reply_markup=create_subscription_keyboard()
            )
            return
        

          
        await message.answer(WELCOME_MESSAGE, reply_markup=create_states_keyboard())
    else:
        await message.reply("Для использования бота, напиши две буквы штата в таком формате:\nПример:\n\n WA", reply_markup=create_states_keyboard())

@router.message(lambda message: message.chat.id == CHANNEL_ID and len(message.text) == 2 and message.text.isalpha())
async def group_chat_handler(message: types.Message):
    state = message.text.upper()
    load_restaurants()
    if state not in restaurants_data:
        return

    restaurants = restaurants_data.get(state, [])

    if not restaurants:
        await message.answer(
            f"❌ <b>В этом штате пока нет зарегистрированных ресторанов.</b>\n"
            "🔍 Попробуйте выбрать другой штат!",
            reply_markup=create_states_keyboard()
        )
    else:
        response = f"📍 <b>Рестораны в штате {state}:</b>\n\n"
        for i, restaurant in enumerate(restaurants, start=1):
            # check if devlivery is No, just dont add id
            delivery = ""
            description = ""
            if restaurant["delivery"] != "No":
                delivery = f"🚙 <b>Доставка:</b> {restaurant['delivery']}"

            if restaurant["description"]:
                description = f"📝 <b>{restaurant['description']}</b>"

            response += (
                f"🍽 <b>{restaurant['name']}</b>\n"
                f"📞 <b>Phone:</b> {restaurant['phone']}\n"
                f"📍 <b>Location:</b> {restaurant['address']}\n"
                f"{delivery}\n"
                f"{description}\n"
                "➖➖➖➖➖➖➖➖➖➖\n"
            )
        await message.answer(response)



# 🔹 Обработчик кнопки "Я подписался"
@router.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription_callback(callback: types.CallbackQuery, bot: Bot):
    if await check_subscription(callback.from_user.id, bot):
        await callback.message.edit_text("✅ Вы подписаны! Теперь можно пользоваться ботом.")
        load_restaurants()
        await callback.message.answer(WELCOME_MESSAGE, reply_markup=create_states_keyboard())
    else:
        await callback.answer("❌ Вы еще не подписались! Проверьте и попробуйте снова.", show_alert=True)

# обрабатывает только сообщение в самом боте
@router.message(StateFilter(None), lambda message: message.text != '/newcafe' and message.chat.id != CHANNEL_ID)
async def process_state(message: types.Message):
    state = message.text.strip().upper()
    
    if state not in restaurants_data:
        await message.answer("❌ <b>Такого штата нет в списке!</b>\n🔍 Попробуйте выбрать из кнопок ниже.", reply_markup=create_states_keyboard())
        return
    
    restaurants = restaurants_data.get(state, [])

    if not restaurants:
        await message.answer(
            f"❌ <b>В этом штате пока нет зарегистрированных ресторанов.</b>\n"
            "🔍 Попробуйте выбрать другой штат!",
            reply_markup=create_states_keyboard()
        )
    else:
        response = f"📍 <b>Рестораны в штате {state}:</b>\n\n"
        for i, restaurant in enumerate(restaurants, start=1):
            # check if devlivery is No, just dont add id
            delivery = ""
            description = ""
            if restaurant["delivery"] != "No":
                delivery = f"🚙 <b>Доставка:</b> {restaurant['delivery']}"

            if restaurant["description"]:
                description = f"📝 <b>{restaurant['description']}</b>"

            response += (
                f"🍽 <b>{restaurant['name']}</b>\n"
                f"📞 <b>Phone:</b> {restaurant['phone']}\n"
                f"📍 <b>Location:</b> {restaurant['address']}\n"
                f"{delivery}\n"
                f"{description}\n"
                "➖➖➖➖➖➖➖➖➖➖\n"
            )
        await message.answer(response, reply_markup=create_states_keyboard())
        
dp.include_router(router)
dp.include_router(admin_router)
# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Bot started")
    asyncio.run(main())
