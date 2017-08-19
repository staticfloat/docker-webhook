import hmac
import logging
from ipaddress import ip_address, ip_network
from json import dumps
from os import X_OK, access, getenv, listdir
from subprocess import PIPE, Popen
from sys import stderr

import requests
from flask import Flask, abort, request

logging.basicConfig(stream=stderr)


# Get github IP whitelist
github_whitelist = requests.get('https://api.github.com/meta').json()['hooks']

# Collect all scripts now; we don't need to search every time
scripts = [f for f in listdir("/app/hooks") if access(f, X_OK)]
if not scripts:
    raise ValueError("No executable hook scripts found; did you forget to"
                     " mount something into /app/hooks or chmod +x them?")

# Get application secret
webhook_secret = getenv('WEBHOOK_SECRET')
if webhook_secret is None:
    raise ValueError("Must define WEBHOOK_SECRET")

# Get branch list that we'll listen to, defaulting to just 'master'
branch_whitelist = getenv('WEBHOOK_BRANCH_LIST', '').split(',')
if not branch_whitelist:
    branch_whitelist = ['master']

# Our Flask application
application = Flask(__name__)


@application.route('/', methods=['POST'])
def index():
    global github_whitelist, webhook_secret, branch_whitelist, scripts

    # Get source ip of incoming webhook
    src_ip = ip_address(str(request.remote_addr))

    # If the source ip does not belong to any of the ips in the
    # github whitelist, quit out
    if not any(src_ip in ip_network(ip) for ip in github_whitelist):
        logging.info("IP address not in whitelist, aborting")
        abort(403)

    # Get signature from the webhook request
    header_signature = request.headers.get('X-Hub-Signature')
    if header_signature is None:
        logging.info("X-Hub-Signature was missing, aborting")
        abort(403)

    # Construct an hmac, abort if it doesn't match
    sha_name, signature = header_signature.split('=')
    mac = hmac.new(str(webhook_secret), msg=request.data, digestmod=sha_name)
    if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
        abort(403)
    
    # Respond to ping properly
    event = request.headers.get("X-GitHub-Event", "ping")
    if event == "ping":
        return dumps({"msg": "pong"})

    # Don't listen to anything but push
    if event != "push":
        abort(403)

    # Try to parse out the branch from the request payload
    try:
        branch = request.get_json()["ref"].split("/", 2)[2]
    except:
        logging.info("Parsing payload failed")
        abort(400)

    # Reject branches not in our whitelist
    if branch not in branch_whitelist:
        logging.info("Branch %s not in branch_whitelist %s",
                     branch, branch_whitelist)
        abort(403)
    
    # Run scripts
    for s in scripts:
        proc = Popen([s, branch], stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()

        # Log errors if a hook failed
        if proc.returncode != 0:
            logging.error('[%s]: %d\n%s', s, proc.returncode, stderr)


# Run the application if we're run as a script
if __name__ == '__main__':
    application.run(debug=True, host='0.0.0.0', port=8000)
