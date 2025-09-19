#!/usr/bin/env python3
"""
Build script for File Hash Generator
Creates executables for different platforms with proper configuration
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path


class Builder:
    def __init__(self):
        self.platform = platform.system().lower()
        self.is_windows = self.platform == 'windows'
        self.is_macos = self.platform == 'darwin'
        self.is_linux = self.platform == 'linux'
        
    def create_icon(self):
        """Create a simple icon if none exists."""
        try:
            from PIL import Image, ImageDraw
            
            # Create a simple icon
            size = 256
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw a simple hash/grid pattern
            color = (46, 134, 171, 255)  # Blue color from our theme
            line_width = 8
            
            # Draw grid
            for i in range(0, size, 32):
                draw.line([(i, 0), (i, size)], fill=color, width=line_width)
                draw.line([(0, i), (size, i)], fill=color, width=line_width)
            
            # Draw border
            draw.rectangle([0, 0, size-1, size-1], outline=color, width=line_width)
            
            # Save different formats
            if self.is_windows:
                # For Windows .ico
                sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                icons = []
                for s in sizes:
                    icons.append(img.resize(s, Image.Resampling.LANCZOS))
                icons[0].save('icon.ico', format='ICO', sizes=[(s.width, s.height) for s in icons])
                print("✅ Created icon.ico")
                
            elif self.is_macos:
                # For macOS .icns (simplified - would need more work for full icns)
                img.resize((128, 128), Image.Resampling.LANCZOS).save('icon.png')
                print("✅ Created icon.png (macOS)")
                
            else:
                # For Linux .png
                img.resize((128, 128), Image.Resampling.LANCZOS).save('icon.png')
                print("✅ Created icon.png (Linux)")
                
        except ImportError:
            print("⚠️  PIL not available, creating simple placeholder icon")
            # Create simple text file as placeholder
            if self.is_windows:
                with open('icon.ico', 'w') as f:
                    f.write('')  # Empty file to prevent build errors
                    
    def create_version_info(self):
        """Create Windows version info file."""
        if not self.is_windows:
            return
            
        version_info = '''# UTF-8
#
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(2, 0, 0, 0),
    prodvers=(2, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Hash Generator Project'),
        StringStruct(u'FileDescription', u'File Hash Generator and Verifier'),
        StringStruct(u'FileVersion', u'2.0.0'),
        StringStruct(u'InternalName', u'file-hash-generator'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2024'),
        StringStruct(u'OriginalFilename', u'file-hash-generator.exe'),
        StringStruct(u'ProductName', u'File Hash Generator'),
        StringStruct(u'ProductVersion', u'2.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
        
        with open('version_info.txt', 'w', encoding='utf-8') as f:
            f.write(version_info)
        print("✅ Created version_info.txt")
    
    def install_dependencies(self):
        """Install required dependencies."""
        print("📦 Installing dependencies...")
        
        # Core dependencies
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller>=5.0'], check=True)
        
        # Optional hash libraries
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'xxhash>=3.0.0'], check=True)
            print("✅ Installed xxhash")
        except subprocess.CalledProcessError:
            print("⚠️  Could not install xxhash (optional)")
            
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'blake3>=0.3.0'], check=True)
            print("✅ Installed blake3")
        except subprocess.CalledProcessError:
            print("⚠️  Could not install blake3 (optional)")
        
        # PIL for icon creation
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'Pillow'], check=True)
            print("✅ Installed Pillow for icon creation")
        except subprocess.CalledProcessError:
            print("⚠️  Could not install Pillow (for icon creation)")
    
    def build_executable(self):
        """Build the executable using PyInstaller."""
        print(f"🔨 Building executable for {self.platform}...")
        
        # Basic PyInstaller command
        cmd = [
            'pyinstaller',
            '--onefile',
            '--name', 'file-hash-generator',
        ]
        
        # Platform-specific options
        if self.is_windows:
            cmd.extend(['--windowed', '--icon=icon.ico'])
            if Path('version_info.txt').exists():
                cmd.extend(['--version-file=version_info.txt'])
        elif self.is_macos:
            cmd.extend(['--windowed'])
            if Path('icon.icns').exists():
                cmd.extend(['--icon=icon.icns'])
        else:  # Linux
            if Path('icon.png').exists():
                cmd.extend(['--icon=icon.png'])
        
        # Add optimization flags
        cmd.extend([
            '--optimize=2',
            '--strip',  # Strip debug symbols
            '--upx-dir=/usr/bin' if shutil.which('upx') else '--noupx',
        ])
        
        # Specify main file
        cmd.append('main.py')
        
        # Run PyInstaller
        try:
            subprocess.run(cmd, check=True)
            print("✅ Build completed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            return False
            
        return True
    
    def post_build_tasks(self):
        """Perform post-build tasks."""
        print("🔧 Performing post-build tasks...")
        
        # Check if executable was created
        dist_dir = Path('dist')
        if self.is_windows:
            executable = dist_dir / 'file-hash-generator.exe'
        else:
            executable = dist_dir / 'file-hash-generator'
            
        if not executable.exists():
            print(f"❌ Executable not found at {executable}")
            return False
        
        print(f"✅ Executable created: {executable}")
        print(f"📊 File size: {executable.stat().st_size / 1024 / 1024:.1f} MB")
        
        # Create release directory
        release_dir = Path('release')
        release_dir.mkdir(exist_ok=True)
        
        # Copy executable
        if self.is_windows:
            shutil.copy2(executable, release_dir / 'file-hash-generator.exe')
        else:
            shutil.copy2(executable, release_dir / 'file-hash-generator')
            # Ensure execute permission
            os.chmod(release_dir / 'file-hash-generator', 0o755)
        
        # Create README
        readme_content = f"""File Hash Generator & Verifier v2.0
