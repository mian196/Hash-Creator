#!/bin/bash

# File Hash Generator & Verifier - Linux Setup Script
# ===================================================

set -e  # Exit on any error

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

# Function to get Linux distribution
get_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo $ID
    elif command_exists lsb_release; then
        lsb_release -si | tr '[:upper:]' '[:lower:]'
    else
        echo "unknown"
    fi
}

# Function to install system packages
install_system_packages() {
    local distro=$(get_distro)
    print_info "Detected Linux distribution: $distro"
    
    case $distro in
        ubuntu|debian)
            print_info "Installing system packages for Ubuntu/Debian..."
            if command_exists apt-get; then
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv python3-tk python3-dev build-essential
            else
                print_warning "apt-get not found, skipping system package installation"
            fi
            ;;
        fedora|rhel|centos)
            print_info "Installing system packages for Fedora/RHEL/CentOS..."
            if command_exists dnf; then
                sudo dnf install -y python3 python3-pip python3-tkinter python3-devel gcc gcc-c++
            elif command_exists yum; then
                sudo yum install -y python3 python3-pip tkinter python3-devel gcc gcc-c++
            else
                print_warning "Neither dnf nor yum found, skipping system package installation"
            fi
            ;;
        arch)
            print_info "Installing system packages for Arch Linux..."
            if command_exists pacman; then
                sudo pacman -S --noconfirm python python-pip tk base-devel
            else
                print_warning "pacman not found, skipping system package installation"
            fi
            ;;
        opensuse*)
            print_info "Installing system packages for openSUSE..."
            if command_exists zypper; then
                sudo zypper install -y python3 python3-pip python3-tkinter python3-devel gcc gcc-c++
            else
                print_warning "zypper not found, skipping system package installation"
            fi
            ;;
        *)
            print_warning "Unknown distribution: $distro"
            print_info "Please ensure Python 3.8+, pip, tkinter, and development tools are installed"
            ;;
    esac
}

