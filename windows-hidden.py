#!/usr/bin/env python3 # Shebang for Linux execution

import tkinter as tk
from PIL import ImageGrab # Using Pillow for screenshots
import requests
import base64
import io
import keyboard # For global hotkeys
import sys
import os
import threading
import traceback # For printing detailed errors

# --- Platform Specific Imports ---
# Import ctypes only if on Windows for screen capture protection
if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes
        print("Imported ctypes for Windows screen capture protection.")
    except ImportError:
        print("WARNING: ctypes module not found. Cannot apply screen capture protection on Windows.")
        ctypes = None # Ensure ctypes is None if import fails
else:
    ctypes = None # ctypes is not needed on other platforms
    print("Not on Windows. Screen capture protection via SetWindowDisplayAffinity is skipped.")


# --- Configuration ---
# IMPORTANT: Replace with your actual Google API endpoint base, model, and NEW key

# Base URL for the Google Generative Language API (Check Google AI documentation)
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key=YOUR_API_KEY_HERE" # Add your key

# Model name (Ensure this model supports vision input and is available to you)
# MODEL_NAME = "gemini-pro-vision" # Model seems included in endpoint now

# !!! IMPORTANT SECURITY WARNING !!!
# Paste your NEW, SECRET Google API Key in the API_ENDPOINT above.
# DO NOT commit this key to public Git repositories or share it publicly.
# If you accidentally expose it, revoke it immediately in Google Cloud Console.
#API_KEY = "YOUR_API_KEY_HERE" # Now included in endpoint URL

