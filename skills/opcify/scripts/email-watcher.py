#!/home/node/.openclaw-env/bin/python3
"""IMAP IDLE email watcher — notifies assistant agent directly via OpenClaw gateway.

Monitors INBOX via IDLE. After each IDLE cycle (new mail or 28-min timeout),
also checks [Gmail]/Sent Mail count so user replies from Gmail or agent-sent
emails are captured in the Opcify Inbox thread view.
"""

import imaplib
import json
import logging
import os
import signal
import subprocess
import time
import uuid

GMAIL_DIR = "/home/node/.openclaw/data/.gmail"
CRED_FILE = f"{GMAIL_DIR}/credentials.json"
LOG_FILE = f"{GMAIL_DIR}/watcher.log"
ACCESS_TOKEN_SCRIPT = f"{GMAIL_DIR}/get-access-token.sh"
TOKEN_EXPIRED_FLAG = f"{GMAIL_DIR}/token-expired"

IDLE_TIMEOUT = 1680  # 28 min (under 29 min RFC limit)
RECONNECT_DELAY = 10  # initial backoff seconds
BATCH_DELAY = 3  # seconds to wait after detection to batch rapid emails

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

running = True


def handle_signal(sig, frame):
    global running
    running = False
    logging.info(f"Received signal {sig}, shutting down...")


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


class RefreshTokenExpired(Exception):
    """Raised when the refresh token is revoked/expired and cannot be recovered."""
    pass


def get_access_token():
    result = subprocess.run(
        [ACCESS_TOKEN_SCRIPT], capture_output=True, text=True, timeout=30
    )
    token = result.stdout.strip()
    if not token:
        # Check if the helper script output contains invalid_grant
        # (Google returns this when refresh token is revoked)
        stderr = result.stderr.strip()
        if "invalid_grant" in stderr or "invalid_grant" in result.stdout:
            raise RefreshTokenExpired("Refresh token revoked or expired")
        raise Exception(f"Failed to get access token: {stderr}")
    return token


def imap_connect(email_addr, access_token):
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    auth_string = f"user={email_addr}\x01auth=Bearer {access_token}\x01\x01"
    mail.authenticate("XOAUTH2", lambda x: auth_string.encode())
    mail.select("INBOX")
    return mail


