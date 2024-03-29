#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# PoGoAntiSpam Bot

# Copyright (C) 2022  @ChrisM431 (Telegram)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Simple Python Anti Spam Bot Implementation"""
# pylint: disable=line-too-long,bad-continuation,global-statement

from datetime import datetime
import threading
import json
import configparser
import logging
import os
import sys
import MySQLdb
import numpy as np
from joblib import load

from telegram import (ParseMode, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          CallbackQueryHandler)

# Constants #
CONFIG_NAME = 'pogoantispambot.ini'  # local
VERSION = 1.0
PYTHON_VERSION = sys.version_info
# --------- #

# Config & Logging
CONFIG = None
GROUP_ID = 0
ADMINS = 0
UPDATER = None
LOGGER = None
WATCHED_GROUPS = 0

def reset_config():
    """Read config"""
    global CONFIG, ADMINS, GROUP_ID, LOGGER
    CONFIG = configparser.ConfigParser(allow_no_value=True)
    CONFIG.read(CONFIG_NAME)
    GROUP_ID = CONFIG['TELEGRAM']['bot_group_id']
    ADMINS = read_config_int_list('TELEGRAM', 'bot_admins_ids')

    # Enable logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                level=logging.INFO,
                filename=CONFIG['SYSTEM']['sys_log_dir'])
    LOGGER = logging.getLogger(__name__)


def dbglog(message):
    """Print Debug Logging in the file"""
    if int(CONFIG['SYSTEM']['sys_enable_debug_log']) == 1:
        logging.info(message)
    else:
        print(message)

