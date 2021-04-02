Try to implement a "SMART HOME" system with a corresponding app.

Goal is to learn full-stack and use embedded devices around the home to get data.
I'm using MQTT protocol to get data to a central device in the home, but
most of the time you're lazy and don't want to get up and look at that device.

To solve this, make a pretty website. Maybe implement a database to log temperature/humidity, this data
could be fun analyzing with the respect of time.

Inspiration taken from Tech with Tim youtube tutorial. Mostly to get started with flask and general structure.

For the curious. DB doesn't store any sensitive data. If you like to learn how to query a .db file
and then do some datascience, go ahead!


Project grew even bigger than expected. Different kinds of api's. Lot's of JS and CSS.
Optimizations that may be too much but optimizing data structures and reducing data transmitted between server-client could be worth it in the long run.

Forcing local usage for more "sensitive" data related stuff at the moment, but might deploy it online with full auth. Just need to solve https the painless way...

There will not be consistency in the code due to learning. Mostly to see how different methods/functions to do the same task.


Update April.
Splitting up the parts into smaller and more focused modules. Too many dependencies that is not necessary.