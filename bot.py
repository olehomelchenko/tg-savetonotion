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

import os
import logging
import yaml
from uuid import uuid1

from db_utils import get_table

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")

sql_string = os.environ.get("PG_STRING")
engine = db.create_engine(sql_string)
conn = engine.connect()

NOTION_TOKEN, NOTION_TABLE_ID, FINISH = range(3)

tbl = get_table(engine, conn, "notion_saver_dev")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext):
    reply_keyboard = [["Add Notion Token"]]
    uid = update.message.from_user.id

    query = db.insert(tbl).values(tg_user_id=str(uid))
    ResultProxy = conn.execute(query)
    logger.info(ResultProxy)

    update.message.reply_text(
        "Hi! Please send notion token below",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Notion Token?",
        ),
    )

    return NOTION_TOKEN


def notion_token(update: Update, context: CallbackContext):
    user = update.message.from_user
    logger.info("Token of %s: %s", user.first_name, update.message.text)

    query = db.update(tbl).values(notion_token=update.message.text)
    query.where(
        tbl.columns.tg_user_id==str(update.message.from_user.id)
    )
    conn.execute(query)

    update.message.reply_text(
        "Got it! Now I need an ID of the table where you want me to save the messages",
        reply_markup=ReplyKeyboardRemove(),
    )

    return NOTION_TABLE_ID


def notion_table_id(update: Update, context: CallbackContext):
    user = update.message.from_user
    logger.info("Table ID of %s: %s", user.first_name, update.message.text)

    query = db.update(tbl).values(notion_db=update.message.text)
    query.where(
        tbl.columns.tg_user_id==str(update.message.from_user.id)
    )
    conn.execute(query)

    update.message.reply_text(
        "Got it! Now try to forward some messages here",
        reply_markup=ReplyKeyboardRemove(),
    )

    return FINISH


def finish(update: Update, context: CallbackContext):
    logger.info("finished")

    message = update.message

    forwarded_from_messageid = message.forward_from_message_id
    forwarded_from_channelid = message.forward_from_chat.username
    channel_url = f"https://t.me/{forwarded_from_channelid}/{forwarded_from_messageid}"

    message_dict = message.to_dict()

    message_text = message_dict.get("text")

    message_yaml = yaml.dump(message_dict, allow_unicode=True)

    to_notion = {"url": channel_url, "text": message_text, "message_yaml": message_yaml}

    logger.info(to_notion)

    file_id = str(uuid1())
    with open(f"{file_id}.yaml", "w") as file:
        yaml.dump(message_dict, file, allow_unicode=True)

    update.message.reply_text(
        "that's all, now try to forward any message here",
        reply_markup=ReplyKeyboardRemove(),
    )

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
