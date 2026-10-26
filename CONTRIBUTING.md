# Contributing

How a change gets into `main`: issue, branch, pull request, review, merge.

Work is tracked as GitHub issues on the team's GitHub Projects board, grouped by milestone (one per demo) and sprint.

## Merge rule

- Nothing is pushed straight to `main`. Every change arrives through a pull request.
- Each pull request closes an issue and comes from its own branch.
- A teammate is asked to review it. Aaditya is requested automatically ([`.github/CODEOWNERS`](.github/CODEOWNERS)); on Aaditya's own pull requests, pick another teammate. Approval is not required to merge, but every member has at least one pull request reviewed and approved during each demo.
- Review comments are resolved before merging.
- The checks pass. The backend checks run automatically on pull requests that touch `backend/`; for a frontend change, run `npm run lint` and `npm run build` in `frontend/app/`.
- The author merges and deletes the branch.

GitHub enforces this on `main` with a ruleset (**Settings → Rules → Rulesets**): a pull request with resolved comments is required, and force pushes and deleting `main` are blocked.

## Steps

| Step | Where | What to do |
| --- | --- | --- |
| 1. Issue | GitHub → **Issues** → **New issue** → **User story** | Title it with the feature, fill in the user story and acceptance criteria, assign yourself, and set the milestone. On the project board, set its sprint and move it to **In Progress** when you start. |
| 2. Branch | The issue's sidebar → **Development** → **Create a branch**, or the commands below | Name it `<area>/<issue number>-<short-name>`, such as `backend/12-login-routes`. Areas: `backend`, `frontend`, `database`, `docs`. |
| 3. Commit and push | Your machine | Run the [checks](README.md#checks), then commit and push the branch. |
| 4. Pull request | GitHub → **Compare & pull request** | Base `main`. Write `Closes #12` in the description so the issue is linked and closes on merge. Aaditya is added under **Reviewers** automatically; if you are Aaditya, pick a teammate. A draft pull request requests no reviewer until **Ready for review**. |
| 5. Review | The pull request → **Files changed** → **Review changes** | The reviewer chooses **Approve** or **Request changes**. To answer a requested change, push to the same branch; the pull request updates. |
| 6. Merge | The pull request → **Merge pull request** | After the review comments are resolved and the checks pass. Then **Delete branch**. |

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
