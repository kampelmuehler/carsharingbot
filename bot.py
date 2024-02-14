import logging
from pathlib import Path
from re import match
from typing import List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from backend import Backend

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

ALLOWED_IDS: List[int] = []  # containing user ids. Use @userinfobot to find
USERS: Tuple[str] = ()  # List[str] containing the names of the users in same order as user ids.
TOKEN: str = ''  # Add your telegram bot API token here
LOGBOOK_PATH: Path = Path(
    'logbook.json')  # Path to where the data will be stored
CURRENCY: str = "EUR"  # your local currency
DISTANCE_UNITS: str = "km"  # your local distance units
VOLUME_UNITS: str = "l"  # your local volume units for fuel

backend = Backend(people=USERS,
                  logbook_path=LOGBOOK_PATH,
                  currency=CURRENCY,
                  distance_units=DISTANCE_UNITS,
                  volume_units=VOLUME_UNITS)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Welcome!")


async def help_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """You can send the bot messages in the format:
Mileage Price Consumption

Examples:
Add 50 km/miles:
50
Mileage can also be negative for rectifications.

Fuel up after 600 miles/km for 60 of your currency:
600 60

Fuel up after 400 km/miles for 35 of your currency and 24 units of volume (eg. liters):
400 35 24

/print prints table of current period as well as total mileage and consumption
/reset deletes current period"""
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=help_text)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("OK", callback_data="reset"),
        InlineKeyboardButton("decline", callback_data="fail"),
    ]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Do you really want to delete the current period?",
        reply_markup=reply_markup)


async def current_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=backend.current_logbook_as_str(),
                                   parse_mode='MarkdownV2')
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=backend.get_total_mileage_and_cost_str())


def parse_text_command(person: str, command: str):
    parts = command.split(' ')
    if not all([match(r'^-?[0-9]+$', p) for p in parts]):
        return "All arguments must be numbers."
    parts = [int(p) for p in parts]
    if len(parts) == 1:
        backend.add_mileage(person, parts[0])
        return f"{person} has driven {parts[0]} {DISTANCE_UNITS}"
    elif 1 < len(parts) < 4:
        msg = backend.settle_bill(person, *parts)
        return msg
    else:
        return "There must be at least one number."


async def text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("OK", callback_data=update.message.text),
        InlineKeyboardButton("decline", callback_data="fail"),
    ]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    split_text = update.message.text.split(" ")
    reply = f"Distance: {split_text[0]} {DISTANCE_UNITS}\n"
    reply += f"Price: {split_text[1] if len(split_text) >= 2 else '-'} {CURRENCY}\n"
    reply += f"Fuel: {split_text[2] if len(split_text) >= 3 else '-'} {VOLUME_UNITS}"
    await update.message.reply_text(reply, reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()
    if query.data == "fail":
        pass
    elif query.data == "reset":
        backend.reset_period()
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Last period removed.")
    else:
        msg = parse_text_command(
            USERS[ALLOWED_IDS.index(update.effective_user.id)], query.data)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=msg,
                                       parse_mode='Markdown')
    await query.message.edit_reply_markup(None)  # remove keyboard


if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    user_filter = filters.User(ALLOWED_IDS)
    handlers = []
    handlers.append(CommandHandler('start', start, filters=user_filter))
    handlers.append(CommandHandler('reset', reset, filters=user_filter))
    handlers.append(CommandHandler('help', help_text, filters=user_filter))
    handlers.append(
        CommandHandler('print', current_period, filters=user_filter))
    handlers.append(
        MessageHandler(filters.TEXT & (~filters.COMMAND) & user_filter,
                       text_command))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handlers(handlers)
    application.run_polling()
