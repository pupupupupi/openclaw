#!/bin/bash
set -e

# Create openclaw command wrapper in user-writable path
mkdir -p "$HOME/.local/bin"
if [ ! -f "$HOME/.local/bin/openclaw" ]; then
  printf '#!/bin/bash\nexec node /app/dist/index.js "$@"\n' > "$HOME/.local/bin/openclaw"
  chmod +x "$HOME/.local/bin/openclaw"
fi
export PATH="$HOME/.local/bin:$PATH"

# Ensure akshare cache directory exists (mounted as named volume)
mkdir -p "$HOME/.akshare_cache"

# Install Python packages for skills (akshare etc.)
if ! python3 -c "import akshare" 2>/dev/null; then
  echo "[entrypoint] Installing pip + akshare..."
  curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py \
    && python3 /tmp/get-pip.py --user --break-system-packages --quiet 2>&1 \
    && "$HOME/.local/bin/pip" install --user --break-system-packages --quiet akshare pandas pyarrow 2>&1 \
    && echo "[entrypoint] akshare installed successfully" \
    || echo "[entrypoint] Warning: failed to install akshare"
  rm -f /tmp/get-pip.py
fi
export PATH="$HOME/.local/bin:$PATH"

# Ensure Chromium is available for browser automation.
# If the image was built with OPENCLAW_INSTALL_BROWSER=1, system chromium is already installed.
# Otherwise, try runtime install as fallback.
if ! command -v chromium >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then
  echo "[entrypoint] Chromium not found."
  if [ "$(id -u)" -eq 0 ]; then
    echo "[entrypoint] Installing chromium via apt..."
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends chromium \
      && apt-get clean && rm -rf /var/lib/apt/lists/* \
      && echo "[entrypoint] Chromium installed successfully" \
      || echo "[entrypoint] Warning: failed to install Chromium (browser tool will be unavailable)"
  else
    echo "[entrypoint] Warning: Cannot install Chromium as non-root. Rebuild image with OPENCLAW_INSTALL_BROWSER=1"
  fi
fi

# Install dependencies for user-mounted plugins under ~/.openclaw/extensions/
EXTENSIONS_DIR="$HOME/.openclaw/extensions"
if [ -d "$EXTENSIONS_DIR" ]; then
  for pkg in "$EXTENSIONS_DIR"/*/package.json; do
    [ -f "$pkg" ] || continue
    plugin_dir="$(dirname "$pkg")"
    plugin_name="$(basename "$plugin_dir")"
    echo "[entrypoint] Installing deps for plugin: $plugin_name"

    # Strip devDependencies with workspace:* protocol that pnpm can't resolve outside workspace
    node -e "
      const fs = require('fs');
      const p = JSON.parse(fs.readFileSync('$pkg','utf8'));
      if (p.devDependencies) {
        for (const [k,v] of Object.entries(p.devDependencies)) {
          if (String(v).startsWith('workspace:')) delete p.devDependencies[k];
        }
      }
      fs.writeFileSync('$pkg', JSON.stringify(p, null, 2) + '\n');
    "

    (cd "$plugin_dir" && pnpm install --prod --no-frozen-lockfile 2>&1) || echo "[entrypoint] Warning: failed to install deps for $plugin_name"
  done
fi

# Start Xvfb virtual display if available (needed for some Chromium operations in Docker)
if command -v Xvfb >/dev/null 2>&1; then
  if ! pgrep -x Xvfb >/dev/null 2>&1; then
    Xvfb :101 -screen 0 1280x720x24 -nolisten tcp &
    export DISPLAY=:101
    echo "[entrypoint] Xvfb started on :101"
  fi
fi

# Warm up browser profile so launchOpenClawChrome skips the bootstrap phase.
# Without this, the first browser(action="start") call triggers a bootstrap that
# spawns Chromium twice (create profile files + real launch), easily exceeding
# the 15s client-side fetch timeout.
BROWSER_PROFILE_DIR="$HOME/.openclaw/browser/openclaw/user-data"
BROWSER_LOCAL_STATE="$BROWSER_PROFILE_DIR/Local State"
BROWSER_PREFS="$BROWSER_PROFILE_DIR/Default/Preferences"
CHROMIUM_BIN=""
if command -v chromium >/dev/null 2>&1; then
  CHROMIUM_BIN="chromium"
elif command -v chromium-browser >/dev/null 2>&1; then
  CHROMIUM_BIN="chromium-browser"
fi

if [ -n "$CHROMIUM_BIN" ] && { [ ! -f "$BROWSER_LOCAL_STATE" ] || [ ! -f "$BROWSER_PREFS" ]; }; then
  echo "[entrypoint] Warming up browser profile..."
  mkdir -p "$BROWSER_PROFILE_DIR"
  # Clean stale Chromium lock files from previous container runs.
  # These persist on the mounted volume and block new Chromium instances.
  rm -f "$BROWSER_PROFILE_DIR/SingletonLock" \
        "$BROWSER_PROFILE_DIR/SingletonSocket" \
        "$BROWSER_PROFILE_DIR/SingletonCookie" 2>/dev/null || true
  $CHROMIUM_BIN \
    --headless=new \
    --disable-gpu \
    --no-sandbox \
    --disable-setuid-sandbox \
    --disable-dev-shm-usage \
    --no-first-run \
    --no-default-browser-check \
    --disable-sync \
    --disable-background-networking \
    --password-store=basic \
    --user-data-dir="$BROWSER_PROFILE_DIR" \
    about:blank &
  WARMUP_PID=$!
  WARMUP_DEADLINE=$((SECONDS + 10))
  while [ $SECONDS -lt $WARMUP_DEADLINE ]; do
    if [ -f "$BROWSER_LOCAL_STATE" ] && [ -f "$BROWSER_PREFS" ]; then
      break
    fi
    sleep 0.2
  done
  kill "$WARMUP_PID" 2>/dev/null || true
  wait "$WARMUP_PID" 2>/dev/null || true
  if [ -f "$BROWSER_LOCAL_STATE" ] && [ -f "$BROWSER_PREFS" ]; then
    echo "[entrypoint] Browser profile warmed up successfully"
  else
    echo "[entrypoint] Warning: browser profile warmup incomplete (first start may be slow)"
  fi
elif [ -n "$CHROMIUM_BIN" ] && [ -d "$BROWSER_PROFILE_DIR" ]; then
  # Profile already exists but lock files may be stale from a previous container.
  rm -f "$BROWSER_PROFILE_DIR/SingletonLock" \
        "$BROWSER_PROFILE_DIR/SingletonSocket" \
        "$BROWSER_PROFILE_DIR/SingletonCookie" 2>/dev/null || true
  echo "[entrypoint] Cleaned stale browser lock files"
fi

# Run the original command
exec "$@"