class DB:
    """Database operations class"""
    conn = None

    def connect(self):
        """Connect to the Database using the given credentials"""
        self.conn = MySQLdb.connect(host=CONFIG['DATABASE']['db_host'],
                                    user=CONFIG['DATABASE']['db_user'],
                                    passwd=CONFIG['DATABASE']['db_password'],
                                    db=CONFIG['DATABASE']['db_name'],
                                    use_unicode=True,
                                    charset="utf8")

    def query(self, sql):
        """Execute the Query"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
        except (AttributeError, MySQLdb.OperationalError):
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute(sql)
        return cursor

    def commit(self):
        """Commit the query"""
        try:
            self.conn.commit()
        except (AttributeError, MySQLdb.OperationalError):
            self.connect()
            self.conn.commit()


CLF = None

def tail(_f, lines=1, _buffer=4098):
    """Tail a file and get X lines from the end

    Returns:
    last x lines"""
    _f = open(_f, "r")
    # place holder for the lines found
    lines_found = []

    # block counter will be multiplied by buffer
    # to get the block size from the end
    block_counter = -1

    # loop until we find X lines
    while len(lines_found) < lines:
        try:
            _f.seek(block_counter * _buffer, os.SEEK_END)
        except IOError:  # either file is too small, or too many lines requested
            _f.seek(0)
            lines_found = _f.readlines()
            break

        lines_found = _f.readlines()

        # decrement the block counter to get the
        # next X bytes
        block_counter -= 1

    return lines_found[-lines:]


def init_neural_net():
    """Load and initialize the trained neural network"""
    global CLF
    CLF = load('trained_sklearn_3d.joblib')

def display_start(update, context):
    """Refactored start message"""
    keyboard = [
        [InlineKeyboardButton("Status", callback_data='status'),
         InlineKeyboardButton("Statistics", callback_data='statistics')],
        [InlineKeyboardButton("Show Log", callback_data='log'),
         InlineKeyboardButton("Show Blacklist", callback_data='show_blacklist')],
        [InlineKeyboardButton("Restart", callback_data='restart')]
                ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(text=CONFIG['MESSAGE']['message_disclaimer'],
                    chat_id=update.message.chat_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup)

def start(update, context):
    """/start Command Handler"""
    dbglog('Bot started by ' + str(update.message.from_user.username))
    display_start(update, context)

def button(update, context):
    """Global InlineButton Handler"""
    query = update.callback_query
    option = query.data

    if option == 'start':
        display_start(update, context)
        return

    if option == 'restart':
        start_bot(restart=True)
        return

    if option == 'status':
        text = 'Updater running: {}'.format(UPDATER.running)
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=None)
        return

    if option == 'log':
        text_tailed = tail(CONFIG['SYSTEM']['sys_log_dir'], 5)
        text = ""
        for item in text_tailed:
            text = text + item + "\n"
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=None)
        return

    if 'kick:' in option:
        user_id = option.split(':')[2]
        name = option.split(':')[1]
        chat_id = option.split(':')[3]
        # kick user
        ret = context.bot.kick_chat_member(
            chat_id=chat_id,
            user_id=user_id
        )
        #text = "User {} aus Chat {} entfernt".format(name,chat_id)
        text = query.message.text + "\n\n"
        if ret:
            try:
                chat_obj = context.bot.get_chat(chat_id)
                chat_id = chat_obj.title
                #print(chat_obj.title)
            except Exception as _:
                chat_id = chat_id
            text = text + CONFIG['BOT']['bot_message_user_removed'].format(name, chat_id)
        else:
            text = text + "Kicking {} failed".format(name)

        context.bot.edit_message_text(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=None)
        return

    if 'unban:' in option:
        _db = DB()
        user_id = option.split(':')[2]
        name = option.split(':')[1]
        chat_id = option.split(':')[3]
        # unban user
        _return = context.bot.unban_chat_member(
            chat_id=chat_id,
            user_id=user_id
        )
        if _return:
            sql = """INSERT INTO `suspicious_messages` \
                (`user_id`, `group_id`, `message`) \
                VALUES ('{}','{}',{!a})
                """.format(user_id, chat_id, 'save message due to unbanning')
            _db.query(sql)
            _db.commit()
            text = CONFIG['BOT']['bot_message_user_unbanned'].format(name, chat_id)
        else:
            text = 'Error unbanning <a href="tg://user?id=' + str(user_id) + '">' + str(name) + '</a>'
        context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=None)
        return

    if option == 'show_blacklist':
        text = '<b>Blacklist:</b>\n\n' + ', '.join(json.loads(CONFIG['BOT']['bot_blacklist']))
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=None)
        return

    if option == 'statistics':
        _db = DB()
        sql_messages = "SELECT COUNT(*) FROM suspicious_messages"
        cursor = _db.query(sql_messages)
        result_messages = cursor.fetchone()[0]
        sql_spam_detected = "SELECT COUNT(*) FROM kicked_users"
        cursor = _db.query(sql_spam_detected)
        result_spam = cursor.fetchone()[0]
        text = '<b>Statistics:</b>\n\n'
        text = text + 'Number of groups: {}\n'.format(WATCHED_GROUPS)
        text = text + 'Total Messages:  {}\n'.format(result_messages)
        text = text + 'Spam Filtered:  {}'.format(result_spam)

        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=None)
        return

def removekeyword(update, context):
    """Remove a blacklist entry"""
    #print("args: ",context.args)
    if len(context.args) < 1:
        text = '<b>Blacklist:</b>\n\n' + ', '.join(json.loads(CONFIG['BOT']['bot_blacklist']))
        context.bot.send_message(text=text,
                    chat_id=update.message.chat_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=None)
    else:
        for word in context.args:
            remove_blacklist_entry(word)

        text = 'Removed entries [{}] from Blacklist\n\nNew Blacklist:\n{}'.format(
            ', '.join(str(x) for x in context.args),
            ', '.join(json.loads(CONFIG['BOT']['bot_blacklist'])))
        context.bot.send_message(text=text,
                    chat_id=update.message.chat_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=None)

def addkeyword(update, context):
    """Add a blacklist entry"""
    #print("args: ",context.args)
    if len(context.args) < 1:
        text = '<b>Blacklist:</b>\n\n' + ', '.join(json.loads(CONFIG['BOT']['bot_blacklist']))
        context.bot.send_message(text=text,
                    chat_id=update.message.chat_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=None)
    else:
        for word in context.args:
            add_blacklist_entry(word)

        text = 'Added entries [{}] to Blacklist\n\nNew Blacklist:\n{}'.format(
            ', '.join(str(x) for x in context.args),
            ', '.join(json.loads(CONFIG['BOT']['bot_blacklist'])))
        context.bot.send_message(text=text,
                    chat_id=update.message.chat_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=None)

def print_groups(update, context):
    """Get group names for all ids, may take a while to load properly"""
    grouplist = [int(x) for x in CONFIG.get('TELEGRAM', 'bot_watch_group_ids').split(',')]
    group_names_list = []
    for group_id in grouplist:
        try:
            chat_obj = context.bot.get_chat(group_id)
            group_names_list.append("{}: {}".format(chat_obj.title, group_id))
            #print(chat_obj.title)
        except Exception as _:
            group_names_list.append(str(group_id))
            #print("Err: " + str(group_id))

    text = '<b>Groups:</b>\n\n' + "\n".join(group_names_list)
    context.bot.send_message(text=text,
        chat_id=update.message.chat_id,
        parse_mode=ParseMode.HTML,
        reply_markup=None)


def addgroup(update, context):
    """Add a group by its ID"""
    if len(context.args) > 0:
        for _group_id in context.args:
            add_group_entry(_group_id)

        text = 'Added entries {} to Groups'.format(
            json.dumps(context.args))
        context.bot.send_message(text=text,
                    chat_id=update.message.chat_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=None)
    print_groups(update, context)

def removegroup(update, context):
    """Remove a group by its ID"""
    if len(context.args) > 0:
        for _group_id in context.args:
            remove_group_entry(_group_id)

        text = 'Removed entries {} from Groups'.format(
            json.dumps(context.args))
        context.bot.send_message(text=text,
                    chat_id=update.message.chat_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=None)
    print_groups(update, context)


def add_group_entry(entry):
    """Add a group entry"""
    grouplist = [int(x) for x in CONFIG.get('TELEGRAM', 'bot_watch_group_ids').split(',')]
    grouplist.append(int(entry))
    grouplist = '{}'.format(','.join(str(x) for x in grouplist))
    edit_config('TELEGRAM', 'bot_watch_group_ids', grouplist)

def remove_group_entry(entry):
    """Remove a group entry"""
    grouplist = [int(x) for x in CONFIG.get('TELEGRAM', 'bot_watch_group_ids').split(',')]
    grouplist.remove(int(entry))
    grouplist = '{}'.format(','.join(str(x) for x in grouplist))
    edit_config('TELEGRAM', 'bot_watch_group_ids', grouplist)

def remove_blacklist_entry(entry):
    """Remove a certain blacklist entry"""
    blacklist = read_config_raw('BOT', 'bot_blacklist')
    blacklist.remove(entry)
    #print("blacklist: ",blacklist)
    blacklist = '["{}"]'.format('","'.join(str(x) for x in blacklist))
    edit_config('BOT', 'bot_blacklist', blacklist)

def add_blacklist_entry(entry):
    """Add a keyword to the blacklist"""
    blacklist = read_config_raw('BOT', 'bot_blacklist')
    blacklist.append(entry)
    blacklist = '["{}"]'.format('","'.join(str(x) for x in blacklist))
    edit_config('BOT', 'bot_blacklist', blacklist)

def edit_config(section, element, value):
    """Edit and write back element in config file"""
    CONFIG.set(section, element, value)
    with open(CONFIG_NAME, "w") as _f:
        CONFIG.write(_f)
    # Reread config
    reset_config()

def read_config_int_list(section, element):
    """Read formatted config"""
    if CONFIG.get(section, element):
        return [int(x) for x in CONFIG.get(section, element).split(',')]
    return []

def read_config_raw(section, element):
    """Read config value"""
    return json.loads(CONFIG[section][element])

def handle_new_users(update, context):
    """Keep track of joined users"""
    #print("in handle_new_users")
    _db = DB()
    for user in update.message.new_chat_members:
        #print(str(user.id), " joined")
        dbglog("{} joined".format(str(user.id)))
        # Add to DB
        sql = """INSERT INTO suspicious_users(`user_id`, `group_id`)
        SELECT '{}','{}' FROM DUAL
        WHERE NOT EXISTS (SELECT id FROM suspicious_users
        WHERE user_id = '{}')""".format(user.id,
                              update.message.chat_id,
                              user.id)
        _db.query(sql)
        _db.commit()
    # Remove Status Messages
    if CONFIG.getboolean('BOT', 'bot_remove_service_messages'):
        update.message.delete()


def handle_edited_messages(update, context):
    """Handle the edited messages"""
    user_id = update.edited_message.from_user.id
    message = update.edited_message
    #print (str(user_id)," edited the message to ", message.text)
    if message.text is not None:
        process_message(update, context, message, message.text, user_id)

    # Handle Pictures
    if message.caption is not None:
        process_message(update, context, message, message.caption, user_id)


def handle_messages(update, context):
    """Handle the incoming sent message by the users"""
    user_id = update.message.from_user.id
    message = update.message
    #print (str(user_id)," sent: ", message)
    if message.text is not None:
        process_message(update, context, message, message.text, user_id)

    # Handle pictures
    if message.caption is not None:
        process_message(update, context, message, message.caption, user_id)

def check_user(update, context, chat_id, user_id):
    """Check the user before processing the message

    Don't look at administrator's or whitelist user's messages"""
    chat = context.bot.get_chat(chat_id)
    chat_admins = chat.get_administrators()
    chat_admins_ids = [x.user.id for x in chat_admins]

    whitelist_users = read_config_int_list('BOT', 'bot_whitelist_users')
    if user_id in chat_admins_ids + whitelist_users:
        return False
    return True


