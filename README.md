[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=PW9CERN8VCHHC)

# TelegramGroupAntiSpamBot
Simple Telegram anti-spam Bot written in Python to prevent Crypto/Finance/... spam messages via a simple method.

# Requirements
## Telegram Requirements
- Bot API Key

- Admin Group (ban users, see notifications)

- Group IDs (add @RawDataBot to group and note chat_id)

## Python requirements
Python 3.x
(Python >3.7.x recommended)

## Libraries
- json

- configparser

- mysqlclient

- scikit-learn

- numpy

- joblib

- python-telegram-bot

## MySQL - Database
see [anti_spam.sql](SQL/anti_spam.sql)

# Setup
- Configure MySQL Database with the included SQL file

- Clone the repository to the server's destination

- Create Bot ID via [Telegram's BotFather bot](https://core.telegram.org/bots#6-botfather)

- Edit and fill all fields in [the config file](python/pogoantispambot.ini) 

- Add Bot to group which should be watched and make it administrator so it can delete messages and add it to the reporting group so it can notify the group administrators about a detected spam message

# Bot Execution
## Python
Simply start via 

`python3 pogoantispambot.py `

## Telegram
### Commands
`/start`  Start the bot and see initial menu

`/addblacklistword <word>`  Add a blacklisted word

`/removeblacklistword <word>`  Remove a blacklisted word

`/addgroup <group_id>`  Add a group id to the list of groups - reboot bot after changing the groups

`/removegroup <group_id>`  Remove a group id from the list of groups - reboot bot after changing the groups
