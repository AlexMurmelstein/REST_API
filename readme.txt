The code in the main.py includes, from top to bottom: 

*A list of imports.

*A setup for the Flask and SQLite components.

*A login manager.

*SQLite database/flask MIXIN classes/tables, with a "User" and "Message" classes.

*A decorator function responsible for restring paths to authenticated users only; a non-authenticated will receive an error message. The decorator was added to the appropriate functions below.

*A general search function, without @path, with an "unread" optional parameter. This function will fetch all the messages sent to a specific user.

* Several authentication-related functions. One registering, another logging in, and yet another for log-out (inserted for the sake of order, for the log-in automatically logs out the signed-in user).

* Several functions directly dealing with the messages in the database. One for writing a message; two (merely calling the general search from above) for getting all/all unread messages sent to a user; one serving a single message, by id provided or, alternatively, the earliest unread message available, when no id is given. Finally, a delete function which delets a selected message by id, provided the logged-in user is either the sender or the receiver of that message. 

#General Note: Appropriate error/forbidden messages were added to the functions. For the sake of having clear error messages, the code is somewhat cumbersome. I prefered clear errors in each case (user forbidden to access message etc.) to better performance and less queries in the database.    