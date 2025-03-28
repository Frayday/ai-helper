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

# --- Configuration ---
# IMPORTANT: Replace with your actual Google API endpoint base, model, and NEW key

# Base URL for the Google Generative Language API (Check Google AI documentation)
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=AIzaSyC-fEpW4ldOtEL7U1-3v_vJnva8qCnHjTY" # Base URL, model name added below

# Model name (Ensure this model supports vision input and is available to you)
MODEL_NAME = "gemini-pro-vision" # Common choice. Or "gemini-1.5-flash" etc.

# !!! IMPORTANT SECURITY WARNING !!!
# Paste your NEW, SECRET Google API Key here.
# DO NOT commit this key to public Git repositories or share it publicly.
# If you accidentally expose it, revoke it immediately in Google Cloud Console.
#API_KEY = "AIzaSy_YOUR_NEW_SECRET_GOOGLE_API_KEY_HERE"

# --- Sanity Checks ---
#if "YOUR_" in API_KEY or API_KEY == "AIzaSy_YOUR_NEW_SECRET_GOOGLE_API_KEY_HERE":
 #   print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
  #  print("!!! WARNING: API_KEY is still a placeholder or example.   !!!")
   # print("!!! Please replace it with your actual Google API key.    !!!")
    #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    # sys.exit("Exiting: API key not configured.") # Optional: force exit
