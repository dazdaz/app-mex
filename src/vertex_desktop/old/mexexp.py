#!/usr/bin/env python3
import sys
import os
import logging
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QTextEdit, QComboBox, QLabel,
                             QCheckBox, QMessageBox, QTabWidget, QFrame,
                             QGraphicsDropShadowEffect, QSplitter, QProgressBar,
                             QSpinBox, QToolTip, QFileDialog, QDialog, QLineEdit,
                             QDialogButtonBox, QTextBrowser, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QElapsedTimer
from PyQt6.QtGui import QFont, QTextCursor, QPalette, QColor, QIcon, QPixmap, QPainter, QLinearGradient
from PyQt6.QtWebEngineWidgets import QWebEngineView
from google.auth import default
from google.auth.transport.requests import Request
import re
# --- CONFIGURATION ---
PROJECT_ID = None # Will be set on startup
LOCATION = os.environ.get("LOCATION", "global")
VERTEX_AI_ENDPOINT = "https://aiplatform.googleapis.com"
DEFAULT_FONT_SIZE = 14
# --- LOGGING SETUP ---
log_dir = Path.home() / ".mex-model-explorer"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
# --- MODEL CONFIGURATION WITH PRICING ---
AVAILABLE_MODELS = {
    "claude-3-7-sonnet": {
        "publisher": "anthropic",
        "model_id": "claude-3-7-sonnet@20250219:streamRawPredict",
        "display_name": "Claude 3.7 Sonnet",
        "max_input_tokens": 200000,
        "max_output_tokens": 64000,
        "icon": "🎭",
        "color": "#FF6B6B",
        "description": "Fast, balanced performance with 200k input / 64k output tokens",
        "pricing": {
            "input": 0.003, # $0.003 per 1K tokens
            "output": 0.015 # $0.015 per 1K tokens
        }
    },
    "claude-opus-4-1": {
        "publisher": "anthropic",
        "model_id": "claude-opus-4-1@20250805:streamRawPredict",
        "display_name": "Claude 4.1 Opus",
        "max_input_tokens": 200000,
        "max_output_tokens": 32000,
        "icon": "🎨",
        "color": "#C92A2A",
        "description": "Most capable model with 200k input / 32k output tokens",
        "pricing": {
            "input": 0.015, # $0.015 per 1K tokens
            "output": 0.075 # $0.075 per 1K tokens
        }
    },
    "gemini-2-5-pro": {
        "publisher": "google",
        "model_id": "gemini-2.5-pro@default:streamGenerateContent",
        "display_name": "Gemini 2.5 Pro",
        "max_input_tokens": 1048576,
        "max_output_tokens": 65536,
        "icon": "💎",
        "color": "#4DABF7",
        "description": "Advanced multimodal with 1M+ input / 65k output tokens",
        "pricing": {
            "input": 0.0025, # $0.0025 per 1K tokens
            "output": 0.01 # $0.01 per 1K tokens
        }
    },
    "gemini-2-5-flash": {
        "publisher": "google",
        "model_id": "gemini-2.5-flash@default:streamGenerateContent",
        "display_name": "Gemini 2.5 Flash",
        "max_input_tokens": 1048576,
        "max_output_tokens": 65535,
        "icon": "⚡",
        "color": "#69DB7C",
        "description": "Fastest response with 1M+ input / 65k output tokens",
        "pricing": {
            "input": 0.00025, # $0.00025 per 1K tokens
            "output": 0.001 # $0.001 per 1K tokens
        }
    }
}
# --- THEME MANAGER ---
class ThemeManager:
    """Manages application themes (light/dark mode)"""
    def __init__(self):
        self.is_dark_mode = False
        self.light_colors = {
            "primary": "#6366F1",
            "primary_hover": "#5558E3",
            "secondary": "#10B981",
            "secondary_hover": "#059669",
            "danger": "#EF4444",
            "warning": "#F59E0B",
            "background": "#F9FAFB",
            "surface": "#FFFFFF",
            "border": "#E5E7EB",
            "text_primary": "#111827",
            "text_secondary": "#6B7280",
            "success_bg": "#D1FAE5",
            "error_bg": "#FEE2E2",
            "info_bg": "#DBEAFE",
            "disclaimer_bg": "#FEF3C7"
        }
        self.dark_colors = {
            "primary": "#818CF8",
            "primary_hover": "#A5B4FC",
            "secondary": "#34D399",
            "secondary_hover": "#6EE7B7",
            "danger": "#F87171",
            "warning": "#FCD34D",
            "background": "#111827",
            "surface": "#1F2937",
            "border": "#374151",
            "text_primary": "#F9FAFB",
            "text_secondary": "#D1D5DB",
            "success_bg": "#064E3B",
            "error_bg": "#7F1D1D",
            "info_bg": "#1E3A8A",
            "disclaimer_bg": "#78350F"
        }
        self.current_colors = self.light_colors.copy()
    def toggle_theme(self):
        """Toggle between light and dark mode"""
        self.is_dark_mode = not self.is_dark_mode
        self.current_colors = self.dark_colors.copy() if self.is_dark_mode else self.light_colors.copy()
        return self.current_colors
    def get_colors(self):
        """Get current color scheme"""
        return self.current_colors
# Global theme manager instance
theme_manager = ThemeManager()
COLORS = theme_manager.get_colors()
# Dynamic font management
class FontManager:
    """Manages application fonts with dynamic sizing"""
    def __init__(self, base_size=DEFAULT_FONT_SIZE):
        self.base_size = base_size
        self.update_fonts()
    def update_fonts(self):
        """Update all font definitions with new base size"""
        self.fonts = {
            "heading": QFont("SF Pro Display", self.base_size + 7, QFont.Weight.Bold),
            "subheading": QFont("SF Pro Display", self.base_size - 1, QFont.Weight.Medium),
            "body": QFont("SF Pro Text", self.base_size),
            "mono": QFont("SF Mono", self.base_size - 1),
            "button": QFont("SF Pro Text", self.base_size, QFont.Weight.Medium)
        }
    def set_base_size(self, size):
        """Set new base font size and update all fonts"""
        self.base_size = size
        self.update_fonts()
    def get_font(self, font_type):
        """Get a specific font type"""
        return self.fonts.get(font_type, self.fonts["body"])
