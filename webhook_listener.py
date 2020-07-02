import hmac
import logging
from json import dumps
from os import X_OK, access, getenv, listdir
from os.path import join
from pathlib import Path
from subprocess import PIPE, Popen
from sys import stderr, exit
from traceback import print_exc

from flask import Flask, abort, request


def get_secret(name):
    """Tries to read Docker secret or corresponding environment variable.

    Returns:
        secret (str): Secret value.

    """
    secret_path = Path('/run/secrets/') / name

    try:
        with open(secret_path, 'r') as file_descriptor:
            # Several text editors add trailing newline which may cause troubles.
            # That's why we're trimming secrets' spaces here.
            return file_descriptor.read() \
                    .strip()
    except OSError as err:
        variable_name = name.upper()
        logging.debug(
            'Can\'t obtain secret %s via %s path. Will use %s environment variable.',
            name,
            secret_path,
            variable_name
        )
        return getenv(variable_name)


logging.basicConfig(stream=stderr, level=logging.INFO)

# Collect all scripts now; we don't need to search every time
# Allow the user to override where the hooks are stored
HOOKS_DIR = getenv("WEBHOOK_HOOKS_DIR", "/app/hooks")
scripts = [join(HOOKS_DIR, f) for f in sorted(listdir(HOOKS_DIR))]
scripts = [f for f in scripts if access(f, X_OK)]
if not scripts:
    logging.error("No executable hook scripts found; did you forget to"
                  " mount something into %s or chmod +x them?", HOOKS_DIR)
    exit(1)

# Get application secret
webhook_secret = get_secret('webhook_secret')
if webhook_secret is None:
    logging.error("Must define WEBHOOK_SECRET")
    exit(1)

# Get branch list that we'll listen to, defaulting to just 'master'
branch_whitelist = getenv('WEBHOOK_BRANCH_LIST', 'master').split(',')

# Our Flask application
application = Flask(__name__)

# Keep the logs of the last execution around
responses = {}


@application.route('/', methods=['POST'])
def index():
    global webhook_secret, branch_whitelist, scripts, responses

    # Get signature from the webhook request
    header_signature = request.headers.get('X-Hub-Signature')
    header_gitlab_token = request.headers.get('X-Gitlab-Token')
    if header_signature is not None:
        # Construct an hmac, abort if it doesn't match
        try:
            sha_name, signature = header_signature.split('=')
        except:
            logging.info("X-Hub-Signature format is incorrect (%s), aborting", header_signature)
            abort(400)
        data = request.get_data()
        try:
            mac = hmac.new(webhook_secret.encode('utf8'), msg=data, digestmod=sha_name)
        except:
            logging.info("Unsupported X-Hub-Signature type (%s), aborting", header_signature)
            abort(400)
        if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
            logging.info("Signature did not match (%s and %s), aborting", str(mac.hexdigest()), str(signature))
            abort(403)
        event = request.headers.get("X-GitHub-Event", "ping")
    elif header_gitlab_token is not None:
        if webhook_secret != header_gitlab_token:
            logging.info("Gitlab Secret Token did not match, aborting")
            abort(403)
        event = request.headers.get("X-Gitlab-Event", "unknown")
    else:
        logging.info("X-Hub-Signature was missing, aborting")
        abort(403)

    # Respond to ping properly
    if event == "ping":
        return dumps({"msg": "pong"})

    # Don't listen to anything but push
    if event != "push" and event != "Push Hook":
        logging.info("Not a push event, aborting")
        abort(403)

    # Try to parse out the branch from the request payload
    try:
        branch = request.get_json(force=True)["ref"].split("/", 2)[2]
    except:
        print_exc()
        logging.info("Parsing payload failed")
        abort(400)

    # Reject branches not in our whitelist
    if branch not in branch_whitelist:
        logging.info("Branch %s not in branch_whitelist %s",
                     branch, branch_whitelist)
        abort(403)
    
    # Run scripts, saving into responses (which we clear out)
    responses = {}
    for script in scripts:
        proc = Popen([script, branch], stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')

        # Log errors if a hook failed
        if proc.returncode != 0:
            logging.error('[%s]: %d\n%s', script, proc.returncode, stderr)
        
        responses[script] = {
            'stdout': stdout,
            'stderr': stderr
        }

    return dumps(responses)

@application.route('/logs', methods=['GET'])
def logs():
    return dumps(responses)


# Run the application if we're run as a script
if __name__ == '__main__':
    logging.info("All systems operational, beginning application loop")
    application.run(debug=False, host='0.0.0.0', port=8000)
