#!/bin/bash

# File Hash Generator & Verifier - macOS Setup Script
# ===================================================
# Note: .command extension allows double-click execution on macOS

set -e  # Exit on any error

# Change to script directory
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${PURPLE}$1${NC}"; }

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check macOS version
check_macos_version() {
    local version=$(sw_vers -productVersion)
    local major=$(echo "$version" | cut -d. -f1)
    local minor=$(echo "$version" | cut -d. -f2)
    
    print_info "macOS version: $version"
    
    # Check if macOS 10.14+ (required for modern Python)
    if [ "$major" -gt 10 ] || ([ "$major" -eq 10 ] && [ "$minor" -ge 14 ]); then
        print_success "macOS version is compatible (10.14+)"
        return 0
    else
        print_warning "macOS 10.14 or higher is recommended"
        return 1
    fi
}

# Function to install Homebrew if not present
install_homebrew() {
    if command_exists brew; then
        print_success "Homebrew is already installed"
        return 0
    fi
    
    print_info "Homebrew not found. Installing Homebrew..."
    print_warning "This requires admin privileges and internet connection"
    
    # Install Homebrew
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == 'arm64' ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    if command_exists brew; then
        print_success "Homebrew installed successfully"
        return 0
    else
        print_error "Homebrew installation failed"
        return 1
    fi
}

# Function to install Python via Homebrew
install_python_homebrew() {
    print_info "Installing Python via Homebrew..."
    
    # Update Homebrew
    brew update
    
    # Install Python
    brew install python@3.11
    
    # Create symlinks if needed
    brew link --overwrite python@3.11
    
    if command_exists python3; then
        print_success "Python installed via Homebrew"
        return 0
    else
        print_error "Python installation via Homebrew failed"
        return 1
    fi
}

# Function to check and install Xcode Command Line Tools
install_xcode_tools() {
    print_info "Checking Xcode Command Line Tools..."
    
    if xcode-select -p &>/dev/null; then
        print_success "Xcode Command Line Tools are installed"
        return 0
    fi
    
    print_info "Installing Xcode Command Line Tools..."
    print_warning "This may take several minutes and requires internet connection"
    
    # Trigger installation
    xcode-select --install 2>/dev/null || true
    
    # Wait for installation
    echo "Please complete the Xcode Command Line Tools installation in the dialog box."
    echo "Press Enter after the installation is complete..."
    read -r
    
    if xcode-select -p &>/dev/null; then
        print_success "Xcode Command Line Tools installed"
        return 0
    else
        print_error "Xcode Command Line Tools installation failed or incomplete"
        return 1
    fi
}

