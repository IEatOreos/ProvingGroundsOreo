Project Noble link test (Nov 18, test 3)
==========================================

What it is: a small test that checks whether two PCs running the mod can pass data to each other while you are both
in MCC. It is needed before Project Noble's search and vote can show up on a friend's screen. It does not change
your games or your install. It writes a log file and sends short test messages over MCC's own chat connection.

Who speaks first: only the friend's copy (the one with pglink_friend.txt in its folder) sends the first message. The
host's copy (no pglink_friend.txt) never messages anyone first; it only answers a PC whose link test spoke to it.
On a PC running the test, the test's messages are hidden from MCC. An MCC that isn't running it may crash when one
arrives, so use it only with the two of you in the lobby. No Xbox players.

1. Host: start MCC with the mod (anti-cheat off), wait for the main menu, and double-click pglink_load.exe. It should
   say "The link test is running in MCC". Then open your Halo: Reach custom game lobby.
2. Friend: start MCC with the mod, wait for the main menu, and double-click pglink_load.exe in your folder (the one
   with pglink_friend.txt). Only then join the host's lobby.
3. Stay in the lobby together for 2 minutes.
4. Play one match from the Project Noble tab. Stay through the carnage report and back to the lobby.
5. Close MCC.
6. Friend: send pglink.log from your folder to the host.

Run pglink_load.exe again each time you restart MCC, before joining. Deleting the folder removes the test.