# Global font manager instance
font_manager = FontManager()
class AboutDialog(QDialog):
    """About dialog with application information"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About MEX - Model EXplorer")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        layout = QVBoxLayout()
        # Title
        title_label = QLabel("MEX - Model EXplorer")
        title_label.setFont(font_manager.get_font("heading"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {COLORS['primary']}; margin: 10px;")
        layout.addWidget(title_label)
        # Version info
        version_label = QLabel("Version 1.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(f"color: {COLORS['text_secondary']}; margin-bottom: 20px;")
        layout.addWidget(version_label)
        # About text
        about_text = QTextBrowser()
        about_text.setOpenExternalLinks(True)
        about_text.setHtml(f"""
        <style>
            body {{
                font-family: 'SF Pro Text', system-ui, -apple-system, sans-serif;
                font-size: {font_manager.base_size}px;
                color: {COLORS['text_primary']};
                line-height: 1.6;
            }}
            h3 {{
                color: {COLORS['primary']};
                margin-top: 15px;
                margin-bottom: 5px;
            }}
            .info {{
                background-color: {COLORS['info_bg']};
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
            }}
            .warning {{
                background-color: {COLORS['warning'] if theme_manager.is_dark_mode else '#FEF3C7'};
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
                border-left: 3px solid {COLORS['warning']};
            }}
            ul {{ margin-left: 20px; }}
        </style>
        <h3>About MEX - Model EXplorer</h3>
        <p>MEX (Model EXplorer) is a powerful desktop interface for Google Cloud's Vertex AI,
        providing easy access to multiple AI models including Claude and Gemini.</p>
        <h3>Token & Character Counting</h3>
        <div class="info">
            <p><b>Approximations used in MEX:</b></p>
            <ul>
                <li>1 token ≈ 0.75 words</li>
                <li>1 token ≈ 4 characters</li>
                <li>100 tokens ≈ 75 words</li>
            </ul>
        </div>
        <div class="warning">
            <p><b>⚠️ Important Note:</b><br>
            The actual token count may vary slightly depending on the specific tokenizer used.
            Different models use different tokenization methods, so the character and token counts
            shown are estimates. The actual usage may differ by ±10-20%.</p>
        </div>
        <h3>Features</h3>
        <ul>
            <li>Support for multiple AI models (Claude 3.7, Claude 4.1, Gemini 2.5)</li>
            <li>Real-time character and token counting</li>
            <li>Multiple query tabs with optional synchronization</li>
            <li>Dark/Light mode toggle</li>
            <li>Raw JSON response viewing</li>
            <li>Response export functionality</li>
            <li>Adjustable font sizes</li>
            <li>Stop query functionality</li>
            <li>Copy query to clipboard button</li>
            <li>Fictional pricing estimates</li>
        </ul>
        <h3>Model Token Limits</h3>
        <ul>
            <li><b>Claude 3.7 Sonnet:</b> 200k input / 64k output tokens</li>
            <li><b>Claude 4.1 Opus:</b> 200k input / 32k output tokens</li>
            <li><b>Gemini 2.5 Pro:</b> 1M+ input / 65k output tokens</li>
            <li><b>Gemini 2.5 Flash:</b> 1M+ input / 65k output tokens</li>
        </ul>
        <h3>Keyboard Shortcuts</h3>
        <ul>
            <li><b>Ctrl+Enter:</b> Execute query (when in prompt field)</li>
            <li><b>Ctrl+T:</b> New tab</li>
            <li><b>Ctrl+W:</b> Close current tab</li>
        </ul>
        """)
        about_text.setStyleSheet(f"""
            QTextBrowser {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 10px;
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
            }}
        """)
        layout.addWidget(about_text)
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 24px;
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: {font_manager.base_size}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}
        """)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        self.setLayout(layout)
class ProjectIdDialog(QDialog):
    """Dialog to request Project ID from the user"""
    def __init__(self, parent=None, default_project=None):
        super().__init__(parent)
        self.setWindowTitle("MEX - Enter Google Cloud Project ID")
        self.setModal(True)
        self.setMinimumWidth(500)
        layout = QVBoxLayout()
        # Info label
        info_label = QLabel("Please enter your Google Cloud Project ID:")
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {font_manager.base_size}px;
            margin-bottom: 10px;
        """)
        layout.addWidget(info_label)
        # Project ID input
        self.project_input = QLineEdit()
        if default_project:
            self.project_input.setText(default_project)
            self.project_input.setPlaceholderText(f"e.g., {default_project}")
        else:
            self.project_input.setPlaceholderText("e.g., my-project-id")
        self.project_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: {font_manager.base_size}px;
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
        """)
        layout.addWidget(self.project_input)
        # Disclaimer box
        disclaimer_box = QGroupBox("⚠️ Disclaimer")
        disclaimer_box.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {COLORS['warning']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {COLORS['disclaimer_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: {COLORS['danger']};
            }}
        """)
        disclaimer_layout = QVBoxLayout()
        disclaimer_text = QLabel(
            "• Use at your own risk\n"
            "• All pricing shown is fictional and for demonstration only\n"
            "• Actual costs may vary significantly\n"
            "• This is not an official Google product"
        )
        disclaimer_text.setWordWrap(True)
        disclaimer_text.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {font_manager.base_size - 1}px;
            font-weight: normal;
            padding: 5px;
        """)
        disclaimer_layout.addWidget(disclaimer_text)
        disclaimer_box.setLayout(disclaimer_layout)
        layout.addWidget(disclaimer_box)
        # Help text
        help_label = QLabel("You can find your Project ID in the Google Cloud Console")
        help_label.setWordWrap(True)
        help_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {font_manager.base_size - 2}px;
            margin-top: 5px;
        """)
        layout.addWidget(help_label)
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        # Style the buttons
        buttons.setStyleSheet(f"""
            QPushButton {{
                padding: 6px 16px;
                border-radius: 4px;
                font-size: {font_manager.base_size}px;
                font-weight: 500;
            }}
            QPushButton[text="OK"] {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
            }}
            QPushButton[text="OK"]:hover {{
                background-color: {COLORS['primary_hover']};
            }}
            QPushButton[text="Cancel"] {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
            }}
            QPushButton[text="Cancel"]:hover {{
                background-color: {COLORS['background']};
            }}
        """)
        layout.addSpacing(10)
        layout.addWidget(buttons)
        self.setLayout(layout)
        # Focus on input
        self.project_input.setFocus()
    def validate_and_accept(self):
        """Validate the project ID and accept if valid"""
        project_id = self.project_input.text().strip()
        if not project_id:
            QMessageBox.warning(
                self,
                "Invalid Project ID",
                "Please enter a valid Project ID"
            )
            return
        # Basic validation: project IDs should contain only lowercase letters, numbers, and hyphens
        if not all(c.isalnum() or c == '-' for c in project_id):
            QMessageBox.warning(
                self,
                "Invalid Project ID",
                "Project ID should only contain lowercase letters, numbers, and hyphens"
            )
            return
        self.accept()
    def get_project_id(self):
        """Get the entered project ID"""
        return self.project_input.text().strip()
class AnimatedButton(QPushButton):
    """Custom animated button with hover effects"""
    def __init__(self, text, primary=False):
        super().__init__(text)
        self.primary = primary
        self.base_font_size = font_manager.base_size
        self.setup_style()
    def setup_style(self):
        if self.primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                              stop: 0 {COLORS['primary']},
                                              stop: 1 {COLORS['primary_hover']});
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: {self.base_font_size}px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                              stop: 0 {COLORS['primary_hover']},
                                              stop: 1 {COLORS['primary']});
                }}
                QPushButton:pressed {{
                    padding: 9px 15px 7px 17px;
                }}
                QPushButton:disabled {{
                    background: #9CA3AF;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    color: {COLORS['text_primary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: 500;
                    font-size: {self.base_font_size}px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['background']};
                    border-color: {COLORS['primary']};
                    color: {COLORS['primary']};
                }}
                QPushButton:pressed {{
                    padding: 7px 11px 5px 13px;
                }}
            """)
    def update_font_size(self, size):
        """Update button font size"""
        self.base_font_size = size
        self.setup_style()
    def update_theme(self):
        """Update button theme"""
        self.setup_style()
