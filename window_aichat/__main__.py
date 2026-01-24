import argparse
import sys
import os

def validate_environment():
    """Check for required environment variables/configuration."""
    try:
        from window_aichat.config import SecureConfig
        # Use a default config path or one relative to user home, similar to app logic
        config_dir = os.path.join(os.path.expanduser("~"), ".aichatdesktop")
        config_path = os.path.join(config_dir, "config.json")
        
        config = SecureConfig(config_path)
        config.validate_keys()
        print("Environment validation passed.")
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please configure your API keys in the settings or .env file.")
        # We don't exit here because the user might be launching the desktop app to configure settings
    except Exception as e:
        print(f"Warning during environment validation: {e}")

def run_desktop():
    """Run the Desktop UI application."""
    validate_environment()
    try:
        from window_aichat.desktop.app import main
        main()
    except ImportError as e:
        print(f"Error starting Desktop UI: {e}")
        sys.exit(1)

def run_server(host="127.0.0.1", port=8000, reload=False):
    """Run the FastAPI backend server."""
    validate_environment()
    try:
        import uvicorn
        # Run uvicorn programmatically
        uvicorn.run("window_aichat.api.server:app", host=host, port=port, reload=reload)
    except ImportError as e:
        print(f"Error starting Server: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Window AI Chat Application")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Desktop command
    desktop_parser = subparsers.add_parser("desktop", help="Run the Desktop UI")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Run the Backend API Server")
    server_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    if args.command == "server":
        print(f"Starting server on {args.host}:{args.port}...")
        run_server(host=args.host, port=args.port, reload=args.reload)
    elif args.command == "desktop":
        print("Starting Desktop UI...")
        run_desktop()
    else:
        # Default behavior if no arguments provided
        if len(sys.argv) == 1:
            print("No command specified, defaulting to Desktop UI...")
            run_desktop()
        else:
            parser.print_help()

if __name__ == "__main__":
    main()
