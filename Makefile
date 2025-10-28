export PROJECTNAME=$(shell basename "$(PWD)")

.SILENT: ;               # no need for @

setup: ## Setup Virtual Env
	python3 -m venv venv
	./venv/bin/pip3 install -r requirements.txt

deps: ## Install dependencies
	./venv/bin/pip3 install -r requirements.txt

clean: ## Clean package
	find . -type d -name '__pycache__' | xargs rm -rf
	rm -rf build dist

deploy: clean ## Copies any changed file to the server
	ssh ${PROJECTNAME} -C 'bash -l -c "mkdir -vp ./tele-mind-gym"'
	rsync -avzr \
		.env \
		main.py \
		manage.py \
		mind_gym_bot \
		requirements.txt \
		scripts \
		${PROJECTNAME}:./tele-mind-gym

start: deploy ## Sets up a screen session on the server and start the app
	ssh ${PROJECTNAME} -C 'bash -l -c "./tele-mind-gym/scripts/setup_bot.sh ${PROJECTNAME}"'

stop: deploy ## Stop any running screen session on the server
	ssh ${PROJECTNAME} -C 'bash -l -c "./tele-mind-gym/scripts/stop_bot.sh ${PROJECTNAME}"'

ssh: ## SSH into the target VM
	ssh ${PROJECTNAME}

run: lint ## Run bot locally
	./venv/bin/python3 main.py

.PHONY: help
.DEFAULT_GOAL := help

help: Makefile
	echo
	echo " Choose a command run in "$(PROJECTNAME)":"
	echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	echo