class StyledCard(QFrame):
    """Styled card component with shadow"""
    def __init__(self):
        super().__init__()
        self.update_theme()
    def update_theme(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        # Add subtle drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 20 if not theme_manager.is_dark_mode else 60))
        self.setGraphicsEffect(shadow)
class APIWorker(QThread):
    """Worker thread for API calls"""
    finished = pyqtSignal(str, str, str, int, int) # response, error, raw_response, input_tokens, output_tokens
    progress = pyqtSignal(str, int) # message, percentage
    def __init__(self, model_config, prompt, credentials):
        super().__init__()
        self.model_config = model_config
        self.prompt = prompt
        self.credentials = credentials
        self._is_cancelled = False
    def cancel(self):
        """Cancel the API request"""
        self._is_cancelled = True
    def get_access_token(self):
        """Get a fresh access token for API calls."""
        self.credentials.refresh(Request())
        return self.credentials.token
    def build_request_payload(self):
        """Build the appropriate request payload based on the model publisher."""
        if self.model_config["publisher"] == "anthropic":
            return {
                "anthropic_version": "vertex-2023-10-16",
                "messages": [{"role": "user", "content": self.prompt}],
                "max_tokens": self.model_config["max_output_tokens"],
                "stream": True
            }
        elif self.model_config["publisher"] == "google":
            return {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": self.prompt}]
                }]
            }
        else:
            raise ValueError(f"Unknown publisher: {self.model_config['publisher']}")
    def parse_anthropic_stream(self, response_text):
        """Parse Anthropic's Server-Sent Events streaming format."""
        full_text = ""
        for line in response_text.split('\n'):
            if line.startswith('data: '):
                try:
                    data_str = line[6:].strip()
                    if data_str and data_str != '[DONE]':
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            delta_text = data.get("delta", {}).get("text", "")
                            full_text += delta_text
                except json.JSONDecodeError:
                    continue
        return full_text
    def parse_google_stream(self, response_text):
        """Parse Google's streaming format - handle newline-delimited JSON."""
        full_text = ""
        # Split by lines and filter out empty lines and commas
        lines = [line.strip() for line in response_text.split('\n') if line.strip() and line.strip() != ',']
        # Handle array format: [obj1, obj2, obj3]
        if response_text.strip().startswith('['):
            try:
                # Try to parse as a JSON array
                data_array = json.loads(response_text)
                for data in data_array:
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            full_text += text
                return full_text
            except json.JSONDecodeError:
                pass
        # Handle newline-delimited JSON format
        for line in lines:
            # Skip lines that are just commas
            if line == ',':
                continue
            try:
                # Remove trailing comma if present
                if line.endswith(','):
                    line = line[:-1]
                data = json.loads(line)
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                        full_text += text
            except json.JSONDecodeError:
                continue
        return full_text
    def parse_response(self, response_text, response_data=None):
        """Parse the response based on the model publisher and format."""
        try:
            if self.model_config["publisher"] == "anthropic":
                # First try streaming format
                if "data:" in response_text:
                    parsed = self.parse_anthropic_stream(response_text)
                    if parsed:
                        return parsed
                # Then try non-streaming JSON format
                elif response_data and isinstance(response_data, dict):
                    if "content" in response_data:
                        if isinstance(response_data["content"], list) and len(response_data["content"]) > 0:
                            return response_data["content"][0].get("text", "")
                # If neither worked, return the raw text
                return response_text
            elif self.model_config["publisher"] == "google":
                # Parse Google's streaming format
                parsed = self.parse_google_stream(response_text)
                if parsed:
                    return parsed
                # If parsing failed, return raw text
                return response_text
            else:
                return response_text
        except Exception as e:
            logging.error(f"Error parsing response: {e}")
            logging.debug(f"Response text preview: {response_text[:500]}")
            return f"Error parsing response: {str(e)}\n\nRaw response:\n{response_text[:1000]}"
    def run(self):
        """Run the API call in a separate thread"""
        try:
            if self._is_cancelled:
                self.finished.emit("", "Query cancelled by user", "", 0, 0)
                return
            self.progress.emit("🔐 Authenticating...", 20)
            access_token = self.get_access_token()
            if self._is_cancelled:
                self.finished.emit("", "Query cancelled by user", "", 0, 0)
                return
            publisher = self.model_config["publisher"]
            model_id = self.model_config["model_id"]
            model_path = model_id.split(":")[0]
            method = model_id.split(":")[1] if ":" in model_id else "predict"
            url = f"{VERTEX_AI_ENDPOINT}/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/{publisher}/models/{model_path}:{method}"
            payload = self.build_request_payload()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            if self._is_cancelled:
                self.finished.emit("", "Query cancelled by user", "", 0, 0)
                return
            self.progress.emit("🚀 Sending request...", 50)
            logging.info(f"Sending request to: {url}")
            response = requests.post(url, headers=headers, json=payload, timeout=60, stream=True)
            if self._is_cancelled:
                self.finished.emit("", "Query cancelled by user", "", 0, 0)
                return
            if response.status_code != 200:
                error_msg = f"API call failed with status {response.status_code}: {response.text}"
                logging.error(error_msg)
                self.finished.emit("", error_msg, "", 0, 0)
                return
            self.progress.emit("📝 Processing response...", 80)
            response_text = response.text
            logging.info(f"Received response of length: {len(response_text)}")
            # Parse the response to extract actual text content
            parsed_response = self.parse_response(response_text)
            # Calculate approximate token counts
            input_tokens = len(self.prompt) // 4
            output_tokens = len(parsed_response) // 4
            # Log what we're returning
            logging.info(f"Returning parsed response of length: {len(parsed_response)}")
            self.progress.emit("✅ Complete!", 100)
            self.finished.emit(parsed_response, "", response_text, input_tokens, output_tokens)
        except Exception as e:
            logging.error(f"Error in API worker: {e}")
            self.finished.emit("", str(e), "", 0, 0)
