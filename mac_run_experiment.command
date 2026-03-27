#!/bin/bash
# BodyLocaliser -- Mac launcher
# Double-click this file to install dependencies and run the experiment.
# PsychoPy requires Python >=3.9, <3.12.

cd "$(dirname "$0")"

VENV_DIR=".venv"
PYTHON=""
NEED_MIN=9
NEED_MAX=11

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
ask_yes_no() {
    local prompt="$1"
    local answer
    while true; do
        read -rp "$prompt [y/n] " answer
        case "$answer" in
            [yY]|[yY][eE][sS]) return 0 ;;
            [nN]|[nN][oO])     return 1 ;;
            *) echo "Please enter y or n." ;;
        esac
    done
}

is_compatible() {
    local bin="$1"
    if ! command -v "$bin" &>/dev/null && [ ! -x "$bin" ]; then return 1; fi
    local ver major minor
    ver=$("$bin" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    [ "$major" -eq 3 ] && [ "$minor" -ge "$NEED_MIN" ] && [ "$minor" -le "$NEED_MAX" ]
}

get_version_str() {
    "$1" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+'
}

# ---------------------------------------------------------------------------
# Step 1: Check for existing compatible venv
# ---------------------------------------------------------------------------
if [ -f "$VENV_DIR/bin/python" ]; then
    if is_compatible "$VENV_DIR/bin/python"; then
        echo "Found existing environment with Python $(get_version_str "$VENV_DIR/bin/python")."
        PYTHON="$VENV_DIR/bin/python"
    else
        echo "Existing .venv uses Python $(get_version_str "$VENV_DIR/bin/python"), which is not compatible."
        echo "PsychoPy requires Python 3.9, 3.10, or 3.11."
        echo ""
        if ask_yes_no "Delete the existing .venv and create a new one?"; then
            rm -rf "$VENV_DIR"
            echo "Removed old environment."
        else
            echo ""
            echo "Cannot continue with an incompatible environment. Exiting."
            read -rp "Press Enter to exit..."
            exit 1
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Step 2: Find a compatible Python on the system
# ---------------------------------------------------------------------------
if [ -z "$PYTHON" ]; then
    echo ""
    echo "Looking for Python 3.9--3.11 on this system..."
    echo ""

    FOUND_ANY_PYTHON=""

    for v in 3.11 3.10 3.9; do
        if is_compatible "python$v"; then
            echo "  Found python$v ($(get_version_str "python$v"))"
            PYTHON="python$v"
            break
        fi
    done

    if [ -z "$PYTHON" ]; then
        for bin in python3 python; do
            if command -v "$bin" &>/dev/null; then
                ver=$(get_version_str "$bin")
                FOUND_ANY_PYTHON="$bin ($ver)"
                if is_compatible "$bin"; then
                    echo "  Found $bin ($ver)"
                    PYTHON="$bin"
                    break
                fi
            fi
        done
    fi

    if [ -n "$PYTHON" ]; then
        echo ""
        echo "Will use: $PYTHON ($(get_version_str "$PYTHON"))"
    fi
fi

# ---------------------------------------------------------------------------
# Step 3: If no compatible Python, offer options
# ---------------------------------------------------------------------------
if [ -z "$PYTHON" ]; then
    echo ""
    if [ -n "$FOUND_ANY_PYTHON" ]; then
        echo "Found $FOUND_ANY_PYTHON, but PsychoPy requires 3.9, 3.10, or 3.11."
    else
        echo "No Python installation found."
    fi
    echo ""
    echo "PsychoPy needs Python 3.9, 3.10, or 3.11 to run."
    echo ""

    HAS_CONDA=false
    HAS_BREW=false
    if command -v conda &>/dev/null; then HAS_CONDA=true; fi
    if command -v brew &>/dev/null; then HAS_BREW=true; fi

    echo "How would you like to install a compatible Python?"
    echo ""
    OPT=1
    OPT_CONDA="" ; OPT_BREW="" ; OPT_INSTALLER=""

    if $HAS_CONDA; then
        echo "  $OPT) Use conda to create an environment with Python 3.11 (recommended)"
        OPT_CONDA=$OPT
        OPT=$((OPT + 1))
    fi
    if $HAS_BREW; then
        echo "  $OPT) Use Homebrew to install Python 3.11"
        OPT_BREW=$OPT
        OPT=$((OPT + 1))
    fi
    echo "  $OPT) Download the Python 3.11 installer from python.org"
    OPT_INSTALLER=$OPT
    OPT=$((OPT + 1))
    echo "  $OPT) Exit (I'll install Python myself)"
    OPT_EXIT=$OPT

    echo ""
    while true; do
        read -rp "Enter choice [1-$OPT_EXIT]: " choice

        # --- Conda ---
        if [ "$choice" = "$OPT_CONDA" ] && [ -n "$OPT_CONDA" ]; then
            echo ""
            echo "Creating conda environment with Python 3.11..."
            if conda create -y -p "$VENV_DIR" python=3.11 pip -q; then
                PYTHON="$VENV_DIR/bin/python"
                echo ""
                echo "Conda environment created successfully."
            else
                echo ""
                echo "Conda environment creation failed."
                if ask_yes_no "Would you like to try another option?"; then
                    continue
                fi
                read -rp "Press Enter to exit..."
                exit 1
            fi
            break

        # --- Homebrew ---
        elif [ "$choice" = "$OPT_BREW" ] && [ -n "$OPT_BREW" ]; then
            echo ""
            echo "Installing Python 3.11 via Homebrew..."
            if brew install python@3.11; then
                if is_compatible "$(brew --prefix)/opt/python@3.11/bin/python3.11"; then
                    PYTHON="$(brew --prefix)/opt/python@3.11/bin/python3.11"
                elif is_compatible python3.11; then
                    PYTHON="python3.11"
                fi
                if [ -n "$PYTHON" ]; then
                    echo ""
                    echo "Homebrew install successful."
                else
                    echo ""
                    echo "Homebrew installed Python but it could not be found on PATH."
                    if ask_yes_no "Would you like to try another option?"; then
                        continue
                    fi
                    read -rp "Press Enter to exit..."
                    exit 1
                fi
            else
                echo ""
                echo "Homebrew install failed."
                if ask_yes_no "Would you like to try another option?"; then
                    continue
                fi
                read -rp "Press Enter to exit..."
                exit 1
            fi
            break

        # --- python.org installer ---
        elif [ "$choice" = "$OPT_INSTALLER" ]; then
            PY_VER="3.11.11"
            PKG_URL="https://www.python.org/ftp/python/${PY_VER}/python-${PY_VER}-macos11.pkg"
            PKG_PATH="/tmp/python-${PY_VER}-installer.pkg"

            echo ""
            echo "Downloading Python ${PY_VER} from python.org..."
            if ! curl -L --progress-bar -o "$PKG_PATH" "$PKG_URL"; then
                echo ""
                echo "Download failed. Check your internet connection."
                if ask_yes_no "Would you like to try again?"; then
                    continue
                fi
                read -rp "Press Enter to exit..."
                exit 1
            fi

            echo ""
            echo "Opening the installer. Please follow the prompts to complete installation."
            open "$PKG_PATH"
            echo ""
            read -rp "Press Enter here after the installer finishes..."

            export PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:/usr/local/bin:$PATH"

            if is_compatible python3.11; then
                PYTHON="python3.11"
                echo ""
                echo "Python 3.11 installed successfully."
            elif is_compatible python3; then
                PYTHON="python3"
                echo ""
                echo "Python installed successfully."
            else
                echo ""
                echo "Python 3.11 was not detected after installation."
                echo "You may need to close this window and double-click mac_run_experiment.command again."
                read -rp "Press Enter to exit..."
                exit 1
            fi
            break

        # --- Exit ---
        elif [ "$choice" = "$OPT_EXIT" ]; then
            echo ""
            echo "Install Python 3.9, 3.10, or 3.11, then run this script again."
            read -rp "Press Enter to exit..."
            exit 0

        else
            echo "Invalid choice. Please enter a number from 1 to $OPT_EXIT."
        fi
    done
fi

# ---------------------------------------------------------------------------
# Step 4: Create virtual environment (if conda didn't already)
# ---------------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment..."
    if ! $PYTHON -m venv "$VENV_DIR"; then
        echo ""
        echo "Failed to create virtual environment."
        echo "This can happen if the 'venv' module is missing."
        echo ""
        if command -v conda &>/dev/null; then
            if ask_yes_no "Would you like to try using conda instead?"; then
                conda create -y -p "$VENV_DIR" python=3.11 pip -q
                PYTHON="$VENV_DIR/bin/python"
            else
                read -rp "Press Enter to exit..."
                exit 1
            fi
        else
            echo "Try: sudo apt install python3.11-venv (Linux) or reinstall Python."
            read -rp "Press Enter to exit..."
            exit 1
        fi
    fi
fi

if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
fi

# ---------------------------------------------------------------------------
# Step 5: Install dependencies
# ---------------------------------------------------------------------------
if [ ! -f "$VENV_DIR/.installed" ]; then
    echo ""
    echo "Installing PsychoPy and dependencies (this may take a few minutes)..."
    echo ""
    if ! "$VENV_DIR/bin/pip" install --upgrade pip -q; then
        echo "Warning: pip upgrade failed, continuing anyway..."
    fi
    if ! "$VENV_DIR/bin/pip" install -r requirements.txt; then
        echo ""
        echo "Dependency installation failed."
        echo ""
        if ask_yes_no "Would you like to retry?"; then
            "$VENV_DIR/bin/pip" install -r requirements.txt
            if [ $? -ne 0 ]; then
                echo ""
                echo "Installation failed again. Check the error messages above."
                read -rp "Press Enter to exit..."
                exit 1
            fi
        else
            echo ""
            echo "You can try running this script again later."
            read -rp "Press Enter to exit..."
            exit 1
        fi
    fi
    touch "$VENV_DIR/.installed"
    echo ""
    echo "Dependencies installed successfully."
fi

# ---------------------------------------------------------------------------
# Step 6: Run the experiment
# ---------------------------------------------------------------------------
echo ""
echo "Starting BodyLocaliser..."
echo "---"
"$VENV_DIR/bin/python" src/main.py
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "Experiment finished."
else
    echo "Experiment exited with code $EXIT_CODE."
fi

if ask_yes_no "Run the experiment again?"; then
    exec "$0"
fi

echo ""
echo "Done. You can close this window."
