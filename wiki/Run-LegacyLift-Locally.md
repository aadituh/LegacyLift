**Authors:** Aaditya Ghimire

# Run LegacyLift Locally
Start the whole product on your own computer with one command. This is the setup that includes verification against GnuCOBOL.

## What you need
* [Docker](https://docs.docker.com/get-docker/) with Compose
* A copy of the [LegacyLift repository](https://github.com/aadituh/LegacyLift)

## Steps
1. Open a terminal in the repository folder.
2. Create a file named `.env` in that folder with a sign-in secret. Use any long random text and keep it the same between starts:

   ```
   LEGACYLIFT_TOKEN_SECRET=<long random text>
   ```

3. Optional: to use AI review, add your Gemini key to the same file:

   ```
   LEGACYLIFT_GEMINI_API_KEY=<your key>
   ```

4. Start everything:

   ```bash
   docker compose up --build
   ```

5. Wait until the terminal stops printing start-up messages, then open <http://localhost:8080>.
6. Create an account and sign in (see [[Create an Account and Sign In|Create-an-Account-and-Sign-In]]).

## What starts
| Service | Purpose | Address |
| --- | --- | --- |
| Web app | The pages you use | <http://localhost:8080> |
| API | Receives requests from the web app | <http://localhost:8000/docs> |
| Database | Saves accounts, projects, files, and runs | Not opened in a browser |
| Runner | Compiles and runs COBOL and Python for verification | Reached only by the API |

## Stop and reset
| To do this | Run |
| --- | --- |
| Stop | `Ctrl+C` in the terminal, or `docker compose down` |
| Stop and delete every saved account and project | `docker compose down -v` |

## If something goes wrong
| What you see | What to do |
| --- | --- |
| The API stops with `schema "neon_auth" does not exist` | Run `docker compose down -v` once, then start again. |
| The page at `localhost:8080` does not load | Wait for start-up to finish. The first build takes longer than later starts. |
| You cannot sign in | Check that `.env` holds `LEGACYLIFT_TOKEN_SECRET`, then start again. |
| You are signed out after a restart | The secret changed. Keep the same value in `.env` and sign in again. |
| "Set LEGACYLIFT_GEMINI_API_KEY before requesting an AI review." | Add the key to `.env` and start again. |
| Every verification result is **Not compared** | Check that the `runner` service is running: `docker compose ps`. |

Next: [[Load Demo Project|Load-Demo-Project]].
