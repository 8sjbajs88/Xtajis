import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext

from aiogram.dispatcher.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import sqlite3

# Set up logging

logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher with MemoryStorage
bot = Bot(token='6707067796:AAE7hWezUfa4NCfWswZK7HaeIj8Kq62jZrM')
dp = Dispatcher(bot, storage=MemoryStorage())

# Connect to SQLite database
conn = sqlite3.connect('your_database.db')
cursor = conn.cursor()

# Create users table if not exists
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT,
        user_id INTEGER,
        role TEXT,
        date TEXT
    )
''')
conn.commit()



# States
class SendMessageState(StatesGroup):
  WaitingForDescription = State()
  WaitingForImage = State()


async def check_channel_membership(chat_id: int, user_id: int):
  try:
    chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    # Check the status of the user in the channel
    if chat_member.status in [
        types.ChatMemberStatus.MEMBER, types.ChatMemberStatus.ADMINISTRATOR,
        types.ChatMemberStatus.CREATOR
    ]:
      return True  # User is a member of the channel
    else:
      return False  # User is not a member
  except Exception as e:
    # Handle exceptions, e.g., user not found or other API errors
    print(f"Error checking channel membership: {e}")
    return False


# Handlers
@dp.message_handler(Command("start"))
async def start(message: types.Message):
  # Check if the user exists in the database
  cursor.execute('SELECT * FROM users WHERE user_id = ?',
                 (message.from_user.id, ))
  user_data = cursor.fetchone()

  if not user_data:
    # If the user doesn't exist, add them to the database with role 'user'
    cursor.execute(
        '''
            INSERT INTO users (full_name, username, user_id, role, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (message.from_user.full_name, message.from_user.username,
              message.from_user.id, 'user', message.date))
    conn.commit()

  # Get the user's role from the database
  cursor.execute('SELECT role FROM users WHERE user_id = ?',
                 (message.from_user.id, ))
  user_role = cursor.fetchone()[0]
  if await check_channel_membership("@x_trade_official", message.from_user.id):
    if user_role == 'owner':
      keyboard_markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
      keyboard_markup.add(KeyboardButton('ناردنی نامە'),
                          KeyboardButton('داتاكان'))
    elif user_role == 'admin':
      keyboard_markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
      keyboard_markup.add(KeyboardButton('ناردنی نامە'),
                          KeyboardButton('داتاكان'))
    else:
      keyboard_markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
      keyboard_markup.add(KeyboardButton('فۆڕێكس'),
                          KeyboardButton('گروپی سیگناڵ'),
                          KeyboardButton('چۆن بەشدار ببم ؟'))
    await message.answer("""
سڵاو بەڕێزەکەم بەخێربێیت بۆ XTradeBOT

ئەم بۆتە درووستکراوە بە مەبەستی خزمەت کردن بە ترەیدەرەکان

بۆ زانیاری زیاتر لەو لیستەی خوارەوە هەڵبژێرە⬇️
""",
                         reply_markup=keyboard_markup)
  else:
    keyboard_markup = InlineKeyboardMarkup()
    keyboard_markup.add(
        InlineKeyboardButton('كەناڵی سەرەكی',
                             url='https://t.me/x_trade_official'))
    await message.answer(
        "ببورە بەڕێزم ، تكایە سەرەتا جۆینی كەناڵ بكە پاشان /start دابگرە",
        reply_markup=keyboard_markup)


@dp.message_handler(lambda message: message.text == 'ناردنی نامە')
async def get_description_handler(message: types.Message, state: FSMContext):
  await message.answer("تكایە دەقی بابەت بنێرە :")
  await SendMessageState.next()


@dp.message_handler(state=SendMessageState.WaitingForDescription)
async def get_description_handler(message: types.Message, state: FSMContext):
  description = message.text

  # Save description in the state
  await state.update_data(description=description)

  # Provide inline keyboard with options
  keyboard_markup = InlineKeyboardMarkup()
  keyboard_markup.add(
      InlineKeyboardButton('دووپاتكردنەوە', callback_data='duplicate'),
      InlineKeyboardButton('زیادكردنی وێنە', callback_data='add_image'),
      InlineKeyboardButton('لابردنەوە', callback_data='cancel'))

  # Use the provided description when answering the user
  await message.answer(
      f"{description}\n\nتكایە یەكێك لە هەڵبژاردنەكان هەڵبژێرە :",
      reply_markup=keyboard_markup)


