# need to figure out way to store uses - as to not conflict with other bot - possibly add to userID set
# add to set with identifier - disregard this on url bot ? seems overcomplicated. Database???

# or - also overcomplicated - create set called uses, in set store userid:number of uses. use for all bots?
# unless i want bot uses to be separate which i do
# set called subtitleUses key userID:NumberOfUses -> also do this for other bot ?? simplicity sake

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
    userName = update.effective_user.first_name
    userID = update.effective_user.id

    await update.message.reply_text('Hello')
    # to expand


    # different keyboards if premium or not - to also be added to premium function
    if r.sismember('premium', update.effective_user.id):
        keyboard = [
            [KeyboardButton("Get youtube video transcript!", callback_data="1")],
            [KeyboardButton("Support!", callback_data="3")],
        ]
    else:
        keyboard = [
            [KeyboardButton("Get youtube video transcript!", callback_data="1")],
            [
                KeyboardButton("Premium", callback_data="2"),
                KeyboardButton("Support!", callback_data="3"),
            ],
        ]

    menu_markup = ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text('Send a URL to get started, or select an option below:', reply_markup=menu_markup)


async def helpInfo(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Help')
    # to expand


# unknown command function
async def unknownCommand(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Unknown command\n\nPlease use /help for help, or send a YouTube Video URL to extra'
                                    'ct the subtitle transcript!')


async def sendURL(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Send a youtube link to extract the subtitles:')


async def checkURL(update: Update, context: CallbackContext) -> None:


async def getTranscript(update: Update, context: CallbackContext) -> None:


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:


async def upgrade(update: Update, context: CallbackContext) -> None:
    if r.sismember('premium', update.effective_user.id):
        keyboard = [
            [KeyboardButton("Get youtube video transcript!", callback_data="1")],
            [KeyboardButton("Support!", callback_data="3")],
        ]

        menu_markup = ReplyKeyboardMarkup(keyboard)
        await update.message.reply_text('You are premium!', reply_markup=menu_markup)

    else:
        chat_id = update.effective_message.chat_id
        title = "Premium Upgrade -Limitless Use!"
        description = 'Get unlimited uses, and full access to a range of bots now, and upcoming bots!\n\nContact ' \
                      '@JacobJEdwards for details '
        payload = 'Youtube Subtitle Extractor Bot Premium'
        currency = "USD"
        price = 1
        prices = [LabeledPrice('Upgrade', price * 100)]
        await context.bot.send_invoice(
            chat_id, title, description, payload, PAYMENT_TOKEN, currency, prices
        )

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

    # handles the pre-made keyboard
    application.add_handler(MessageHandler(filters.Regex('Support!'), helpInfo))
    application.add_handler(MessageHandler(filters.Regex('Get youtube video transcript!'), sendURL))
    application.add_handler(MessageHandler(filters.Regex('Premium'), upgrade))

    # Pre-checkout handler to final check
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, upgradeSuccessful))

    application.add_handler(MessageHandler(filters.ALL &
                                           (filters.Entity(MessageEntity.URL) | filters.Entity(
                                               MessageEntity.TEXT_LINK)),
                                           checkURL))

    application.add_handler(MessageHandler(filters.ALL, unknownCommand))

if __name__ == '__main__':
    main()
