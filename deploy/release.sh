#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <git-tag>" >&2
  exit 2
fi

tag="$1"
git diff --quiet && git diff --cached --quiet || {
  echo "Refusing to deploy from a dirty worktree" >&2
  exit 1
}
git fetch --tags --prune origin
git rev-parse --verify "refs/tags/$tag" >/dev/null
git checkout --detach "$tag"
docker compose --profile production config --quiet
docker compose --profile production up --build -d

container_id="$(docker compose ps -q backend)"
i=0
while [ "$i" -lt 30 ]; do
  status="$(docker inspect --format '{{.State.Health.Status}}' "$container_id")"
  [ "$status" = "healthy" ] && break
  [ "$status" = "unhealthy" ] && {
    docker compose logs --tail=100 backend
    exit 1
  }
  i=$((i + 1))
  sleep 2
done
[ "$(docker inspect --format '{{.State.Health.Status}}' "$container_id")" = "healthy" ] || exit 1
docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=5)"
echo "Deployed $tag"