# Main setup function
main() {
    clear
    print_header "====================================="
    print_header " File Hash Generator & Verifier Setup"
    print_header "====================================="
    print_header " Platform: macOS"
    print_header " Version: 2.0"
    print_header "====================================="
    echo
    
    # Display system information
    print_info "System: $(sw_vers -productName) $(sw_vers -productVersion)"
    print_info "Architecture: $(uname -m)"
    print_info "User: $USER"
    echo

    # Step 1: Check macOS version
    print_info "[1/10] Checking macOS version..."
    check_macos_version

    # Step 2: Check/Install Xcode Command Line Tools
    print_info "[2/10] Checking development tools..."
    if ! install_xcode_tools; then
        print_error "Development tools are required but not available"
        exit 1
    fi

    # Step 3: Check Python installation
    print_info "[3/10] Checking Python installation..."
    
    PYTHON_CMD=""
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_info "Found system Python $PYTHON_VERSION"
        
        # Check if Python version is 3.8 or higher
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            print_success "Python version is compatible (3.8+)"
            PYTHON_CMD="python3"
        else
            print_warning "System Python $PYTHON_VERSION is too old (need 3.8+)"
            PYTHON_CMD=""
        fi
    fi
    
    # If no compatible Python found, install via Homebrew
    if [ -z "$PYTHON_CMD" ]; then
        print_info "Installing Python via Homebrew..."
        
        # Install Homebrew if needed
        if ! install_homebrew; then
            print_error "Cannot install Python without Homebrew"
            exit 1
        fi
        
        # Install Python
        if ! install_python_homebrew; then
            print_error "Python installation failed"
            exit 1
        fi
        
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    fi
    
    print_success "Using Python $PYTHON_VERSION"

    # Step 4: Check pip
    print_info "[4/10] Checking pip availability..."
    if $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
        print_success "pip is available"
    else
        print_error "pip is not available"
        print_info "Installing pip..."
        if command_exists curl; then
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
            $PYTHON_CMD get-pip.py --user
            rm get-pip.py
        else
            print_error "curl not found. Please install pip manually"
            exit 1
        fi
    fi

    # Step 5: Check tkinter (usually included with Python on macOS)
    print_info "[5/10] Checking tkinter availability..."
    if $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
        print_success "tkinter is available"
    else
        print_warning "tkinter is not available"
        print_info "Installing Python with tkinter via Homebrew..."
        
        if command_exists brew; then
            brew install python-tk@3.11 || print_warning "python-tk installation failed"
        else
            print_error "Homebrew not available, cannot install tkinter"
            exit 1
        fi
        
        # Check again
        if $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
            print_success "tkinter is now available"
        else
            print_error "tkinter installation failed"
            print_info "Please install Python with tkinter support"
            exit 1
        fi
    fi

    # Step 6: Create virtual environment
    print_info "[6/10] Creating virtual environment..."
    if [ -d "venv" ]; then
        print_info "Virtual environment already exists, removing..."
        rm -rf venv
    fi

    $PYTHON_CMD -m venv venv
    if [ $? -eq 0 ]; then
        print_success "Virtual environment created"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi

    # Step 7: Activate virtual environment
    print_info "[7/10] Activating virtual environment..."
    source venv/bin/activate
    if [ $? -eq 0 ]; then
        print_success "Virtual environment activated"
    else
        print_error "Failed to activate virtual environment"
        exit 1
    fi

    # Step 8: Upgrade pip
    print_info "[8/10] Upgrading pip..."
    python -m pip install --upgrade pip
    if [ $? -ne 0 ]; then
        print_warning "Failed to upgrade pip, continuing..."
    fi

    # Step 9: Install requirements
    print_info "[9/10] Installing requirements..."

    if [ -f "requirements.txt" ]; then
        print_info "Installing from requirements.txt..."
        pip install -r requirements.txt
    else
        print_info "requirements.txt not found, installing essential packages..."
        
        print_info "Installing PyInstaller for building executables..."
        pip install "pyinstaller>=5.0"
        
        print_info "Installing optional hash libraries..."
        pip install "xxhash>=3.0.0" || print_warning "xxhash installation failed (optional dependency)"
        pip install "blake3>=0.3.0" || print_warning "blake3 installation failed (optional dependency)"
        
        print_info "Installing Pillow for icon generation..."
        pip install "Pillow" || print_warning "Pillow installation failed (optional dependency)"
    fi

    # Step 10: Create helper scripts and app bundle
    print_info "[10/10] Creating helper scripts and macOS integration..."

    # Check if main.py exists
    if [ ! -f "main.py" ]; then
        print_warning "main.py not found in current directory"
        print_info "Make sure you have all the project files in this folder"
    fi

    # Create run script
    print_info "Creating run script (run.command)..."
    cat > run.command << 'EOF'
#!/bin/bash

# File Hash Generator & Verifier - macOS Run Script

# Change to script directory
cd "$(dirname "$0")"

print_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
print_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

echo "🚀 Starting File Hash Generator & Verifier..."

# Check if virtual environment exists
if [ -d "venv" ]; then
    print_info "Activating virtual environment..."
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        print_error "Failed to activate virtual environment"
        read -p "Press Enter to exit..."
        exit 1
    fi
else
    print_info "No virtual environment found, using system Python"
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    print_error "main.py not found in current directory"
    read -p "Press Enter to exit..."
    exit 1
fi

# Run the application
print_info "Launching application..."
python main.py

# Check exit status
if [ $? -ne 0 ]; then
    print_error "Application failed to start"
    read -p "Press Enter to exit..."
fi
EOF

    chmod +x run.command
    print_success "Created run.command"

    # Create build script
    print_info "Creating build script (build.command)..."
    cat > build.command << 'EOF'
#!/bin/bash

# File Hash Generator & Verifier - macOS Build Script

# Change to script directory
cd "$(dirname "$0")"

print_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
print_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

echo "🔨 Building File Hash Generator executable..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    print_info "Activating virtual environment..."
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        print_error "Failed to activate virtual environment"
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

# Check if build.py exists
if [ ! -f "build.py" ]; then
    print_error "build.py not found in current directory"
    read -p "Press Enter to exit..."
    exit 1
fi

# Run build script
print_info "Starting build process..."
python build.py "$@"

echo "🏁 Build process completed!"
read -p "Press Enter to exit..."
EOF

    chmod +x build.command
    print_success "Created build.command"

    # Create app bundle structure (optional)
    read -p "Would you like to create a macOS app bundle? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Creating macOS app bundle..."
        
        APP_NAME="File Hash Generator.app"
        APP_DIR="$APP_NAME/Contents"
        
        mkdir -p "$APP_DIR/MacOS"
        mkdir -p "$APP_DIR/Resources"
        
        # Create Info.plist
        cat > "$APP_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>File Hash Generator</string>
    <key>CFBundleDisplayName</key>
    <string>File Hash Generator & Verifier</string>
    <key>CFBundleIdentifier</key>
    <string>com.hashgenerator.app</string>
    <key>CFBundleVersion</key>
    <string>2.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>HASH</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
</dict>
</plist>
EOF

        # Create launcher script
        CURRENT_DIR=$(pwd)
        cat > "$APP_DIR/MacOS/launcher" << EOF
#!/bin/bash
cd "$CURRENT_DIR"
source venv/bin/activate 2>/dev/null || true
python main.py
EOF

        chmod +x "$APP_DIR/MacOS/launcher"
        
        print_success "Created app bundle: $APP_NAME"
        print_info "You can now double-click the app bundle to run the application"
    fi

    # Create uninstall script
    print_info "Creating uninstall script..."
    cat > uninstall.command << 'EOF'
#!/bin/bash

# File Hash Generator & Verifier - macOS Uninstall Script

# Change to script directory
cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}File Hash Generator & Verifier - Uninstall${NC}"
echo "This will remove the virtual environment and generated files"
echo

