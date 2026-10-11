# Contributing

How a change gets into `main`: issue, branch, pull request, review, merge.

## Merge rule

- Nothing is pushed straight to `main`. Every change arrives through a pull request.
- Each pull request closes an issue and comes from its own branch.
- One other team member approves it before it is merged. Nobody approves their own pull request.
- The checks pass. The backend checks run automatically on pull requests that touch `backend/`; for a frontend change, run `npm run lint` and `npm run build` in `frontend/app/`.
- The author merges after approval and deletes the branch.

## Steps

| Step | Where | What to do |
| --- | --- | --- |
| 1. Issue | GitHub → **Issues** → **New issue** | Title it with the feature or fix, say what "done" means, and assign yourself. Paste the Trello card link if there is one. |
| 2. Branch | The issue's sidebar → **Development** → **Create a branch**, or the commands below | Name it `<area>/<issue number>-<short-name>`, such as `backend/12-login-routes`. Areas: `backend`, `frontend`, `database`, `docs`. |
| 3. Commit and push | Your machine | Run the [checks](README.md#checks), then commit and push the branch. |
| 4. Pull request | GitHub → **Compare & pull request** | Base `main`. Write `Closes #12` in the description so the issue is linked and closes on merge. Pick a teammate under **Reviewers**. |
| 5. Review | The pull request → **Files changed** → **Review changes** | The reviewer chooses **Approve** or **Request changes**. To answer a requested change, push to the same branch; the pull request updates. |
| 6. Merge | The pull request → **Merge pull request** | Only after one approval and passing checks. Then **Delete branch**. |

Commands for steps 2, 3, and 6, with issue 12 as the example:

```bash
git switch main
git pull
git switch -c backend/12-login-routes     # skip if GitHub created the branch: git fetch, then git switch backend/12-login-routes

git add <files>
git commit -m "Add login routes"
git push -u origin backend/12-login-routes

git switch main                            # after the pull request is merged
git pull
git branch -d backend/12-login-routes
```
