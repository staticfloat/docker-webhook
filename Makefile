# Build the actual webhook listener
build:
	docker build -t webhook .

# Build a testing webhook-targeting one-shot wonder
build-test:
	docker build -t webhook_archer test/archer

# Run webhook listener, with example hook
check: build build-test
	@-docker stop webhook >/dev/null 2>/dev/null
	docker run --rm --name=webhook -d -e WEBHOOK_SECRET=secret -e WEBHOOK_BRANCH_LIST=master,sf/testing -v $$(pwd)/test/hooks:/app/hooks:ro -ti webhook >/dev/null
	@sleep 1
	docker run --rm --link=webhook -ti -e WEBHOOK_SECRET=secret webhook_archer
	@docker stop webhook >/dev/null