read -p "Are you sure you want to uninstall? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Uninstalling...${NC}"
    
    # Remove directories
    [ -d "venv" ] && rm -rf venv && echo "Removed venv/"
    [ -d "build" ] && rm -rf build && echo "Removed build/"
    [ -d "dist" ] && rm -rf dist && echo "Removed dist/"
    [ -d "release" ] && rm -rf release && echo "Removed release/"
    [ -d "__pycache__" ] && rm -rf __pycache__ && echo "Removed __pycache__/"
    [ -d "File Hash Generator.app" ] && rm -rf "File Hash Generator.app" && echo "Removed app bundle"
    
    # Remove files
    [ -f *.spec ] && rm -f *.spec && echo "Removed *.spec files"
    [ -f "run.command" ] && rm -f run.command && echo "Removed run.command"
    [ -f "build.command" ] && rm -f build.command && echo "Removed build.command"
    
    # Remove this script last
    rm -f uninstall.command
    
    echo -e "${GREEN}Uninstall completed!${NC}"
    echo "You can now safely delete this folder"
else
    echo -e "${YELLOW}Uninstall cancelled${NC}"
fi

read -p "Press Enter to exit..."
EOF

    chmod +x uninstall.command
    print_success "Created uninstall.command"

    # Final summary
    echo
    print_header "====================================="
    print_header " Setup Completed Successfully!"
    print_header "====================================="
    echo
    echo -e "${GREEN}What's been installed:${NC}"
    echo "  ✓ Python virtual environment (venv/)"
    echo "  ✓ Required Python packages"
    echo "  ✓ Run script (run.command)"
    echo "  ✓ Build script (build.command)"
    echo "  ✓ Uninstall script (uninstall.command)"
    if [ -d "File Hash Generator.app" ]; then
        echo "  ✓ macOS app bundle (File Hash Generator.app)"
    fi
    echo
    echo -e "${CYAN}Next steps:${NC}"
    echo "  1. To run the application:"
    echo "     • Double-click: run.command"
    if [ -d "File Hash Generator.app" ]; then
        echo "     • Double-click: File Hash Generator.app"
    fi
    echo "     • Terminal: ./run.command"
    echo "     • Manual: source venv/bin/activate && python main.py"
    echo
    echo "  2. To build an executable:"
    echo "     • Double-click: build.command"
    echo "     • Terminal: ./build.command"
    echo "     • Manual: source venv/bin/activate && python build.py"
    echo
    echo "  3. To uninstall everything:"
    echo "     • Double-click: uninstall.command"
    echo
    echo -e "${GREEN}The application is ready to use!${NC}"
    echo

    # Offer to run the application immediately
    read -p "Would you like to run the application now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo
        print_info "Starting File Hash Generator..."
        if [ -f "main.py" ]; then
            python main.py &
        else
            print_error "main.py not found. Please ensure all project files are present."
            read -p "Press Enter to exit..."
        fi
    fi

    echo
    print_success "Setup script completed successfully!"
    echo "You can now close this terminal window."
    
    # Keep terminal open for a moment
    sleep 2
}

# Handle script interruption
trap 'echo; print_warning "Setup interrupted by user"; read -p "Press Enter to exit..."; exit 1' INT TERM

# Run main function
main "$@"

# Keep terminal open briefly if run by double-click
if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
    sleep 3
fi