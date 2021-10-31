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

from db_utils import get_table
from notion_utils import create_page

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")

sql_string = os.environ.get("PG_STRING")
PG_TABLE_NAME = os.getenv("PG_TABLE_NAME")
engine = db.create_engine(sql_string)

NOTION_TOKEN, NOTION_TABLE_ID, FINISH = range(3)

tbl = get_table(engine, PG_TABLE_NAME)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext):
    uid = update.message.from_user.id

    try:
        s = Session(engine)
        user = s.query(tbl).filter_by(tg_user_id=str(update.message.from_user.id)).one()
        logger.info(f"user {user} exists")
        s.close()
        if not user.notion_token:
            update.message.reply_text(
                "You don't have a Notion Integration Token! Please send enter it below"
            )
            return NOTION_TOKEN
        if not user.notion_db:
            update.message.reply_text(
                "You didn't specify a Notion DB ID! Please enter it below"
            )
            return NOTION_TABLE_ID
        update.message.reply_text(
            "Looks like I have both Integration Token and Database ID."
            "Try to forward some messages here and they'll appear in your database!"
        )
        return FINISH
    except NoResultFound:

        conn = engine.connect()
        query = db.insert(tbl).values(tg_user_id=str(uid))
        ResultProxy = conn.execute(query)
        logger.info(ResultProxy)
        conn.close()

    update.message.reply_markdown(
        "Hi! Please send notion integration token."
        "It can be found using step 1 & 2 of instructions: https://developers.notion.com/docs/getting-started",
    )

    return NOTION_TOKEN


def notion_token(update: Update, context: CallbackContext):
    user = update.message.from_user
    logger.info("Token of %s: %s", user.first_name, update.message.text)

    conn = engine.connect()
    query = (
        db.update(tbl)
        .values(notion_token=update.message.text)
        .where(tbl.columns.tg_user_id == str(update.message.from_user.id))
    )
    conn.execute(query)
    conn.close()

    update.message.reply_markdown(
        "Got it! Now I need an ID of the table where you want me to save the messages."
        "You can find it from URL of the database: `https://www.notion.so/my-base/*DB_ID_HERE*?v=...`"
        "Your database *must* have these fields: `Name`, `Tags` (multiselect), `URL` (type url) - all case-sensitive."
    )

    return NOTION_TABLE_ID


def notion_table_id(update: Update, context: CallbackContext):
    user = update.message.from_user
    logger.info("Table ID of %s: %s", user.first_name, update.message.text)

    conn = engine.connect()
    query = (
        db.update(tbl)
        .values(notion_db=update.message.text)
        .where(tbl.columns.tg_user_id == str(update.message.from_user.id))
    )
    conn.execute(query)
    conn.close()

    update.message.reply_markdown(
        "Got it! Now try to forward some messages here and they'll appear in your database!"
    )

    return FINISH


def finish(update: Update, context: CallbackContext):
    logger.info("finished")

    with Session(engine) as s:
        res = s.query(tbl).filter_by(tg_user_id=str(update.message.from_user.id)).one()

        create_page(res.notion_token, res.notion_db, update.message)
        s.close()

    update.message.reply_text("Saved successfully!")

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text("Cancel initiated", reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def main():

    updater = Updater(TG_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(Filters.forwarded, finish),
        ],
        states={
            NOTION_TOKEN: [MessageHandler(Filters.regex("^(.+)$"), notion_token)],
            NOTION_TABLE_ID: [MessageHandler(Filters.regex("^(.+)$"), notion_table_id)],
            FINISH: [MessageHandler(Filters.forwarded, finish)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
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
