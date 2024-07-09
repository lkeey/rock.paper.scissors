from telegram import (
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    Update,
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from configparser import ConfigParser
from random import choice

config = ConfigParser()
config.read("config.ini")
BOT_TOKEN = config["Telegram"]["tg_token"]

PLAY_OR_REGISTER, CHOOSE_ACTION, AGAIN_OR_CANCEL = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    keyboard = [
        [
            InlineKeyboardButton("Play", callback_data="1"),
            InlineKeyboardButton("Register", callback_data="2"),
        ],
    ]

    await update.message.reply_text(
        "Hi! Would to play Rock & Paper & Scissors with me?",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

    return PLAY_OR_REGISTER

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    reply_keyboard = [["Rock", "Paper", "Scissors"]]

    await update.message.reply_text(
        "Choose option:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )

    return CHOOSE_ACTION

async def check_winner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    computer = choice(["Rock", "Paper", "Scissors"])

    reply_keyboard = [["Play again", "Cancel"]]

    await update.message.reply_text(
        f"You win or defeat?\n Computer - {computer}",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )

    return AGAIN_OR_CANCEL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    await update.message.reply_text(
        "Bye!", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:

    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PLAY_OR_REGISTER: [
                MessageHandler(filters.Text("Play"), play_game),
                # TODO
            ],
            CHOOSE_ACTION: [
                MessageHandler(filters.Regex("^(Rock|Paper|Scissors)$"), check_winner), 
            ],
            AGAIN_OR_CANCEL: [
                MessageHandler(filters.Text("Play again"), play_game),
                MessageHandler(filters.Text("Cancel"), cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
