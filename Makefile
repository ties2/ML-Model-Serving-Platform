VENV = .venv
VENV_BIN = $(VENV)/bin

.PHONY: all clean

# Default command when you just type 'make'
all: $(VENV)

# This rule says: "Only run these commands if requirements.txt is newer than the .venv folder"
$(VENV): requirements.txt
	python3.12 -m venv $(VENV)
	$(VENV_BIN)/python -m pip install --upgrade pip
	$(VENV_BIN)/pip install -r requirements.txt
	@# Touch the folder to update its timestamp, so Make knows it's up to date
	@touch $(VENV)

# Clean up the environment
clean:
	rm -rf $(VENV)