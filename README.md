# lastfm-telegram-shouter
Posts scrobbles of users it's watching to a channel.

This uses [telepot](https://github.com/nickoala/telepot) as its telegram wrapper and [pylast](https://github.com/pylast/pylast) as its last.fm wrapper.

I made this as an exercise in threaded stuff, and because my friends and I thought it'd be cool to have a channel that shows what we're listening to.

---

Todo:

* Write a custom lastfm / *.fm wrapper that exposes more data at once so I can do with less api calls
* Make the posted messages prettier (if the link previews showed album art, I'd use that)
* Potentially say when someone has a song on repeat (maybe only say something every 5 scrobbles to avoid spam / potential duplicate messages)
* Possibly track artists/albums/tracks for the channel so stats can be posted daily on what's listened to
