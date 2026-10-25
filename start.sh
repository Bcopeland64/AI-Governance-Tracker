#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$APP_DIR/.streamlit/streamlit.pid"
LOG_FILE="$APP_DIR/.streamlit/streamlit.log"
HOST="${AI_GOVERNANCE_HOST:-127.0.0.1}"
PORT="${AI_GOVERNANCE_PORT:-8501}"

is_tracker_process() {
    local pid="$1"
    local command

    kill -0 "$pid" 2>/dev/null || return 1
    command="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    [[ "$command" == *"streamlit run $APP_DIR/app.py"* ]]
}

read_tracker_pid() {
    [[ -f "$PID_FILE" ]] || return 1
    local pid
    pid="$(<"$PID_FILE")"
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    is_tracker_process "$pid" || return 1
    printf '%s\n' "$pid"
}

start_tracker() {
    if read_tracker_pid >/dev/null; then
        echo "AI Governance Tracker is already running (PID $(<"$PID_FILE"))."
        echo "http://$HOST:$PORT"
        return
    fi

    rm -f -- "$PID_FILE"
    command -v streamlit >/dev/null 2>&1 || {
        echo "Streamlit is not installed or is not on PATH." >&2
        exit 1
    }

    cd "$APP_DIR"
    nohup env AI_GOVERNANCE_ALLOW_SHUTDOWN=1 \
        streamlit run "$APP_DIR/app.py" \
        --server.address "$HOST" \
        --server.port "$PORT" \
        >"$LOG_FILE" 2>&1 </dev/null &
    local pid=$!
    printf '%s\n' "$pid" >"$PID_FILE"

    for _ in {1..30}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "The tracker did not start. See $LOG_FILE for details." >&2
            rm -f -- "$PID_FILE"
            exit 1
        fi
        if is_tracker_process "$pid" \
            && command -v curl >/dev/null 2>&1 \
            && curl --silent --fail --max-time 1 \
                "http://$HOST:$PORT/_stcore/health" >/dev/null; then
            echo "AI Governance Tracker is running at http://$HOST:$PORT"
            echo "Logs: $LOG_FILE"
            return
        fi
        sleep 1
    done

    if is_tracker_process "$pid"; then
        kill -TERM "$pid"
    fi
    rm -f -- "$PID_FILE"
    echo "The tracker did not become ready. See $LOG_FILE for details." >&2
    exit 1
}

stop_tracker() {
    local pid
    if ! pid="$(read_tracker_pid)"; then
        rm -f -- "$PID_FILE"
        echo "AI Governance Tracker is not running."
        return
    fi

    kill -TERM "$pid"
    rm -f -- "$PID_FILE"
    echo "Sent a shutdown signal to AI Governance Tracker (PID $pid)."
}

status_tracker() {
    local pid
    if pid="$(read_tracker_pid)"; then
        echo "AI Governance Tracker is running (PID $pid) at http://$HOST:$PORT"
    else
        echo "AI Governance Tracker is not running."
        return 1
    fi
}

case "${1:-start}" in
    start) start_tracker ;;
    stop) stop_tracker ;;
    status) status_tracker ;;
    *)
        echo "Usage: $0 [start|stop|status]" >&2
        exit 2
        ;;
esac
