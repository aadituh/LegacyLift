**Authors:** Spencer Peloquin

# Login and Registration
Users register and sign in so projects stay private to their account. The design presentation keeps login simple so demo time stays on the GnuCOBOL proof.

## Registration rules (requirements §3.1.1)
* Username 3–30 characters: letters, digits, underscores only.  
* Password 8–128 characters.  
* Failed rules show a message naming the rule; duplicate usernames are rejected.  
* Passwords stored only as salted hashes.

## Login behaviour (requirements §3.1.2)
* Matching credentials start a session; wrong credentials show a generic error.  
* Five failed attempts lock the account out of login for 30 minutes.  
* Log Out ends the session and returns to the login page.

## Usability (requirements §3.2.4)
The app runs in current Chrome, Edge, and Firefox without installing software. Errors appear on the screen where they happened, naming the problem.
