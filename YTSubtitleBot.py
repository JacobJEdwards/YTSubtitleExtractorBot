# need to figure out way to store uses - as to not conflict with other bot - possibly add to userID set
# add to set with identifier - disregard this on url bot ? seems overcomplicated. Database???

# or - also overcomplicated - create set called uses, in set store userid:number of uses. use for all bots?
# unless i want bot uses to be separate which i do
# set called subtitleUses key userID:NumberOfUses -> also do this for other bot ?? simplicity sake

import redis
import requests
import logging
import json
import os

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

from youtube_transcript_api import YouTubeTranscriptApi

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

r = redis.Redis()
PAYMENT_TOKEN = '284685063:TEST:ZmU4YzRkOTg0MmVm'


async def start(update: Update, context: CallbackContext) -> None:
    userName = update.effective_user.first_name
    userID = update.effective_user.id
    userKey = f'transcript:{userID}'
    numUses = r.scard(userKey)

    if numUses == 0:
        await update.message.reply_text(f'Hello {userName}\n\nWelcome to Youtube Video Transcript Bot!\n\nThis bot is'
                                        f' used to automatically extract the subtitles from a Youtube video.\n\n'
                                        f'To begin, simply send a Youtube video link, and the transcript will be '
                                        f'sent to you.\n\n')

    if not r.sismember('premium', userID):
        await update.message.reply_text(f'You have {8-numUses} uses remaining on your free trial.\n\nOr upgrade to '
                                        f'Premium for unlimited use across a number of different bots!')
        keyboard = [
            [KeyboardButton("Get Youtube video transcript!", callback_data="1")],
            [
                KeyboardButton("Premium", callback_data="2"),
                KeyboardButton("Support!", callback_data="3"),
            ],
        ]
    else:
        await update.message.reply_text('Your account is premium!\n\nUnlimited use!')
        keyboard = [
            [KeyboardButton("Get Youtube video transcript!", callback_data="1")],
            [KeyboardButton("Support!", callback_data="3")],
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


# arbitrary function to add something to keyboard
async def sendURL(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Please send a Youtube video link to extract the subtitles:')


# checks whether the url is valid
async def checkURL(update: Update, context: CallbackContext, url) -> bool:
    # if this url is valid, if returns true (status code 200, 404 means not true)
    testURL = f'https://www.youtube.com/oembed?url={url}'
    checkLink = requests.get(testURL)

    return checkLink.status_code == 200


# downloads and sends the youtube video transcript to user
async def getTranscript(update: Update, context: CallbackContext) -> None:
    userID = update.effective_user.id
    userKey = f'transcript:{userID}'
    numUses = r.scard(userKey)

    # checks that the user is able to preform this process - if not sends inline message to upgrade
    if numUses > 7 and not r.sismember('premium', userID):
        await update.message.reply_text('Sorry, you have reached the free trial limit.\n\nPlease update to premium '
                                        'for unlimited use')
        inlineKeyboard = [[InlineKeyboardButton('Upgrade to Premium', callback_data='1')]]
        reply_markup = InlineKeyboardMarkup(inlineKeyboard)

        await update.message.reply_text('Click:', reply_markup=reply_markup)
        return

    url = update.message.text

    # checks if url is valid
    if await checkURL(update, context, url):
        videoID = url.replace('https://www.youtube.com/watch?v=', '').split("&")[0]

        # writes transcript to text file
        with open('transcript.txt', 'w') as file:
            transcript = YouTubeTranscriptApi.get_transcript(videoID)
            for i in transcript:
                file.write(i['text'])
                file.write(' ')

        # writes raw data to json file
        with open('rawTranscript.json', 'w') as rawFile:
            json.dump(transcript, rawFile)

        await context.bot.send_document(chat_id=userID, document=open('transcript.txt', 'rb'))
        await context.bot.send_document(chat_id=userID, document=open('rawTranscript.json', 'rb'))

        # logs the number of uses by saving url to a database
        r.sadd(userKey, url)

        # removes the files to save memory
        if os.path.exists("transcript.txt"):
            os.remove('transcript.txt')

        if os.path.exists('rawTranscript.json'):
            os.remove('rawTranscript.json')

    else:
        await update.message.reply_text('Sorry, this is not a YouTube video link!\n\nPlease send a link to a Youtube '
                                        'video, or contact me @JacobJEdwards if you need extra help')


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    await query.answer()
    await query.edit_message_text(text="Thank you for choosing to upgrade!\nPay below:")
    await upgrade(update, context)


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


def main() -> None:
    application = Application.builder().token("5561745160:AAHLaEHPUZ1QGfdxcUrxnmJUKiI4WDo8pFY").build()

    # basic command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', helpInfo))

    application.add_handler(CallbackQueryHandler(button))

    # handles the pre-made keyboard
    application.add_handler(MessageHandler(filters.Regex('Support!'), helpInfo))
    application.add_handler(MessageHandler(filters.Regex('Extract subtitles!'), sendURL))
    application.add_handler(MessageHandler(filters.Regex('Premium'), upgrade))

    # Pre-checkout handler to final check
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, upgradeSuccessful))

    application.add_handler(MessageHandler(filters.ALL &
                                           (filters.Entity(MessageEntity.URL) | filters.Entity(
                                               MessageEntity.TEXT_LINK)),
                                           getTranscript))

    application.add_handler(MessageHandler(filters.ALL, unknownCommand))

    # runs the bot
    application.run_polling()


if __name__ == '__main__':
    main()
