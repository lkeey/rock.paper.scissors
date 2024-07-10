import logging
import aiosqlite
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database initialization function
async def init_db():
    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        await db.commit()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hi! Send me a message and I will store it in the database.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('You can send me any message, and I will store it in the database. Use /getmessages to retrieve your stored messages.')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    message_text = update.message.text

    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute('INSERT INTO messages (user_id, message) VALUES (?, ?)', (user_id, message_text))
        await db.commit()

    await update.message.reply_text('Message stored in the database.')

async def get_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    async with aiosqlite.connect('bot_database.db') as db:
        async with db.execute('SELECT message FROM messages WHERE user_id = ?', (user_id,)) as cursor:
            rows = await cursor.fetchall()
            messages = [row[0] for row in rows]

    if messages:
        await update.message.reply_text('\n'.join(messages))
    else:
        await update.message.reply_text('No messages found for you in the database.')

async def main() -> None:
    # Initialize the database
    await init_db()
    
    # Initialize the bot application
    application = ApplicationBuilder().token('7397306826:AAEIjS_uxNfgmUOzNxf9kUhdZLu6H1apd-g').build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('getmessages', get_messages))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Starting bot...")
    
    # Initialize the application
    await application.initialize()
    
    # Start the application and updater
    await application.start()
    await application.updater.start_polling()
    
    # Shutdown the application
    await application.shutdown()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
