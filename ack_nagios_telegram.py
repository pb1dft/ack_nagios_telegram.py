#!/usr/bin/env python3
"""
Set vim variables
vim: set expandtab tabstop=4 shiftwidth=4 softtabstop=4:
"""
"""
Simple Bot to acknowledge to nagios problems through Telegram messages.


Before Usage:
 - Edit the location of the command_file
 - Edit the allowed userlist based on the telegram users
 - Edit the token to the token of the correct bot
 - When run as a deamon edit the programs pid location
 
Usage:
sent /help to bot ;)
.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

command_file='/var/spool/nagios/cmd/nagios.cmd'
userlist = ['user1', 'user2']
bot_token = 'token'
pid_dir = '/tmp'

import logging, re, time

from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

import getopt, os, sys
from daemonize import Daemonize
from systemd import journal

# For debuggin purpose only
#from inspect import getmembers
#from pprint import pprint

# Enable logging
logging.basicConfig( format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger('ack_nagios_telegram')
logger.addHandler(journal.JournaldLogHandler())
logger.setLevel(logging.INFO)

def usage():
    print('use -f to stay on foreground\n-h to print this help')

# Define a few command handlers. These usually take the two arguments update and
# context.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}\!',
        reply_markup=ForceReply(selective=True),
    )

def info(update: Update, context: CallbackContext) -> None:
   user = update.effective_user
   update.message.reply_text('Userid: '+str(user.id)+'\nUsername: '+user.username+'\nFirst name: '+user.first_name+'\nLast name: '+user.last_name)

def chatinfo(update: Update, context: CallbackContext) -> None:
   chat = update.effective_chat
   update.message.reply_text('Name: '+str(chat.title)+'\nChat id: '+str(chat.id))

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('To acknowledge a problem, reply to the original problem message with !ack <comment>')
    update.message.reply_text('To get your telegram details type /info')


def acknowledge(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    """Check valid user"""
    #update.message.reply_text(update.message.chat.username)
    #pprint(getmembers(update.effective_message.from_user))
    if not str(update.effective_message.from_user.username) in userlist:
       update.message.reply_text(update.effective_message.from_user.username+" is not authorized to issue commands!")
       return
    if re.match(r'!ack', update.message.text):
        if re.search(r'\/', update.message.reply_to_message.text):
           try:
              orig = update.message.reply_to_message.text
              orig = re.search(r'([A-Za-z0-9\.-]+)\/([A-Za-z0-9\s\.\/]+):', orig)
              host = orig.group(1)
              service = orig.group(2)
              user = str(update.effective_message.from_user.first_name)
              comment = re.sub(r'!ack ', '', update.message.text)
              msg = "["+str(int(time.time())) + "] ACKNOWLEDGE_SVC_PROBLEM;"+host+";"+service+";2;1;0;"+user+";"+comment+"\n"
              #update.message.reply_text(msg)
              logger.info('Received message:')
              logger.info(msg)
              logger.info('Sending command to nagios')
              file1 = open(command_file, "w")
              file1.write(msg)
              file1.close()
              return 
           except:
              update.message.reply_text("Failed to process!")
              return
        elif re.search(r' ([A-Za-z0-9\.\-]+) \(([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\):', update.message.reply_to_message.text):
           try:
              orig = update.message.reply_to_message.text
              orig = re.search(r' ([A-Za-z0-9\.\-]+) \(([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\):', update.message.reply_to_message.text)
              host = orig.group(1)
              user = str(update.effective_message.from_user.first_name)
              comment = re.sub(r'!ack ', '', update.message.text)
              msg = "["+str(int(time.time())) + "] ACKNOWLEDGE_HOST_PROBLEM;"+host+";1;1;0;"+user+";"+comment+"\n"
              logger.info('Received message:')
              logger.info(msg)
              logger.info('Sending command to nagios')
              file1 = open(command_file, "w")
              file1.write(msg)
              file1.close()
              return 
           except:
              update.message.reply_text("Failed to process!")
              return
        else:
           update.message.reply_text("Could not determine type!")


def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(bot_token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("info", info))
    dispatcher.add_handler(CommandHandler("chatinfo", chatinfo))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, acknowledge))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf", ["help"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    for o, a in opts:
        if o == "-f":
            main()
            sys.exit()
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"
    myname=os.path.basename(sys.argv[0])
    pidfile='%s/%s.pid' % (pid_dir,myname)       # any name
    daemon = Daemonize(app=myname,pid=pidfile, action=main)
    daemon.start()
