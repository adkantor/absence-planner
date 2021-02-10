from functools import wraps
from flask import session, redirect

def apology(message, code=400):
    """Render message as an apology to user."""
    # def escape(s):
    #     """
    #     Escape special characters.

    #     https://github.com/jacebrowning/memegen#special-characters
    #     """
    #     for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
    #                      ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
    #         s = s.replace(old, new)
    #     return s
    # return render_template("apology.html", top=code, bottom=escape(message)), code
    return f'Error: {code} {message}'
