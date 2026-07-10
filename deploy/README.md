# Production Operations

## Production readiness checklist

Complete these items before calling the application fully deployed:

- [ ] Review the complete production-candidate scope in `CHANGELOG.md` and the
  current architecture/invariants in `CONTEXT.md`.
- [ ] Commit the intentionally dirty `feat-fullstack-mini-app` working tree,
  review its diff, merge the approved result to `main`, and confirm both GitHub
  Actions workflows pass.
- [ ] Run `python -m pytest`, `npm run test:local`, and `npm run build` from a
  clean checkout. Perform a rendered mobile-width smoke test of authentication,
  medicine CRUD/sync, dashboard actions, history, settings, rating, and bug
  reporting.
- [ ] Create production secrets: rotate `BOT_TOKEN`, generate a unique
  `JWT_SECRET` of at least 32 bytes, and set `TUNNEL_TOKEN`. Keep `.env` mode
  `0600` and outside Git.
- [ ] Confirm the Cloudflare Tunnel hostname points to `http://backend:8000`,
  TLS works, and public `/health`, `/ready`, and `/api/v1` requests reach the
  backend without exposing port 8000 directly.
- [ ] Set GitHub repository variable `VITE_API_BASE_URL` to the final HTTPS URL
  ending in `/api/v1`; verify the Pages deployment uses `/MedAlarm/` and loads
  without console or asset errors.
- [ ] Set BotFather's Mini App/menu URL to the final GitHub Pages URL and test
  Telegram `initData` authentication from the real bot on iOS, Android, and
  Telegram Desktop where available.
- [ ] Confirm the feedback forum chat and topic IDs in `.env`. Add the bot to
  chat `FEEDBACK_CHAT_ID`, allow it to post in topics
  `FEEDBACK_TOPIC_ID`/`BUG_REPORT_TOPIC_ID`, then submit one real rating and one
  bug report with a screenshot.
- [ ] Decide screenshot retention before launch: extend `backup.sh` and
  `restore.sh` to archive `/app/data/feedback_screenshots`, or explicitly accept
  that the current database-only backup cannot restore screenshots.
- [ ] Install the daily backup cron, enable weekly VPS snapshots, run one manual
  backup, and complete a restore drill before accepting real user data.
- [ ] Create an immutable release tag, run `sh deploy/release.sh <tag>`, verify
  one healthy backend replica, and add an external HTTPS uptime check for
  `/ready`.
- [ ] After deployment, verify bot reminders, snooze restart recovery,
  Taken/Skipped idempotency, Mini App sync, feedback delivery, logs, disk space,
  and the newest backup timestamp.

## First deployment

1. Create a DNS zone in Cloudflare and a named Tunnel with public hostname
   `https://<api-host>` targeting `http://backend:8000`.
2. Clone this repository to `/opt/medalarm` on the Hostinger VPS.
3. Copy `.env.example` to `.env`, replace every placeholder, and run
   `chmod 600 .env`. Rotate the Telegram bot token before inserting it.
4. Set the GitHub Actions repository variable `VITE_API_BASE_URL` to
   `https://<api-host>/api/v1`.
5. Set the BotFather Mini App URL to
   `https://miha21222.github.io/MedAlarm/`.
6. Create and push a release tag, then run `sh deploy/release.sh <tag>` on the
   VPS. Confirm `https://<api-host>/ready` returns `{"status":"ready"}`.

The deployment supports exactly one backend replica. Do not scale the bot or
scheduler horizontally while SQLite and Telegram long polling are in use.

The feedback relay uses these production variables:

- `FEEDBACK_CHAT_ID`: Telegram forum supergroup receiving submissions.
- `FEEDBACK_TOPIC_ID`: topic receiving ratings.
- `BUG_REPORT_TOPIC_ID`: topic receiving bug reports.

The bot must be a member of the forum and have permission to post in both
topics. Feedback is first persisted in SQLite; Telegram notification is
best-effort and a relay failure does not fail the user submission.

## Backups

Run `sh deploy/backup.sh` daily from root's cron. It uses SQLite's online backup
API, retains seven daily backups and four weekly backups, and writes files with
mode `0600` under `/var/backups/medalarm` by default.

Current limitation: this script backs up `medalarm.db` only. Uploaded feedback
screenshots live in `/app/data/feedback_screenshots` and are not included in
backup or restore yet. Resolve that checklist item before relying on screenshot
retention.

```cron
15 2 * * * cd /opt/medalarm && sh deploy/backup.sh >> /var/log/medalarm-backup.log 2>&1
```

Enable weekly Hostinger VPS snapshots. Every quarter, restore the newest
backup into a temporary copy of the Compose project and verify `/ready`, bot
startup, and history retrieval.

## Restore and rollback

`sh deploy/restore.sh <backup.db.gz>` validates the archive and SQLite integrity,
stops the stack, replaces the database through the backend container, and
starts the production profile again.

Application rollback uses the same release command with the previous tag:

```sh
sh deploy/release.sh <previous-tag>
```

After every release or restore, check `docker compose ps`, the last 100 backend
and tunnel log lines, the public `/ready` endpoint, disk space, and the newest
backup timestamp. Add an external HTTPS uptime check for `/ready`.