====================================

Platform: {platform.system()} {platform.machine()}
Built on: {platform.platform()}

FEATURES:
- Generate hashes for files and directories
- Support for multiple algorithms: MD5, SHA1, SHA-3, SHA256, SHA512, xxHash64, Blake2b, Blake3, CRC32
- Verify file integrity against saved hashes
- Modern GUI with progress tracking
- Multi-threaded processing
- Auto-save functionality
- Detailed error reporting

USAGE:
{'Double-click file-hash-generator.exe to run' if self.is_windows else 'Run ./file-hash-generator from terminal or file manager'}

No Python installation required - this is a standalone executable.

SYSTEM REQUIREMENTS:
"""
        
        if self.is_windows:
            readme_content += "- Windows 10 or later (64-bit)\n"
        elif self.is_macos:
            readme_content += "- macOS 10.14 or later\n"
        else:
            readme_content += "- Any modern Linux distribution (64-bit)\n"
            
        with open(release_dir / 'README.txt', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✅ Release files created in {release_dir}/")
        return True
    
    def clean_build_files(self):
        """Clean up build artifacts."""
        print("🧹 Cleaning up build files...")
        
        dirs_to_remove = ['build', '__pycache__']
        files_to_remove = ['*.pyc', '*.pyo', '*.spec']
        
        for dir_name in dirs_to_remove:
            if Path(dir_name).exists():
                shutil.rmtree(dir_name)
                print(f"🗑️  Removed {dir_name}/")
        
        for pattern in files_to_remove:
            for file_path in Path('.').glob(pattern):
                file_path.unlink()
                print(f"🗑️  Removed {file_path}")
    
    def build(self, clean=True):
        """Main build process."""
        print(f"🚀 Starting build process for {platform.system()}...")
        print(f"Python version: {sys.version}")
        print(f"Platform: {platform.platform()}")
        
        try:
            # Step 1: Install dependencies
            self.install_dependencies()
            
            # Step 2: Create resources
            self.create_icon()
            self.create_version_info()
            
            # Step 3: Build executable
            if not self.build_executable():
                return False
            
            # Step 4: Post-build tasks
            if not self.post_build_tasks():
                return False
            
            # Step 5: Clean up (optional)
            if clean:
                self.clean_build_files()
            
            print("🎉 Build completed successfully!")
            print("\nNext steps:")
            print("1. Test the executable in the release/ directory")
            print("2. Distribute the contents of release/ directory")
            
            return True
            
        except Exception as e:
            print(f"💥 Build failed with error: {e}")
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build File Hash Generator executable')
    parser.add_argument('--no-clean', action='store_true', 
                       help='Do not clean build files after build')
    parser.add_argument('--deps-only', action='store_true',
                       help='Only install dependencies, do not build')
    
    args = parser.parse_args()
    
    builder = Builder()
    
    if args.deps_only:
        builder.install_dependencies()
        return
    
    success = builder.build(clean=not args.no_clean)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()