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
    filters
)
from configparser import ConfigParser
from random import choice
from datetime import time
import aiosqlite
import asyncio
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
import pytz

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

# conversation statuces
START, PLAYED, REGISTERED, PLAYED_AND_REGISTERED = range(4)

# job statuces
ONCE, DAYLY= range(2)

# database initialization
async def init_db():
    async with aiosqlite.connect('bot.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                wins INTEGER,
                defeats INTEGER,        
                name TEXT,
                phone TEXT,
                conversation_status INTEGER default 0
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

    """Ответил, поэтому писать уже не нужно"""
    remove_job_if_exists(name=f"{user_id}-{ONCE}", context=context)

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
                        SET wins = ?, conversation_status = ?
                        WHERE user_id = ?
                    ''', (w, PLAYED_AND_REGISTERED, user_id))
                else:
                    d = row[1] + 1 if row[1] != None else 1
                    await db.execute('''
                        UPDATE users
                        SET defeats = ?, conversation_status = ?
                        WHERE user_id = ?
                    ''', (d, PLAYED_AND_REGISTERED, user_id))
            else:
                # if user does not exist set 1 or 0 change on get name
                await db.execute('''
                    INSERT INTO users (user_id, wins, defeats, conversation_status) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, 1 if is_winner else 0, 0 if is_winner else 1, PLAYED))
            await db.commit()


    await update.message.reply_text(
        f"Computer - {computer}\n{message_to_user}",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

    return CHOOSING

async def choosing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_chat.id

    if int(query.data) == PLAY:
        await query.edit_message_text(text="Let's play!")

        reply_keyboard = [["Rock", "Paper"], ["Scissors"]]

        """если не походит, то через минуту напишем, чтобы ходил"""
        context.job_queue.run_once(once_job_step, 10, chat_id=user_id, name=f"{user_id}-{ONCE}")

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
                if row and row[0] != None:
                    await query.edit_message_text('You are already registered with the name')
                    
                    return await start(update, context)

        await query.edit_message_text(text="Let's start registration")
        await query.message.reply_text('Please, send me your name')
        
        return NAME
    elif int(query.data) == CONVERSIONS:
        await query.edit_message_text(text="It's conversions:")
    
        states_list = ["START", "PLAYED", "REGISTERED", "PLAYED_AND_REGISTERED"]

        number_users = await get_conversions()
        message = f"{states_list[0]}"
        
        for i in range(len(states_list) - 1):
            conversion = round(number_users[i + 1] / number_users[i] * 100, 2)
            
            message += f"\n|\n|    {conversion}%\nv\n{states_list[i+1]}"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
        )
        
        return await start(update, context)
    elif int(query.data) == LEADER_BOARD:
        await query.edit_message_text(text="There are all users:")
        await get_users(query, context)
        
        return await start(update, context)
    elif int(query.data) == MAIL:
        await query.edit_message_text(text="Send me message and I'll send it everyone")
        
        return GET_MAIL
    elif int(query.data) == YES_MAIL:
        await send_mail(query, context)
                
        return await start(update, context)
    elif int(query.data) == NO_MAIL:
               
        return await start(update, context)
    else:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)
        
        return await start(update, context)

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_message.text
    user_id = update.effective_user.id
    
    await update.message.reply_text(f'Thank you for sharing your name: {name}')
    
    async with aiosqlite.connect('bot.db') as db:  
        async with db.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] != None:
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
    user_id = update.effective_user.id

    await update.message.reply_text(f'Thank you for sharing your phone number: {phone_number}')
    
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT conversation_status FROM users WHERE user_id = ?', (user_id,)) as cursor:
            current_status = await cursor.fetchone()
            new_status = current_status[0]

            if current_status[0] == PLAYED:
                new_status = PLAYED_AND_REGISTERED
            elif current_status[0] == START:
                new_status = REGISTERED

            await db.execute('''
                UPDATE users
                SET phone = ?, conversation_status = ?
                WHERE user_id = ?
            ''', (phone_number, new_status, user_id))
            await db.commit()

    return await start(update, context)
    
async def get_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT user_id, wins, defeats, name, phone, conversation_status FROM users') as cursor:
            rows = await cursor.fetchall()
            messages = '\n'.join([f"{row[0]}: ({row[1]} - {row[2]}) - {row[3]} - {row[4]} #{row[5]}" for row in rows])

    if len(messages) != 0:
        await update.message.reply_text("user_id: (wins - defeats) - name - phone #conversationStatus")
        await update.message.reply_text(messages)
    else:
        await update.message.reply_text("- no users -")
 
async def get_mail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message.text
    
    keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data=YES_MAIL),
                InlineKeyboardButton("No", callback_data=NO_MAIL),
            ]
        ]

    context.user_data['msg'] = msg

    await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Send it:\n\n{msg}',
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="MarkdownV2"
        )

    return CHOOSING

async def send_mail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = context.user_data.get('msg', 'no message found')
    
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            async for row in cursor:
                await context.bot.send_message(
                    chat_id=row[0],
                    text=msg,
                    parse_mode="MarkdownV2"
                )

async def get_conversions():
    db = await aiosqlite.connect("bot.db")
    
    number_users = []
    statuses = [START, PLAYED, REGISTERED, PLAYED_AND_REGISTERED]

    for status in statuses:
        total_users_with_status = await db.execute(
            """SELECT COUNT(*) FROM users WHERE conversation_status >= ?""", (status,)
        )
        total_users_with_status = await total_users_with_status.fetchone()
        total_users_with_status = total_users_with_status[0]
        
        number_users.append(total_users_with_status)

    return number_users

def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

async def daily_job_progrev(context: ContextTypes.DEFAULT_TYPE) -> None:
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT user_id, name FROM users') as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                print(row)
                if row[1] != None:
                    await context.bot.send_message(chat_id=row[0], text=f"Hello, {row[1]}, let's play!")
                else:
                    await context.bot.send_message(chat_id=row[0], text=f"Hello, let's play!")

async def once_job_step(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    await context.bot.send_message(chat_id=job.chat_id, text="Go ahead))")

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

    # set correct time zone
    application.job_queue.run_daily(daily_job_progrev, time=time(hour=17, minute=54, tzinfo=pytz.timezone("Europe/Moscow")))

    application.add_handler(conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())

    main()
