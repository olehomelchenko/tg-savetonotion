from telegram.ext.conversationhandler import ConversationHandler
from telegram.ext.updater import Updater
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from telegram.replykeyboardremove import ReplyKeyboardRemove
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
import sqlalchemy as db
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

import os
import logging

import db_utils
from notion_utils import create_page

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")


SETUP, NOTION_TOKEN, NOTION_TABLE_ID, FINISH = range(4)

tbl = db_utils.get_or_create_table()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext):
    logger.info("trigger: start")

    try:
        user = db_utils.get_user(update.message.from_user.id, tbl)
        logger.info(f"user {user.tg_user_id} exists")
        reply_text = "Welcome back!"
        reply_kbd = None
        if not user.notion_token:
            reply_text = (
                "You don't have a Notion Integration Token! Please send enter it below"
            )
            reply_kbd = [["Set Notion Token"]]
        if not user.notion_db:
            reply_text = (
                "You don't have a Notion Database ID! Please send enter it below"
            )
            reply_kbd = [["Set Notion Database"]]
        update.message.reply_text(
            reply_text,
            reply_markup=ReplyKeyboardMarkup(reply_kbd) if reply_kbd else None,
        )
        return
    except NoResultFound:
        db_utils.create_user(update.message.from_user.id, tbl)

        update.message.reply_markdown(
            "Hi! Please send notion integration token."
            "It can be found using step 1 & 2 of instructions: https://developers.notion.com/docs/getting-started",
        )

        return NOTION_TOKEN


def setup(update: Update, context: CallbackContext):
    logger.info("trigger: setup")

    uid = update.message.from_user.id

    user = db_utils.get_user(uid, tbl)

    if update.message.text == "Set Notion Token":
        reply_text = (
            f"Your current token is {user.notion_token}. \nEnter your new one below"
        )
        return_state = NOTION_TOKEN
    if update.message.text == "Set Notion Database":
        reply_text = (
            f"Your current token is {user.notion_db}. \nEnter your new one below"
        )
        return_state = NOTION_TABLE_ID
    update.message.reply_markdown(reply_text)
    return return_state


def notion_token(update: Update, context: CallbackContext):
    logger.info("trigger: notion_token")

    uid = update.message.from_user.id
    db_utils.update_user(uid, tbl, notion_token=update.message.text)

    update.message.reply_markdown(
        "Got it! Now I need an ID of the table where you want me to save the messages."
        "You can find it from URL of the database: `https://www.notion.so/my-base/*DB_ID_HERE*?v=...`"
        "Your database *must* have these fields: `Name`, `Tags` (multiselect), `URL` (type url) - all case-sensitive."
    )

    return NOTION_TABLE_ID


def notion_table_id(update: Update, context: CallbackContext):
    logger.info("trigger: notion_table_id")
    user = update.message.from_user
    logger.info("Table ID of %s: %s", user.first_name, update.message.text)

    uid = update.message.from_user.id
    db_utils.update_user(uid, tbl, notion_db=update.message.text)

    update.message.reply_markdown(
        "Got it! Now try to forward some messages here and they'll appear in your database!"
    )

    return FINISH


def finish(update: Update, context: CallbackContext):
    logger.info("trigger: finish")

    uid = update.message.from_user.id
    try:
        user = db_utils.get_user(uid, tbl)
    except NoResultFound:

        update.message.reply_text(
            "We don't have any records of you. Would you like to set things up?",
            reply_markup=ReplyKeyboardMarkup([["Start"]], one_time_keyboard=True),
        )
        return
    try:
        create_page(user.notion_token, user.notion_db, update.message)
    except Exception as e:

        logger.error(f"Exception: {e}")

        reply_keyboard = [["Set Notion Token", "Set Notion Database"]]
        update.message.reply_text(
            "Error saving to Notion. Check if your token and db are correct",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                input_field_placeholder="input field placeholder?",
            ),
        )
        return SETUP

    update.message.reply_text("Saved successfully!")

    return FINISH


def main():

    updater = Updater(TG_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(Filters.regex("^Start$"), start),
            MessageHandler(Filters.all, finish),
        ],
        states={
            NOTION_TOKEN: [MessageHandler(Filters.regex("^(.+)$"), notion_token)],
            SETUP: [
                MessageHandler(Filters.regex("^Set Notion (Token|Database)$"), setup)
            ],
            NOTION_TABLE_ID: [MessageHandler(Filters.regex("^(.+)$"), notion_table_id)],
            FINISH: [
                MessageHandler(Filters.forwarded, finish),
                MessageHandler(Filters.all, finish),
            ],
        },
        fallbacks=[MessageHandler(Filters.all, finish)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
