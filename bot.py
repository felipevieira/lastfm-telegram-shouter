import pylast
import sqlite3
import sys
import telepot
import collections # queue won't suffice since I need an easy way to remove things
import threading
import time
import re


tgram_API_KEY = sys.argv[1]
fm_API_KEY = sys.argv[2]
fm_API_SECRET = sys.argv[3]
lock = threading.Lock()
fm_db = sqlite3.connect("fm.db", check_same_thread=False)
fm_cur = fm_db.cursor()
fm_cur.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, lastfm TEXT NOT     NULL)')
fm_db.commit()
queue = collections.OrderedDict()
# lock immediately so that the lastfm bot can go and build the shared queue first before the telegram bot processes anything
lock.acquire() 



def tgram_start(msg):
  bot.sendMessage(msg['chat']['id'], "Heya, this bot is the messenger for @last_fm. To get started, send your last.fm name with /addfm [name].")

def tgram_addfm(msg):
  '''Your username should be between 2 and 15 characters, begin with a letter and contain only letters, numbers, '_' or '-'.'''
  exists = fm_cur.execute("SELECT user_id FROM users WHERE user_id=?", (msg['from']['id'],)).fetchone()

  if (exists):
    bot.sendMessage(msg['chat']['id'], "Sorry, but you'll need to go remove your associated name with /rmfm first before you can add one (might support multiple accounts in the future)")
  else:
    result = re.match('^/addfm ([a-zA-Z][a-zA-Z0-9_-]{1,14})$', msg['text'].replace('@lastfm_channel_bot', ''))
  
    if (result != None):
      fmname = result.group(1)
      fmname_exists = fm_cur.execute("SELECT username FROM users WHERE lastfm=?", (fmname,)).fetchone()

      if (fmname_exists):
        username = ""
        if (fmname_exists[0] != ""):
          username = "@" + fmname_exists[0]
        else:
          username = "a user with no @ handle"
        bot.sendMessage("The given lastfm username is already in the database, and was added by " + username + ". If you believe this was in error, then contact the user, or if you cannot, contact @PandorasFox")
        return

      tgramHandle = ""
      if msg['from']['username']:
        tgramHandle=msg['from']['username']
        fm_cur.execute("INSERT INTO users values(?,?,?)", (msg['from']['id'], tgramHandle, fmname))
      fm_db.commit() # t_fm_db.commit()

      if (fmname in queue):
        print("somehow this guy was already in the queue")
        bot.sendMessage(msg['chat']['id'], "somehow that username was already in the watch queue, so no effect. (the username was added successfully; no one else had already claimed it)")
        return
      else:
        queue[fmname] = dict(scrobbles=0, artist='', track='', username=tgramHandle)
      bot.sendMessage(msg['chat']['id'], "username '" + fmname + "' added to the watchlist")
    else:
      bot.sendMessage(msg['chat']['id'], "No valid name found; a valid name is:\n2-15 characters;\nbegins with a letters;\ncontains only letters, numbers, '-' and '_'.")
     

def tgram_rmfm(msg):
  exists = fm_cur.execute("SELECT user_id, username, lastfm FROM users WHERE user_id=?", (msg['from']['id'],)).fetchone()

  if (exists):
    user_id = exists[0]
    username = exists[1]
    fmname = exists[2]

    print(exists)

    if (fmname in queue):
      del queue[fmname]

    fm_cur.execute("DELETE FROM users WHERE user_id=?", (msg['from']['id'],))
    bot.sendMessage(msg['chat']['id'], "Removed from watchlist successfully.")
  else:
    bot.sendMessage(msg['chat']['id'], "No record for you found; are you sure you had an account associated?")


def tgram_help(msg):
  bot.sendMessage(msg['chat']['id'], "where is your god now")

'''
handles a message sent to @lastfm_channel_bot

takes commands:
/help: prints a help message
/addFM: lets a user tie a last.fm name to their user id
  this needs to check and make sure they don't already have one tied to their user id
  also needs to check and make sure an account (1) exists and (2) isn't already tied to another user id
  needs to add the user to both the DB and the name to the end of the queue
      needs to store userID, @name, lastfm name
/rmFM: lets a user remove a last.fm account from their user id, takes no arguments
  remove row
    if row exists, also remove that name from the queue
'''

