#!/usr/bin/env python3

import sys
import os
import threading
import traceback
import io
import base64
import requests

from PIL import ImageGrab # Using Pillow for screenshots
import keyboard          # For global hotkeys

# --- PyQt5 Imports ---
try:
    from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget, QVBoxLayout, QWidget
    from PyQt5.QtCore import Qt, pyqtSignal, QObject, QMetaObject, QThread, QSize, Q_ARG
    from PyQt5.QtGui import QKeyEvent, QScreen
    HAS_PYQT5 = True
except ImportError as e:
    print("="*60)
    print(f"!!! PyQt5 IMPORT ERROR: {e} !!!")
    print("PyQt5 is required.")
    print("Install PyQt5: pip install PyQt5")
    print("="*60)
    HAS_PYQT5 = False
    sys.exit(1) # Exit if PyQt5 is missing

# --- OpenGL Imports ---
try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *
    HAS_OPENGL = True
except ImportError as e:
    print("="*60)
    print(f"!!! OpenGL IMPORT ERROR: {e} !!!")
    print("PyOpenGL, PyOpenGL-accelerate, and system GLUT libraries are required for text rendering.")
    print("Install PyOpenGL: pip install PyOpenGL PyOpenGL-accelerate")
    print("Install GLUT (Debian/Ubuntu): sudo apt install freeglut3-dev")
    # ... (other OS instructions)
    print("="*60)
    HAS_OPENGL = False
    # Allow running without OpenGL text rendering? Probably not useful.
    if HAS_PYQT5: QApplication.quit() # Quit if GL is missing but Qt is there
    sys.exit(1)


# Initialize GLUT early for text rendering (if available)
if HAS_OPENGL and 'glutInit' in globals():
     try:
        if not bool(glutGet(GLUT_INIT_STATE)):
             glutInit(sys.argv)
             print("GLUT initialized for text rendering.")
        else:
             print("GLUT already initialized.")
     except Exception as e_glut:
         print(f"Warning: Error during glutInit: {e_glut}")
         # Proceeding, but text rendering might fail.

# --- Configuration ---
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=AIzaSyC-fEpW4ldOtEL7U1-3v_vJnva8qCnHjTY" # Replace with your actual endpoint/key setup
MODEL_NAME = "gemini-pro-vision"
# API_KEY = "YOUR_API_KEY_HERE" # Include if needed by your endpoint setup

# --- UI and Hotkey Settings ---
HOTKEY_CAPTURE = 'ctrl+alt+s'
HOTKEY_EXIT = 'ctrl+alt+x'
OPACITY = 0.85                  # Window opacity (0.0 to 1.0)
INITIAL_POSITION = (50, 50)     # Initial (x, y)
MOVE_STEP = 20                  # Pixels to move window per arrow key press
PROCESSING_TEXT = "Processing..."
ERROR_PREFIX = "Error: "

# --- OpenGL Text Settings ---
OPENGL_FONT = GLUT_BITMAP_9_BY_15
OPENGL_FONT_HEIGHT = 15
OPENGL_FONT_WIDTH = 9
# Use RGBA for glClearColor - Alpha needs to be 0 for transparency to work with WA_TranslucentBackground
OPENGL_BG_COLOR = (0.1, 0.1, 0.1, 0.0) # Almost black, fully transparent
OPENGL_TEXT_COLOR = (1.0, 1.0, 1.0) # White
OPENGL_PADDING = 10
MAX_WINDOW_WIDTH = 900
MAX_WINDOW_HEIGHT = 700
MIN_WINDOW_WIDTH = 150
MIN_WINDOW_HEIGHT = 50

# --- Global Variables ---
app = None                  # The QApplication instance
main_window = None          # The MainWindow instance
is_processing = False       # Lock for API calls
current_display_text = ""   # Text currently shown in the overlay

