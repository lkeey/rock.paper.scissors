from telegram import (
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    Update,
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from configparser import ConfigParser
from random import choice
import aiosqlite

config = ConfigParser()
config.read("config.ini")
BOT_TOKEN = config["Telegram"]["tg_token"]

#states
CHOOSING, CHOOSE_ACTION, NAME, PHONE = range(4)

# callbacks
CANCEL, PLAY, REGISTER, LEADER_BOARD = range(4)

# Database initialization
async def init_db():
    async with aiosqlite.connect('bot.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                wins INTEGER,
                name TEXT,
                phone TEXT
            )
        ''')
        await db.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    keyboard = [
        [
            InlineKeyboardButton("Play", callback_data=PLAY),
            InlineKeyboardButton("Register", callback_data=REGISTER),
        ],
        [
            InlineKeyboardButton("LeaderBoard", callback_data=LEADER_BOARD),
        ]
    ]

    await update.message.reply_text(
        "Hi! Would to play Rock & Paper & Scissors with me?",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

    return CHOOSING

async def check_winner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    computer = choice(["Rock", "Paper", "Scissors"])
    user = update.effective_message.text

    keyboard = [
        [
            InlineKeyboardButton("Play again", callback_data=PLAY),
            InlineKeyboardButton("Cancel", callback_data=CANCEL),
        ],
    ]

    message_to_user = "No one won"

    if (user == "Paper" and computer == "Rock") or (user == "Scissors" and computer == "Paper") or (user == "Rock" and computer == "Scissors"):
        message_to_user = "You won!!"
    elif (user == "Rock" and computer == "Paper") or (user == "Paper" and computer == "Scissors") or (user == "Scissors" and computer == "Rock"):
        message_to_user = "You lost!!"

    await update.message.reply_text(
        f"Computer - {computer}\n{message_to_user}",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

    return CHOOSING

async def choosing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if int(query.data) == PLAY:
        await query.edit_message_text(text="Let's play!")

        reply_keyboard = [["Rock", "Paper"], ["Scissors"]]

        await query.message.reply_text(
            "Choose option:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True
            ),
        )
        return CHOOSE_ACTION
    elif int(query.data) == REGISTER:
        async with aiosqlite.connect('bot.db') as db:
            async with db.execute('SELECT name FROM users WHERE user_id = ?', (update.effective_user.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    await query.edit_message_text('You are already registered with the name')
                    await start(query, context)
                    return ConversationHandler.END

        await query.edit_message_text(text="Let's start registration")

        await query.message.reply_text('Please, send me your name')
        return NAME
    elif int(query.data) == LEADER_BOARD:
        await query.edit_message_text(text="There are all users:")
        await get_users(query, context)
        await start(query, context)

        return ConversationHandler.END
    else:
        await query.edit_message_text(text="Bye...")
        await start(query, context)

        return ConversationHandler.END

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_message.text
    id = update.effective_user.id
    
    await update.message.reply_text(f'Thank you for sharing your name: {name}')
    
    async with aiosqlite.connect('bot.db') as db:  
        await db.execute('''
            INSERT INTO users (user_id, wins, name, phone) 
            VALUES (?, ?, ?, ?)
        ''', (id, 0, name, "none"))
        await db.commit()

    contact_button = KeyboardButton(text="Share your phone number", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text('Please, send me your phone number:', reply_markup=reply_markup)
    return PHONE

async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    phone_number = update.message.contact.phone_number
    id = update.effective_user.id

    await update.message.reply_text(f'Thank you for sharing your phone number: {phone_number}')
    
    async with aiosqlite.connect('bot.db') as db:
        await db.execute('''
            UPDATE users
            SET phone = ?
            WHERE user_id = ?
        ''', (phone_number, id))
        await db.commit()

    await start(update, context)

    return ConversationHandler.END
    
async def get_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT user_id, wins, name, phone FROM users') as cursor:
            rows = await cursor.fetchall()
            messages = '\n'.join([f"{row[0]}: ({row[1]}) - {row[2]} - {row[3]}" for row in rows])

    await update.message.reply_text(messages)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    await update.message.reply_text(
        "Bye!", reply_markup=ReplyKeyboardRemove()
    )

    await start(update, context)
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(choosing_callback), 
            ],
            CHOOSE_ACTION: [
                MessageHandler(filters.Regex("^(Rock|Paper|Scissors)$"), check_winner), 
            ],
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)
            ],
            PHONE: [
                MessageHandler(filters.CONTACT, save_phone)
            ],
        },
        # обязательно ли его прописывать?
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # import asyncio
    # asyncio.run(init_db())
    main()
