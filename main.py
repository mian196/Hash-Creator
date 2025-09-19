#!/usr/bin/env python3
"""
File Hash Generator and Verifier
A Python application with GUI for computing and verifying file hashes.
Enhanced version with comprehensive algorithms and better UI.
"""

import os
import sys
import json
import hashlib
import threading
import time
import zlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, Callable
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

# Try to import additional hash libraries
try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False

try:
    import blake3
    BLAKE3_AVAILABLE = True
except ImportError:
    BLAKE3_AVAILABLE = False


class HashGenerator:
    """Core class for hash generation and verification operations."""
    
    def __init__(self):
        self.stop_event = threading.Event()
        self.SUPPORTED_ALGORITHMS = self._get_supported_algorithms()
        
    def _get_supported_algorithms(self):
        """Get all supported hash algorithms."""
        algorithms = {
            'MD5': lambda: hashlib.md5(),
            'SHA1': lambda: hashlib.sha1(),
            'SHA-3': lambda: hashlib.sha3_256(),
            'SHA256': lambda: hashlib.sha256(),
            'SHA512': lambda: hashlib.sha512(),
            'xxHash64': lambda: xxhash.xxh64() if XXHASH_AVAILABLE else None,
            'Blake2b': lambda: hashlib.blake2b(),
            'Blake3': lambda: blake3.blake3() if BLAKE3_AVAILABLE else None,
            'CRC32': lambda: None,  # Special case - handled separately
        }
        
        # Filter out unavailable algorithms
        available = {}
        for name, func in algorithms.items():
            if name == 'CRC32':
                available[name] = func
            else:
                try:
                    test = func()
                    if test is not None:
                        available[name] = func
                except:
                    continue
                    
        return available
    
    def calculate_file_hash(self, file_path: str, algorithm: str = 'SHA256', 
                          chunk_size: int = 8192) -> Optional[str]:
        """Calculate hash for a single file."""
        try:
            if algorithm not in self.SUPPORTED_ALGORITHMS:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
            
            # Special handling for CRC32
            if algorithm == 'CRC32':
                crc = 0
                with open(file_path, 'rb') as f:
                    while chunk := f.read(chunk_size):
                        if self.stop_event.is_set():
                            return None
                        crc = zlib.crc32(chunk, crc)
                return f"{crc & 0xffffffff:08x}"
            
            # Handle xxHash
            if algorithm == 'xxHash64' and XXHASH_AVAILABLE:
                hasher = xxhash.xxh64()
                with open(file_path, 'rb') as f:
                    while chunk := f.read(chunk_size):
                        if self.stop_event.is_set():
                            return None
                        hasher.update(chunk)
                return hasher.hexdigest()
            
            # Handle Blake3
            if algorithm == 'Blake3' and BLAKE3_AVAILABLE:
                hasher = blake3.blake3()
                with open(file_path, 'rb') as f:
                    while chunk := f.read(chunk_size):
                        if self.stop_event.is_set():
                            return None
                        hasher.update(chunk)
                return hasher.hexdigest()
            
            # Standard hashlib algorithms
            hash_func = self.SUPPORTED_ALGORITHMS[algorithm]()
            
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    if self.stop_event.is_set():
                        return None
                    hash_func.update(chunk)
                    
            return hash_func.hexdigest()
            
        except (IOError, OSError, PermissionError) as e:
            print(f"Error reading file {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error processing {file_path}: {e}")
            return None
            
    def scan_location(self, location: str, algorithm: str = 'SHA256', 
                     progress_callback: Optional[Callable] = None,
                     max_workers: int = 4) -> Tuple[Dict[str, str], List[str]]:
        """Scan a location and calculate hashes for all files."""
        results = {}
        error_files = []
        file_list = []
        
        # Collect all files
        try:
            if os.path.isfile(location):
                file_list = [location]
            elif os.path.isdir(location):
                for root, dirs, files in os.walk(location):
                    if self.stop_event.is_set():
                        break
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            file_list.append(file_path)
        except Exception as e:
            print(f"Error scanning location {location}: {e}")
            return results, [f"Scan error: {str(e)}"]
        
        total_files = len(file_list)
        if total_files == 0:
            return results, error_files
            
        # Process files with threading
        completed_files = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.calculate_file_hash, file_path, algorithm): file_path
                for file_path in file_list
            }
            
            # Process completed tasks
            for future in as_completed(future_to_file):
                if self.stop_event.is_set():
                    break
                    
                file_path = future_to_file[future]
                try:
                    hash_value = future.result()
                    if hash_value:
                        results[file_path] = hash_value
                    else:
                        error_files.append(file_path)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    error_files.append(f"{file_path} - Error: {str(e)}")
                
                completed_files += 1
                if progress_callback:
                    progress_callback(completed_files, total_files, file_path)
        
        return results, error_files
    
    def save_hashes(self, hash_data: Dict[str, str], error_files: List[str], 
                   output_file: str, algorithm: str, scan_location: str) -> bool:
        """Save hash data and errors to files."""
        try:
            # Prepare main data
            data = {
                'metadata': {
                    'algorithm': algorithm,
                    'scan_location': scan_location,
                    'timestamp': datetime.now().isoformat(),
                    'total_files': len(hash_data),
                    'error_files': len(error_files),
                    'application': 'File Hash Generator v2.0'
                },
                'hashes': {},
                'errors': error_files
            }
            
            # Convert paths and add file info
            base_path = os.path.dirname(scan_location) if os.path.isfile(scan_location) else scan_location
            
            for file_path, hash_value in hash_data.items():
                try:
                    rel_path = os.path.relpath(file_path, base_path)
                except ValueError:
                    rel_path = file_path
                
                file_size = 0
                file_mtime = 0
                try:
                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    file_mtime = stat.st_mtime
                except:
                    pass
                
                data['hashes'][rel_path] = {
                    'hash': hash_value,
                    'full_path': file_path,
                    'size': file_size,
                    'modified': file_mtime
                }
            
            # Save main hash file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Save separate error file if there are errors
            if error_files:
                error_file = output_file.replace('.json', '_errors.txt')
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"Error Report - {datetime.now().isoformat()}\n")
                    f.write(f"Scan Location: {scan_location}\n")
                    f.write(f"Algorithm: {algorithm}\n\n")
                    f.write("Files with errors:\n")
                    f.write("=" * 50 + "\n")
                    for error in error_files:
                        f.write(f"{error}\n")
                
            return True
            
        except Exception as e:
            print(f"Error saving hashes: {e}")
            return False
    
    def load_hashes(self, hash_file: str) -> Optional[Dict]:
        """Load hash data from a file."""
        try:
            with open(hash_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate structure
            if 'metadata' not in data or 'hashes' not in data:
                raise ValueError("Invalid hash file format")
                
            return data
            
        except Exception as e:
            print(f"Error loading hashes: {e}")
            return None
    
    def verify_integrity(self, hash_file: str, base_path: str = None,
                        progress_callback: Optional[Callable] = None) -> Tuple[Dict[str, str], List[str], List[str]]:
        """Verify file integrity against saved hashes."""
        hash_data = self.load_hashes(hash_file)
        if not hash_data:
            return {}, [], ["Failed to load hash file"]
        
        algorithm = hash_data['metadata']['algorithm']
        hashes = hash_data['hashes']
        results = {}
        corrupted_files = []
        error_files = []
        
        total_files = len(hashes)
        completed_files = 0
        
        for rel_path, file_info in hashes.items():
            if self.stop_event.is_set():
                break
                
            stored_hash = file_info['hash']
            full_path = file_info.get('full_path', '')
            
            # Determine actual file path
            current_path = None
            if base_path and os.path.exists(os.path.join(base_path, rel_path)):
                current_path = os.path.join(base_path, rel_path)
            elif os.path.exists(full_path):
                current_path = full_path
            elif os.path.exists(rel_path):
                current_path = rel_path
            
            if not current_path:
                results[rel_path] = "FILE_NOT_FOUND"
                error_files.append(f"{rel_path} - File not found")
                completed_files += 1
                if progress_callback:
                    progress_callback(completed_files, total_files, rel_path)
                continue
            
            # Calculate current hash
            try:
                current_hash = self.calculate_file_hash(current_path, algorithm)
                
                if current_hash is None:
                    results[rel_path] = "READ_ERROR"
                    error_files.append(f"{rel_path} - Unable to read file")
                elif current_hash == stored_hash:
                    results[rel_path] = "MATCH"
                else:
                    results[rel_path] = "MISMATCH"
                    corrupted_files.append({
                        'path': current_path,
                        'relative_path': rel_path,
                        'stored_hash': stored_hash,
                        'current_hash': current_hash,
                        'algorithm': algorithm
                    })
            except Exception as e:
                results[rel_path] = "VERIFICATION_ERROR"
                error_files.append(f"{rel_path} - Verification error: {str(e)}")
            
            completed_files += 1
            if progress_callback:
                progress_callback(completed_files, total_files, current_path)
        
        return results, corrupted_files, error_files
    
    def save_verification_report(self, results: Dict[str, str], corrupted_files: List[Dict], 
                               error_files: List[str], output_file: str, hash_file: str) -> bool:
        """Save verification report with corrupted files details."""
        try:
            report = {
                'metadata': {
                    'verification_time': datetime.now().isoformat(),
                    'source_hash_file': hash_file,
                    'total_files_checked': len(results),
                    'corrupted_files': len(corrupted_files),
                    'error_files': len(error_files),
                    'application': 'File Hash Generator v2.0'
                },
                'summary': {
                    'matches': sum(1 for r in results.values() if r == 'MATCH'),
                    'mismatches': sum(1 for r in results.values() if r == 'MISMATCH'),
                    'not_found': sum(1 for r in results.values() if r == 'FILE_NOT_FOUND'),
                    'read_errors': sum(1 for r in results.values() if r == 'READ_ERROR'),
                    'verification_errors': sum(1 for r in results.values() if r == 'VERIFICATION_ERROR')
                },
                'detailed_results': results,
                'corrupted_files': corrupted_files,
                'errors': error_files
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            # Save separate corrupted files list if any
            if corrupted_files:
                corrupted_file = output_file.replace('.json', '_corrupted.txt')
                with open(corrupted_file, 'w', encoding='utf-8') as f:
                    f.write(f"Corrupted Files Report - {datetime.now().isoformat()}\n")
                    f.write(f"Source: {hash_file}\n")
                    f.write(f"Total corrupted files: {len(corrupted_files)}\n\n")
                    
                    for i, file_info in enumerate(corrupted_files, 1):
                        f.write(f"{i}. {file_info['relative_path']}\n")
                        f.write(f"   Full Path: {file_info['path']}\n")
                        f.write(f"   Algorithm: {file_info['algorithm']}\n")
                        f.write(f"   Expected:  {file_info['stored_hash']}\n")
                        f.write(f"   Actual:    {file_info['current_hash']}\n\n")
            
            return True
            
        except Exception as e:
            print(f"Error saving verification report: {e}")
            return False
    
    def stop_operation(self):
        """Stop current operation."""
        self.stop_event.set()
    
    def reset_stop_event(self):
        """Reset stop event for new operations."""
        self.stop_event.clear()


class ModernHashGeneratorGUI:
    """Modern GUI for the File Hash Generator and Verifier."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("File Hash Generator & Verifier v2.0")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Set modern colors
        self.colors = {
            'bg': '#f0f0f0',
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'success': '#2E8B57',
            'warning': '#FF8C00',
            'error': '#DC143C',
            'text': '#2F4F4F'
        }
        
        self.hash_generator = HashGenerator()
        self.current_operation = None
        self.hash_results = {}
        self.error_files = []
        
        self.setup_styles()
        self.setup_gui()
        
    def setup_styles(self):
        """Setup modern ttk styles."""
        style = ttk.Style()
        
        # Configure modern theme
        style.theme_use('clam')
        
        # Custom button styles
        style.configure('Modern.TButton', 
                       font=('Segoe UI', 10),
                       borderwidth=1,
                       focuscolor='none')
        
        style.configure('Primary.TButton',
                       background=self.colors['primary'],
                       foreground='white',
                       font=('Segoe UI', 10, 'bold'),
                       borderwidth=0)
        
        style.map('Primary.TButton',
                 background=[('active', '#1E5F73')])
        
        style.configure('Success.TButton',
                       background=self.colors['success'],
                       foreground='white',
                       font=('Segoe UI', 10, 'bold'))
        
        style.configure('Warning.TButton',
                       background=self.colors['warning'],
                       foreground='white',
                       font=('Segoe UI', 10, 'bold'))
        
        style.configure('Error.TButton',
                       background=self.colors['error'],
                       foreground='white',
                       font=('Segoe UI', 10, 'bold'))
        
        # Custom frame styles
        style.configure('Card.TFrame',
                       background='white',
                       relief='solid',
                       borderwidth=1)
        
        # Custom labelframe style
        style.configure('Modern.TLabelframe',
                       background='white',
                       font=('Segoe UI', 10, 'bold'))
        
        style.configure('Modern.TLabelframe.Label',
                       background='white',
                       foreground=self.colors['primary'],
                       font=('Segoe UI', 10, 'bold'))
        
        # Progress bar style
        style.configure('Modern.Horizontal.TProgressbar',
                       background=self.colors['primary'],
                       troughcolor='#E0E0E0',
                       borderwidth=0,
                       lightcolor=self.colors['primary'],
                       darkcolor=self.colors['primary'])
        
    def setup_gui(self):
        """Setup the modern GUI layout."""
        # Configure root
        self.root.configure(bg=self.colors['bg'])
        
        # Header
        header_frame = tk.Frame(self.root, bg=self.colors['primary'], height=60)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, 
                              text="File Hash Generator & Verifier",
                              bg=self.colors['primary'],
                              fg='white',
                              font=('Segoe UI', 16, 'bold'))
        title_label.pack(expand=True)
        
        subtitle_label = tk.Label(header_frame,
                                 text="Secure file integrity checking with modern algorithms",
                                 bg=self.colors['primary'],
                                 fg='#B8E0FF',
                                 font=('Segoe UI', 10))
        subtitle_label.pack()
        
        # Main container
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Hash Generation Tab
        self.hash_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.hash_tab, text="  Generate Hashes  ")
        self.setup_hash_tab()
        
        # Verification Tab
        self.verify_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.verify_tab, text="  Verify Files  ")
        self.setup_verify_tab()
        
        # Status bar
        self.status_bar = tk.Frame(self.root, bg='#E0E0E0', height=25)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_bar, 
                                    text="Ready", 
                                    bg='#E0E0E0',
                                    fg=self.colors['text'],
                                    font=('Segoe UI', 9))
        self.status_label.pack(side=tk.LEFT, padx=10, pady=2)
        
    def setup_hash_tab(self):
        """Setup modern hash generation tab."""
        # Scrollable frame
        canvas = tk.Canvas(self.hash_tab, bg=self.colors['bg'])
        scrollbar = ttk.Scrollbar(self.hash_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Location selection
        location_frame = ttk.LabelFrame(scrollable_frame, text="📁 Select Location", 
                                       padding=20, style='Modern.TLabelframe')
        location_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.location_var = tk.StringVar()
        location_entry = ttk.Entry(location_frame, textvariable=self.location_var, 
                                  font=('Segoe UI', 10), width=50)
        location_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        btn_frame = tk.Frame(location_frame, bg='white')
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="📄 File", command=self.browse_file,
                  style='Modern.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📁 Folder", command=self.browse_folder,
                  style='Modern.TButton').pack(side=tk.LEFT, padx=2)
        
        # Algorithm and settings
        settings_frame = ttk.LabelFrame(scrollable_frame, text="⚙️ Settings", 
                                      padding=20, style='Modern.TLabelframe')
        settings_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Algorithm selection
        algo_frame = tk.Frame(settings_frame, bg='white')
        algo_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(algo_frame, text="Hash Algorithm:", bg='white', 
                font=('Segoe UI', 10, 'bold'), fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.algorithm_var = tk.StringVar(value='SHA256')
        algo_combo = ttk.Combobox(algo_frame, textvariable=self.algorithm_var,
                                 values=list(self.hash_generator.SUPPORTED_ALGORITHMS.keys()),
                                 state='readonly', font=('Segoe UI', 10), width=15)
        algo_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Performance settings
        perf_frame = tk.Frame(settings_frame, bg='white')
        perf_frame.pack(fill=tk.X)
        
        tk.Label(perf_frame, text="Threads:", bg='white',
                font=('Segoe UI', 10, 'bold'), fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.threads_var = tk.StringVar(value='4')
        threads_spin = ttk.Spinbox(perf_frame, from_=1, to=16, width=5,
                                  textvariable=self.threads_var, font=('Segoe UI', 10))
        threads_spin.pack(side=tk.LEFT, padx=(10, 20))
        
        # Auto-save option
        self.autosave_var = tk.BooleanVar(value=True)
        autosave_check = ttk.Checkbutton(perf_frame, text="Auto-save results",
                                        variable=self.autosave_var)
        autosave_check.pack(side=tk.LEFT)
        
        # Control buttons
        control_frame = ttk.Frame(scrollable_frame, style='Card.TFrame', padding=20)
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        btn_container = tk.Frame(control_frame, bg='white')
        btn_container.pack()
        
        self.generate_btn = ttk.Button(btn_container, text="🔄 Generate Hashes",
                                      command=self.generate_hashes,
                                      style='Primary.TButton')
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_container, text="⏹️ Stop",
                                  command=self.stop_operation,
                                  style='Error.TButton', state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = ttk.Button(btn_container, text="💾 Save Results",
                                  command=self.save_results, 
                                  style='Success.TButton', state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress
        progress_frame = ttk.Frame(scrollable_frame, style='Card.TFrame', padding=20)
        progress_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.progress_var = tk.StringVar(value="Ready to generate hashes")
        progress_label = tk.Label(progress_frame, textvariable=self.progress_var,
                                 bg='white', font=('Segoe UI', 10), fg=self.colors['text'])
        progress_label.pack(anchor=tk.W, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, length=400, mode='determinate',
                                           style='Modern.Horizontal.TProgressbar')
        self.progress_bar.pack(fill=tk.X)
        
        # Results
        results_frame = ttk.LabelFrame(scrollable_frame, text="📊 Results", 
                                     padding=20, style='Modern.TLabelframe')
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=12, wrap=tk.WORD,
                                                     font=('Consolas', 9), bg='#F8F8F8')
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def setup_verify_tab(self):
        """Setup modern verification tab."""
        # Scrollable frame
        canvas = tk.Canvas(self.verify_tab, bg=self.colors['bg'])
        scrollbar = ttk.Scrollbar(self.verify_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Hash file selection
        hash_file_frame = ttk.LabelFrame(scrollable_frame, text="📋 Hash File", 
                                       padding=20, style='Modern.TLabelframe')
        hash_file_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.hash_file_var = tk.StringVar()
        hash_file_entry = ttk.Entry(hash_file_frame, textvariable=self.hash_file_var, 
                                   font=('Segoe UI', 10), width=50)
        hash_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        ttk.Button(hash_file_frame, text="📂 Browse",
                  command=self.browse_hash_file, style='Modern.TButton').pack(side=tk.RIGHT)
        
        # Base path selection
        base_path_frame = ttk.LabelFrame(scrollable_frame, text="📍 Base Path (Optional)", 
                                       padding=20, style='Modern.TLabelframe')
        base_path_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.base_path_var = tk.StringVar()
        base_path_entry = ttk.Entry(base_path_frame, textvariable=self.base_path_var, 
                                   font=('Segoe UI', 10), width=50)
        base_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        ttk.Button(base_path_frame, text="📂 Browse",
                  command=self.browse_base_path, style='Modern.TButton').pack(side=tk.RIGHT)
        
        # Settings
        verify_settings_frame = ttk.LabelFrame(scrollable_frame, text="⚙️ Verification Settings", 
                                             padding=20, style='Modern.TLabelframe')
        verify_settings_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.auto_save_report_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(verify_settings_frame, text="Auto-save verification report",
                       variable=self.auto_save_report_var).pack(anchor=tk.W)
        
        # Control buttons
        verify_control_frame = ttk.Frame(scrollable_frame, style='Card.TFrame', padding=20)
        verify_control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        verify_btn_container = tk.Frame(verify_control_frame, bg='white')
        verify_btn_container.pack()
        
        self.verify_btn = ttk.Button(verify_btn_container, text="🔍 Verify Files",
                                    command=self.verify_files,
                                    style='Primary.TButton')
        self.verify_btn.pack(side=tk.LEFT, padx=5)
        
        self.verify_stop_btn = ttk.Button(verify_btn_container, text="⏹️ Stop",
                                         command=self.stop_operation,
                                         style='Error.TButton', state=tk.DISABLED)
        self.verify_stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_report_btn = ttk.Button(verify_btn_container, text="📄 Save Report",
                                         command=self.save_verification_report,
                                         style='Success.TButton', state=tk.DISABLED)
        self.save_report_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress
        verify_progress_frame = ttk.Frame(scrollable_frame, style='Card.TFrame', padding=20)
        verify_progress_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.verify_progress_var = tk.StringVar(value="Ready to verify files")
        verify_progress_label = tk.Label(verify_progress_frame, textvariable=self.verify_progress_var,
                                        bg='white', font=('Segoe UI', 10), fg=self.colors['text'])
        verify_progress_label.pack(anchor=tk.W, pady=(0, 10))
        
        self.verify_progress_bar = ttk.Progressbar(verify_progress_frame, length=400, mode='determinate',
                                                  style='Modern.Horizontal.TProgressbar')
        self.verify_progress_bar.pack(fill=tk.X)
        
        # Results
        verify_results_frame = ttk.LabelFrame(scrollable_frame, text="🔍 Verification Results", 
                                            padding=20, style='Modern.TLabelframe')
        verify_results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.verify_results_text = scrolledtext.ScrolledText(verify_results_frame, height=12, 
                                                           wrap=tk.WORD, font=('Consolas', 9),
                                                           bg='#F8F8F8')
        self.verify_results_text.pack(fill=tk.BOTH, expand=True)
        
        # Store verification results
        self.verification_results = {}
        self.corrupted_files = []
        self.verification_errors = []
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def browse_file(self):
        """Browse for a single file."""
        filename = filedialog.askopenfilename(
            title="Select File to Hash",
            filetypes=[("All Files", "*.*")]
        )
        if filename:
            self.location_var.set(filename)
            self.update_status(f"Selected file: {os.path.basename(filename)}")
    
    def browse_folder(self):
        """Browse for a folder."""
        foldername = filedialog.askdirectory(title="Select Folder to Scan")
        if foldername:
            self.location_var.set(foldername)
            self.update_status(f"Selected folder: {os.path.basename(foldername)}")
    
    def browse_hash_file(self):
        """Browse for hash file."""
        filename = filedialog.askopenfilename(
            title="Select Hash File",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filename:
            self.hash_file_var.set(filename)
            self.update_status(f"Selected hash file: {os.path.basename(filename)}")
    
    def browse_base_path(self):
        """Browse for base path."""
        foldername = filedialog.askdirectory(title="Select Base Path")
        if foldername:
            self.base_path_var.set(foldername)
            self.update_status(f"Selected base path: {os.path.basename(foldername)}")
    
    def update_status(self, message):
        """Update status bar."""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def update_progress(self, current, total, current_file):
        """Update progress bar and status."""
        progress = (current / total) * 100 if total > 0 else 0
        self.progress_bar['value'] = progress
        filename = os.path.basename(current_file)
        self.progress_var.set(f"Processing: {filename} ({current}/{total})")
        self.update_status(f"Generating hashes... {current}/{total} files processed")
        self.root.update_idletasks()
    
    def update_verify_progress(self, current, total, current_file):
        """Update verification progress bar and status."""
        progress = (current / total) * 100 if total > 0 else 0
        self.verify_progress_bar['value'] = progress
        filename = os.path.basename(current_file)
        self.verify_progress_var.set(f"Verifying: {filename} ({current}/{total})")
        self.update_status(f"Verifying files... {current}/{total} files checked")
        self.root.update_idletasks()
    
    def generate_hashes(self):
        """Generate hashes for selected location."""
        location = self.location_var.get().strip()
        if not location or not os.path.exists(location):
            messagebox.showerror("❌ Error", "Please select a valid file or folder.")
            return
        
        algorithm = self.algorithm_var.get()
        max_workers = int(self.threads_var.get())
        
        # Disable controls
        self.generate_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.DISABLED)
        
        # Clear results
        self.results_text.delete(1.0, tk.END)
        self.progress_bar['value'] = 0
        
        # Reset stop event
        self.hash_generator.reset_stop_event()
        
        def hash_thread():
            try:
                self.progress_var.set("Initializing hash generation...")
                self.update_status("Starting hash generation...")
                self.root.update_idletasks()
                
                # Generate hashes
                self.hash_results, self.error_files = self.hash_generator.scan_location(
                    location, algorithm, self.update_progress, max_workers
                )
                
                # Auto-save if enabled
                if self.autosave_var.get() and (self.hash_results or self.error_files):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    auto_filename = f"hash_results_{timestamp}.json"
                    self.hash_generator.save_hashes(
                        self.hash_results, self.error_files, auto_filename, 
                        algorithm, location
                    )
                    self.root.after(0, lambda: self.update_status(f"Results auto-saved to {auto_filename}"))
                
                # Display results
                self.root.after(0, self.display_hash_results)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("❌ Error", f"Hash generation failed: {str(e)}"))
            finally:
                self.root.after(0, self.hash_generation_complete)
        
        # Start thread
        self.current_operation = threading.Thread(target=hash_thread)
        self.current_operation.start()
    
    def display_hash_results(self):
        """Display hash generation results with better formatting."""
        self.results_text.delete(1.0, tk.END)
        
        if not self.hash_results and not self.error_files:
            self.results_text.insert(tk.END, "❌ No files processed or operation was cancelled.\n")
            return
        
        # Header
        self.results_text.insert(tk.END, "=" * 80 + "\n")
        self.results_text.insert(tk.END, f"📊 HASH GENERATION RESULTS\n")
        self.results_text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Summary
        self.results_text.insert(tk.END, f"🔧 Algorithm: {self.algorithm_var.get()}\n")
        self.results_text.insert(tk.END, f"📁 Location: {self.location_var.get()}\n")
        self.results_text.insert(tk.END, f"✅ Files processed: {len(self.hash_results)}\n")
        self.results_text.insert(tk.END, f"❌ Files with errors: {len(self.error_files)}\n")
        self.results_text.insert(tk.END, f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Successful hashes
        if self.hash_results:
            self.results_text.insert(tk.END, f"✅ SUCCESSFUL HASHES ({len(self.hash_results)} files)\n")
            self.results_text.insert(tk.END, "-" * 50 + "\n")
            
            for i, (file_path, hash_value) in enumerate(self.hash_results.items(), 1):
                filename = os.path.basename(file_path)
                self.results_text.insert(tk.END, f"{i:3d}. {filename}\n")
                self.results_text.insert(tk.END, f"     Path: {file_path}\n")
                self.results_text.insert(tk.END, f"     Hash: {hash_value}\n\n")
        
        # Error files
        if self.error_files:
            self.results_text.insert(tk.END, f"❌ FILES WITH ERRORS ({len(self.error_files)} files)\n")
            self.results_text.insert(tk.END, "-" * 50 + "\n")
            
            for i, error in enumerate(self.error_files, 1):
                self.results_text.insert(tk.END, f"{i:3d}. {error}\n")
        
        self.results_text.see(1.0)
        self.save_btn.config(state=tk.NORMAL)
    
    def hash_generation_complete(self):
        """Re-enable controls after hash generation."""
        self.generate_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_var.set("Hash generation complete")
        self.update_status("Ready")
        self.current_operation = None
    
    def save_results(self):
        """Save hash results to file."""
        if not self.hash_results and not self.error_files:
            messagebox.showwarning("⚠️ Warning", "No results to save.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"hash_results_{timestamp}.json"
        
        filename = filedialog.asksaveasfilename(
            title="Save Hash Results",
            defaultextension=".json",
            initialvalue=default_name,
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if filename:
            if self.hash_generator.save_hashes(
                self.hash_results, self.error_files, filename, 
                self.algorithm_var.get(), self.location_var.get()
            ):
                messagebox.showinfo("✅ Success", f"Hash results saved to:\n{filename}")
                if self.error_files:
                    error_file = filename.replace('.json', '_errors.txt')
                    messagebox.showinfo("📄 Additional File", f"Error report saved to:\n{error_file}")
                self.update_status(f"Results saved to {os.path.basename(filename)}")
            else:
                messagebox.showerror("❌ Error", "Failed to save hash results.")
    
    def verify_files(self):
        """Verify files against saved hashes."""
        hash_file = self.hash_file_var.get().strip()
        if not hash_file or not os.path.exists(hash_file):
            messagebox.showerror("❌ Error", "Please select a valid hash file.")
            return
        
        base_path = self.base_path_var.get().strip() or None
        
        # Disable controls
        self.verify_btn.config(state=tk.DISABLED)
        self.verify_stop_btn.config(state=tk.NORMAL)
        self.save_report_btn.config(state=tk.DISABLED)
        
        # Clear results
        self.verify_results_text.delete(1.0, tk.END)
        self.verify_progress_bar['value'] = 0
        
        # Reset stop event
        self.hash_generator.reset_stop_event()
        
        def verify_thread():
            try:
                self.verify_progress_var.set("Initializing verification...")
                self.update_status("Starting file verification...")
                self.root.update_idletasks()
                
                # Verify files
                self.verification_results, self.corrupted_files, self.verification_errors = \
                    self.hash_generator.verify_integrity(hash_file, base_path, self.update_verify_progress)
                
                # Auto-save report if enabled
                if self.auto_save_report_var.get() and self.verification_results:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    auto_filename = f"verification_report_{timestamp}.json"
                    self.hash_generator.save_verification_report(
                        self.verification_results, self.corrupted_files,
                        self.verification_errors, auto_filename, hash_file
                    )
                    self.root.after(0, lambda: self.update_status(f"Report auto-saved to {auto_filename}"))
                
                # Display results
                self.root.after(0, self.display_verify_results)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("❌ Error", f"Verification failed: {str(e)}"))
            finally:
                self.root.after(0, self.verification_complete)
        
        # Start thread
        self.current_operation = threading.Thread(target=verify_thread)
        self.current_operation.start()
    
    def display_verify_results(self):
        """Display verification results with enhanced formatting."""
        self.verify_results_text.delete(1.0, tk.END)
        
        if not self.verification_results:
            self.verify_results_text.insert(tk.END, "❌ No files verified or operation was cancelled.\n")
            return
        
        # Count results by status
        status_counts = {'MATCH': 0, 'MISMATCH': 0, 'FILE_NOT_FOUND': 0, 'READ_ERROR': 0, 'VERIFICATION_ERROR': 0}
        for status in self.verification_results.values():
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Header
        self.verify_results_text.insert(tk.END, "=" * 80 + "\n")
        self.verify_results_text.insert(tk.END, f"🔍 FILE VERIFICATION RESULTS\n")
        self.verify_results_text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Summary
        self.verify_results_text.insert(tk.END, f"📋 Hash file: {os.path.basename(self.hash_file_var.get())}\n")
        self.verify_results_text.insert(tk.END, f"📁 Base path: {self.base_path_var.get() or 'Not specified'}\n")
        self.verify_results_text.insert(tk.END, f"📊 Total files checked: {len(self.verification_results)}\n")
        self.verify_results_text.insert(tk.END, f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Status summary
        self.verify_results_text.insert(tk.END, "📈 SUMMARY\n")
        self.verify_results_text.insert(tk.END, "-" * 30 + "\n")
        self.verify_results_text.insert(tk.END, f"✅ Matches:           {status_counts['MATCH']:4d}\n")
        self.verify_results_text.insert(tk.END, f"❌ Mismatches:        {status_counts['MISMATCH']:4d}\n")
        self.verify_results_text.insert(tk.END, f"❓ Not found:         {status_counts['FILE_NOT_FOUND']:4d}\n")
        self.verify_results_text.insert(tk.END, f"⚠️  Read errors:       {status_counts['READ_ERROR']:4d}\n")
        self.verify_results_text.insert(tk.END, f"🚫 Verification errors: {status_counts['VERIFICATION_ERROR']:4d}\n\n")
        
        # Corrupted files (detailed)
        if self.corrupted_files:
            self.verify_results_text.insert(tk.END, f"🔥 CORRUPTED FILES ({len(self.corrupted_files)} files)\n")
            self.verify_results_text.insert(tk.END, "=" * 50 + "\n")
            
            for i, file_info in enumerate(self.corrupted_files, 1):
                filename = os.path.basename(file_info['path'])
                self.verify_results_text.insert(tk.END, f"{i:3d}. ❌ {filename}\n")
                self.verify_results_text.insert(tk.END, f"     Path: {file_info['path']}\n")
                self.verify_results_text.insert(tk.END, f"     Expected: {file_info['stored_hash']}\n")
                self.verify_results_text.insert(tk.END, f"     Actual:   {file_info['current_hash']}\n\n")
        
        # All results (grouped by status)
        self.verify_results_text.insert(tk.END, f"📋 DETAILED RESULTS\n")
        self.verify_results_text.insert(tk.END, "-" * 30 + "\n")
        
        # Group files by status
        grouped = {}
        for file_path, status in self.verification_results.items():
            if status not in grouped:
                grouped[status] = []
            grouped[status].append(file_path)
        
        status_symbols = {
            'MATCH': '✅',
            'MISMATCH': '❌',
            'FILE_NOT_FOUND': '❓',
            'READ_ERROR': '⚠️',
            'VERIFICATION_ERROR': '🚫'
        }
        
        for status, files in grouped.items():
            if files:
                symbol = status_symbols.get(status, '?')
                self.verify_results_text.insert(tk.END, f"\n{symbol} {status} ({len(files)} files):\n")
                for file_path in files:
                    filename = os.path.basename(file_path)
                    self.verify_results_text.insert(tk.END, f"  • {filename}\n")
        
        self.verify_results_text.see(1.0)
        self.save_report_btn.config(state=tk.NORMAL)
        
        # Show corruption alert
        if self.corrupted_files:
            messagebox.showwarning(
                "⚠️ Files Corrupted", 
                f"{len(self.corrupted_files)} corrupted files detected!\n"
                "Check the results for details."
            )
    
    def verification_complete(self):
        """Re-enable controls after verification."""
        self.verify_btn.config(state=tk.NORMAL)
        self.verify_stop_btn.config(state=tk.DISABLED)
        self.verify_progress_var.set("Verification complete")
        self.update_status("Ready")
        self.current_operation = None
    
    def save_verification_report(self):
        """Save verification report to file."""
        if not self.verification_results:
            messagebox.showwarning("⚠️ Warning", "No verification results to save.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"verification_report_{timestamp}.json"
        
        filename = filedialog.asksaveasfilename(
            title="Save Verification Report",
            defaultextension=".json",
            initialvalue=default_name,
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if filename:
            if self.hash_generator.save_verification_report(
                self.verification_results, self.corrupted_files,
                self.verification_errors, filename, self.hash_file_var.get()
            ):
                messagebox.showinfo("✅ Success", f"Verification report saved to:\n{filename}")
                if self.corrupted_files:
                    corrupted_file = filename.replace('.json', '_corrupted.txt')
                    messagebox.showinfo("📄 Additional File", f"Corrupted files list saved to:\n{corrupted_file}")
                self.update_status(f"Report saved to {os.path.basename(filename)}")
            else:
                messagebox.showerror("❌ Error", "Failed to save verification report.")
    
    def stop_operation(self):
        """Stop current operation."""
        self.hash_generator.stop_operation()
        self.progress_var.set("Stopping operation...")
        self.verify_progress_var.set("Stopping operation...")
        self.update_status("Stopping operation...")


def main():
    """Main application entry point."""
    root = tk.Tk()
    
    # Set application icon (if available)
    try:
        # For Windows
        root.iconbitmap(default='icon.ico')
    except:
        pass
    
    app = ModernHashGeneratorGUI(root)
    
    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # Handle close event
    def on_closing():
        if app.current_operation and app.current_operation.is_alive():
            if messagebox.askokcancel("❓ Quit", "An operation is running. Stop and quit?"):
                app.hash_generator.stop_operation()
                # Give some time for threads to stop
                root.after(1000, root.destroy)
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Bind mouse wheel to canvas scrolling
    def bind_mousewheel(event):
        def _on_mousewheel(event):
            if hasattr(event.widget, 'yview_scroll'):
                event.widget.yview_scroll(int(-1*(event.delta/120)), "units")
        root.bind_all("<MouseWheel>", _on_mousewheel)
    
    root.bind('<Enter>', bind_mousewheel)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        root.destroy()


if __name__ == "__main__":
    main()