# --- API Function (Keep As Is - Ensure Authentication is Correct) ---
def get_api_response(image_bytes):
    """
    Encodes image, sends it to the Google Generative Language API (Gemini),
    and returns the response text. (Ensure API_ENDPOINT/KEY are correct)
    """
    global API_ENDPOINT #, MODEL_NAME #, API_KEY

    # Ensure full_api_url and headers/params are correct for your auth
    full_api_url = f"{API_ENDPOINT}" # Adjust if needed
    print(f"Sending request to {MODEL_NAME}...")

    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        headers = { "Content-Type": "application/json" }
        # Add API Key handling here if needed (Header or URL param)
        # e.g., headers["x-goog-api-key"] = API_KEY
        # e.g., params={'key': API_KEY} in requests.post

        payload = {
           "contents": [{"parts": [
               {"text": "Analyze this screenshot and provide a solution to the potential LeetCode problem shown. If it's not a LeetCode problem, describe the content."},
               {"inline_data": {"mime_type": "image/png", "data": base64_image}}
           ]}],
           "generationConfig": {"maxOutputTokens": 800, "temperature": 0.4}
        }

        response = requests.post(full_api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        api_result = response.json()
        print("API Response Received.")

        # Safely extract text (including handling content filtering)
        try:
            # ... (Keep the improved parsing logic from the previous Tkinter version) ...
            candidates = api_result.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                text_response = parts[0].get('text', f"{ERROR_PREFIX}No text in part.") if parts else f"{ERROR_PREFIX}No parts in content."
            elif 'promptFeedback' in api_result:
                 feedback = api_result['promptFeedback']
                 reason = feedback.get('blockReason', 'Unknown')
                 ratings = feedback.get('safetyRatings', [])
                 details = ", ".join([f"{r.get('category','?').split('_')[-1]}: {r.get('probability','?')}" for r in ratings])
                 text_response = f"{ERROR_PREFIX}Content blocked. Reason: {reason}. Details: {details}"
            else:
                 text_response = f"{ERROR_PREFIX}No candidates/feedback in response."
                 print(f"--- Full API Response ---\n{api_result}\n---")
        except Exception as e_parse:
             print(f"Error parsing API response structure: {e_parse}")
             text_response = f"{ERROR_PREFIX}Could not parse API response structure."

        return text_response.strip()

    # ... (Keep existing requests error handling) ...
    except requests.exceptions.Timeout: return f"{ERROR_PREFIX}API request timed out."
    except requests.exceptions.RequestException as e:
        details = f" (Status: {e.response.status_code})" if e.response else ""
        print(f"API Request Error: {e}{details}")
        # Specific handling...
        return f"{ERROR_PREFIX}Could not reach API{details}.\n{e}"
    except Exception as e:
        print(f"Unexpected API error: {e}")
        traceback.print_exc()
        return f"{ERROR_PREFIX}Processing API request failed.\n{e}"


# --- OpenGL Widget ---
class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""

    def setText(self, text):
        """Sets the text to be rendered."""
        if self._text != text:
            self._text = text
            self.update() # Trigger repaint

    def initializeGL(self):
        """Called once when the widget is initialized."""
        if not HAS_OPENGL: return
        try:
            # Set clear color RGBA (Alpha=0 for transparency)
            glClearColor(*OPENGL_BG_COLOR)
            # Enable blending for transparency
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            # Optional: Enable depth test if needed (usually not for 2D text)
            # glEnable(GL_DEPTH_TEST)
            print("GLWidget initialized.")
        except Exception as e:
            print(f"Error in initializeGL: {e}")

    def resizeGL(self, width, height):
        """Called when the widget is resized."""
        if not HAS_OPENGL: return
        try:
            if height == 0: height = 1
            glViewport(0, 0, width, height)
            # Set up ortho projection here is fine
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluOrtho2D(0, width, 0, height)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            # print(f"GLWidget resized to: {width}x{height}")
        except Exception as e:
            print(f"Error in resizeGL: {e}")

    def paintGL(self):
        """Called whenever the widget needs to be painted."""
        global current_display_text # Or use self._text
        if not HAS_OPENGL: return

        try:
            # Clear the buffer with the configured background color
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity() # Reset modelview matrix

            if not self._text: # If no text, do nothing further
                 glFlush()
                 return

            # Set text color
            glColor3f(*OPENGL_TEXT_COLOR)

            # Get widget dimensions
            width = self.width()
            height = self.height()
            if width <= 0 or height <= 0: return

            # --- Text Rendering with Basic Wrapping (Origin Bottom-Left) ---
            y = height - OPENGL_PADDING - OPENGL_FONT_HEIGHT # Start near top-left
            max_chars_per_line = (width - 2 * OPENGL_PADDING) // OPENGL_FONT_WIDTH
            if max_chars_per_line <= 0: max_chars_per_line = 1

            lines = self._text.splitlines()
            for line in lines:
                # Word Wrapping Logic
                while len(line) > max_chars_per_line:
                    wrap_at = line.rfind(' ', 0, max_chars_per_line)
                    if wrap_at == -1: wrap_at = max_chars_per_line # Force break

                    segment = line[:wrap_at]
                    self._draw_text_line_gl(OPENGL_PADDING, y, segment)
                    y -= OPENGL_FONT_HEIGHT
                    if y < OPENGL_PADDING: break # Out of vertical bounds
                    line = line[wrap_at:].lstrip()

                if y < OPENGL_PADDING: break
                self._draw_text_line_gl(OPENGL_PADDING, y, line)
                y -= OPENGL_FONT_HEIGHT

            glFlush() # Ensure drawing commands are processed

        except NameError as ne:
             print(f"OpenGL Function Missing in paintGL? {ne}")
        except Exception as e:
            print(f"Error during paintGL: {e}")
            traceback.print_exc()

    def _draw_text_line_gl(self, x, y, text, font=OPENGL_FONT):
        """Helper to render a single line using GLUT bitmap fonts."""
        if not HAS_OPENGL or 'glRasterPos2f' not in globals(): return
        try:
            glRasterPos2f(x, y)
            for char in text:
                glutBitmapCharacter(font, ord(char))
        except Exception as e:
            print(f"Error drawing char '{char}': {e}")


# --- Main Application Window ---
class MainWindow(QMainWindow):
    # Signal to update the text from a different thread
    update_text_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.gl_widget = None # Initialize
        self._init_ui()
        # Connect the signal to the slot
        self.update_text_signal.connect(self._handle_update_text)

    def _init_ui(self):
        # --- Window Flags ---
        # Frameless, Always on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        # Enable background transparency (requires OpenGL alpha=0 and blending)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # self.setAttribute(Qt.WA_NoSystemBackground, True) # Alternative?

        # --- Initial Setup ---
        self.setGeometry(INITIAL_POSITION[0], INITIAL_POSITION[1], MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.setWindowOpacity(OPACITY)

        # --- OpenGL Widget Setup ---
        if HAS_OPENGL:
            self.gl_widget = GLWidget(self)
            self.setCentralWidget(self.gl_widget) # Use QMainWindow's central widget
        else:
            # Fallback if OpenGL isn't available (e.g., simple label - won't hide from capture)
            print("Warning: OpenGL not available, using basic QLabel fallback (will be captured).")
            from PyQt5.QtWidgets import QLabel
            fallback_label = QLabel("OpenGL Error - See Console", self)
            fallback_label.setAlignment(Qt.AlignCenter)
            fallback_label.setStyleSheet("background-color: rgba(30, 30, 30, 200); color: white; padding: 10px;")
            self.setCentralWidget(fallback_label)

        self.setWindowTitle("Overlay")
        self.hide() # Start hidden

    # --- Slot for Thread Signal ---
    def _handle_update_text(self, text):
        """This method is called by the signal from the API thread."""
        global current_display_text
        current_display_text = text

        if not text:
            self.hide()
            if self.gl_widget: self.gl_widget.setText("") # Clear GL widget too
            return

        # --- Calculate Required Size ---
        lines = text.splitlines()
        num_lines_est = 0
        max_len_chars = 0

        est_chars_per_line = (MAX_WINDOW_WIDTH - 2 * OPENGL_PADDING) // OPENGL_FONT_WIDTH
        if est_chars_per_line <= 0: est_chars_per_line = 1

        for line in lines:
            num_lines_est += 1 + (len(line) - 1) // est_chars_per_line
            max_len_chars = max(max_len_chars, len(line))

        req_width = min(max_len_chars * OPENGL_FONT_WIDTH + 2 * OPENGL_PADDING, MAX_WINDOW_WIDTH)
        req_height = min(num_lines_est * OPENGL_FONT_HEIGHT + 2 * OPENGL_PADDING, MAX_WINDOW_HEIGHT)

        req_width = max(req_width, MIN_WINDOW_WIDTH)
        req_height = max(req_height, MIN_WINDOW_HEIGHT)

        # --- Apply Size and Show ---
        # self.resize(req_width, req_height) # Resizing might be jerky, maybe just set maximums?
        # Set fixed size or adjust layout constraints? For now, let's resize.
        self.setFixedSize(QSize(req_width, req_height)) # Try fixed size first


        if self.gl_widget:
             self.gl_widget.setText(text) # Update text in GLWidget, triggering its repaint

        self.show()
        self.raise_() # Ensure it's on top

    # --- Window Movement ---
    def keyPressEvent(self, event: QKeyEvent):
        """ Handle Alt + Arrow key presses for moving the window. """
        modifiers = event.modifiers()
        key = event.key()

        if modifiers == Qt.AltModifier:
            current_pos = self.pos()
            new_x, new_y = current_pos.x(), current_pos.y()

            if key == Qt.Key_Up:    new_y -= MOVE_STEP
            elif key == Qt.Key_Down:  new_y += MOVE_STEP
            elif key == Qt.Key_Left:  new_x -= MOVE_STEP
            elif key == Qt.Key_Right: new_x += MOVE_STEP
            else:
                super().keyPressEvent(event) # Pass other keys along
                return

            # --- Basic Screen Boundary Check ---
            try:
                 screen_rect = QApplication.screenAt(current_pos).availableGeometry()
                 win_width = self.width()
                 win_height = self.height()
                 # Clamp within available screen geometry
                 new_x = max(screen_rect.left(), min(new_x, screen_rect.right() - win_width))
                 new_y = max(screen_rect.top(), min(new_y, screen_rect.bottom() - win_height))
            except AttributeError:
                 # Fallback if screen detection fails (older Qt?)
                 print("Warning: Screen boundary check failed.")

            self.move(new_x, new_y)
            # print(f"Moved window to: {new_x}, {new_y}")
        else:
            super().keyPressEvent(event) # Important for other key events

# --- Worker Thread for API Calls ---
# Using QObject/QThread is more Qt-idiomatic, but threading module is simpler here
def run_api_call_in_thread(image_bytes):
    global is_processing, main_window
    api_response = f"{ERROR_PREFIX}API thread failed unexpectedly."
    try:
        api_response = get_api_response(image_bytes)
    except Exception as thread_e:
        print(f"Error directly in API thread function: {thread_e}")
        traceback.print_exc()
        api_response = f"{ERROR_PREFIX}API thread error.\n{thread_e}"
    finally:
         # --- Emit signal to update UI on the main thread ---
         if main_window:
             # Safely emit the signal
             # Simply emit the signal directly - PyQt handles thread safety
             main_window.update_text_signal.emit(api_response)
             # main_window.update_text_signal.emit(api_response) # Direct emit might be ok if careful
         else:
              print("API response received, but main window is gone.")
         is_processing = False
         print("--- Processing finished ---")


# --- Capture & Process Function (Triggered by Global Hotkey) ---
def capture_and_process():
    """ Captures screen, starts API thread, updates overlay via signal. """
    global is_processing, main_window
    print(f"\n--- Hotkey '{HOTKEY_CAPTURE}' detected ---")
    if is_processing:
        print("Request already in progress. Ignoring.")
        return
    if not main_window:
        print("Main window not ready. Ignoring.")
        return

    is_processing = True
    # Update UI immediately with "Processing..." using the signal mechanism
    # Simply emit the signal directly
    main_window.update_text_signal.emit(PROCESSING_TEXT)
    # main_window.update_text_signal.emit(PROCESSING_TEXT) # Direct emit

    try:
        print("Capturing screen...")
        # Use QScreen for potentially better multi-monitor/Wayland compatibility?
        # screen = QApplication.primaryScreen()
        # screenshot_qpixmap = screen.grabWindow(0) # Captures entire screen
        # screenshot = screenshot_qpixmap.toImage() # Convert to QImage
        # buffer = QBuffer()
        # buffer.open(QBuffer.ReadWrite)
        # screenshot.save(buffer, "PNG")
        # img_bytes = buffer.data().data() # Get bytes
        # --- Or stick with Pillow/ImageGrab ---
        screenshot_pil = ImageGrab.grab()
        print(f"Screenshot captured (Size: {screenshot_pil.size}).")
        img_bytes_io = io.BytesIO()
        screenshot_pil.save(img_bytes_io, format='PNG')
        img_bytes = img_bytes_io.getvalue()
        print(f"Screenshot converted to {len(img_bytes)} bytes (PNG).")

        # --- Start API call in background thread ---
        api_thread = threading.Thread(target=run_api_call_in_thread, args=(img_bytes,), daemon=True)
        api_thread.start()

    except ImportError:
         err_msg = f"{ERROR_PREFIX}Pillow/ImageGrab or Qt capture failed."
         print(err_msg)
         if main_window: QMetaObject.invokeMethod(main_window, "update_text_signal.emit", Qt.QueuedConnection, Q_ARG(str, err_msg))
         is_processing = False # Reset lock
    except Exception as e:
        err_msg = f"{ERROR_PREFIX}Capture Error: {e}"
        print(err_msg)
        traceback.print_exc()
        if "scrot" in str(e).lower():
             err_msg += "\nIs 'scrot' installed? (sudo apt install scrot)"
        if main_window: QMetaObject.invokeMethod(main_window, "update_text_signal.emit", Qt.QueuedConnection, Q_ARG(str, err_msg))
        is_processing = False # Reset lock


# --- Safe Quit Function ---
def safe_quit():
    """ Safely quits the PyQt5 application and unhooks hotkeys. """
    global app
    print("\nInitiating shutdown...")
    try:
        print("Unhooking global hotkeys...")
        keyboard.unhook_all()
    except Exception as e:
        print(f"Note: Minor error during hotkey unhooking: {e}")

    if app:
        print("Quitting PyQt5 application...")
        try:
             app.quit() # Tell the application event loop to exit
             print("Qt Application quit requested.")
        except Exception as e:
             print(f"Error quitting Qt application: {e}")
    else:
        print("Qt Application instance not found.")

    print("Shutdown complete sequence initiated.")


# --- Main Execution ---
if __name__ == "__main__":
    print("--- Starting PyQt5 OpenGL Overlay App ---")

    if not HAS_PYQT5 or not HAS_OPENGL:
        print("\nExiting due to missing dependencies (PyQt5 or PyOpenGL/GLUT).")
        sys.exit(1)

    # Check root/sudo only if using the 'keyboard' library
    try:
        if hasattr(os, 'getuid') and os.getuid() != 0:
             print("\n!!! WARNING: Not running as root. Global hotkeys ('keyboard' lib) might fail. !!!")
             print(f"!!! Try: sudo {sys.executable} {__file__} !!!\n")
        elif hasattr(os, 'getuid'): print("Running as root. Global hotkeys should work.")
        else: print("Skipping root check.")
    except Exception as e: print(f"Privilege check error: {e}")

    # --- Setup PyQt Application ---
    app = QApplication(sys.argv)

    # --- Create Main Window ---
    try:
        main_window = MainWindow()
        # main_window.show() # Window starts hidden, shown on first text update
    except Exception as e_setup:
        print(f"FATAL: Error creating MainWindow: {e_setup}")
        traceback.print_exc()
        sys.exit("Exiting due to window creation failure.")

    # --- Setup Global Hotkeys ---
    try:
        print(f"Registering global capture hotkey: {HOTKEY_CAPTURE}")
        keyboard.add_hotkey(HOTKEY_CAPTURE, capture_and_process)
        print(f"Registering global exit hotkey: {HOTKEY_EXIT}")
        keyboard.add_hotkey(HOTKEY_EXIT, safe_quit)
        print("Global hotkeys registered.")
    except ImportError: # Should have been caught earlier, but double-check
         print("\n!!! ERROR: 'keyboard' library not found. Hotkeys disabled. !!!")
         safe_quit()
         sys.exit("Exiting due to missing 'keyboard' library.")
    except Exception as e_hotkey:
        print(f"\n!!! FATAL ERROR registering global hotkeys: {e_hotkey}")
        print("!!! This often requires root/sudo permissions on Linux. !!!")
        safe_quit()
        sys.exit("Exiting due to hotkey registration failure.")

    # --- Start Event Loop ---
    print(f"\nApp running.")
    print(f"- Press '{HOTKEY_CAPTURE}' to capture screen.")
    print(f"- Use 'Alt + Arrow Keys' to move the overlay.")
    print(f"- Press '{HOTKEY_EXIT}' to quit.")

    exit_code = app.exec_()
    print(f"--- PyQt5 Overlay App Exited (Code: {exit_code}) ---")
    sys.exit(exit_code)
