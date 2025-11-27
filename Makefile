.PHONY: help setup activate clean download cut join gui test-cut test-join

# Default Python interpreter
PYTHON := venv/bin/python3
PIP := venv/bin/pip

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help:
	@echo "$(GREEN)🔥 FIRE Video Processing Toolkit$(NC)"
	@echo "===================================="
	@echo ""
	@echo "$(BLUE)Setup Commands:$(NC)"
	@echo "  make setup          - Create venv and install dependencies"
	@echo "  make clean          - Remove venv and cache files"
	@echo ""
	@echo "$(BLUE)Main Commands:$(NC)"
	@echo "  make download URL=<url> NAME=<name> [FOLDER=<folder>] [CHUNK=<minutes>]"
	@echo "                      - Download YouTube video in chunks"
	@echo "  make cut SOURCE=<video.mp4> TIMES=<timestamps.txt> [SORT=1]"
	@echo "                      - Cut video by timestamps with overlays"
	@echo "  make join FOLDER=<parts-dir> [OUTPUT=<output.mp4>]"
	@echo "                      - Join video parts into one file"
	@echo "  make gui            - Launch GUI timestamp recorder"
	@echo ""
	@echo "$(BLUE)Examples:$(NC)"
	@echo "  make download URL='https://youtube.com/watch?v=xyz' NAME=myvideo CHUNK=10"
	@echo "  make cut SOURCE=dedictvigympl/dedictvigympl.mp4 TIMES=dedictvigympl/timestamps.txt SORT=1"
	@echo "  make join FOLDER=dedictvigympl/out-parts"
	@echo "  make gui"
	@echo ""
	@echo "$(BLUE)Quick Test Commands:$(NC)"
	@echo "  make testcut        - Clean and test cut with dedictvigympl example"

setup:
	@echo "$(GREEN)🔥 Setting up FIRE environment...$(NC)"
	@if [ ! -d "venv" ]; then \
		echo "$(YELLOW)Creating virtual environment...$(NC)"; \
		python3 -m venv venv; \
	else \
		echo "$(GREEN)✅ Virtual environment already exists$(NC)"; \
	fi
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@echo "$(GREEN)✅ Setup complete!$(NC)"
	@echo ""
	@$(PYTHON) --version
	@echo ""
	@echo "$(GREEN)🚀 Run 'make help' to see available commands$(NC)"

clean:
	@echo "$(RED)🧹 Cleaning up...$(NC)"
	rm -rf venv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

# Download YouTube video
download:
ifndef URL
	@echo "$(RED)❌ Error: URL is required$(NC)"
	@echo "Usage: make download URL='https://youtube.com/watch?v=xyz' NAME=myvideo [FOLDER=folder] [CHUNK=10]"
	@exit 1
endif
ifndef NAME
	@echo "$(RED)❌ Error: NAME is required$(NC)"
	@echo "Usage: make download URL='https://youtube.com/watch?v=xyz' NAME=myvideo [FOLDER=folder] [CHUNK=10]"
	@exit 1
endif
	@echo "$(GREEN)📥 Downloading video...$(NC)"
	@if [ -n "$(FOLDER)" ]; then \
		if [ -n "$(CHUNK)" ]; then \
			$(PYTHON) firetimer-ytdownload.py -u "$(URL)" -n "$(NAME)" -f "$(FOLDER)" -c $(CHUNK); \
		else \
			$(PYTHON) firetimer-ytdownload.py -u "$(URL)" -n "$(NAME)" -f "$(FOLDER)"; \
		fi \
	else \
		if [ -n "$(CHUNK)" ]; then \
			$(PYTHON) firetimer-ytdownload.py -u "$(URL)" -n "$(NAME)" -c $(CHUNK); \
		else \
			$(PYTHON) firetimer-ytdownload.py -u "$(URL)" -n "$(NAME)"; \
		fi \
	fi

# Cut video by timestamps
cut:
ifndef SOURCE
	@echo "$(RED)❌ Error: SOURCE is required$(NC)"
	@echo "Usage: make cut SOURCE=video.mp4 TIMES=timestamps.txt [SORT=1]"
	@exit 1
endif
ifndef TIMES
	@echo "$(RED)❌ Error: TIMES is required$(NC)"
	@echo "Usage: make cut SOURCE=video.mp4 TIMES=timestamps.txt [SORT=1]"
	@exit 1
endif
	@echo "$(GREEN)✂️  Cutting video...$(NC)"
	@if [ -n "$(SORT)" ] && [ "$(SORT)" = "1" ]; then \
		$(PYTHON) firetimer-cutvid.py -s "$(SOURCE)" -t "$(TIMES)" -z; \
	else \
		$(PYTHON) firetimer-cutvid.py -s "$(SOURCE)" -t "$(TIMES)"; \
	fi

# Join video parts
join:
ifndef FOLDER
	@echo "$(RED)❌ Error: FOLDER is required$(NC)"
	@echo "Usage: make join FOLDER=parts-dir [OUTPUT=output.mp4]"
	@exit 1
endif
	@echo "$(GREEN)🔗 Joining video parts...$(NC)"
	@if [ -n "$(OUTPUT)" ]; then \
		$(PYTHON) firetimer-joinvids.py --parts "$(FOLDER)" --out "$(OUTPUT)"; \
	else \
		$(PYTHON) firetimer-joinvids.py --parts "$(FOLDER)"; \
	fi

# Launch GUI timestamp recorder
gui:
	@echo "$(GREEN)🎮 Launching GUI...$(NC)"
	@$(PYTHON) video_timestamp_recorder.py

# Test command - clean and run cut on dedictvigympl
testcut:
	@echo "$(YELLOW)🧪 Cleaning dedictvigympl outputs...$(NC)"
	@rm -f dedictvigympl/final_out_video.mp4
	@rm -rf dedictvigympl/out-parts
	@echo "$(GREEN)✅ Cleaned$(NC)"
	@echo "$(YELLOW)🧪 Running cut on dedictvigympl...$(NC)"
	@if [ -f "dedictvigympl/dedictvigympl.mp4" ] && [ -f "dedictvigympl/timestamps.txt" ]; then \
		$(PYTHON) firetimer-cutvid.py -s dedictvigympl/dedictvigympl.mp4 -t dedictvigympl/timestamps.txt -z; \
		echo "$(GREEN)✅ Cut complete$(NC)"; \
		if [ -f "dedictvigympl/final_out_video.mp4" ]; then \
			echo "$(GREEN)🎬 Opening video in player...$(NC)"; \
			if command -v ffplay >/dev/null 2>&1; then \
				ffplay dedictvigympl/final_out_video.mp4 & \
			else \
				echo "$(YELLOW)⚠️  No video player found (ffplay)$(NC)"; \
				echo "$(YELLOW)   Video saved at: dedictvigympl/final_out_video.mp4$(NC)"; \
			fi \
		fi \
	else \
		echo "$(RED)❌ Test files not found: dedictvigympl/dedictvigympl.mp4 or dedictvigympl/timestamps.txt$(NC)"; \
		exit 1; \
	fi
