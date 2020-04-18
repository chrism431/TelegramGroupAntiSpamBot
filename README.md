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

# Bot Execution
Simply start via 

`sudo python3 pogoantispambot.py `
