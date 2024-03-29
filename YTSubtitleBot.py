import redis
import requests
import logging
import os

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    MessageEntity,
)

from telegram.error import TimedOut

from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    ApplicationBuilder,
)

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from youtube_transcript_api.formatters import JSONFormatter, TextFormatter
import yt_dlp as youtube_dl

from dotenv import load_dotenv

load_dotenv()

PAYMENT_TOKEN: str = os.getenv("PAYMENT_TOKEN", "")
BOT_API_TOKEN: str = os.getenv("BOT_API_TOKEN", "")


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

r = redis.Redis()


async def start(update: Update, context: CallbackContext) -> None:
    userName = update.effective_user.first_name
    userID = update.effective_user.id

    numUses = r.zscore("subtitleBot", userID)
    numUses = 0 if numUses is None else int(numUses)

    if numUses == 0:
        await update.message.reply_text(
            f"Hello {userName}\n\nWelcome to Youtube Video Transcript Bot!\n\nThis bot is"
            f" used to automatically extract the subtitles from a Youtube video.\n\n"
            f"To begin, simply send a Youtube video link, and the transcript will be "
            f"sent to you.\n\n"
        )

    if not r.sismember("premium", userID):
        await update.message.reply_text(
            f"You have {8 - numUses} uses remaining on your free trial.\n\nOr upgrade to "
            f"Premium for unlimited use across a number of different bots!"
        )
        keyboard = [
            [KeyboardButton("Extract subtitles!")],
            [
                KeyboardButton("Premium"),
                KeyboardButton("Support!"),
            ],
        ]
    else:
        await update.message.reply_text("Your account is premium!\n\nUnlimited use!")
        keyboard = [
            [KeyboardButton("Extract subtitles!")],
            [KeyboardButton("Support!")],
        ]

    menu_markup = ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Send a URL to get started, or select an option below:",
        reply_markup=menu_markup,
    )


async def helpInfo(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Help")
    # to expand


# unknown command function
async def unknownCommand(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Unknown command\n\nPlease use /help for help, or send a YouTube Video URL to extra"
        "ct the subtitle transcript!"
    )


# arbitrary function to add something to keyboard
async def sendURL(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Please send a Youtube video link to extract the subtitles:"
    )


# checks whether the url is valid
async def checkURL(update: Update, context: CallbackContext, url) -> bool:
    # if this url is valid, if returns true (status code 200, 404 means not true)
    testURL = f"https://www.youtube.com/oembed?url={url}"
    checkLink = requests.get(testURL)

    return checkLink.status_code == 200


# allows the user to choose if they want a text file or json file using inline keyboards
async def transcriptOptions(update: Update, context: CallbackContext) -> None:
    # gets user identity stuff
    userID = update.effective_user.id
    numUses = r.zscore("subtitleBot", userID)
    numUses = 0 if numUses is None else numUses

    url = update.message.text

    # checks whether the user is able to use the bot
    if numUses > 7 and not r.sismember("premium", userID):
        await update.message.reply_text(
            "Sorry, you have reached the free trial limit.\n\nPlease update to premium "
            "for unlimited use"
        )
        # sends inline keyboard to upgrade - callback data as keyboard used for other things
        inlineKeyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="upgrade")]
        ]
        reply_markup = InlineKeyboardMarkup(inlineKeyboard)

        await update.message.reply_text("Click:", reply_markup=reply_markup)
        return

    # if user passes the test the url is checked if its valid - if function returns true options are sent to user
    if not await checkURL(update, context, url):
        await update.message.reply_text("This is not a valid Youtube video URL")
        return

    await update.message.reply_text(
        "Would you like the transcript as a textfile, or raw JSON file ->"
    )
    # creates inline keyboard and allows me to pass data to the button function using callback data
    inlineKeyboard = [
        [InlineKeyboardButton("Textfile", callback_data=f"2:{url}")],
        [InlineKeyboardButton("Raw JSON file", callback_data=f"3:{url}")],
    ]
    reply_markup = InlineKeyboardMarkup(inlineKeyboard)
    await update.message.reply_text("Select an option:", reply_markup=reply_markup)


# downloads and sends the YouTube video transcript to user as textfile
async def getTranscript(update: Update, context: CallbackContext, url) -> None:
    # gets the data needed
    userID = update.effective_user.id
    videoID = url.replace("https://www.youtube.com/watch?v=", "").split("&")[0]

    message = await context.bot.send_message(
        text="_fetching transcript..._", chat_id=userID, parse_mode="Markdown"
    )

    try:
        transcript = YouTubeTranscriptApi.get_transcript(videoID)
        formatter = TextFormatter()
        text_formatted = formatter.format_transcript(transcript)

        try:
            video_info = youtube_dl.YoutubeDL().extract_info(url=url, download=False)
            filename = f"{video_info['title']}.txt"

        except Exception as e:
            logger.error(e)
            filename = "transcript.txt"

        with open(filename, "w") as file:
            file.write(text_formatted)

        await context.bot.delete_message(
            message_id=message["message_id"], chat_id=userID
        )
        await context.bot.send_document(
            chat_id=userID, document=open(filename, "rb"), write_timeout=45
        )

        # logs the number of uses by saving url to a database
        r.zincrby("subtitleBot", 1, userID)

    except TranscriptsDisabled:
        await context.bot.edit_message_text(
            text="*Subtitles are not available for this video*",
            message_id=message["message_id"],
            chat_id=userID,
            parse_mode="Markdown",
        )
        return

    except TimedOut:
        await context.bot.edit_message_text_message(
            text="Sorry, I'm having some trouble sending that.\nPlease try " "again.",
            message_id=message["message_id"],
            chat_id=userID,
        )

    finally:
        # removes the files to save memory
        if os.path.exists(filename):
            os.remove(filename)


