# Git Workflow (Git Flow)

Follow the **Git Flow** branching model.

## Branches

- `main` – Stable releases, each tagged with a version number (e.g., `v0.0.1`).
- `develop` – Integration branch for the next release. All feature branches and bug fixes (except hotfixes) must be merged here.
- `feature/*` – New features or enhancements. Branch from `develop`, merge back into `develop`.
- `hotfix/*` – Urgent fixes for the current release. Branch from `main`, merge back into both `main` and `develop`.

## Step‑by‑Step (for a new feature)

1. Fork the repository on GitHub.
2. Clone your fork locally:
   git clone https://github.com/your-username/blender-ctr-toolkit.git
   cd blender-ctr-toolkit
3. Add the upstream remote:
   git remote add upstream https://github.com/kjorgecaballero/blender-ctr-toolkit.git
4. Create a feature branch from `develop`:
   git checkout develop
   git pull upstream develop
   git checkout -b feature/my-new-feature
5. Make your changes, commit with clear messages.
6. Push the branch to your fork:
   git push origin feature/my-new-feature
7. Open a Pull Request against the `develop` branch of the upstream repository.

## Keeping Your Branch Up‑to‑Date

git fetch upstream
git rebase upstream/develop

Resolve any conflicts, then force-push to your feature branch (only if you are the sole contributor on that branch).

## Hotfix Workflow

1. Branch from `main`:
   git checkout main
   git pull upstream main
   git checkout -b hotfix/critical-fix
2. Fix the issue and commit.
3. Merge into `main` (tag a new version) and also into `develop`:
   git checkout main
   git merge --no-ff hotfix/critical-fix
   git tag -a v0.0.2 -m "Hotfix description"
   git checkout develop
   git merge --no-ff hotfix/critical-fix
4. Delete the hotfix branch.

## Commit Messages

- Use the imperative mood.
- Keep the first line under 72 characters.
- Reference issues (e.g., `Closes #123`).

## Merging

Pull requests are merged via **squash and merge** or **rebase and merge** – maintainers will choose the appropriate method.