# --- Sanity Checks ---
if "YOUR_API_KEY_HERE" in API_ENDPOINT:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! WARNING: API Key placeholder detected in API_ENDPOINT.  !!!")
    print("!!! Please replace it with your actual Google API key.    !!!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    # sys.exit("Exiting: API key not configured.") # Optional: force exit
if not API_ENDPOINT.startswith("https://"):
     print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
     print("!!! WARNING: API_ENDPOINT looks invalid. Check the URL.   !!!")
     print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

# --- UI and Hotkey Settings ---
HOTKEY_CAPTURE = 'ctrl+alt+s'   # Hotkey to trigger screenshot and query
HOTKEY_EXIT = 'ctrl+alt+x'      # Hotkey to close the application
TRANSPARENCY = 0.8              # Overlay transparency (0.0=invisible, 1.0=opaque)
WINDOW_POSITION = "+10+10"      # Initial position (e.g., "+10+10" for top-left)
FONT_SETTINGS = ("Arial", 12)   # Font: (Family, Size)
LABEL_BG = "#222222"            # Dark background for the text area
LABEL_FG = "#E0E0E0"            # Light grey text color for readability
PROCESSING_TEXT = "Processing..."
ERROR_PREFIX = "Error: "

# --- Global Variables ---
root = None           # The main Tkinter window
label = None          # The label widget displaying text
is_processing = False # Lock to prevent multiple simultaneous requests


# --- Core Functions ---

def get_api_response(image_bytes):
    """
    Encodes image, sends it to the Google Generative Language API (Gemini),
    and returns the response text.
    """
    global API_ENDPOINT # Access global config

    print("Encoding image for Google API...")
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        # --- Google Generative Language API Specific Section ---

        # 1. Construct the Full URL (Already includes model, action, and key)
        full_api_url = API_ENDPOINT
        print(f"Sending request to Google API...")

        # 2. Set Headers
        headers = {
            "Content-Type": "application/json"
        }

        # 3. Create Payload (Gemini format for multimodal input)
        payload = {
           "contents": [{
               "parts": [
                   {"text": "Analyze this screenshot and provide a solution to leet code."},
                   {"inline_data": {
                       "mime_type": "image/png",
                       "data": base64_image
                   }}
               ]
           }],
           "generationConfig": {
               "maxOutputTokens": 8192, # Increased token limit if needed
               "temperature": 0.4,
               # "topP": 1, # Default
               # "topK": 32 # Default
           }
           # Add safetySettings if needed
           # "safetySettings": [
           #    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
           #    ... other categories
           # ]
        }

        # 4. Make the API Call
        response = requests.post(full_api_url, headers=headers, json=payload, timeout=60) # Increased timeout
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        print("Google API Response Received.")
        api_result = response.json()

        # 5. Parse the Response (Handle potential errors/empty responses)
        try:
            # Check for 'candidates' first
            if 'candidates' in api_result and api_result['candidates']:
                candidate = api_result['candidates'][0]
                # Check for 'content' and 'parts'
                if 'content' in candidate and 'parts' in candidate['content'] and candidate['content']['parts']:
                    text_response = candidate['content']['parts'][0].get('text', '') # Use .get for safety
                    if text_response:
                        print("Successfully parsed API response text.")
                    else:
                        print("Warning: API response part contained no text.")
                        text_response = f"{ERROR_PREFIX}API returned empty content."
                else:
                     print("Error parsing Google API response: Missing 'content' or 'parts'.")
                     text_response = f"{ERROR_PREFIX}Unexpected API response structure (content/parts)."
            # Handle block reason if present
            elif 'promptFeedback' in api_result and 'blockReason' in api_result['promptFeedback']:
                 reason = api_result['promptFeedback']['blockReason']
                 print(f"API request blocked due to: {reason}")
                 text_response = f"{ERROR_PREFIX}Blocked by API ({reason})."
            else:
                print("Error parsing Google API response: Missing 'candidates' or unknown structure.")
                text_response = f"{ERROR_PREFIX}Could not parse API response (no candidates)."

        except (KeyError, IndexError, TypeError, AttributeError) as e:
            print(f"Error parsing Google API response JSON structure: {e}")
            text_response = f"{ERROR_PREFIX}Could not parse API response structure. Check logs."

        # --- Log Full API Response on Parsing Error for Debugging ---
        if ERROR_PREFIX in text_response:
            print(f"--- Full API Response (due to parsing error) ---\n{api_result}\n--- End Full API Response ---")
        # --- End Google Specific Section ---

        return text_response.strip()

    except requests.exceptions.Timeout:
        print("API Request Error: Timeout")
        return f"{ERROR_PREFIX}Google API request timed out."
    except requests.exceptions.HTTPError as e: # Catch HTTP errors specifically
        print(f"API Request HTTP Error: {e}")
        if e.response is not None:
             print(f"Response status code: {e.response.status_code}")
             print(f"Response text: {e.response.text[:500]}...") # Limit long errors
             if e.response.status_code == 400:
                 # More specific check for API key issues often in 400 errors
                 if "API key not valid" in e.response.text:
                      return f"{ERROR_PREFIX}API Key likely invalid (400)."
                 else:
                      return f"{ERROR_PREFIX}Bad request (400). Check Endpoint/Payload.\nDetails: {e.response.text[:200]}"
             elif e.response.status_code == 403:
                 return f"{ERROR_PREFIX}Forbidden (403). API Key may lack permissions/billing issues?"
             elif e.response.status_code == 429:
                 return f"{ERROR_PREFIX}Rate limit exceeded (429). Please wait and try again."
             else:
                  return f"{ERROR_PREFIX}HTTP Error {e.response.status_code}.\n{e.response.text[:200]}"
        else:
             return f"{ERROR_PREFIX}HTTP Error, no response body.\n{e}"
    except requests.exceptions.RequestException as e:
        print(f"API Request Error (Network/Connection): {e}")
        return f"{ERROR_PREFIX}Could not reach Google API.\nCheck network connection.\n{e}"
    except Exception as e:
        print(f"An unexpected error occurred during API interaction: {e}")
        traceback.print_exc()
        return f"{ERROR_PREFIX}Processing API request failed unexpectedly.\n{e}"

# --- UI Update Function ---
def update_overlay(text=""):
    """ Safely updates the text and visibility of the overlay window. """
    if not root or not label or not root.winfo_exists():
        return
    try:
        # Limit text length to prevent massive windows
        max_chars = 3000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... (truncated)"

        label.config(text=text)
        if text:
            # Basic geometry calculation (adjust as needed)
            lines = text.count('\n') + 1
            # Estimate width based on average char width, add padding
            max_line_len = max((len(line) for line in text.split('\n')), default=10)
            font_family, font_size = FONT_SETTINGS
            # Rough estimate: adjust 0.6 multiplier based on font
            w_pixels = int(max_line_len * (font_size * 0.65) + 30)
            # Estimate height based on line height, add padding
            h_pixels = int(lines * (font_size * 1.6) + 20)

            # Clamp to reasonable min/max dimensions
            w_pixels = max(150, min(w_pixels, 800)) # Min/Max width
            h_pixels = max(50, min(h_pixels, 600)) # Min/Max height

            root.geometry(f"{w_pixels}x{h_pixels}{WINDOW_POSITION}")
            root.attributes('-alpha', TRANSPARENCY)
            root.deiconify() # Make window visible
        else:
            root.withdraw() # Hide window if no text
        root.update_idletasks() # Force update
    except tk.TclError as e:
        # Handle cases where the window might be destroyed during update
        print(f"Tkinter TclError updating overlay (likely during shutdown): {e}")
    except Exception as e:
        print(f"Unexpected error updating overlay: {e}")
        traceback.print_exc()
        # Attempt to show an error message in the overlay itself
        try:
            label.config(text=f"Overlay Update Error:\n{e}")
            root.geometry(f"300x100{WINDOW_POSITION}") # Fixed size for error
            root.attributes('-alpha', TRANSPARENCY)
            root.deiconify()
            root.update_idletasks()
        except:
            print("!!! Critical overlay update failure after error !!!")


# --- Capture/Process Function ---
def capture_and_process():
    """ Triggered by hotkey: Captures screen, calls API, updates overlay. """
    global is_processing
    print(f"\n--- Hotkey '{HOTKEY_CAPTURE}' detected ---")
    if is_processing:
        print("Request already in progress. Ignoring.")
        return

    is_processing = True
    # Schedule the UI update using root.after to ensure it runs on the main thread
    root.after(0, update_overlay, PROCESSING_TEXT)

    # Run potentially blocking operations in a separate thread
    def processing_thread():
        nonlocal is_processing # Allow modification of the outer scope variable
        try:
            print("Capturing screen with Pillow (ImageGrab)...")
            screenshot = ImageGrab.grab(bbox=None, all_screens=True) # Capture all screens if needed
            print(f"Screenshot captured (Size: {screenshot.size}).")

            img_bytes_io = io.BytesIO()
            # Use PNG for lossless quality, consider JPEG for smaller size if quality allows
            screenshot.save(img_bytes_io, format='PNG')
            img_bytes = img_bytes_io.getvalue()
            print(f"Screenshot converted to {len(img_bytes)} bytes (PNG).")

            # Perform the network request
            response_text = get_api_response(img_bytes)

            # Schedule the final UI update back on the main thread
            root.after(0, update_overlay, response_text)

        except ImportError:
             print("Error: Pillow (PIL) library not found or ImageGrab failed.")
             root.after(0, update_overlay, f"{ERROR_PREFIX}Pillow/ImageGrab not available.")
        except Exception as e:
            print(f"Error during capture or processing thread: {e}")
            traceback.print_exc()
            err_msg = f"{ERROR_PREFIX}{e}"
            # Check common Linux error if ImageGrab fails without X server tools
            if "Xlib" in str(e) or "scrot" in str(e).lower() or "gnome-screenshot" in str(e).lower():
                 err_msg = (f"{ERROR_PREFIX}ImageGrab failed. Ensure screenshot tool is installed\n"
                           f"(e.g., 'sudo apt install scrot' or 'gnome-screenshot') and X11/Wayland allows it.")
            root.after(0, update_overlay, err_msg)
        finally:
            is_processing = False # Release the lock
            print("--- Processing thread finished ---")

    # Start the processing in a new thread
    thread = threading.Thread(target=processing_thread, daemon=True)
    thread.start()


# --- Window Setup Function ---
def setup_overlay_window():
    """ Creates and configures the transparent, borderless Tkinter window. """
    global root, label
    print("Setting up overlay window...")
    root = tk.Tk()
    root.withdraw() # Start hidden
    root.overrideredirect(True) # No window borders/title bar
    root.geometry(WINDOW_POSITION) # Initial position
    root.wm_attributes('-topmost', 1) # Keep on top
    # Set initial alpha to 0.0, update_overlay will set it correctly later
    root.attributes('-alpha', 0.0)

    # Add a frame for better background control if needed, but label directly is simpler
    label = tk.Label(root, text="", font=FONT_SETTINGS, fg=LABEL_FG, bg=LABEL_BG,
                     justify=tk.LEFT, anchor='nw', padx=10, pady=10,
                     wraplength=780) # Adjust wraplength based on max expected width
    label.pack(expand=True, fill="both")

    # --- Apply Windows Screen Capture Protection ---
    if sys.platform == "win32" and ctypes:
        print("Attempting to apply screen capture protection (Windows)...")
        try:
            # Constants for SetWindowDisplayAffinity
            WDA_NONE = 0 # Default, allows capture
            WDA_MONITOR = 1 # Prevents capture except on physical monitor

            # Get user32 library
            user32 = ctypes.windll.user32

            # Define SetWindowDisplayAffinity function prototype
            # BOOL SetWindowDisplayAffinity(HWND hWnd, DWORD dwAffinity);
            set_display_affinity = user32.SetWindowDisplayAffinity
            set_display_affinity.restype = wintypes.BOOL
            set_display_affinity.argtypes = [wintypes.HWND, wintypes.DWORD]

            # Get the window handle (HWND) from Tkinter window ID
            # Need to call update_idletasks to ensure the window exists before getting ID
            root.update_idletasks()
            hwnd = root.winfo_id()
            print(f"Obtained window handle (HWND): {hwnd}")

            # Apply the protection
            success = set_display_affinity(hwnd, WDA_MONITOR)

            if success:
                print("Successfully applied SetWindowDisplayAffinity(WDA_MONITOR). Window should resist capture.")
            else:
                # Get and print the last error if the call failed
                error_code = ctypes.GetLastError()
                print(f"WARNING: SetWindowDisplayAffinity failed. Error code: {error_code}")
                # You might want to look up common error codes (e.g., 5 = Access Denied)

        except AttributeError as e:
             print(f"AttributeError accessing ctypes/user32 (maybe running in restricted env?): {e}")
        except Exception as e:
            print(f"An unexpected error occurred applying screen capture protection: {e}")
            traceback.print_exc()
    # --- End Windows Protection ---

    print("Overlay window configured.")
    return root

# --- Safe Quit Function ---
def safe_quit():
    """ Safely quits the Tkinter application and attempts cleanup. """
    global root, is_processing
    print("\nInitiating shutdown...")
    is_processing = True # Prevent new captures during shutdown

    try:
        print("Unhooking hotkeys...")
        # Use remove_all_hotkeys() for cleaner removal if available and needed,
        # but unhook_all() is generally sufficient on exit.
        keyboard.unhook_all()
    except Exception as e:
        print(f"Note: Minor error during hotkey unhooking: {e}")

    if root:
        try:
            print("Destroying Tkinter window...")
            # Using destroy directly is usually sufficient for cleanup
            root.destroy()
            root = None # Clear the global reference
        except tk.TclError as e:
             # This can happen if the window is already gone
             print(f"Note: TclError destroying Tkinter root (likely already destroyed): {e}")
        except Exception as e:
            print(f"Error destroying Tkinter root: {e}")

    print("Shutdown complete.")
    # Force exit if threads might be lingering (though daemon threads should exit)
    # os._exit(0) # Use cautiously, skips normal Python exit handlers


# --- Main Execution ---
if __name__ == "__main__":
    print("--- Starting Overlay App ---")

    # Check for root/sudo privileges (especially needed for 'keyboard' library)
    try:
        # Use os.getuid() on Unix-like systems
        if hasattr(os, 'getuid'):
            effective_uid = os.getuid()
            if effective_uid != 0:
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("!!! WARNING: Script not running as root (or via sudo).           !!!")
                print("!!! Global hotkeys ('keyboard' library) may not work correctly.  !!!")
                print(f"!!! Try running with: sudo {sys.executable} {os.path.abspath(__file__)} !!!")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            else:
                print("Script running with root privileges (sudo detected).")
        # Basic check for admin privileges on Windows (less reliable)
        elif sys.platform == "win32" and ctypes:
             is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
             if not is_admin:
                  print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                  print("!!! WARNING: Script not running as Administrator on Windows.     !!!")
                  print("!!! Global hotkeys ('keyboard' library) may not work correctly.  !!!")
                  print("!!! Try running by right-clicking and 'Run as administrator'.    !!!")
                  print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
             else:
                  print("Script running with Administrator privileges (Windows detected).")
        else:
             print("Could not reliably determine privileges for this OS.")

    except Exception as e:
         print(f"Warning: Error checking privileges: {e}")

    # Setup the GUI window
    root = setup_overlay_window()
    if not root:
        sys.exit("Failed to create Tkinter window. Exiting.")

    # Setup Hotkeys
    try:
        print(f"Registering capture hotkey: {HOTKEY_CAPTURE}")
        # trigger_on_release=False ensures it fires when pressed down
        keyboard.add_hotkey(HOTKEY_CAPTURE, capture_and_process, trigger_on_release=False)

        print(f"Registering exit hotkey: {HOTKEY_EXIT}")
        keyboard.add_hotkey(HOTKEY_EXIT, safe_quit, trigger_on_release=False)
        print("Hotkeys registered successfully.")
    except Exception as e:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"!!! FATAL ERROR: Failed to register hotkeys: {e}")
        print("!!! This often happens without root/sudo/admin permissions.")
        if sys.platform != "win32":
            print(f"!!! Try running with: sudo {sys.executable} {os.path.abspath(__file__)}")
        else:
             print("!!! Try running by right-clicking and 'Run as administrator'.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        safe_quit() # Attempt cleanup before exiting
        sys.exit("Exiting due to hotkey registration failure.")

    # Start the Tkinter event loop
    print(f"\nApp running. Press '{HOTKEY_CAPTURE}' to capture screen, '{HOTKEY_EXIT}' to quit.")
    try:
        # Check if root window still exists before starting mainloop
        if root and root.winfo_exists():
            root.mainloop()
        else:
             print("Root window was destroyed before mainloop started. Exiting.")
    except KeyboardInterrupt:
        print("\nCtrl+C detected.")
        safe_quit()
    except Exception as e:
        print(f"\nUnhandled exception in main loop: {e}")
        traceback.print_exc()
        safe_quit() # Attempt cleanup

    print("--- Overlay App Exited ---")