async def getTranscriptRaw(update: Update, context: CallbackContext, url) -> None:
    # gets data needed
    userID = update.effective_user.id
    videoID = url.replace("https://www.youtube.com/watch?v=", "").split("&")[0]

    message = await context.bot.send_message(
        text="_fetching transcript..._", chat_id=userID, parse_mode="Markdown"
    )

    try:
        transcript = YouTubeTranscriptApi.get_transcript(videoID)
        formatter = JSONFormatter()
        json_formatted = formatter.format_transcript(transcript, indent=2)

        try:
            video_info = youtube_dl.YoutubeDL().extract_info(url=url, download=False)
            filename = f"{video_info['title']}Raw.json"

        except:
            filename = "transcriptRaw.txt"

        # writes raw data to json file
        with open(filename, "w") as rawFile:
            rawFile.write(json_formatted)

        # logs the number of uses by saving url to a database
        r.zincrby("subtitleBot", 1, userID)

        await context.bot.delete_message(
            message_id=message["message_id"], chat_id=userID
        )
        await context.bot.send_document(chat_id=userID, document=open(filename, "rb"))

    except TranscriptsDisabled:
        await context.bot.edit_message_text(
            text="*Subtitles are not available for this video*",
            message_id=message["message_id"],
            chat_id=userID,
            parse_mode="Markdown",
        )
        return

    except TimedOut:
        await context.bot.edit_message_text_message(
            text="Sorry, I'm having some trouble sending that.\nPlease try " "again.",
            message_id=message["message_id"],
            chat_id=userID,
        )

    finally:
        # deletes the file after sending it
        if os.path.exists(filename):
            os.remove(filename)


# handles the inline buttons
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    await query.answer()

    # handles the premium function
    if query.data == "upgrade":
        await query.edit_message_text(
            text="Thank you for choosing to upgrade!\nPay below:"
        )
        await upgrade(update, context)

    # separates the url from the callback data - and checks which option was selected
    elif query.data[0:1] == "2":
        url = query.data[2:]
        await query.edit_message_text(text="Selected option: Textfile")
        await getTranscript(update, context, url)

    elif query.data[0:1] == "3":
        url = query.data[2:]
        await query.edit_message_text(text="Selected option: Raw file")
        await getTranscriptRaw(update, context, url)

    # will never be called but good as a failsafe
    else:
        await query.edit_message_text(text="Invalid option")


# sends invoice to upgrade user to premium
async def upgrade(update: Update, context: CallbackContext) -> None:
    # checks that the user is premium or not
    if r.sismember("premium", update.effective_user.id):
        keyboard = [
            [KeyboardButton("Get youtube video transcript!")],
            [KeyboardButton("Support!")],
        ]

        menu_markup = ReplyKeyboardMarkup(keyboard)
        await update.message.reply_text("You are premium!", reply_markup=menu_markup)

    # generates and sends the invoice to user
    else:
        chat_id = update.effective_message.chat_id
        title = "Premium Upgrade - Limitless Use!"
        description = (
            "Get unlimited uses, and full access to a range of bots now, and upcoming bots!\n\nContact "
            "@JacobJEdwards for details "
        )
        payload = "Youtube Subtitle Extractor Bot Premium"
        currency = "USD"
        price = 15
        prices = [LabeledPrice("Upgrade", price * 10)]
        await context.bot.send_invoice(
            chat_id, title, description, payload, PAYMENT_TOKEN, currency, prices
        )


# checks that the data is correct after user agrees to pay
async def precheckout_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != "Youtube Subtitle Extractor Bot Premium":
        # answer False pre_checkout_query
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)


# called when the payment is successful
async def upgradeSuccessful(update: Update, context: CallbackContext) -> None:
    # saves user as premium - accessible from all bots linked to the database
    r.sadd("premium", update.effective_user.id)

    keyboard = [
        [KeyboardButton("Extract subtitles!")],
        [KeyboardButton("Support!")],
    ]
    menu_markup = ReplyKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Upgrade successful! Welcome to premium.", reply_markup=menu_markup
    )


# generates the bot and handlers
def main() -> None:
    application = (
        ApplicationBuilder().token(BOT_API_TOKEN).arbitrary_callback_data(True).build()
    )

    # basic command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", helpInfo))

    # handles inline keyboard
    application.add_handler(CallbackQueryHandler(button))

    # handles the pre-made keyboard
    application.add_handler(MessageHandler(filters.Regex("Support!"), helpInfo))
    application.add_handler(
        MessageHandler(filters.Regex("Extract subtitles!"), sendURL)
    )
    application.add_handler(MessageHandler(filters.Regex("Premium"), upgrade))

    # Pre-checkout handler to final check
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    # post checkout handler
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, upgradeSuccessful)
    )

    # handles a url being sent
    application.add_handler(
        MessageHandler(
            filters.ALL
            & (
                filters.Entity(MessageEntity.URL)
                | filters.Entity(MessageEntity.TEXT_LINK)
            ),
            transcriptOptions,
        )
    )

    # catch all handler
    application.add_handler(MessageHandler(filters.ALL, unknownCommand))

    # runs the bot
    application.run_polling()


# calls main
if __name__ == "__main__":
    main()
