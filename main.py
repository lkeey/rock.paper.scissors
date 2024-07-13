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
import asyncio
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

ADMINS = [5712064064, 1010205515]

# dont show per_message error
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

config = ConfigParser()
config.read("config.ini")
BOT_TOKEN = config["Telegram"]["tg_token"]

#states
CHOOSING, CHOOSE_ACTION, NAME, PHONE, GET_MAIL = range(5)

# callbacks
CANCEL, PLAY, REGISTER, CONVERSIONS, LEADER_BOARD, MAIL, YES_MAIL, NO_MAIL = range(8)

# database initialization
async def init_db():
    async with aiosqlite.connect('bot.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                wins INTEGER,
                defeats INTEGER,        
                name TEXT,
                phone TEXT
            )
        ''')
        await db.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    if update.effective_user.id in ADMINS:
        keyboard = [
            [
                InlineKeyboardButton("Conversions", callback_data=CONVERSIONS),
                InlineKeyboardButton("List of Users", callback_data=LEADER_BOARD),
            ],
            [
                InlineKeyboardButton("Send everyone", callback_data=MAIL),
            ]
        ]

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are in admin panel",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        keyboard = [
            [
                InlineKeyboardButton("Play", callback_data=PLAY),
                InlineKeyboardButton("Register", callback_data=REGISTER),
            ]
        ]

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Hi! Would to play Rock & Paper & Scissors with me?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    return CHOOSING

async def check_winner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    computer = choice(["Rock", "Paper", "Scissors"])
    user = update.effective_message.text
    user_id = update.effective_user.id

    is_winner = False

    keyboard = [
        [
            InlineKeyboardButton("Play again", callback_data=PLAY),
            InlineKeyboardButton("Cancel", callback_data=CANCEL),
        ],
    ]

    message_to_user = "No one won"

    if (user == "Paper" and computer == "Rock") or (user == "Scissors" and computer == "Paper") or (user == "Rock" and computer == "Scissors"):
        message_to_user = "You won!!"
        is_winner = True

    elif (user == "Rock" and computer == "Paper") or (user == "Paper" and computer == "Scissors") or (user == "Scissors" and computer == "Rock"):
        message_to_user = "You lost!!"
        is_winner = False

    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT wins, defeats FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                # if user exists, increment their points
                
                if is_winner:
                    w = row[0] + 1 if row[0] != None else 1
                    await db.execute('''
                        UPDATE users
                        SET wins = ?
                        WHERE user_id = ?
                    ''', (w, user_id))
                else:
                    d = row[1] + 1 if row[1] != None else 1
                    await db.execute('''
                        UPDATE users
                        SET defeats = ?
                        WHERE user_id = ?
                    ''', (d, user_id))
            else:
                # if user does not exist set 1 or 0 change on get name
                await db.execute('''
                    INSERT INTO users (user_id, wins, defeats) 
                    VALUES (?, ?, ?)
                ''', (user_id, 1 if is_winner else 0, 0 if is_winner else 1))
            await db.commit()


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
                if row[0] != None:
                    await query.edit_message_text('You are already registered with the name')
                    
                    return await start(query, context)

        await query.edit_message_text(text="Let's start registration")
        await query.message.reply_text('Please, send me your name')
        
        return NAME
    elif int(query.data) == CONVERSIONS:
        await query.edit_message_text(text="It's conversions:")
        # TODO
        
        return await start(query, context)
    elif int(query.data) == LEADER_BOARD:
        await query.edit_message_text(text="There are all users:")
        await get_users(query, context)
        
        return await start(update, context)
    elif int(query.data) == MAIL:
        await query.edit_message_text(text="Send me message and I'll send it everyone")
        
        return GET_MAIL
    elif int(query.data) == YES_MAIL:
        await send_mail(query, context)
                
        return await start(query, context)
    elif int(query.data) == NO_MAIL:
               
        return await start(query, context)
    else:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)
        
        return await start(query, context)

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_message.text
    user_id = update.effective_user.id
    
    await update.message.reply_text(f'Thank you for sharing your name: {name}')
    
    async with aiosqlite.connect('bot.db') as db:  
        async with db.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row[0] != None:
                await db.execute('''
                    UPDATE users
                    SET name = ?
                    WHERE user_id = ?
                ''', (name, user_id))
            else:
                await db.execute('''
                    INSERT INTO users (user_id, name) 
                    VALUES (?, ?)
                ''', (user_id, name))
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

    return await start(update, context)
    
async def get_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT user_id, wins, defeats, name, phone FROM users') as cursor:
            rows = await cursor.fetchall()
            messages = '\n'.join([f"{row[0]}: ({row[1]} - {row[2]}) - {row[3]} - {row[4]}" for row in rows])

    if len(messages) != 0:
        await update.message.reply_text("user_id: (wins - defeats) - name - phone")
        await update.message.reply_text(messages)
    else:
        await update.message.reply_text("- no users -")
 
async def get_mail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message.text
    
    keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data=YES_MAIL),
                InlineKeyboardButton("No", callback_data=NO_MAIL),
            ]
        ]

    await update.message.reply_text(
        f'Send it:\n\n{msg}',
        reply_markup=keyboard,
        context={"msg": msg},
        parse_mode="MarkdownV2"
    )

    return CHOOSING

async def send_mail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = context["msg"]
    
    # TODO send everyone
    await update.message.reply_text(
        msg,
        context={},
        parse_mode="MarkdownV2"
    )

    return CHOOSING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    await update.message.reply_text(
        "Bye!", reply_markup=ReplyKeyboardRemove()
    )

    return await start(update, context)

def main() -> None:
    print("MAIN")

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
            GET_MAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_mail)
            ],
        },
        #always handles 
        fallbacks=[CommandHandler("cancel", cancel)],
        # per_message=True,
    )

    application.add_handler(conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())

    main()