class QueryTab(QWidget):
    """Individual query tab widget with enhanced design"""
    font_size_changed = pyqtSignal(int) # Signal for font size changes
    def __init__(self, tab_name, credentials, parent=None):
        super().__init__(parent)
        self.tab_name = tab_name
        self.credentials = credentials
        self.worker = None
        self.start_time = None
        self.raw_response = "" # Store raw response
        self.parsed_response = ""
        self.parsed_html = ""
        self.current_model_config = None
        self.query_timer = QElapsedTimer()
        self.init_ui()
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)
        # Create a splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS['border']};
                border-radius: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS['text_secondary']};
            }}
        """)
        # TOP SECTION (Controls + Prompt)
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setSpacing(8)
        top_layout.setContentsMargins(0, 0, 0, 0)
        # Compact Header with Model Selector
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        # Execute and Stop buttons
        self.generate_btn = AnimatedButton("🚀 Execute", primary=True)
        self.generate_btn.clicked.connect(self.generate_response)
        header_layout.addWidget(self.generate_btn)
        # Stop button (initially hidden)
        self.stop_btn = AnimatedButton("⏹️ Stop", primary=True)
        self.stop_btn.clicked.connect(self.stop_query)
        self.stop_btn.setVisible(False)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 {COLORS['danger']},
                                          stop: 1 #DC2626);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: {font_manager.base_size}px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #DC2626,
                                          stop: 1 {COLORS['danger']});
            }}
        """)
        header_layout.addWidget(self.stop_btn)
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        self.model_combo.setMaximumWidth(250)
        self.update_combo_style()
        # Add models to combo box - Claude Opus 4.1 will be added second
        for key, config in AVAILABLE_MODELS.items():
            self.model_combo.addItem(f"{config['icon']} {config['display_name']}", key)
        # Set Claude Opus 4.1 as default (it's the second item, index 1)
        self.model_combo.setCurrentIndex(1)
        # Model info label with tooltip
        self.model_info = QLabel("")
        self.model_info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: {font_manager.base_size - 2}px;")
        self.model_info.setCursor(Qt.CursorShape.WhatsThisCursor)
        header_layout.addWidget(self.model_combo)
        header_layout.addWidget(self.model_info)
        header_layout.addStretch()
        # Pricing label
        self.pricing_label = QLabel("")
        self.pricing_label.setStyleSheet(f"""
            color: {COLORS['warning']};
            font-size: {font_manager.base_size - 2}px;
            padding: 2px 6px;
            background-color: {COLORS['disclaimer_bg']};
            border-radius: 3px;
            font-weight: 600;
        """)
        self.pricing_label.setVisible(False)
        header_layout.addWidget(self.pricing_label)
        # Input character and token count labels
        self.input_char_count_label = QLabel("Input: 0 chars")
        self.input_char_count_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {font_manager.base_size - 2}px;
            padding: 2px 6px;
            background-color: {COLORS['background']};
            border-radius: 3px;
        """)
        self.input_token_count_label = QLabel("~0 tokens")
        self.input_token_count_label.setStyleSheet(f"""
            color: {COLORS['primary']};
            font-size: {font_manager.base_size - 2}px;
            padding: 2px 6px;
            background-color: {COLORS['info_bg']};
            border-radius: 3px;
            font-weight: 600;
        """)
        # Raw JSON checkbox
        self.show_raw_json_checkbox = QCheckBox("Raw JSON")
        self.show_raw_json_checkbox.setChecked(False)
        self.show_raw_json_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_secondary']};
                font-size: {font_manager.base_size - 2}px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['surface']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """)
        self.show_raw_json_checkbox.stateChanged.connect(self.toggle_response_format)
        # Add Save button
        self.save_btn = AnimatedButton("💾 Save")
        self.save_btn.clicked.connect(self.save_response)
        self.save_btn.setEnabled(False)
        # Copy Output button
        self.copy_output_btn = AnimatedButton("📋 Copy Output")
        self.copy_output_btn.clicked.connect(self.copy_output)
        self.copy_output_btn.setEnabled(False)
        # Copy Query and Clear buttons - Updated label here
        self.copy_btn = AnimatedButton("Copy Query") # Changed from "Copy" to "Copy Query"
        self.copy_btn.clicked.connect(self.copy_response)
        self.clear_btn = AnimatedButton("Clear")
        self.clear_btn.clicked.connect(self.clear_all)
        header_layout.addWidget(self.input_char_count_label)
        header_layout.addWidget(self.input_token_count_label)
        header_layout.addWidget(self.show_raw_json_checkbox)
        header_layout.addWidget(self.save_btn)
        header_layout.addWidget(self.copy_output_btn)
        header_layout.addWidget(self.copy_btn)
        header_layout.addWidget(self.clear_btn)
        # Prompt Input - now with 9 lines minimum height
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Enter your query here...")
        # Calculate height for 9 lines
        font_metrics = self.prompt_edit.fontMetrics()
        line_height = font_metrics.lineSpacing()
        nine_lines_height = line_height * 9 + 20 # 20px for padding
        self.prompt_edit.setMinimumHeight(nine_lines_height)
        self.prompt_edit.setMaximumHeight(300) # Increased max height for resizability
        self.prompt_edit.setFont(font_manager.get_font("mono"))
        self.update_prompt_style()
        self.prompt_edit.textChanged.connect(self.update_char_count)
        self.prompt_edit.textChanged.connect(self.update_pricing_estimate)
        # Progress Bar (compact)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                text-align: center;
                font-size: {font_manager.base_size - 2}px;
                background-color: {COLORS['background']};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 {COLORS['primary']},
                                          stop: 1 {COLORS['secondary']});
                border-radius: 3px;
            }}
        """)
        top_layout.addLayout(header_layout)
        top_layout.addWidget(self.prompt_edit)
        top_layout.addWidget(self.progress_bar)
        # BOTTOM SECTION (Response - gets more space)
        response_widget = QWidget()
        response_layout = QVBoxLayout(response_widget)
        response_layout.setSpacing(4)
        response_layout.setContentsMargins(0, 0, 0, 0)
        # Response header
        response_header = QHBoxLayout()
        response_label = QLabel("💬 Response")
        response_label.setFont(font_manager.get_font("subheading"))
        response_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")
        self.response_info = QLabel("")
        self.response_info.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {font_manager.base_size - 2}px;
            padding: 2px 6px;
            background-color: {COLORS['background']};
            border-radius: 3px;
        """)
        # Output character and token count labels
        self.output_char_count_label = QLabel("")
        self.output_char_count_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {font_manager.base_size - 2}px;
            padding: 2px 6px;
            background-color: {COLORS['background']};
            border-radius: 3px;
        """)
        self.output_token_count_label = QLabel("")
        self.output_token_count_label.setStyleSheet(f"""
            color: {COLORS['secondary']};
            font-size: {font_manager.base_size - 2}px;
            padding: 2px 6px;
            background-color: {COLORS['success_bg']};
            border-radius: 3px;
            font-weight: 600;
        """)
        response_header.addWidget(response_label)
        response_header.addStretch()
        response_header.addWidget(self.output_char_count_label)
        response_header.addWidget(self.output_token_count_label)
        response_header.addWidget(self.response_info)
        # Response text (takes all available space)
        self.response_edit = QWebEngineView()
        self.response_edit.setHtml('<html><body><p>Response will appear here...</p></body></html>')
        response_layout.addLayout(response_header)
        response_layout.addWidget(self.response_edit, 1) # Give it stretch factor
        # Status label (compact)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        self.status_label.setMaximumHeight(30)
        self.update_status_style()
        # Add widgets to splitter
        splitter.addWidget(top_widget)
        splitter.addWidget(response_widget)
        # Set initial sizes - adjusted for 9-line prompt (35% top, 65% bottom)
        splitter.setSizes([350, 450])
        # Prevent the top section from becoming too small
        splitter.setStretchFactor(0, 0) # Don't stretch top section
        splitter.setStretchFactor(1, 1) # Allow bottom section to stretch
        # Add to main layout
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.status_label)
        self.setLayout(main_layout)
        self.update_model_info()
        self.model_combo.currentIndexChanged.connect(self.update_model_info)
        self.model_combo.currentIndexChanged.connect(self.update_pricing_estimate)
    def markdown_to_html(self, text):
        if not text:
            return "<html><body></body></html>"
        # Escape HTML
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        # Simple markdown parsing
        # Bold
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        # Italic
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code class="inline">\1</code>', text)
        # Headers
        text = re.sub(r'^### (.*)$', r'<h3>\1</h3>', text, flags=re.M)
        text = re.sub(r'^## (.*)$', r'<h2>\1</h2>', text, flags=re.M)
        text = re.sub(r'^# (.*)$', r'<h1>\1</h1>', text, flags=re.M)
        # Code blocks
        def replace_code(match):
            lang = match.group(1).strip() if match.group(1) else 'text'
            code = match.group(2)
            return f'''<pre class="code-pre">
<div class="code-header">
  <span class="language">{lang}</span>
  <div class="code-actions">
    <button class="collapse-btn" onclick="toggleCollapse(this)">× Collapse</button>
    <button class="wrap-btn" onclick="toggleWrap(this)">≡ Wrap</button>
    <button class="copy-btn" onclick="copyCode(this)">○ Copy</button>
  </div>
</div>
<code class="language-{lang}">{code}</code>
</pre>'''
        text = re.sub(r'```(\w*)\n(.*?)\n```', replace_code, text, flags=re.S)
        # Replace \n with <br>
        text = text.replace('\n', '<br>')
        # Full HTML
        html = f'''<html><head><style>
body {{
    margin: 0;
    padding: 10px;
    font-family: 'SF Pro Text', system-ui;
    font-size: {font_manager.base_size}px;
    color: {COLORS['text_primary']};
    background-color: {COLORS['surface']};
    line-height: 1.6;
}}
h1, h2, h3 {{
    color: {COLORS['primary']};
}}
code.inline {{
    background-color: {COLORS['background']};
    padding: 2px 4px;
    border-radius: 3px;
    font-family: 'SF Mono', monospace;
}}
.code-pre {{
    position: relative;
    padding: 30px 12px 12px 12px;
    margin: 16px 0;
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    overflow-x: auto;
    white-space: pre;
    word-wrap: normal;
    background-color: {COLORS['background']};
    font-family: 'SF Mono', monospace;
    font-size: 0.95em;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
.code-pre.wrapped {{
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: hidden;
}}
.code-header {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    padding: 4px 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: transparent;
    z-index: 1;
}}
.language {{
    font-size: 0.8em;
    color: {COLORS['text_secondary']};
    background-color: {COLORS['surface']};
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
}}
.code-actions button {{
    background: none;
    border: none;
    padding: 4px 8px;
    color: {COLORS['text_secondary']};
    cursor: pointer;
    font-size: 0.9em;
    border-radius: 3px;
}}
.code-actions button:hover {{
    background-color: {COLORS['surface']};
    color: {COLORS['primary']};
}}
</style>
<script>
function copyCode(btn) {{
    const code = btn.closest('.code-pre').querySelector('code').innerText;
    navigator.clipboard.writeText(code).then(() => {{
        btn.innerText = '○ Copied';
        setTimeout(() => btn.innerText = '○ Copy', 2000);
    }});
}}
function toggleCollapse(btn) {{
    const code = btn.closest('.code-pre').querySelector('code');
    if (code.style.display === 'none') {{
        code.style.display = '';
        btn.innerText = '× Collapse';
    }} else {{
        code.style.display = 'none';
        btn.innerText = '× Expand';
    }}
}}
function toggleWrap(btn) {{
    const pre = btn.closest('.code-pre');
    if (pre.classList.contains('wrapped')) {{
        pre.classList.remove('wrapped');
        btn.innerText = '≡ Wrap';
    }} else {{
        pre.classList.add('wrapped');
        btn.innerText = '≡ No Wrap';
    }}
}}
</script>
</head><body>{text}</body></html>'''
        return html
    def format_raw_response(self):
        try:
            formatted = ""
            lines = self.raw_response.split('\n')
            for line in lines:
                if line.strip():
                    try:
                        data = json.loads(line.strip(','))
                        formatted += json.dumps(data, indent=2) + '\n\n'
                    except:
                        formatted += line + '\n'
            return self.markdown_to_html(f'```json\n{formatted}\n```')
        except:
            return self.markdown_to_html(f'```text\n{self.raw_response}\n```')
    def set_response_content(self):
        if self.show_raw_json_checkbox.isChecked() and self.raw_response:
            self.response_edit.setHtml(self.format_raw_response())
        else:
            self.response_edit.setHtml(self.parsed_html)
    def update_response_display(self):
        if self.parsed_response:
            self.parsed_html = self.markdown_to_html(self.parsed_response)
            self.set_response_content()
    def update_pricing_estimate(self):
        """Calculate and display fictional pricing estimate"""
        if not self.current_model_config:
            return
        input_tokens = len(self.prompt_edit.toPlainText()) // 4
        if input_tokens == 0:
            self.pricing_label.setVisible(False)
            return
        # Estimate output tokens (assume 2x input for estimation)
        estimated_output_tokens = input_tokens * 2
        # Get pricing info
        pricing = self.current_model_config.get("pricing", {"input": 0.001, "output": 0.002})
        # Calculate costs in USD
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (estimated_output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost
        # Format price display
        if total_cost < 0.01:
            price_text = f"${total_cost:.4f}"
        elif total_cost < 1:
            price_text = f"${total_cost:.3f}"
        else:
            price_text = f"${total_cost:.2f}"
        self.pricing_label.setText(f"💰 ~{price_text} USD*")
        self.pricing_label.setToolTip(
            f"Fictional pricing estimate:\n"
            f"Input: ~{input_tokens:,} tokens × ${pricing['input']:.3f}/1K = ${input_cost:.4f}\n"
            f"Output: ~{estimated_output_tokens:,} tokens × ${pricing['output']:.3f}/1K = ${output_cost:.4f}\n"
            f"Total: ~{price_text} USD\n\n"
            f"*Prices are fictional and for demonstration only"
        )
        self.pricing_label.setVisible(True)
    def stop_query(self):
        """Stop the current query"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.quit()
            self.worker.wait()
            self.on_query_stopped()
    def on_query_stopped(self):
        """Handle query stop"""
        self.generate_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.response_info.setText("⏹️ Stopped")
        self.show_message("Query stopped", "warning")
    def copy_output(self):
        """Copy the output response to clipboard"""
        response = self.parsed_response if self.parsed_response else ""
        if response:
            QApplication.clipboard().setText(response)
            self.show_message(f"Output copied! ({len(response):,} characters)", "success")
        else:
            self.show_message("No output to copy", "warning")
    def save_response(self):
        """Save the response to a text file"""
        if not self.parsed_response and not self.raw_response:
            self.show_message("No response to save", "warning")
            return
        # Prepare default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = self.model_combo.currentText().split()[1] if self.model_combo.currentText() else "response"
        # Determine file extension based on current view
        if self.show_raw_json_checkbox.isChecked():
            default_filename = f"{model_name}_{timestamp}_raw.json"
            file_filter = "JSON Files (*.json);;Text Files (*.txt);;All Files (*.*)"
        else:
            default_filename = f"{model_name}_{timestamp}.txt"
            file_filter = "Text Files (*.txt);;JSON Files (*.json);;All Files (*.*)"
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Response",
            default_filename,
            file_filter
        )
        if file_path:
            try:
                # Determine what to save based on checkbox state and file extension
                content_to_save = ""
                if file_path.endswith('.json') or self.show_raw_json_checkbox.isChecked():
                    # Save raw JSON (formatted if possible)
                    if self.raw_response:
                        try:
                            # Try to format as pretty JSON
                            lines = self.raw_response.strip().split('\n')
                            formatted_json = []
                            for line in lines:
                                if line.strip() and line.strip() != ',':
                                    try:
                                        if line.endswith(','):
                                            line = line[:-1]
                                        json_obj = json.loads(line)
                                        formatted_json.append(json.dumps(json_obj, indent=2))
                                    except:
                                        formatted_json.append(line)
                            content_to_save = "\n\n".join(formatted_json)
                        except:
                            content_to_save = self.raw_response
                    else:
                        content_to_save = self.parsed_response
                else:
                    # Save parsed plaintext
                    content_to_save = self.parsed_response
                # Add metadata header
                metadata = f"""# Generated by MEX - Model EXplorer
# Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# Model: {self.model_combo.currentText()}
# Query Length: {len(self.prompt_edit.toPlainText())} characters
# Response Length: {len(content_to_save)} characters
# Format: {'Raw JSON' if (file_path.endswith('.json') or self.show_raw_json_checkbox.isChecked()) else 'Parsed Text'}
{"="*50}
"""
                # Save the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    if not file_path.endswith('.json'):
                        f.write(metadata)
                    f.write(content_to_save)
                # Show success message
                file_size = os.path.getsize(file_path)
                size_kb = file_size / 1024
                self.show_message(f"Saved to {os.path.basename(file_path)} ({size_kb:.1f} KB)", "success")
                logging.info(f"Response saved to: {file_path}")
            except Exception as e:
                error_msg = f"Failed to save file: {str(e)}"
                self.show_message(error_msg, "error")
                logging.error(error_msg)
    def format_token_display(self, tokens):
        """Format token count for display (e.g., 1048576 -> 1M)"""
        if tokens >= 1000000:
            return f"{tokens/1000000:.1f}M"
        elif tokens >= 1000:
            return f"{tokens//1000}k"
        else:
            return str(tokens)
    def update_model_info(self):
        """Update model information display with accurate tooltip"""
        model_key = self.model_combo.currentData()
        if model_key:
            config = AVAILABLE_MODELS[model_key]
            self.current_model_config = config
            # Format the token display
            input_display = self.format_token_display(config['max_input_tokens'])
            output_display = self.format_token_display(config['max_output_tokens'])
            # Update the label to show input/output limits
            self.model_info.setText(f"{input_display}/{output_display} tokens")
            # Calculate approximate words and characters
            input_words = int(config['max_input_tokens'] * 0.75)
            output_words = int(config['max_output_tokens'] * 0.75)
            input_chars = config['max_input_tokens'] * 4 # Approximately 4 chars per token
            output_chars = config['max_output_tokens'] * 4
            # Get pricing info
            pricing = config.get("pricing", {"input": 0.001, "output": 0.002})
            # Set detailed tooltip
            tooltip_text = f"""
            <b>{config['display_name']}</b><br><br>
            <b>Input Token Limit:</b> {config['max_input_tokens']:,} tokens<br>
            ≈ {input_words:,} words or ~{input_chars:,} characters<br><br>
            <b>Output Token Limit:</b> {config['max_output_tokens']:,} tokens<br>
            ≈ {output_words:,} words or ~{output_chars:,} characters<br><br>
            <b>Fictional Pricing:</b><br>
            Input: ${pricing['input']:.3f} per 1K tokens<br>
            Output: ${pricing['output']:.3f} per 1K tokens<br><br>
            <b>Description:</b> {config.get('description', 'General purpose model')}<br><br>
            <i>Note: All pricing is fictional. Actual costs will vary.</i>
            """
            self.model_info.setToolTip(tooltip_text)
            # Update char count display to reflect current model's limit
            self.update_char_count()
    def update_char_count(self):
        """Update character and token counts with visual feedback"""
        count = len(self.prompt_edit.toPlainText())
        # Calculate approximate token count (1 token ≈ 4 characters)
        approx_tokens = count // 4
        # Update input labels
        self.input_char_count_label.setText(f"Input: {count:,} chars")
        self.input_token_count_label.setText(f"~{approx_tokens:,} tokens")
        # Get current model's max input tokens
        if self.current_model_config:
            max_tokens = self.current_model_config['max_input_tokens']
            # Calculate percentage based on token approximation
            percentage = (approx_tokens / max_tokens) * 100 if max_tokens > 0 else 0
            # Update colors based on usage
            if percentage > 95:
                char_color = COLORS['danger']
                token_bg = COLORS['error_bg']
            elif percentage > 80:
                char_color = COLORS['warning']
                token_bg = "#FEF3C7" if not theme_manager.is_dark_mode else "#78350F"
            else:
                char_color = COLORS['text_secondary']
                token_bg = COLORS['info_bg']
            self.input_char_count_label.setStyleSheet(f"""
                color: {char_color};
                font-size: {font_manager.base_size - 2}px;
                font-weight: 600;
                padding: 2px 6px;
                background-color: {COLORS['background']};
                border-radius: 3px;
            """)
            self.input_token_count_label.setStyleSheet(f"""
                color: {char_color if percentage > 80 else COLORS['primary']};
                font-size: {font_manager.base_size - 2}px;
                padding: 2px 6px;
                background-color: {token_bg};
                border-radius: 3px;
                font-weight: 600;
            """)
    def update_output_counts(self, text):
        """Update output character and token counts"""
        if text:
            char_count = len(text)
            token_count = char_count // 4 # Approximate tokens
            self.output_char_count_label.setText(f"Output: {char_count:,} chars")
            self.output_token_count_label.setText(f"~{token_count:,} tokens")
            self.output_char_count_label.setVisible(True)
            self.output_token_count_label.setVisible(True)
        else:
            self.output_char_count_label.setVisible(False)
            self.output_token_count_label.setVisible(False)
    def update_combo_style(self):
        """Update combo box style with current font size"""
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 6px 10px;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                font-size: {font_manager.base_size}px;
                font-weight: 500;
            }}
            QComboBox:hover {{
                border-color: {COLORS['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {COLORS['text_secondary']};
                margin-right: 4px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['primary']};
                selection-color: white;
            }}
        """)
    def update_prompt_style(self):
        """Update prompt edit style with current font size"""
        self.prompt_edit.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px;
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                font-size: {font_manager.base_size}px;
            }}
            QTextEdit:focus {{
                border-color: {COLORS['primary']};
            }}
        """)
    def update_status_style(self):
        """Update status label style with current font size"""
        self.status_label.setStyleSheet(f"""
            padding: 6px;
            border-radius: 4px;
            font-size: {font_manager.base_size}px;
            font-weight: 500;
        """)
    def update_font_sizes(self, size):
        """Update all font sizes in this tab"""
        # Update text editors
        self.prompt_edit.setFont(font_manager.get_font("mono"))
        # Recalculate height for 9 lines with new font size
        font_metrics = self.prompt_edit.fontMetrics()
        line_height = font_metrics.lineSpacing()
        nine_lines_height = line_height * 9 + 20 # 20px for padding
        self.prompt_edit.setMinimumHeight(nine_lines_height)
        # Update styles
        self.update_combo_style()
        self.update_prompt_style()
        self.update_status_style()
        # Update buttons
        if hasattr(self, 'generate_btn'):
            self.generate_btn.update_font_size(size)
            self.stop_btn.update_font_size(size)
            self.clear_btn.update_font_size(size)
            self.copy_btn.update_font_size(size)
            self.copy_output_btn.update_font_size(size)
            self.save_btn.update_font_size(size)
        # Update labels
        self.model_info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: {size - 2}px;")
        self.input_char_count_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {size - 2}px;
            padding: 2px 6px;
            background-color: {COLORS['background']};
            border-radius: 3px;
        """)
        self.update_response_display()
    def update_theme(self):
        """Update all colors when theme changes"""
        global COLORS
        COLORS = theme_manager.get_colors()
        # Update all styles
        self.update_combo_style()
        self.update_prompt_style()
        self.update_status_style()
        # Update buttons
        if hasattr(self, 'generate_btn'):
            self.generate_btn.update_theme()
            self.stop_btn.update_theme()
            self.clear_btn.update_theme()
            self.copy_btn.update_theme()
            self.copy_output_btn.update_theme()
            self.save_btn.update_theme()
        # Update labels and other elements
        self.update_char_count()
        self.update_output_counts(self.parsed_response)
        self.update_response_display()
    def toggle_response_format(self):
        """Toggle between raw JSON and parsed text display"""
        self.set_response_content()
    def generate_response(self):
        """Generate response with enhanced UX"""
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            self.show_message("Please enter a query", "warning")
            return
        # Check against model's input limit
        if self.current_model_config:
            max_chars = self.current_model_config['max_input_tokens'] * 4
            if len(prompt) > max_chars:
                self.show_message(f"Query exceeds maximum of {max_chars:,} characters for this model", "error")
                return
        model_key = self.model_combo.currentData()
        model_config = AVAILABLE_MODELS[model_key]
        # Start timing
        self.query_timer.start()
        self.start_time = datetime.now()
        # Update UI state
        self.generate_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.response_edit.setHtml('<html><body><p>Loading...</p></body></html>')
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.raw_response = ""
        self.parsed_response = ""
        self.parsed_html = ""
        self.save_btn.setEnabled(False)
        self.copy_output_btn.setEnabled(False)
        self.output_char_count_label.setVisible(False)
        self.output_token_count_label.setVisible(False)
        self.worker = APIWorker(model_config, prompt, self.credentials)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_response)
        self.worker.start()
    def on_progress(self, message, percentage):
        """Handle progress updates with animation"""
        self.response_info.setText(message)
        self.progress_bar.setValue(percentage)
    def on_response(self, response, error, raw_response, input_tokens, output_tokens):
        """Handle API response with timing and pricing"""
        # Restore UI state
        self.generate_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if error:
            self.show_message(f"Error: {error}", "error")
            self.response_info.setText("❌ Failed")
        else:
            elapsed = self.query_timer.elapsed() / 1000.0 # Convert to seconds
            # Store both raw and parsed responses
            self.raw_response = raw_response
            self.parsed_response = response
            # Enable save and copy buttons
            self.save_btn.setEnabled(True)
            self.copy_output_btn.setEnabled(True)
            # Display based on checkbox state
            self.parsed_html = self.markdown_to_html(response)
            self.set_response_content()
            # Update output counts
            self.update_output_counts(response)
            # Calculate actual pricing
            if self.current_model_config:
                pricing = self.current_model_config.get("pricing", {"input": 0.001, "output": 0.002})
                input_cost = (input_tokens / 1000) * pricing["input"]
                output_cost = (output_tokens / 1000) * pricing["output"]
                total_cost = input_cost + output_cost
                # Format price
                if total_cost < 0.01:
                    price_text = f"${total_cost:.4f}"
                else:
                    price_text = f"${total_cost:.2f}"
                self.response_info.setText(f"✅ {elapsed:.1f}s | {price_text} USD*")
                self.response_info.setToolTip(
                    f"Query completed in {elapsed:.1f} seconds\n"
                    f"Input: {input_tokens:,} tokens × ${pricing['input']:.3f}/1K = ${input_cost:.4f}\n"
                    f"Output: {output_tokens:,} tokens × ${pricing['output']:.3f}/1K = ${output_cost:.4f}\n"
                    f"Total: {price_text} USD\n\n"
                    f"*Fictional pricing for demonstration only"
                )
            else:
                self.response_info.setText(f"✅ {elapsed:.1f}s")
            # Ensure the response is visible by scrolling to top
            self.response_edit.page().runJavaScript("window.scrollTo(0,0);")
            self.show_message("Query executed successfully!", "success")
    def clear_all(self):
        """Clear all fields"""
        self.prompt_edit.clear()
        self.response_edit.setHtml('<html><body></body></html>')
        self.response_info.setText("")
        self.raw_response = ""
        self.parsed_response = ""
        self.parsed_html = ""
        self.save_btn.setEnabled(False)
        self.copy_output_btn.setEnabled(False)
        self.output_char_count_label.setVisible(False)
        self.output_token_count_label.setVisible(False)
        self.pricing_label.setVisible(False)
    def copy_response(self):
        """Copy query text with feedback"""
        query = self.prompt_edit.toPlainText()
        if query:
            QApplication.clipboard().setText(query)
            self.show_message(f"Query copied! ({len(query):,} characters)", "success")
        else:
            self.show_message("No query to copy", "warning")
    def show_message(self, message, msg_type="info"):
        """Show status message with appropriate styling"""
        self.status_label.setVisible(True)
        if msg_type == "success":
            icon = "✅"
            bg_color = COLORS['success_bg']
            text_color = "#065F46" if not theme_manager.is_dark_mode else "#A7F3D0"
        elif msg_type == "error":
            icon = "❌"
            bg_color = COLORS['error_bg']
            text_color = "#991B1B" if not theme_manager.is_dark_mode else "#FCA5A5"
        elif msg_type == "warning":
            icon = "⚠️"
            bg_color = "#FEF3C7" if not theme_manager.is_dark_mode else "#78350F"
            text_color = "#92400E" if not theme_manager.is_dark_mode else "#FDE68A"
        else:
            icon = "ℹ️"
            bg_color = COLORS['info_bg']
            text_color = "#1E40AF" if not theme_manager.is_dark_mode else "#93C5FD"
        self.status_label.setText(f"{icon} {message}")
        self.status_label.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            padding: 6px;
            border-radius: 4px;
            font-size: {font_manager.base_size}px;
            font-weight: 500;
        """)
        # Auto-hide after delay
        QTimer.singleShot(3000, lambda: self.status_label.setVisible(False))