#if not API_ENDPOINT.startswith("https://"):
 #    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
  #   print("!!! WARNING: API_ENDPOINT looks invalid. Check the URL.   !!!")
   #  print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

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
    global API_ENDPOINT, MODEL_NAME # API_KEY # Access global config

    print("Encoding image for Google API...")
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        # --- Google Generative Language API Specific Section ---

        # 1. Construct the Full URL (Model + Action + API Key)
        action = ":generateContent"
        full_api_url = f"{API_ENDPOINT}"
        print(f"Sending request to Google API (model: {MODEL_NAME})...")

        # 2. Set Headers (Simple for key-in-URL authentication)
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
               "maxOutputTokens": 500,
               "temperature": 0.4,
           }
        }

        # 4. Make the API Call
        response = requests.post(full_api_url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()

        print("Google API Response Received.")
        api_result = response.json()

        # 5. Parse the Response (Gemini 'candidates' structure)
        try:
            text_response = api_result['candidates'][0]['content']['parts'][0]['text']
            print("Successfully parsed API response.")
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            print(f"Error parsing Google API response: {e}")
            print(f"--- Full API Response (for debugging) ---\n{api_result}\n--- End Full API Response ---")
            text_response = f"{ERROR_PREFIX}Could not parse API response. Check logs."

        # --- End Google Specific Section ---

        return text_response.strip()

    except requests.exceptions.Timeout:
        print("API Request Error: Timeout")
        return f"{ERROR_PREFIX}Google API request timed out."
    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        if e.response is not None:
             print(f"Response status code: {e.response.status_code}")
             print(f"Response text: {e.response.text[:500]}...") # Limit long errors
             if e.response.status_code == 400:
                 return f"{ERROR_PREFIX}Bad request (400). Check API Key, Endpoint, Model, Payload.\nDetails: {e.response.text[:200]}"
             elif e.response.status_code == 403:
                 return f"{ERROR_PREFIX}Forbidden (403). API Key likely invalid/lacks permissions."
        return f"{ERROR_PREFIX}Could not reach Google API.\n{e}"
    except Exception as e:
        print(f"An unexpected error occurred during API interaction: {e}")
        traceback.print_exc()
        return f"{ERROR_PREFIX}Processing API request failed.\n{e}"

# --- UI Update Function ---
def update_overlay(text=""):
    """ Safely updates the text and visibility of the overlay window. """
    if not root or not label or not root.winfo_exists():
        return
    try:
        label.config(text=text)
        if text:
            lines = text.count('\n') + 1
            max_line_len = max(len(line) for line in text.split('\n')) if text else 10
            font_size = FONT_SETTINGS[1]
            w_pixels = int(max_line_len * (font_size * 0.7) + 20)
            h_pixels = int(lines * (font_size * 1.5) + 15)
            w_pixels = max(w_pixels, 100)
            h_pixels = max(h_pixels, 30)
            root.geometry(f"{w_pixels}x{h_pixels}{WINDOW_POSITION}")
            root.attributes('-alpha', TRANSPARENCY)
            root.deiconify()
        else:
            root.withdraw()
        root.update_idletasks()
    except Exception as e:
        print(f"Error updating overlay: {e}")
        try:
            label.config(text=f"Overlay Update Error:\n{e}")
            root.geometry(f"300x100{WINDOW_POSITION}")
            root.attributes('-alpha', TRANSPARENCY)
            root.deiconify()
            root.update_idletasks()
        except:
            print("!!! Critical overlay update failure !!!")

# --- Capture/Process Function ---
def capture_and_process():
    """ Triggered by hotkey: Captures screen, calls API, updates overlay. """
    global is_processing
    print(f"\n--- Hotkey '{HOTKEY_CAPTURE}' detected ---")
    if is_processing:
        print("Request already in progress. Ignoring.")
        return
    is_processing = True
    root.after(0, update_overlay, PROCESSING_TEXT)
    try:
        print("Capturing screen with Pillow (ImageGrab)...")
        screenshot = ImageGrab.grab(bbox=None)
        print(f"Screenshot captured (Size: {screenshot.size}).")

        img_bytes_io = io.BytesIO()
        screenshot.save(img_bytes_io, format='PNG')
        img_bytes = img_bytes_io.getvalue()
        print(f"Screenshot converted to {len(img_bytes)} bytes (PNG).")

        response_text = get_api_response(img_bytes)

        root.after(0, update_overlay, response_text)
    except ImportError:
         print("Error: Pillow (PIL) library not found or ImageGrab failed.")
         root.after(0, update_overlay, f"{ERROR_PREFIX}Pillow/ImageGrab not available.")
    except Exception as e:
        print(f"Error during capture or processing: {e}")
        traceback.print_exc()
        err_msg = f"{ERROR_PREFIX}{e}"
        if "scrot" in str(e).lower():
             err_msg = f"{ERROR_PREFIX}ImageGrab failed.\nIs 'scrot' installed? (sudo apt install scrot)"
        root.after(0, update_overlay, err_msg)
    finally:
        is_processing = False
        print("--- Processing finished ---")

# --- Window Setup Function ---
def setup_overlay_window():
    """ Creates and configures the transparent, borderless Tkinter window. """
    global root, label
    print("Setting up overlay window...")
    root = tk.Tk()
    root.withdraw()
    root.overrideredirect(True)
    root.geometry(WINDOW_POSITION)
    root.wm_attributes('-topmost', 1)
    root.attributes('-alpha', 0.0)
    label = tk.Label(root, text="", font=FONT_SETTINGS, fg=LABEL_FG, bg=LABEL_BG,
                     justify=tk.LEFT, anchor='nw', padx=10, pady=10, wraplength=600)
    label.pack(expand=True, fill="both")
    print("Overlay window configured.")
    return root

# --- Safe Quit Function ---
def safe_quit():
    """ Safely quits the Tkinter application and attempts cleanup. """
    global root
    print("\nInitiating shutdown...")
    try:
        print("Unhooking hotkeys...")
        keyboard.unhook_all()
    except Exception as e:
        print(f"Note: Minor error during hotkey unhooking: {e}")

    # Correctly indented try-except block for destroying the root window
    if root:
        try:
            print("Destroying Tkinter window...")
            root.quit()
            root.destroy()
            root = None
        except Exception as e:
            print(f"Error destroying Tkinter root: {e}")

    print("Shutdown complete.")


# --- Main Execution ---
if __name__ == "__main__":
    print("--- Starting Overlay App ---")

    # Check for root/sudo privileges
    try:
        effective_uid = os.geteuid()
        if effective_uid != 0:
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("!!! WARNING: Script not running as root (or via sudo).           !!!")
            print("!!! Global hotkeys ('keyboard' library) may not work correctly.  !!!")
            print(f"!!! Try running with: sudo {sys.executable} {__file__} !!!")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        else:
            print("Script running with root privileges (sudo detected).")
    except AttributeError:
         print("Warning: Could not check user privileges (os.geteuid not available).")
    except Exception as e:
         print(f"Warning: Error checking privileges: {e}")

    # Setup the GUI window
    root = setup_overlay_window()
    if not root:
        sys.exit("Failed to create Tkinter window. Exiting.")

    # Setup Hotkeys
    try:
        print(f"Registering capture hotkey: {HOTKEY_CAPTURE}")
        keyboard.add_hotkey(HOTKEY_CAPTURE, capture_and_process, trigger_on_release=False)
        print(f"Registering exit hotkey: {HOTKEY_EXIT}")
        keyboard.add_hotkey(HOTKEY_EXIT, safe_quit, trigger_on_release=False)
        print("Hotkeys registered successfully.")
    except Exception as e:
        # This is the block where the SyntaxError occurred and is now fixed
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"!!! FATAL ERROR: Failed to register hotkeys: {e}")
        print("!!! This often happens without root/sudo permissions.")
        print(f"!!! Try running with: sudo {sys.executable} {__file__}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        # --- CORRECTED CLEANUP ON HOTKEY FAILURE ---
        if root: # Check if root object exists before trying to destroy
            try: # Start a block for the destroy attempt
                root.destroy() # Attempt to destroy the window
            except: # Catch *any* error during destroy on fatal exit
                pass # Ignore the error and proceed to exit
        # --- END CORRECTION ---

        sys.exit("Exiting due to hotkey registration failure.")

    # Start the Tkinter event loop
    print(f"\nApp running. Press '{HOTKEY_CAPTURE}' to capture screen, '{HOTKEY_EXIT}' to quit.")
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nCtrl+C detected.")
        safe_quit()
    except Exception as e:
        print(f"\nUnhandled exception in main loop: {e}")
        traceback.print_exc()
        safe_quit()

    print("--- Overlay App Exited ---")
