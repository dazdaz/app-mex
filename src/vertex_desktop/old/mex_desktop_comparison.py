#!/usr/bin/env python3

import sys
import os
import logging
import json
import requests
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QTextEdit, QComboBox, QLabel,
                             QSplitter, QCheckBox, QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QPalette, QColor
from google.auth import default
from google.auth.transport.requests import Request

# --- CONFIGURATION ---
PROJECT_ID = os.environ.get("PROJECT_ID", "daev-playground")
LOCATION = os.environ.get("LOCATION", "global")
MAX_PROMPT_LENGTH = 32000
VERTEX_AI_ENDPOINT = "https://aiplatform.googleapis.com"

# --- LOGGING SETUP ---
log_dir = Path.home() / ".vertex-desktop-app"
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

# --- MODEL CONFIGURATION ---
AVAILABLE_MODELS = {
    "claude-3-7-sonnet": {
        "publisher": "anthropic",
        "model_id": "claude-3-7-sonnet@20250219:streamRawPredict",
        "display_name": "Claude 3.7 Sonnet",
        "max_tokens": 32000
    },
    "claude-opus-4-1": {
        "publisher": "anthropic",
        "model_id": "claude-opus-4-1@20250805:streamRawPredict",
        "display_name": "Claude 4.1 Opus",
        "max_tokens": 32000
    },
    "gemini-2-5-pro": {
        "publisher": "google",
        "model_id": "gemini-2.5-pro@default:streamGenerateContent",
        "display_name": "Gemini 2.5 Pro",
        "max_tokens": 32000
    },
    "gemini-2-5-flash": {
        "publisher": "google",
        "model_id": "gemini-2.5-flash@default:streamGenerateContent",
        "display_name": "Gemini 2.5 Flash",
        "max_tokens": 32000
    }
}

class APIWorker(QThread):
    """Worker thread for API calls"""
    finished = pyqtSignal(str, str)  # response, error
    progress = pyqtSignal(str)
    
    def __init__(self, model_config, prompt, credentials):
        super().__init__()
        self.model_config = model_config
        self.prompt = prompt
        self.credentials = credentials
        
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
                "max_tokens": self.model_config["max_tokens"],
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
        """Parse Google's streaming format."""
        full_text = ""
        for line in response_text.strip().split('\n'):
            if line.strip():
                try:
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
                if "data:" in response_text:
                    return self.parse_anthropic_stream(response_text)
                elif response_data and isinstance(response_data, dict):
                    if "content" in response_data:
                        if isinstance(response_data["content"], list) and len(response_data["content"]) > 0:
                            return response_data["content"][0].get("text", "")
                return response_text
            elif self.model_config["publisher"] == "google":
                if '\n' in response_text and '{' in response_text:
                    return self.parse_google_stream(response_text)
                if response_data and "candidates" in response_data:
                    candidates = response_data["candidates"]
                    if candidates and len(candidates) > 0:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts and len(parts) > 0:
                            return parts[0].get("text", "")
                return response_text
            else:
                return response_text
        except Exception as e:
            logging.error(f"Error parsing response: {e}")
            return f"Error parsing response: {str(e)}\n\nRaw response:\n{response_text[:1000]}"
    
    def run(self):
        """Run the API call in a separate thread"""
        try:
            self.progress.emit("Getting access token...")
            access_token = self.get_access_token()
            
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
            
            self.progress.emit("Calling API...")
            response = requests.post(url, headers=headers, json=payload, timeout=60, stream=True)
            
            if response.status_code != 200:
                self.finished.emit("", f"API call failed with status {response.status_code}: {response.text}")
                return
            
            response_text = response.text
            response_data = None
            try:
                if not response_text.startswith('data:'):
                    response_data = json.loads(response_text)
            except json.JSONDecodeError:
                pass
            
            parsed_response = self.parse_response(response_text, response_data)
            self.finished.emit(parsed_response, "")
            
        except Exception as e:
            self.finished.emit("", str(e))