@dp.callback_query_handler(
    lambda query: query.data in ['duplicate', 'add_image', 'cancel'],
    state=SendMessageState.WaitingForDescription)
async def inline_button_handler(query: types.CallbackQuery, state: FSMContext):
  data = await state.get_data()
  description = data.get('description')

  if query.data == 'duplicate':
    await state.finish()
    # Check if an image exists and send message accordingly
    if 'image' in data:
      await send_message_to_all(description, photo=data['image'])
    else:
      await send_message_to_all(description)
  elif query.data == 'add_image':
    # Set the state to WaitingForImage
    await SendMessageState.WaitingForImage.set()
    await query.answer("ڕەسمەكە بنێرە")
  elif query.data == 'cancel':
    await state.finish()
    await query.answer("بەسەركەوتووی هەڵوەشایەوە.")


@dp.message_handler(content_types=types.ContentType.PHOTO,
                    state=SendMessageState.WaitingForImage)
async def get_image_handler(message: types.Message, state: FSMContext):
  # Save image in the state
  await state.update_data(image=message.photo[-1].file_id)

  # Provide inline keyboard with options
  keyboard_markup = InlineKeyboardMarkup()
  keyboard_markup.add(
      InlineKeyboardButton('دووپاتكردنەوە', callback_data='duplicate'),
      InlineKeyboardButton('لابردنەوە', callback_data='cancel'))

  # Use the provided description when answering the user
  data = await state.get_data()
  await message.answer(
      f"{data.get('description')}\n\nتكایە یەكێك لە هەڵبژاردنەكان هەڵبژێرە :",
      reply_markup=keyboard_markup)


@dp.callback_query_handler(lambda query: query.data in ['duplicate', 'cancel'],
                           state=SendMessageState.WaitingForImage)
async def inline_button_image_handler(query: types.CallbackQuery,
                                      state: FSMContext):
  data = await state.get_data()
  description = data.get('description')

  if query.data == 'duplicate':
    await state.finish()
    await send_message_to_all(description, photo=data.get('image'))
  elif query.data == 'cancel':
    await state.finish()
    await query.answer("بەسەركەوتووی هەڵوەشایەوە.")


async def send_message_to_all(description, photo=None):
  # Get all user IDs from the users table
  cursor.execute('SELECT user_id FROM users')
  user_ids = [user_id[0] for user_id in cursor.fetchall()]

  # Send message to each user
  for user_id in user_ids:
    try:
      if photo:
        await bot.send_photo(chat_id=user_id,
                             photo=photo,
                             caption=f"{description}")
      else:
        await bot.send_message(chat_id=user_id, text=f"{description}")
    except Exception as e:
      # Handle exceptions, e.g., if the user has blocked the bot
      logging.error(f"Error sending message to user {user_id}: {e}")


@dp.message_handler(lambda message: message.text == 'داتاكان', state="*")
async def handle_data_button(message: types.Message):
  # Check if the user is the owner
  cursor.execute('SELECT role FROM users WHERE user_id = ?',
                 (message.from_user.id, ))
  user_role = cursor.fetchone()[0]

  if user_role == 'owner':
    # Fetch all users and create an Excel file
    cursor.execute('SELECT * FROM users')
    users_data = cursor.fetchall()

    # # Create a Pandas DataFrame
    # df = pd.DataFrame(users_data, columns=['ID', 'Full Name', 'Username', 'User ID', 'Role', 'Date'])

    # # Save DataFrame to an Excel file
    # excel_buffer = io.BytesIO()
    # df.to_excel(excel_buffer, index=False, sheet_name='Users Info')
    # excel_buffer.seek(0)

    # Send the Excel file to the user
    count_of_users = len(users_data)
    await bot.send_message(chat_id=message.from_user.id,
                           text=f"ژمارەی بەشداربووەكان: {count_of_users}")


