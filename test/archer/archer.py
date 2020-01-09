import requests, hmac, json, os, logging

WEBHOOK_SECRET=os.getenv("WEBHOOK_SECRET", None)
if WEBHOOK_SECRET is None:
    logging.error("Must define WEBHOOK_SECRET")
    exit(1)

def send(headers={}, data=''):
    global WEBHOOK_SECRET

    # Sign the request with our secret
    mac = hmac.new(WEBHOOK_SECRET.encode('utf8'), msg=data.encode('utf8'), digestmod='sha1')
    headers['X-Hub-Signature'] = "sha1="+str(mac.hexdigest())

    # Shoot off the webhook!
    r = requests.post('http://webhook:8000', headers=headers, data=data)
    try:
        return r.json()
    except:
        return r

def send_ping():
    return send(headers={'X-GitHub-Event': 'ping'})

def send_push(branch_name):
    return send(
        headers={'X-GitHub-Event': 'push'},
        data=json.dumps({
            'ref': 'refs/heads/' + branch_name,
        }),
    )

# Test that a `ping` gets a `pong`
r = send_ping()
if r["msg"] != "pong":
    logging.error("Invalid response to `ping`: ", r)
    exit(1)
else:
    print("ping good!")

for good_branch in ("master", "sf/testing"):
    r = send_push(good_branch)
    if r["/app/hooks/print_branch.sh"]["stdout"] != "Webhook received for branch '%s'\n"%(good_branch):
        logging.error("Invalid response to `push` on branch %s"%(good_branch))
        exit(1)
    else:
        print("push on %s good!"%(good_branch))

r = send_push("bad_branch_name")
if r.status_code != 403:
    logging.error("Failed to fail on bad branch name push!")
else:
    print("push on bad_branch_name good!")