class MainWindow(QMainWindow):
    """Enhanced main application window"""
    def __init__(self):
        super().__init__()
        self.credentials = None
        self.tabs = []
        self.sync_checkbox = None
        self.authenticate()
        self.init_ui()
    def authenticate(self):
        """Authenticate with Google Cloud"""
        try:
            self.credentials, project = default()
            logging.info(f"✅ Authenticated with credentials for project: {project}")
        except Exception as e:
            logging.error(f"❌ Authentication failed: {e}")
            QMessageBox.critical(None, "Authentication Error",
                                f"Failed to authenticate with Google Cloud:\n{str(e)}\n\n"
                                "Please ensure you have valid credentials set up.")
            sys.exit(1)
    def init_ui(self):
        """Initialize the enhanced UI"""
        self.setWindowTitle(f"MEX - Model EXplorer | Project: {PROJECT_ID}")
        self.setGeometry(100, 100, 1400, 900)
        # Set application style
        self.update_main_style()
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # Main layout with minimal margins
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(16, 16, 16, 16)
        # Compact Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        # Execute All and New Tab buttons
        self.generate_all_btn = AnimatedButton("⚡ Execute All", primary=True)
        self.generate_all_btn.clicked.connect(self.generate_all)
        self.add_tab_btn = AnimatedButton("+ New Tab")
        self.add_tab_btn.clicked.connect(lambda: self.add_new_tab(f"Query {len(self.tabs) + 1}"))
        # Add Execute All and New Tab buttons first (leftmost)
        header_layout.addWidget(self.generate_all_btn)
        header_layout.addWidget(self.add_tab_btn)
        # Add app title with project info
        app_title = QLabel(f"MEX - Model EXplorer")
        app_title.setFont(font_manager.get_font("heading"))
        app_title.setStyleSheet(f"color: {COLORS['text_primary']}; margin: 0 20px;")
        # Add project badge
        project_badge = QLabel(f"📁 {PROJECT_ID}")
        project_badge.setStyleSheet(f"""
            color: {COLORS['primary']};
            font-size: {font_manager.base_size - 1}px;
            font-weight: 600;
            padding: 4px 8px;
            background-color: {COLORS['info_bg']};
            border-radius: 4px;
        """)
        header_layout.addWidget(app_title)
        header_layout.addWidget(project_badge)
        header_layout.addStretch()
        # Dark/Light mode toggle button
        self.theme_btn = AnimatedButton("🌙 Dark" if not theme_manager.is_dark_mode else "☀️ Light")
        self.theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_btn)
        # About button
        self.about_btn = AnimatedButton("ℹ️ About")
        self.about_btn.clicked.connect(self.show_about_dialog)
        header_layout.addWidget(self.about_btn)
        # Font size control
        font_size_label = QLabel("Font Size:")
        font_size_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: {font_manager.base_size}px;")
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setMinimum(10)
        self.font_size_spinbox.setMaximum(20)
        self.font_size_spinbox.setValue(font_manager.base_size)
        self.font_size_spinbox.setSuffix("px")
        self.font_size_spinbox.setStyleSheet(f"""
            QSpinBox {{
                padding: 4px 8px;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                font-size: {font_manager.base_size}px;
                min-width: 70px;
            }}
            QSpinBox:hover {{
                border-color: {COLORS['primary']};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {COLORS['surface']};
                border: none;
            }}
            QSpinBox::up-arrow, QSpinBox::down-arrow {{
                color: {COLORS['text_secondary']};
            }}
        """)
        self.font_size_spinbox.valueChanged.connect(self.update_font_size)
        header_layout.addWidget(font_size_label)
        header_layout.addWidget(self.font_size_spinbox)
        # Sync checkbox
        self.sync_checkbox = QCheckBox("Sync queries")
        self.sync_checkbox.setFont(font_manager.get_font("body"))
        self.sync_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                font-size: {font_manager.base_size}px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['surface']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """)
        self.sync_checkbox.stateChanged.connect(self.sync_prompts_changed)
        header_layout.addWidget(self.sync_checkbox)
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        # Add initial tabs
        self.add_new_tab("Query 1")
        self.add_new_tab("Query 2")
        # Set the first tab as selected
        self.tab_widget.setCurrentIndex(0)
        # Add all to main layout
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.tab_widget, 1)
        central_widget.setLayout(main_layout)
    def toggle_theme(self):
        """Toggle between dark and light mode"""
        global COLORS
        COLORS = theme_manager.toggle_theme()
        # Update button text
        self.theme_btn.setText("🌙 Dark" if not theme_manager.is_dark_mode else "☀️ Light")
        # Update main window style
        self.update_main_style()
        # Update all tabs
        for tab in self.tabs:
            tab.update_theme()
        # Update all buttons
        self.generate_all_btn.update_theme()
        self.add_tab_btn.update_theme()
        self.theme_btn.update_theme()
        self.about_btn.update_theme()
        # Update other UI elements
        self.sync_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                font-size: {font_manager.base_size}px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['surface']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """)
        self.font_size_spinbox.setStyleSheet(f"""
            QSpinBox {{
                padding: 4px 8px;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                font-size: {font_manager.base_size}px;
                min-width: 70px;
            }}
            QSpinBox:hover {{
                border-color: {COLORS['primary']};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {COLORS['surface']};
                border: none;
            }}
            QSpinBox::up-arrow, QSpinBox::down-arrow {{
                color: {COLORS['text_secondary']};
            }}
        """)
    def update_main_style(self):
        """Update main window style"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {COLORS['surface']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_secondary']};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
                font-size: {font_manager.base_size}px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['primary']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLORS['background']};
            }}
            QTabBar::close-button {{
                image: none;
                width: 14px;
                height: 14px;
                border-radius: 7px;
                background-color: {COLORS['text_secondary']}22;
            }}
            QTabBar::close-button:hover {{
                background-color: {COLORS['danger']};
            }}
        """)
    def show_about_dialog(self):
        """Show the About dialog"""
        dialog = AboutDialog(self)
        dialog.exec()
    def update_font_size(self, size):
        """Update font size across the application"""
        font_manager.set_base_size(size)
        # Update all tabs
        for tab in self.tabs:
            tab.update_font_sizes(size)
        # Update main window components
        self.update_main_style()
        # Update buttons
        self.generate_all_btn.update_font_size(size)
        self.add_tab_btn.update_font_size(size)
        self.about_btn.update_font_size(size)
        self.theme_btn.update_font_size(size)
    def add_new_tab(self, name):
        """Add a new query tab with animation"""
        tab = QueryTab(name, self.credentials)
        self.tabs.append(tab)
        if self.sync_checkbox and self.sync_checkbox.isChecked():
            tab.prompt_edit.textChanged.connect(self.sync_prompts)
        index = self.tab_widget.addTab(tab, name)
        # Don't automatically switch to new tab when adding initial tabs
        # Only switch when user explicitly adds a new tab
        if len(self.tabs) > 2: # After initial tabs
            self.tab_widget.setCurrentIndex(index)
        self.tab_widget.setTabsClosable(self.tab_widget.count() > 1)
    def close_tab(self, index):
        """Close a tab with confirmation"""
        if self.tab_widget.count() > 1:
            tab = self.tabs[index]
            # Check if tab has content
            if tab.prompt_edit.toPlainText() or tab.parsed_response:
                reply = QMessageBox.question(self, "Close Tab",
                                            "This tab contains content. Are you sure you want to close it?",
                                            QMessageBox.StandardButton.Yes |
                                            QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self.tabs.remove(tab)
            self.tab_widget.removeTab(index)
            self.tab_widget.setTabsClosable(self.tab_widget.count() > 1)
    def sync_prompts_changed(self):
        """Handle sync checkbox state change"""
        if self.sync_checkbox.isChecked():
            # Connect all tabs
            for tab in self.tabs:
                tab.prompt_edit.textChanged.connect(self.sync_prompts)
            # Sync with current tab's content if it has any
            current_tab = self.tab_widget.currentWidget()
            if current_tab and current_tab.prompt_edit.toPlainText():
                self.sync_prompts_from_tab(current_tab)
        else:
            # Disconnect all tabs
            for tab in self.tabs:
                try:
                    tab.prompt_edit.textChanged.disconnect(self.sync_prompts)
                except:
                    pass
    def sync_prompts_from_tab(self, source_tab):
        """Sync prompts from a specific tab to all others"""
        if not self.sync_checkbox or not self.sync_checkbox.isChecked():
            return
        text = source_tab.prompt_edit.toPlainText()
        for tab in self.tabs:
            if tab != source_tab:
                tab.prompt_edit.blockSignals(True)
                tab.prompt_edit.setPlainText(text)
                tab.update_char_count()
                tab.update_pricing_estimate()
                tab.prompt_edit.blockSignals(False)
    def sync_prompts(self):
        """Sync queries across all tabs"""
        if not self.sync_checkbox or not self.sync_checkbox.isChecked():
            return
        sender = self.sender()
        if sender and hasattr(sender, 'toPlainText'):
            text = sender.toPlainText()
            for tab in self.tabs:
                if tab.prompt_edit != sender:
                    tab.prompt_edit.blockSignals(True)
                    tab.prompt_edit.setPlainText(text)
                    tab.update_char_count()
                    tab.update_pricing_estimate()
                    tab.prompt_edit.blockSignals(False)
    def generate_all(self):
        """Generate responses in all tabs"""
        has_prompt = False
        for tab in self.tabs:
            if tab.prompt_edit.toPlainText().strip():
                has_prompt = True
                tab.generate_response()
        if not has_prompt:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("No Query")
            msg.setText("Please enter a query in at least one tab")
            msg.exec()
def get_project_id():
    """Get the project ID from environment variable or user input"""
    global PROJECT_ID
    # First check if PROJECT_ID is set in environment
    env_project_id = os.environ.get("PROJECT_ID")
    if env_project_id:
        PROJECT_ID = env_project_id
        logging.info(f"Using PROJECT_ID from environment: {PROJECT_ID}")
        return
    # Try to get the default project from gcloud
    default_project = None
    try:
        credentials, default_project = default()
        logging.info(f"Default project from gcloud: {default_project}")
    except:
        pass
    # Create a temporary QApplication for the dialog
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        temp_app = True
    else:
        temp_app = False
    # Show dialog to get project ID
    dialog = ProjectIdDialog(None, default_project)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        PROJECT_ID = dialog.get_project_id()
        logging.info(f"Using PROJECT_ID from user input: {PROJECT_ID}")
    else:
        # User cancelled
        logging.error("No PROJECT_ID provided, exiting")
        sys.exit(0)
    # Clean up temporary app
    if temp_app:
        app.quit()
def main():
    # Get project ID before creating main application
    get_project_id()
    # Create main application
    app = QApplication(sys.argv)
    app.setApplicationName("MEX - Model EXplorer")
    app.setStyle("Fusion")
    # Set application palette for consistent theming
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["background"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text_primary"]))
    app.setPalette(palette)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
if __name__ == "__main__":
    main()