@dp.message_handler(lambda message: message.text == 'گەڕانەوە')
async def signal_group(message: types.Message):
  keyboard_markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
  keyboard_markup.add(KeyboardButton('فۆڕێكس'), KeyboardButton('گروپی سیگناڵ'),
                      KeyboardButton('چۆن بەشدار ببم ؟'))
  await message.answer("""
سڵاو بەڕێزەکەم بەخێربێیت بۆ XTradeBOT

ئەم بۆتە درووستکراوە بە مەبەستی خزمەت کردن بە ترەیدەرەکان

بۆ زانیاری زیاتر لەو لیستەی خوارەوە هەڵبژێرە⬇️
""",
                       reply_markup=keyboard_markup)


@dp.message_handler(lambda message: message.text == 'گروپی سیگناڵ')
async def signal_group(message: types.Message):
  await message.answer(
      "گرووپی سیگناڵ واتا گرووپی ئاماژە دان ئەم گرووپە دائیمەن بە پارەیە. "
      "بۆ ؟ چونکە کاتێک من مامەڵە ئەکەمەوە لە ئاڵتون(زێڕ) ئەوە دێم لە گرووپەکە بە ئێوەش ئەڵێم لە ئاڵتون بە بای یاخود سێڵ مامەڵە بکەنەوە و بەم شێوەیەش بەیەکەوە ئەکەوینە قازانجەوە. "
      "تۆ هیچ لە کارەکە نەزانیت ئەتوانی پارە داخیل بکەیت و لەگەڵ ئێمە مامەڵە بکەیتەوە و دایخەیتەوە واتا بێ لێ زانینیش ئەتوانی قازانج بکەیت."
  )


@dp.message_handler(lambda message: message.text == 'فۆڕێكس')
async def handle_forex(message: types.Message):
  await message.answer("تكایە كەمێك چاوەڕێ بكە")
  await bot.send_video(chat_id=message.from_user.id,
                       video=open("whatsisforex.mp4", 'rb'),
                       caption="""
فۆڕێکس چیە ؟  چۆن ئیشەکات ؟

بریتییە لە ئاڵو گۆڕی دراوە جیهانیەکان و کانزا و پشکی کۆمپانیاکان بە ئۆنڵاین واتا هەر لە نێو مۆبایلەکەتەوە یاخود کۆمپیوتەرەکەتەوە دەتوانیت ئەم ئاڵو گۆڕانە بکەیت
بۆ ئەمەش پێویستە ئەکاونت دابنێیتە و پارە داخیل بکەیت
کەمترین بڕی داخل کردنی پارە ٥٠$ە

لە بەرنامەی (MetaTrader5) ئاڵو گۆڕەکان ئەکرێ
لەم ڤیدیۆیە بە ڕونی فێرکاری دانراوە
""")


@dp.message_handler(lambda message: message.text == 'كڕینی كۆرس')
async def handle_forex(message: types.Message):
  keyboard_markup = InlineKeyboardMarkup()
  keyboard_markup.add(
      InlineKeyboardButton('ئەدمین', url='https://t.me/xsky_addmin'))

  await message.answer("بۆ كرینی كۆرس و زانیاری زیاتر نامە بنێرە بۆ ئەدمین",
                       reply_markup=keyboard_markup)


@dp.message_handler(lambda message: message.text == 'چۆن بەشدار ببم ؟')
async def how_to_join(message: types.Message):
  keyboard_markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
  keyboard_markup.add(KeyboardButton('گروپی سیگناڵ'),
                      KeyboardButton('كڕینی كۆرس'), KeyboardButton("گەڕانەوە"))
  await message.answer("""
چۆن منیش فێر بم ؟
فێر بوون پێویستی بە کۆڕسە
کۆڕسیش لە کوردستان نرخی لە نێوان ٥٠٠$-٤،٠٠٠$ە
بەڵام ئێمە وەک هاوکاریەک باشترین و ناوازە ترین کۆڕسمان بۆ داناون تەنها بە ٥٨،٠٠٠ دینار
""",
                       reply_markup=keyboard_markup)


# Polling
if __name__ == '__main__':
  from aiogram import executor
  executor.start_polling(dp, skip_updates=True)