def process_message(update, context, message, message_text, user_id):
    """Process and handle the incoming message by the neural network

    Parameters:
    message_text, user_id
    """
    #print("Message: {}\n".format(message_text))
    # Check user if need to process message is present
    should_process = check_user(update, context, message.chat_id, user_id)
    if not should_process:
        return

    _db = DB()

    # Convert Text to ascii
    message_text = message_text.encode('ascii', 'replace').decode()
    message_text = message_text.lower()

    # Process Data
    features = []
    # [1] = blacklist
    bad_shortener = json.loads(CONFIG['BOT']['bot_blacklist'])
    matches = [x for x in bad_shortener if x in message_text]
    features.append(len(matches))

    # [2] = joined_days
    sql = "SELECT DATEDIFF(NOW(),date) FROM `suspicious_users` WHERE `user_id` = '{}'".format(user_id)
    cursor = _db.query(sql)
    result = cursor.fetchone()
    if result is None:
        features.append(10)  # Not in suspicous users
    else:
        features.append(result[0])  # get joined days

    # [3] = num messages
    sql = "SELECT count(*) FROM `suspicious_messages` WHERE `user_id` = '{}'".format(user_id)
    cursor = _db.query(sql)
    result = cursor.fetchone()
    if result is None:
        features.append(0)  # Nothing posted yet
    else:
        features.append(result[0])  # message count

    #print(features)
    _x = np.array(features).reshape(1, -1)
    y_pred = CLF.predict(_x)

    # Uncomment to track messages via file
    #dbglog("User: {} - predict: {}{} - Message: {}".format(str(user_id),str(y_pred),str(features),message_text))
    if y_pred == 1:
        # Spam
        now = datetime.now()
        spammer = ""
        if message.from_user is not None:
            spammer = message.from_user.first_name
        else:
            spammer = user_id
        # Track spam in file
        dbglog("Spam detected: {} ({}) - {}".format(str(spammer), str(features), message_text))

        # Group message output
        spam_msg = ""
        spam_msg = spam_msg + "<b>Spam detected!</b> " + now.strftime("%d.%m.%Y - %H:%M:%S") + "\n"
        spam_msg = spam_msg + "<b>Chat: " + update.message.chat.title + "</b>\n"
        spam_msg = spam_msg + '<a href="tg://user?id=' + str(user_id) + '">' + str(spammer) + '</a>\n\n'

        # Truncate for group message
        spam_chat_message = (message_text[:23] + '..') if len(message_text) > 25 else message_text
        spam_msg = spam_msg + spam_chat_message + "\n\n"

        # Information about matched words
        spam_msg = spam_msg + "Keywords matched: " + ', '.join(matches) + "\n"
        # Features
        spam_msg = spam_msg + "Features: " + str(features)

        reply_markup = None
        # Ban option
        if CONFIG.getboolean('BOT', 'bot_auto_ban'):
            # Kick user
            context.bot.kick_chat_member(
                chat_id=message.chat.id,
                user_id=user_id
            )
            # Notify group chat
            text = CONFIG['BOT']['bot_message_user_removed'].format(spammer, update.message.chat.title)
            context.bot.send_message(
                chat_id=GROUP_ID,
                message_id=message.message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=None)
            keyboard = [
                [InlineKeyboardButton(
                    (CONFIG['BOT']['bot_message_unban_user'].format(spammer)),
                    callback_data='unban:'+spammer+':'+str(user_id)+':'+str(message.chat.id))
                    ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            keyboard = [
                [InlineKeyboardButton(
                    (CONFIG['BOT']['bot_message_remove_user'].format(spammer)),
                    callback_data='kick:'+spammer+':'+str(user_id)+':'+str(message.chat.id))
                    ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

        # Send message to group
        context.bot.send_message(
            chat_id=GROUP_ID,
            text=spam_msg,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
            reply_markup=reply_markup)

        if CONFIG.getboolean('BOT', 'bot_forward_message_to_group'):
            # Forward message to admin group
            context.bot.forward_message(
                chat_id=GROUP_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )

        # delete message
        context.bot.delete_message(
            chat_id=message.chat.id,
            message_id=message.message_id
        )

        # save in DB
        sql = """INSERT INTO `kicked_users`(`user_id`, `chat_id`, `time`, `message`)
        VALUES ('{}','{}',NOW(),{!a})""".format(user_id, message.chat.id, str(y_pred)+str(features)+' '+message_text)
        cursor = _db.query(sql)
        _db.commit()

    else:
        # Track all messages
        sql = """INSERT INTO `suspicious_messages` \
            (`user_id`, `group_id`, `message`) \
            VALUES ('{}','{}',{!a})
            """.format(user_id, message.chat.id, str(y_pred)+str(features)+' '+message_text)
        _db.query(sql)
        _db.commit()

def error(update, context):
    """Log Errors caused by Updates."""
    dbglog('Update "{}" caused error "{}"'.format(update, context.error))
    LOGGER.warning('Update "%s" caused error "%s"', update, context.error)

def restart_bot():
    """Restart bot"""
    global UPDATER
    UPDATER.stop()
    print("Updater halted")
    threading.Thread(target=start_bot(restart=False)).start()


def start_bot(restart=True):
    """Starts the updater"""
    global UPDATER, WATCHED_GROUPS
    if restart:
        threading.Thread(target=restart_bot).start()
        return

    # Init config
    reset_config()

    # Init Neural Network
    init_neural_net()

    UPDATER = Updater(CONFIG['TELEGRAM']['bot_api_key'],
                      request_kwargs={'read_timeout': 10, 'connect_timeout': 10},
                      use_context=True)

    # Get the dispatcher to register handlers
    _dp = UPDATER.dispatcher
    _dp.add_handler(CommandHandler('start', start, Filters.user(ADMINS)))
    _dp.add_handler(CommandHandler('removeblacklistword', removekeyword, Filters.user(ADMINS)))
    _dp.add_handler(CommandHandler('addblacklistword', addkeyword, Filters.user(ADMINS)))

    _dp.add_handler(CommandHandler('addgroup', addgroup, Filters.user(ADMINS)))
    _dp.add_handler(CommandHandler('removegroup', removegroup, Filters.user(ADMINS)))


    _dp.add_handler(CallbackQueryHandler(button))
    _dp.add_error_handler(error)

    # Get New Users
    group_ids = read_config_int_list('TELEGRAM', 'bot_watch_group_ids')
    for _group_id in group_ids:
        # New Users
        _dp.add_handler(MessageHandler(Filters.status_update & Filters.chat(_group_id), handle_new_users))
        # Edited Messages
        _dp.add_handler(MessageHandler(Filters.update.edited_message & Filters.chat(_group_id), handle_edited_messages))
        # All Messages
        _dp.add_handler(MessageHandler((Filters.update.message | Filters.forwarded) & Filters.chat(_group_id), handle_messages))

    WATCHED_GROUPS = len(group_ids)
    # Start the Bot
    UPDATER.start_polling()
    #UPDATER.idle()
    print("Updater started. Bot ready!")

def main():
    """main"""
    # Python Version check
    assert PYTHON_VERSION >= (3, 5)

    # Create the EventHandler and pass it your bot's token.
    start_bot(restart=False)

if __name__ == '__main__':
    main()