def get_sent_count(email_addr, access_token):
    """Get the message count of the Sent folder via a short-lived connection."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        auth_string = f"user={email_addr}\x01auth=Bearer {access_token}\x01\x01"
        mail.authenticate("XOAUTH2", lambda x: auth_string.encode())
        status, data = mail.select('"[Gmail]/Sent Mail"', readonly=True)
        count = int(data[0]) if status == "OK" else 0
        mail.logout()
        return count
    except Exception as e:
        logging.warning(f"Failed to check Sent folder: {e}")
        return -1


def idle_loop(mail):
    tag = mail._new_tag().decode()
    mail.send(f"{tag} IDLE\r\n".encode())
    mail.sock.settimeout(IDLE_TIMEOUT)
    try:
        while True:
            line = mail.readline().decode()
            if "EXISTS" in line:
                mail.send(b"DONE\r\n")
                mail.readline()
                return "new_mail"
            if line.startswith(tag):
                return "idle_ended"
    except (imaplib.IMAP4.abort, TimeoutError, OSError):
        return "timeout"
    finally:
        try:
            mail.send(b"DONE\r\n")
            mail.readline()
        except Exception:
            pass


def notify_agent(reason="inbox"):
    """Dispatch the assistant agent to a dedicated "email" session.

    We call the Gateway's `agent` RPC directly via `openclaw gateway call`
    so we can pass an explicit `sessionKey` of `agent:{slug}:email`. The
    `openclaw agent` CLI does not expose a way to override the session key
    (its --session-id flag is for looking up an existing session, not for
    routing), so it always dispatches to `:main`. The lower-level
    `gateway call` path lets us target the `:email` scope, keeping email
    traffic isolated from the agent's main conversation.
    """
    try:
        creds = json.load(open(CRED_FILE))
        agent_slug = creds.get("assistant_agent_slug", "personal-assistant")

        if reason == "sent":
            message = (
                "[EMAIL-WATCHER] New sent email detected in Gmail Sent folder. "
                "Please check for recently sent emails using himalaya, "
                "and push them to the Opcify Inbox so they appear in the thread view."
            )
        else:
            message = (
                "[EMAIL-WATCHER] New email detected in Gmail inbox. "
                "Please check for new unread emails using himalaya, "
                "triage them, and push important ones to the Opcify Inbox."
            )

        session_key = f"agent:{agent_slug}:email"
        params = json.dumps({
            "message": message,
            "agentId": agent_slug,
            "sessionKey": session_key,
            "deliver": False,
            "idempotencyKey": str(uuid.uuid4()),
        })

        # Fire-and-forget: spawn via nohup so the watcher keeps listening.
        subprocess.Popen(
            ["nohup", "openclaw", "gateway", "call", "agent",
             "--expect-final",
             "--timeout", "600000",
             "--params", params],
            stdout=open("/tmp/email-triage.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        logging.info(
            f"Agent '{agent_slug}' (sessionKey={session_key}) spawned for {reason} triage"
        )
        return True
    except Exception as e:
        logging.error(f"Failed to notify agent: {e}")
        return False


def main():
    creds = json.load(open(CRED_FILE))
    email_addr = creds["email"]

    logging.info(f"Email watcher starting for {email_addr}")
    print(f"[email-watcher] Starting for {email_addr}", flush=True)

    consecutive_errors = 0
    last_sent_count = -1  # will be initialized on first connect

    while running:
        try:
            # Get a fresh access token on every connect cycle
            access_token = get_access_token()
            logging.info("Access token obtained")

            # Initialize sent count on first run
            if last_sent_count < 0:
                last_sent_count = get_sent_count(email_addr, access_token)
                logging.info(f"Initial Sent folder count: {last_sent_count}")

            mail = imap_connect(email_addr, access_token)
            consecutive_errors = 0
            logging.info("Connected to Gmail IMAP, entering IDLE")

            while running:
                result = idle_loop(mail)
                if result == "new_mail":
                    logging.info("New email detected")
                    time.sleep(BATCH_DELAY)
                    notify_agent()
                elif result == "timeout":
                    logging.info("IDLE timeout, reconnecting")
                    break
                elif result == "idle_ended":
                    break

                # After each IDLE cycle, also check the Sent folder
                try:
                    current_sent = get_sent_count(
                        email_addr, access_token
                    )
                    if (
                        current_sent > last_sent_count
                        and last_sent_count >= 0
                    ):
                        logging.info(
                            f"New sent email detected "
                            f"({last_sent_count} -> {current_sent})"
                        )
                        notify_agent("sent")
                    if current_sent >= 0:
                        last_sent_count = current_sent
                except Exception as e:
                    logging.warning(f"Sent folder check failed: {e}")

            try:
                mail.logout()
            except Exception:
                pass

        except RefreshTokenExpired:
            logging.error(
                "Refresh token is revoked/expired. "
                "User must reconnect Gmail in Opcify Inbox page."
            )
            # Write flag file so Opcify can detect the expired state
            with open(TOKEN_EXPIRED_FLAG, "w") as f:
                f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            print(
                "[email-watcher] Refresh token expired. "
                "Please reconnect Gmail in Opcify.",
                flush=True,
            )
            break  # Stop watching — can't recover without user action

        except Exception as e:
            consecutive_errors += 1
            delay = min(RECONNECT_DELAY * (2**consecutive_errors), 300)
            logging.error(f"IMAP error (attempt {consecutive_errors}): {e}")
            for _ in range(int(delay)):
                if not running:
                    break
                time.sleep(1)

    logging.info("Email watcher stopped")
    print("[email-watcher] Stopped", flush=True)


if __name__ == "__main__":
    main()