class ModelPanel(QWidget):
    """Individual model panel widget"""
    def __init__(self, panel_num, credentials, parent=None):
        super().__init__(parent)
        self.panel_num = panel_num
        self.credentials = credentials
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"Model {self.panel_num}")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        self.model_combo = QComboBox()
        for key, config in AVAILABLE_MODELS.items():
            self.model_combo.addItem(config["display_name"], key)
        if self.panel_num == 2:
            self.model_combo.setCurrentIndex(1)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.model_combo)
        
        # Prompt area
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Enter your prompt here...")
        self.prompt_edit.setMaximumHeight(150)
        self.prompt_edit.textChanged.connect(self.update_char_count)
        
        self.char_count_label = QLabel("0 / 32,000 characters")
        self.char_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self.generate_response)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_all)
        self.copy_btn = QPushButton("Copy Response")
        self.copy_btn.clicked.connect(self.copy_response)
        
        button_layout.addWidget(self.generate_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.copy_btn)
        
        # Response area
        self.response_label = QLabel("Response:")
        self.response_label.setStyleSheet("font-weight: bold;")
        self.response_info = QLabel("")
        
        response_header = QHBoxLayout()
        response_header.addWidget(self.response_label)
        response_header.addStretch()
        response_header.addWidget(self.response_info)
        
        self.response_edit = QTextEdit()
        self.response_edit.setReadOnly(True)
        self.response_edit.setPlaceholderText("Response will appear here...")
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        
        # Add all to layout
        layout.addLayout(header_layout)
        layout.addWidget(self.prompt_edit)
        layout.addWidget(self.char_count_label)
        layout.addLayout(button_layout)
        layout.addLayout(response_header)
        layout.addWidget(self.response_edit)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def update_char_count(self):
        """Update character count label"""
        count = len(self.prompt_edit.toPlainText())
        self.char_count_label.setText(f"{count} / {MAX_PROMPT_LENGTH} characters")
        
        if count > MAX_PROMPT_LENGTH:
            self.char_count_label.setStyleSheet("color: red;")
        elif count > MAX_PROMPT_LENGTH * 0.9:
            self.char_count_label.setStyleSheet("color: orange;")
        else:
            self.char_count_label.setStyleSheet("color: black;")
    
    def generate_response(self):
        """Generate response from API"""
        prompt = self.prompt_edit.toPlainText().strip()
        
        if not prompt:
            self.show_error("Please enter a prompt")
            return
        
        if len(prompt) > MAX_PROMPT_LENGTH:
            self.show_error(f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters")
            return
        
        model_key = self.model_combo.currentData()
        model_config = AVAILABLE_MODELS[model_key]
        
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("Generating...")
        self.response_edit.clear()
        self.response_info.setText("Generating...")
        self.status_label.setText("")
        
        self.worker = APIWorker(model_config, prompt, self.credentials)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_response)
        self.worker.start()
    
    def on_progress(self, message):
        """Handle progress updates"""
        self.response_info.setText(message)
    
    def on_response(self, response, error):
        """Handle API response"""
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate")
        
        if error:
            self.show_error(error)
            self.response_info.setText("Error")
        else:
            self.response_edit.setPlainText(response)
            model_name = self.model_combo.currentText()
            self.response_info.setText(f"{model_name} - Complete")
            self.show_success("Response generated successfully!")
    
    def clear_all(self):
        """Clear all fields"""
        self.prompt_edit.clear()
        self.response_edit.clear()
        self.status_label.setText("")
        self.response_info.setText("")
    
    def copy_response(self):
        """Copy response to clipboard"""
        response = self.response_edit.toPlainText()
        if response:
            QApplication.clipboard().setText(response)
            self.show_success("Response copied to clipboard!")
    
    def show_error(self, message):
        """Show error message"""
        self.status_label.setStyleSheet("color: red; background-color: #ffebee; padding: 5px;")
        self.status_label.setText(f"Error: {message}")
        QTimer.singleShot(5000, lambda: self.status_label.setText(""))
    
    def show_success(self, message):
        """Show success message"""
        self.status_label.setStyleSheet("color: green; background-color: #e8f5e9; padding: 5px;")
        self.status_label.setText(message)
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.credentials = None
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
        """Initialize the UI"""
        self.setWindowTitle("🤖 Vertex AI Desktop Client - Dual Model Comparison")
        self.setGeometry(100, 100, 1400, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title = QLabel("🤖 Dual Model Comparison Tool")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        main_layout.addWidget(title)
        
        # Sync controls
        sync_layout = QHBoxLayout()
        self.sync_checkbox = QCheckBox("Sync prompts (type in one, appears in both)")
        self.sync_checkbox.setChecked(True)
        
        self.generate_both_btn = QPushButton("Generate Both Responses")
        self.generate_both_btn.clicked.connect(self.generate_both)
        
        sync_layout.addWidget(self.sync_checkbox)
        sync_layout.addStretch()
        sync_layout.addWidget(self.generate_both_btn)
        
        sync_group = QGroupBox()
        sync_group.setLayout(sync_layout)
        main_layout.addWidget(sync_group)
        
        # Create panels
        panels_layout = QHBoxLayout()
        self.panel1 = ModelPanel(1, self.credentials)
        self.panel2 = ModelPanel(2, self.credentials)
        
        # Connect sync functionality
        self.panel1.prompt_edit.textChanged.connect(self.sync_prompts)
        self.panel2.prompt_edit.textChanged.connect(self.sync_prompts)
        
        # Use splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.panel1)
        splitter.addWidget(self.panel2)
        splitter.setSizes([700, 700])
        
        panels_layout.addWidget(splitter)
        main_layout.addLayout(panels_layout)
        
        central_widget.setLayout(main_layout)
        
        # Apply stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Monaco', 'Courier New', monospace;
            }
            QComboBox {
                padding: 5px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
            }
            QGroupBox {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
                margin: 5px;
            }
        """)
    
    def sync_prompts(self):
        """Sync prompts between panels if enabled"""
        if not self.sync_checkbox.isChecked():
            return
        
        sender = self.sender()
        if sender == self.panel1.prompt_edit:
            text = self.panel1.prompt_edit.toPlainText()
            if self.panel2.prompt_edit.toPlainText() != text:
                self.panel2.prompt_edit.blockSignals(True)
                self.panel2.prompt_edit.setPlainText(text)
                self.panel2.update_char_count()
                self.panel2.prompt_edit.blockSignals(False)
        elif sender == self.panel2.prompt_edit:
            text = self.panel2.prompt_edit.toPlainText()
            if self.panel1.prompt_edit.toPlainText() != text:
                self.panel1.prompt_edit.blockSignals(True)
                self.panel1.prompt_edit.setPlainText(text)
                self.panel1.update_char_count()
                self.panel1.prompt_edit.blockSignals(False)
    
    def generate_both(self):
        """Generate responses for both panels"""
        prompt1 = self.panel1.prompt_edit.toPlainText().strip()
        prompt2 = self.panel2.prompt_edit.toPlainText().strip()
        
        if not prompt1 and not prompt2:
            QMessageBox.warning(self, "Warning", "Please enter at least one prompt")
            return
        
        if prompt1:
            self.panel1.generate_response()
        if prompt2:
            self.panel2.generate_response()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Vertex AI Desktop Client")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
