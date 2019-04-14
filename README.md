# docker-webhook

Simple python application to listen for GitHub webhook events and run scripts in response to `push` events.  This is mostly useful as a part of a larger project that needs to reload itself on deploy events.  The behavior of this image can be altered through the use of environment variables, the full list of which are included in a table below.  The suggested way of using this image is through a `docker-compose.yml` setup.  To illustrate this, read through the following scenario and code bits:

Let us imagine I have an application running with an nginx frontend and some kind of backend.  I want this application to redeploy itself when it receives a `push` event from GitHub on either the branch `master` or `release-1.0`.  To do so, I would first add configuration to the application's `docker-compose.yml` file similar to the following:

```yaml
version: '2.1'
services:
    frontend:
        // blah blah blah...
    main_app:
        // blah blah blah...
    webhook:
        restart: unless-stopped
        image: staticfloat/docker-webhook
        volumes:
            # Mount this code into /code
            - ./:/code
            # Mount the docker socket
            - /var/run/docker.sock:/var/run/docker.sock
        environment:
            - WEBHOOK_SECRET=${WEBHOOK_SECRET}
            - WEBHOOK_HOOKS_DIR=/code/hooks
            - WEBHOOK_BRANCH_LIST=master
        expose:
            - 8000
```

This creates a `webhook` service that will listen for incoming webhook events on (docker-internal) port 8000.  Note that I have left the `WEBHOOK_SECRET` as a variable even in the `docker-compose.yml`.  This is because I have found it handy to encrypt these values in a separate `.env` file with [`git-crypt`](https://github.com/AGWA/git-crypt).
You're able to use `webhook_secret` [Docker secret](https://docs.docker.com/compose/compose-file/#secrets) instead of environment variable to provide this value.

To route webhook events to the `webhook` image, I will add this snippet to my frontend `nginx` config:

```
    location /_webhook {
        proxy_pass http://webhook:8000/;
    }
```

Finally, within my application code, I will create a directory `hooks` and place executable files such as `bash` shell scripts that will run within there.  In this case, I will put a `deploy.sh` file within that directory:

```bash
#!/bin/bash

cd /code
docker-compose build --pull && docker-compose up --build --remove-orphans -d
```

Commands such as `bash`, `make`, `python` and `docker-compose` are available within the `staticfloat/docker-webhook` image, but if you need something more complex than that, you will likely need to add them.

## Significant environment variables:

| Variable            | Required | Effect                                                     |
| --------------------|----------|------------------------------------------------------------|
| WEBHOOK_SECRET      | YES      | Defines the secret used for github hook verification       |
| WEBHOOK_HOOKS_DIR   | NO       | Directory where hooks are stored, defaults to `/app/hooks` |
| WEBHOOK_BRANCH_LIST | NO       | Comma-separated list of branches, defaults to `master`     |

## Misc. information

There is also a `/logs` endpoint that will show the `stdout` and `stderr` of the last execution.
