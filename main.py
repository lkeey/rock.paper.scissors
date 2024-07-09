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
    CallbackQueryHandler,
    filters,
)
from configparser import ConfigParser
from random import choice

config = ConfigParser()
config.read("config.ini")
BOT_TOKEN = config["Telegram"]["tg_token"]

CHOOSING, CHOOSE_ACTION = range(2)
CANCEL, PLAY, REGISTER = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    keyboard = [
        [
            InlineKeyboardButton("Play", callback_data=PLAY),
            InlineKeyboardButton("Register", callback_data=REGISTER),
        ],
    ]

    await update.message.reply_text(
        "Hi! Would to play Rock & Paper & Scissors with me?",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

    return CHOOSING

# async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
#     reply_keyboard = [["Rock", "Paper", "Scissors"]]

#     await update.message.reply_text(
#         "Choose option:",
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True
#         ),
#     )

#     return CHOOSE_ACTION

async def check_winner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    computer = choice(["Rock", "Paper", "Scissors"])

    keyboard = [
        [
            InlineKeyboardButton("Play again", callback_data=PLAY),
            InlineKeyboardButton("Cancel", callback_data=CANCEL),
        ],
    ]

    print(context.args)

    await update.message.reply_text(
        f"Computer - {computer}\nYou win or defeat?",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

    return CHOOSING


async def choosing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    print("CALLBACK -", query.data)

    if int(query.data) == PLAY:
        await query.edit_message_text(text="Let's play!")

        reply_keyboard = [["Rock", "Paper", "Scissors"]]

        await query.message.reply_text(
            "Choose option:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True
            ),
        )
        return CHOOSE_ACTION
    elif query.data == REGISTER:
        # TODO
        pass
    else:
        await query.edit_message_text(text="Bye!")

        return ConversationHandler.END

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
            CHOOSING: [
                CallbackQueryHandler(choosing_callback), 
            ],
            CHOOSE_ACTION: [
                MessageHandler(filters.Regex("^(Rock|Paper|Scissors)$"), check_winner), 
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
