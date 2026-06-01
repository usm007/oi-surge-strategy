import os
import sys
import webbrowser
import shutil
from generate_signal import main as run_signal_generation

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def main():
    print("=" * 48)
    print("  OI SURGE — Local Desktop Launcher")
    print("=" * 48)
    
    # 1. Ensure local docs folder and index.html exist
    cwd = os.getcwd()
    local_docs_dir = os.path.join(cwd, "docs")
    if not os.path.exists(local_docs_dir):
        os.makedirs(local_docs_dir)
        
    local_html_path = os.path.join(local_docs_dir, "index.html")
    
    if not os.path.exists(local_html_path):
        bundled_html = resource_path(os.path.join("docs", "index.html"))
        if os.path.exists(bundled_html):
            shutil.copy(bundled_html, local_html_path)
            print("  [+] Initialized local dashboard HTML.")
        else:
            print("  [!] Error: Bundled index.html not found.")
            print("  Press Enter to exit...")
            input()
            sys.exit(1)

    print("  1. Fetching live NSE data...")
    # Run the generator logic to write docs/signal.js in the current directory!
    try:
        run_signal_generation()
        print("\n  [+] Dashboard signal data successfully updated!")
    except Exception as e:
        print(f"\n  [!] Error generating signal: {e}")
        print("  Press Enter to exit...")
        input()
        sys.exit(1)
        
    print(f"  2. Launching dashboard in your default browser...")
    webbrowser.open("file://" + os.path.abspath(local_html_path))
    
    print("\n  Dashboard opened successfully!")
    print("  You can now close this window.")
    print("  Press Enter to exit...")
    input()

if __name__ == "__main__":
    main()
