.PHONY: help setup activate clean download cut join timer gui test-cut test-join

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
	@echo ""
	@echo "  make gui            - Launch GUI timestamp recorder"
	@echo ""
	@echo "  make cut SOURCE=<video.mp4> TIMES='<timestamps.txt>' [SORT=1]"
	@echo "                      - Cut video by timestamps with overlays"
	@echo "                      - For multiple files: TIMES='file1.txt file2.txt file3.txt'"
	@echo ""
	@echo "  make join FOLDER=<parts-dir> [OUTPUT=<output.mp4>]"
	@echo "                      - Join video parts into one file"
	@echo ""
	@echo "  make timer SOURCE=<video.mp4> [START=<HH:MM:SS.mmm>] [END=<HH:MM:SS.mmm>] [END_REL=<HH:MM:SS.mmm>] [OUTPUT=<out.mp4>]"
	@echo "                      - Add running timer overlay to a video"
	@echo "                      - START: absolute time when timer begins (default: 0)"
	@echo "                      - END: absolute time when timer freezes (default: end of video)"
	@echo "                      - END_REL: duration from START when timer freezes (alternative to END)"
	@echo ""
	@echo "$(BLUE)Examples:$(NC)"
	@echo "  make download URL='https://youtube.com/watch?v=xyz' NAME=myvideo CHUNK=10"
	@echo "  make cut SOURCE=extraliga-netin/extraliga-netin.mp4 TIMES='extraliga-netin/timestamps.txt' SORT=1"
	@echo "  make cut SOURCE=video.mp4 TIMES='timestamps1.txt timestamps2.txt' SORT=1"
	@echo "  make join FOLDER=extraliga-netin/out-parts"
	@echo "  make timer SOURCE=myvideo.mp4 START=00:00:05.000 END=00:00:20.000"
	@echo "  make timer SOURCE=myvideo.mp4 START=00:00:05.000 END_REL=00:00:15.000"
	@echo "  make gui"
	@echo ""
	@echo "$(BLUE)Quick Test Commands:$(NC)"
	@echo "  make testcut        - Clean and test cut with extraliga-netin example"

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
	@echo "Usage: make cut SOURCE=video.mp4 TIMES='timestamps.txt' [SORT=1]"
	@echo "       make cut SOURCE=video.mp4 TIMES='file1.txt file2.txt' [SORT=1]"
	@exit 1
endif
ifndef TIMES
	@echo "$(RED)❌ Error: TIMES is required$(NC)"
	@echo "Usage: make cut SOURCE=video.mp4 TIMES='timestamps.txt' [SORT=1]"
	@echo "       make cut SOURCE=video.mp4 TIMES='file1.txt file2.txt' [SORT=1]"
	@exit 1
endif
	@echo "$(GREEN)✂️  Cutting video...$(NC)"
	@if [ -n "$(SORT)" ] && [ "$(SORT)" = "1" ]; then \
		$(PYTHON) firetimer-cutvid.py -s "$(SOURCE)" -t $(TIMES) -z; \
	else \
		$(PYTHON) firetimer-cutvid.py -s "$(SOURCE)" -t $(TIMES); \
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

# Add timer overlay to a video
timer:
ifndef SOURCE
	@echo "$(RED)❌ Error: SOURCE is required$(NC)"
	@echo "Usage: make timer SOURCE=video.mp4 [START=HH:MM:SS.mmm] [END=HH:MM:SS.mmm] [END_REL=HH:MM:SS.mmm] [OUTPUT=out.mp4]"
	@exit 1
endif
	@echo "$(GREEN)⏱️  Adding timer overlay...$(NC)"
	@cmd="$(PYTHON) add-timer.py -s \"$(SOURCE)\""; \
	if [ -n "$(START)" ]; then cmd="$$cmd --start \"$(START)\""; fi; \
	if [ -n "$(END)" ]; then cmd="$$cmd --end \"$(END)\""; fi; \
	if [ -n "$(END_REL)" ]; then cmd="$$cmd --end-relative \"$(END_REL)\""; fi; \
	if [ -n "$(OUTPUT)" ]; then cmd="$$cmd -o \"$(OUTPUT)\""; fi; \
	eval $$cmd

# Launch GUI timestamp recorder
gui:
	@echo "$(GREEN)🎮 Launching GUI...$(NC)"
	@$(PYTHON) video_timestamp_recorder.py

# Test command - clean and run cut on extraliga-netin
testcut:
	@echo "$(YELLOW)🧪 Cleaning extraliga-netin outputs...$(NC)"
	@rm -f extraliga-netin/final_out_video.mp4
	@rm -f extraliga-netin/out-parts/*.mp4 2>/dev/null || true
	@rm -rf extraliga-netin/out-parts
	@echo "$(GREEN)✅ Cleaned$(NC)"
	@echo "$(YELLOW)🧪 Running cut on extraliga-netin...$(NC)"
	@if [ -f "extraliga-netin/extraliga-netin.mp4" ] && [ -f "extraliga-netin/timestamps.txt" ]; then \
		$(PYTHON) firetimer-cutvid.py -s extraliga-netin/extraliga-netin.mp4 -t extraliga-netin/timestamps.txt -z; \
		echo "$(GREEN)✅ Cut complete$(NC)"; \
		if [ -f "extraliga-netin/final_out_video.mp4" ]; then \
			echo "$(GREEN)🎬 Opening video in player...$(NC)"; \
			if command -v ffplay >/dev/null 2>&1; then \
				ffplay extraliga-netin/final_out_video.mp4 & \
			else \
				echo "$(YELLOW)⚠️  No video player found (ffplay)$(NC)"; \
				echo "$(YELLOW)   Video saved at: extraliga-netin/final_out_video.mp4$(NC)"; \
			fi \
		fi \
	else \
		echo "$(RED)❌ Test files not found: extraliga-netin/extraliga-netin.mp4 or extraliga-netin/timestamps.txt$(NC)"; \
		exit 1; \
	fi
