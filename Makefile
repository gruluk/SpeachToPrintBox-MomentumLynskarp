PI ?= pi@speechbox.local
REMOTE_DIR = ~/SpeachToPrintBox

deploy:
	ssh $(PI) 'cd $(REMOTE_DIR) && git pull'

run:
	ssh $(PI) 'cd $(REMOTE_DIR) && .venv/bin/python main.py'

deploy-run: deploy run

ssh:
	ssh $(PI)

setup-pi:
	ssh $(PI) 'cd $(REMOTE_DIR) && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt'

.PHONY: deploy run deploy-run ssh setup-pi
