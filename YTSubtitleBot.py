import redis
import requests
import logging

from telegram import *

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ContextTypes,
    PreCheckoutQueryHandler
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


r = redis.Redis()
PAYMENT_TOKEN = ''


async def start(update: Update, context: CallbackContext) -> None:


async def helpInfo(update: Update, context: CallbackContext) -> None:


# unknown command function
async def unknownCommand(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Unknown command\n\nPlease use /help for help, or send a YouTube Video URL to extra'
    'ct the subtitle transcript!')


async def checkURL(update: Update, context: CallbackContext) -> None:


async def getTranscript(update: Update, context: CallbackContext) -> None:


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:


async def premium(update: Update, context: CallbackContext) -> None:


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != "Youtube Subtitle Extractor Bot Premium":
        # answer False pre_checkout_query
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)


async def upgradeSuccessful(update: Update, context: CallbackContext) -> None:
    r.sadd('premium', update.effective_user.id)

    keyboard = [
        [KeyboardButton("Extract subtitles!", callback_data="1")],
        [KeyboardButton("Support!", callback_data="3")],
    ]
    menu_markup = ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text('Upgrade successful! Welcome to premium.', reply_markup=menu_markup)


async def main() -> None:
    application = Application.builder().token("5561745160:AAG2eaMgXjV-LXu5w0JCHLzPM3r6Pz_dnis").build()

    # basic command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', helpInfo))



if __name__ == '__main__':
    main()