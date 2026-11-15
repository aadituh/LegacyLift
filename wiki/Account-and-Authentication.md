**Authors:** Spencer Peloquin

# Account and Authentication
LegacyLift ties projects to accounts so each user only sees their own work. Passwords are stored only as salted hashes. Neon Auth and API email/password paths support the demo’s private-projects story.

## User accounts (requirements §3.1.1)
* Registration takes a username and password.  
* Username: 3–30 characters, letters/digits/underscores only.  
* Password: 8–128 characters.  
* Reject invalid registrations with a message naming the failed rule; reject usernames that already exist.  
* Store new accounts in the database; link each new project to the creating account; show a logged-in user only their projects.

## Login and logout (requirements §3.1.2)
* Login page takes username and password; start a session on match.  
* Wrong credentials show an error without saying which field failed.  
* After five failed attempts, reject login for 30 minutes.  
* Keep the user logged in until Log Out ends the session.

## Design presentation notes
* Accounts and private projects: each new project stores its owner; another login gets “not found.”  
* Security constraints: never return or log the database connection string or API keys; accept browser requests only from configured origins; reject bodies larger than 1.2 MB.  
* Storage: PostgreSQL on Neon (accounts and projects); design constraint §3.3.4.