def handle(msg):
  content_type, chat_type, chat_id = telepot.glance(msg)
  print(content_type, chat_type, chat_id)
  
  lock.acquire()
  #t_fm_db = sqlite3.connect("fm.db")
  #t_fm_cur = t_fm_db.cursor()
  
  if (content_type == 'text'):
    message_words = msg['text'].strip().lower().split()
    
    if (msg['text'][0] != "/"):
      return
    else:
      if (message_words[0] == "/start"):
        tgram_start(msg)
      elif (message_words[0].replace("/addfm@lastfm_channel_bot", "/addfm") == "/addfm"):
        tgram_addfm(msg)
      elif (message_words[0].replace("/rmfm@lastfm_channel_bot", "/rmfm") == "/rmfm"):
        tgram_rmfm(msg)
      elif (message_words[0].replace("/help@lastfm_channel_bot", "/help") == "/help"):
        tgram_help(msg)
      elif (message_words[0].replace("/github@lastfm_channel_bot", "/github") == "/github"):
        bot.sendMessage(msg['chat']['id'], "https://github.com/Arcaena/lastfm-telegram-shouter")

  fm_db.commit()

  #t_fm_db.commit()
  #t_fm_db.close()

  lock.release()

'''kicks off the telegram bot thread'''

def tgram_bot():
  bot.message_loop(handle)

'''
the lastfm listener thread. It needs to init (build a queue from the db),
  then start its checks, with waits of 400ms between each
  needs to get a person's recently played, and if they are currently playing, get their # scrobbles
  needs to wait 200ms after each call since i dont think the api wrapper does that itself 
    (need to do a custom wrapper with this...)
  when sending a message to the group, it should:
    "@username is now scrobbling xxx by zzz!" or "[...] their 111st song, [xxx] by [zzz]!"
    maybe link to profiles

will eventually support other scrobbling services
'''
def lastfmListen():
  
  lastfm = pylast.LastFMNetwork(api_key=fm_API_KEY, api_secret=fm_API_SECRET)

  while True:
    
    if (queue):
      curUser = queue.popitem(last=False)
      newUserInfo = curUser[1]
      success = False

      print(curUser)
      user = lastfm.get_user(curUser[0])
      user_scrobbles = user.get_playcount()
      c_track = user.get_now_playing()
      userHandle = curUser[1].get('username')
    
      userURL = ""
      if (userHandle != ''):
        userURL = "http://telegram.me/" + userHandle
      else:
        userURL = "http://www.last.fm/user/" + curUser[0]

      if (c_track):
        c_url = c_track.get_url()
        c_artist = c_track.artist.name
        c_title = c_track.title

        print(user_scrobbles, c_track)

        track_prefix = "th"
        track_num = user_scrobbles + 1
        if (10 < (track_num % 100) < 14):
          pass # ignore the 11-13 for prefixes
        elif (track_num % 10 == 1):
          track_prefix = "st"
        elif (track_num %10 == 2):
          track_prefix = "nd"
        elif (track_num % 10 == 3):
          track_prefix = "rd"

        if (curUser[1].get('last post', 0) + 15 > time.time()):
          pass # timeout hasn't passed yet
        elif (curUser[1].get('artist') != c_artist or curUser[1].get('track') != c_title):
          bot.sendMessage("@last_fm", "User <a href='" + userURL + "'>" +  curUser[0] + "</a> is scrobbling their " + str(track_num) + track_prefix + " song: <a href = '" + c_url + "'>" + c_title + "</a> by " + c_artist + ".", parse_mode='HTML', disable_web_page_preview=True)
          success = True
        else:
          if (curUser[1].get('scrobbles') != user_scrobbles):
            bot.sendMessage("@last_fm", "User <a href='" + userURL + "'>" +  curUser[0] + "</a> is scrobbling their " + str(track_num) + track_prefix + " song: <a href = '" + c_url + "'>" + c_title + "</a> by " + c_artist + ".", parse_mode='HTML', disable_web_page_preview=True)
            success = True
        if (success):
          newUserInfo['artist'] = c_artist
          newUserInfo['track'] = c_title
          newUserInfo['scrobbles'] = user_scrobbles
          newUserInfo['last post'] = time.time()
      queue[curUser[0]] = newUserInfo
      time.sleep(1)

bot = telepot.Bot(tgram_API_KEY)

t = threading.Thread(target=tgram_bot)
t.daemon = True
t.start()

print("I have successfully spun off the telegram bot")

users = fm_cur.execute("SELECT lastfm, username  FROM users").fetchall()

for user in users:
  # lastfm username, artist name, track title, scrobble count
  # need to store all this so that if someone is on repeat we can tell if they're playing a new song or not
  # and when to announce
  # on bot init we just assume nothing since I'm not going to have the fm-side modify the sql db yet
  if (user[0] in queue):
    print("dude how is this person in the queue already")
  else:
    queue[user[0]] = dict(scrobbles=0, artist='', track='', username=user[1])

lock.release()


lastfmListen()

#except KeyboardInterrupt:
#  fm_db.commit()
#  fm_db.close()
#  sys.exit()

