# AI Chat Desktop

A lightweight Windows application to chat with **Gemini 2.0 Flash** and **DeepSeek** simultaneously. Compare answers from two of the world's leading AI models in one interface.

## 🚀 Quick Start
1. **Install Python**: Ensure you have Python 3.8+ installed.
2. **Setup**: Double-click `install_dependencies.cmd` to install required libraries.
3. **Run**: Launch `run_app.bat` or run `python main.py` directly.

## 🛠️ How to Build (.EXE)
If you want to create a standalone executable that works without Python:
1. Double-click `build_app.cmd`.
2. Wait for the process to finish.
3. Open the newly created `dist` folder.
4. Your application is ready as `AIChatDesktop.exe`.

## 🔑 Configuration
Go to **Settings** within the app to enter your API keys:
- **Gemini Key**: [Get it here](https://aistudio.google.com/app/apikey)
- **DeepSeek Key**: [Get it here](https://platform.deepseek.com/)

## 📝 Features
- **Dual Chat**: Send one prompt and see both Gemini and DeepSeek respond side-by-side.
- **One-Click Build**: Optimized automation scripts included for easy deployment.
- **Status Indicators**: Real-time visual feedback on whether your API keys are active.
- **Export**: Save your conversations for later review.

## 📦 Requirements
- Windows 10/11
- Python 3.8 or higher
- `google-generativeai`, `requests`, `pyinstaller` (installed via the .cmd script)# window-aichat