# Main setup function
main() {
    clear
    print_header "====================================="
    print_header " File Hash Generator & Verifier Setup"
    print_header "====================================="
    print_header " Platform: Linux"
    print_header " Version: 2.0"
    print_header "====================================="
    echo

    # Check if running as root (not recommended)
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root is not recommended for this setup"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Setup cancelled"
            exit 0
        fi
    fi

    # Step 1: Check Python installation
    print_info "[1/8] Checking Python installation..."
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION found"
        
        # Check if Python version is 3.8 or higher
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            print_success "Python version is compatible (3.8+)"
        else
            print_error "Python 3.8 or higher is required"
            print_info "Current version: $PYTHON_VERSION"
            
            read -p "Would you like to install system packages that might include a newer Python? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                install_system_packages
            else
                print_info "Please install Python 3.8+ manually and run this script again"
                exit 1
            fi
        fi
    else
        print_error "Python 3 is not installed"
        print_info "Would you like to install system packages including Python?"
        read -p "Install system packages? (Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            install_system_packages
        else
            print_info "Please install Python 3.8+ manually and run this script again"
            exit 1
        fi
    fi

    # Step 2: Check pip
    print_info "[2/8] Checking pip availability..."
    if python3 -m pip --version >/dev/null 2>&1; then
        print_success "pip is available"
    else
        print_error "pip is not available"
        print_info "Installing pip..."
        if command_exists curl; then
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
            python3 get-pip.py --user
            rm get-pip.py
        else
            print_error "curl not found. Please install pip manually"
            exit 1
        fi
    fi

    # Step 3: Check tkinter
    print_info "[3/8] Checking tkinter availability..."
    if python3 -c "import tkinter" 2>/dev/null; then
        print_success "tkinter is available"
    else
        print_warning "tkinter is not available"
        print_info "This is required for the GUI. Installing system packages..."
        install_system_packages
        
        # Check again
        if python3 -c "import tkinter" 2>/dev/null; then
            print_success "tkinter is now available"
        else
            print_error "tkinter installation failed"
            print_info "Please install python3-tkinter manually for your distribution"
            print_info "Ubuntu/Debian: sudo apt-get install python3-tk"
            print_info "Fedora: sudo dnf install python3-tkinter"
            print_info "Arch: sudo pacman -S tk"
            exit 1
        fi
    fi

    # Step 4: Create virtual environment
    print_info "[4/8] Creating virtual environment..."
    if [ -d "venv" ]; then
        print_info "Virtual environment already exists, removing..."
        rm -rf venv
    fi

    python3 -m venv venv
    if [ $? -eq 0 ]; then
        print_success "Virtual environment created"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi

    # Step 5: Activate virtual environment
    print_info "[5/8] Activating virtual environment..."
    source venv/bin/activate
    if [ $? -eq 0 ]; then
        print_success "Virtual environment activated"
    else
        print_error "Failed to activate virtual environment"
        exit 1
    fi

    # Step 6: Upgrade pip
    print_info "[6/8] Upgrading pip..."
    python -m pip install --upgrade pip
    if [ $? -ne 0 ]; then
        print_warning "Failed to upgrade pip, continuing..."
    fi

    # Step 7: Install requirements
    print_info "[7/8] Installing requirements..."

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

    # Step 8: Create helper scripts
    print_info "[8/8] Creating helper scripts..."

    # Check if main.py exists
    if [ ! -f "main.py" ]; then
        print_warning "main.py not found in current directory"
        print_info "Make sure you have all the project files in this folder"
    fi

    # Create run script
    print_info "Creating run script (run.sh)..."
    cat > run.sh << 'EOF'
#!/bin/bash

# File Hash Generator & Verifier - Run Script

print_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
print_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

echo "🚀 Starting File Hash Generator & Verifier..."

# Check if virtual environment exists
if [ -d "venv" ]; then
    print_info "Activating virtual environment..."
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        print_error "Failed to activate virtual environment"
        exit 1
    fi
else
    print_info "No virtual environment found, using system Python"
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    print_error "main.py not found in current directory"
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

    chmod +x run.sh
    print_success "Created run.sh"

    # Create build script
    print_info "Creating build script (build.sh)..."
    cat > build.sh << 'EOF'
#!/bin/bash

# File Hash Generator & Verifier - Build Script

print_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
print_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

echo "🔨 Building File Hash Generator executable..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    print_info "Activating virtual environment..."
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        print_error "Failed to activate virtual environment"
        exit 1
    fi
fi

# Check if build.py exists
if [ ! -f "build.py" ]; then
    print_error "build.py not found in current directory"
    exit 1
fi

# Run build script
print_info "Starting build process..."
python build.py "$@"

echo "🏁 Build process completed!"
EOF

    chmod +x build.sh
    print_success "Created build.sh"

    # Create desktop entry (optional)
    if command_exists desktop-file-install || [ -d "$HOME/.local/share/applications" ]; then
        read -p "Would you like to create a desktop entry? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Creating desktop entry..."
            CURRENT_DIR=$(pwd)
            DESKTOP_FILE="$HOME/.local/share/applications/file-hash-generator.desktop"
            
            mkdir -p "$HOME/.local/share/applications"
            
            cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=File Hash Generator
Comment=File Hash Generator and Verifier
Exec=$CURRENT_DIR/run.sh
Icon=application-x-executable
Terminal=false
Type=Application
Categories=Utility;Security;
StartupWMClass=file-hash-generator
EOF

            if [ -f "$DESKTOP_FILE" ]; then
                print_success "Desktop entry created"
                
                # Try to update desktop database
                if command_exists update-desktop-database; then
                    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
                fi
            else
                print_warning "Failed to create desktop entry"
            fi
        fi
    fi

    # Create uninstall script
    print_info "Creating uninstall script..."
    cat > uninstall.sh << 'EOF'
#!/bin/bash

# File Hash Generator & Verifier - Uninstall Script

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
    
    # Remove files
    [ -f "*.spec" ] && rm -f *.spec && echo "Removed *.spec files"
    [ -f "run.sh" ] && rm -f run.sh && echo "Removed run.sh"
    [ -f "build.sh" ] && rm -f build.sh && echo "Removed build.sh"
    
    # Remove desktop entry
    DESKTOP_FILE="$HOME/.local/share/applications/file-hash-generator.desktop"
    [ -f "$DESKTOP_FILE" ] && rm -f "$DESKTOP_FILE" && echo "Removed desktop entry"
    
    # Remove this script last
    rm -f uninstall.sh
    
    echo -e "${GREEN}Uninstall completed!${NC}"
else
    echo -e "${YELLOW}Uninstall cancelled${NC}"
fi
EOF

    chmod +x uninstall.sh
    print_success "Created uninstall.sh"

    # Final summary
    echo
    print_header "====================================="
    print_header " Setup Completed Successfully!"
    print_header "====================================="
    echo
    echo -e "${GREEN}What's been installed:${NC}"
    echo "  ✓ Python virtual environment (venv/)"
    echo "  ✓ Required Python packages"
    echo "  ✓ Run script (run.sh)"
    echo "  ✓ Build script (build.sh)"
    echo "  ✓ Uninstall script (uninstall.sh)"
    echo
    echo -e "${CYAN}Next steps:${NC}"
    echo "  1. To run the application:"
    echo "     • GUI: ./run.sh"
    echo "     • Manual: source venv/bin/activate && python main.py"
    echo
    echo "  2. To build an executable:"
    echo "     • Script: ./build.sh"
    echo "     • Manual: source venv/bin/activate && python build.py"
    echo
    echo "  3. To uninstall everything:"
    echo "     • Run: ./uninstall.sh"
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
            python main.py
        else
            print_error "main.py not found. Please ensure all project files are present."
        fi
    fi

    echo
    print_success "Setup script completed successfully!"
}

# Handle script interruption
trap 'echo; print_warning "Setup interrupted by user"; exit 1' INT TERM

# Run main function
main "$@"