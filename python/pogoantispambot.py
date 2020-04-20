#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# PoGoAntiSpam Bot

# Copyright (C) 2020  @ChrisM431 (Telegram)

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

# Constants #
config_name = 'pogoantispambot.ini'  # local
VERSION = 1.0
# --------- #

from datetime import datetime
import json
import configparser
import logging
import MySQLdb
import numpy as np
import re
import os
from joblib import load

from telegram.utils.helpers import escape_markdown
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineQueryResultArticle,
                      ParseMode, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, InlineQueryHandler, CallbackQueryHandler)
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)

# Init ConfigParser
config = configparser.ConfigParser()
config.read(config_name)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO,
                    filename=config['SYSTEM']['sys_log_dir'])

logger = logging.getLogger(__name__)


def dbglog(message):
    """Print Debug Logging in the file"""
    if int(config['SYSTEM']['sys_enable_debug_log']) == 1:
        logging.info(message)


group_id = config['TELEGRAM']['bot_group_id']

admins = json.loads(config['TELEGRAM']['bot_admins_ids'])

class DB:
    """Database operations class"""
    conn = None

    def connect(self):
        """Connect to the Database using the given credentials"""
        self.conn = MySQLdb.connect(host=config['DATABASE']['db_host'],
                                    user=config['DATABASE']['db_user'],
                                    passwd=config['DATABASE']['db_password'],
                                    db=config['DATABASE']['db_name'],
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


clf = None

def tail(f, lines=1, _buffer=4098):
    """Tail a file and get X lines from the end
    
    Returns:
    last x lines"""
    f = open(f, "r")
    # place holder for the lines found
    lines_found = []

    # block counter will be multiplied by buffer
    # to get the block size from the end
    block_counter = -1

    # loop until we find X lines
    while len(lines_found) < lines:
        try:
            f.seek(block_counter * _buffer, os.SEEK_END)
        except IOError:  # either file is too small, or too many lines requested
            f.seek(0)
            lines_found = f.readlines()
            break

        lines_found = f.readlines()

        # decrement the block counter to get the
        # next X bytes
        block_counter -= 1

    return lines_found[-lines:]


def init_neural_net():
    """Load and initialize the trained neural network"""
    global clf
    clf = load('trained_sklearn_3d.joblib')
    print("Bot ready!")


def start(update, context):
    """/start Command Handler"""
    logging.info('Bot started by ' + str(update.message.from_user.username))
    keyboard = [
                [InlineKeyboardButton("Status", callback_data='status'),
                InlineKeyboardButton("Statistics", callback_data='statistics')],
                [InlineKeyboardButton("Show Log", callback_data='log'),
                InlineKeyboardButton("Show Blacklist", callback_data='show_blacklist')]                 
                 ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(text=config['MESSAGE']['message_disclaimer'],
                             chat_id=update.message.chat_id,
                             parse_mode=ParseMode.HTML,
                             reply_markup=reply_markup)

def button(update, context):
    """Global InlineButton Handler"""
    query = update.callback_query
    option = query.data        

    if 'status' in option:
        # TODO: make better
        text = 'Status ✅'
        context.bot.send_message(
					chat_id=query.message.chat_id,
					text=text,                					
					parse_mode=ParseMode.HTML,
					disable_web_page_preview=True,
					reply_markup=None)
        return

    if 'log' in option:
        text_tailed = tail(config['SYSTEM']['sys_log_dir'],4)
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

    if 'ban' in option:
        user_id = option.split(':')[2]
        name = option.split(':')[1]
        chat_id = option.split(':')[3]
        # kick user
        context.bot.kick_chat_member(
           chat_id=chat_id,
           user_id=user_id
        )
        #text = "User {} aus Chat {} entfernt".format(name,chat_id)
        text = config['BOT']['bot_message_remove_user'].format(name,chat_id)
        context.bot.edit_message_text(
					chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
					text=text,                					
					parse_mode=ParseMode.HTML,
					disable_web_page_preview=True,
					reply_markup=None)        
        return

    if 'show_blacklist' in option:
        text = '<b>Blacklist:</b>\n\n' + ', '.join(json.loads(config['BOT']['bot_blacklist']))
        context.bot.send_message(
					chat_id=query.message.chat_id,
					text=text,                					
					parse_mode=ParseMode.HTML,
					disable_web_page_preview=True,
					reply_markup=None)
        return

    if 'statistics' in option:
        db = DB()
        sql_messages = "SELECT COUNT(*) FROM suspicious_messages"
        cursor = db.query(sql_messages)
        result_messages = cursor.fetchone()[0]
        sql_spam_detected = "SELECT COUNT(*) FROM kicked_users"
        cursor = db.query(sql_spam_detected)
        result_spam = cursor.fetchone()[0]
        text = '<b>Statistics:</b>\n\n'
        text = text + 'Number of groups: {}\n'.format(len(json.loads(config['TELEGRAM']['bot_watch_group_ids'])))
        text = text + 'Total Messages:  {}\n'.format(result_messages)
        text = text + 'Spam Filtered:  {}'.format(result_spam) 

        context.bot.send_message(
					chat_id=query.message.chat_id,
					text=text,                					
					parse_mode=ParseMode.HTML,
					disable_web_page_preview=True,
					reply_markup=None)
        return


def handle_new_users(update, context):
    """Keep track of joined users"""
    db = DB()
    for user in update.message.new_chat_members:
        #print(str(user.id), " joined")
        dbglog("{} joined".format(str(user.id)))
        # Add to DB
        sql = """INSERT INTO suspicious_users(`user_id`, `group_id`)
        SELECT '{}','{}'
        WHERE NOT EXISTS (SELECT id FROM suspicious_users
        WHERE user_id = '{}')""".format(user.id,
                              update.message.chat_id,
                              user.id)
        db.query(sql)
        db.commit()


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


def process_message(update, context, message, message_text, user_id):
    """Process and handle the incoming message by the neural network
    
    Parameters:
    message_text, user_id
    """
    #print("Message: {}\n".format(message_text))
    
    # Convert Text to ascii
    message_text = message_text.encode('ascii', 'replace').decode()
    message_text = message_text.lower()
    
    # Process Data
    features = []
    # [1] = blacklist
    bad_shortener = json.loads(config['BOT']['bot_blacklist'])
    features.append(len([x for x in bad_shortener if x in message_text]))    

    # [2] = joined_days
    db = DB()
    sql = "SELECT DATEDIFF(NOW(),date) FROM `suspicious_users` WHERE `user_id` = '{}'".format(user_id)
    cursor = db.query(sql)
    result = cursor.fetchone()    
    if result is None:
        features.append(10)  # Not in suspicous users
    else:
        features.append(result[0])  # get joined days
    
    # [3] = num messages
    db = DB()
    sql = "SELECT count(*) FROM `suspicious_messages` WHERE `user_id` = '{}'".format(user_id)
    cursor = db.query(sql)
    result = cursor.fetchone()    
    if result is None:
        features.append(0)  # Nothing posted yet
    else:
        features.append(result[0])  # message count
    
    #print(features)
    X = np.array(features).reshape(1, -1)
    y_pred = clf.predict(X)
    
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
        dbglog("Spam detected: {} ({}) - {}".format(str(spammer),str(features),message_text))
        #print("Spam detected: {} ({}) - {}".format(str(spammer),str(features),message_text))
        
        # Group message output
        spam_msg = ""
        spam_msg = spam_msg + "<b>Spam detected!</b> " + now.strftime("%d.%m.%Y - %H:%M:%S") + "\n"
        spam_msg = spam_msg + "<b>Chat: " + update.message.chat.title + "</b>\n"
        spam_msg = spam_msg + '<a href="tg://user?id=' + str(user_id) + '">' + str(spammer) + '</a>\n\n'
        
        # Truncate for group message
        spam_chat_message = (message_text[:23] + '..') if len(message_text) > 25 else message_text
        spam_msg = spam_msg + spam_chat_message

        # Ban option
        keyboard = [[InlineKeyboardButton((config['BOT']['bot_message_remove_user'].format(spammer)), callback_data='ban:'+spammer+':'+str(user_id)+':'+str(message.chat.id))]]

        reply_markup = InlineKeyboardMarkup(keyboard)        

        # send message to group
        context.bot.send_message(
            chat_id=group_id,
            text=spam_msg,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
            reply_markup=reply_markup)
        # delete message
        context.bot.delete_message(
            chat_id=message.chat.id,
            message_id=message.message_id
        )

        # save in DB
        sql = """INSERT INTO `kicked_users`(`user_id`, `chat_id`, `time`, `message`)
        VALUES ('{}','{}',NOW(),{!a})""".format(user_id, message.chat.id, str(y_pred)+str(features)+' '+message_text)
        cursor = db.query(sql)
        db.commit()

    else:
        # Track all messages        
        sql = """INSERT INTO `suspicious_messages` \
            (`user_id`, `group_id`, `message`) \
            VALUES ('{}','{}',{!a})
            """.format(user_id, message.chat.id, str(y_pred)+str(features)+' '+message_text)   
        db.query(sql)
        db.commit()     


def remove_service_pin_message(update, context):
    """Remove the service messages, like 'User joined the group'"""
	update.message.delete()                  


def error(update, context):
    """Log Errors caused by Updates."""
    print('Update "{}" caused error "{}"'.format(update, context.error))
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """main"""
    # Init Neural Network
    init_neural_net()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(config['TELEGRAM']['bot_api_key'],
                      request_kwargs={'read_timeout': 10, 'connect_timeout': 10},
                      use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start, Filters.user(admins)))
    dp.add_handler(CallbackQueryHandler(button))    

    dp.add_error_handler(error)

    # Get New Users
    group_ids = json.loads(config['TELEGRAM']['bot_watch_group_ids'])
    for group_id in group_ids:
        # New Users
        dp.add_handler(MessageHandler(Filters.status_update.new_chat_members & Filters.chat(group_id), handle_new_users))
        # Edited Messages
        dp.add_handler(MessageHandler(Filters.update.edited_message & Filters.chat(group_id), handle_edited_messages))
        # All Messages
        dp.add_handler(MessageHandler((Filters.update.message | Filters.forwarded) & Filters.chat(group_id), handle_messages))
        # Remove Status Messages
        #dp.add_handler(MessageHandler(Filters.status_update & Filters.chat(group_id), remove_service_pin_message))    

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
