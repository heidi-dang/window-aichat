# Skill: Dependency Manager
**Description:** Handles environment setup and library installation automatically.

## Instructions
1. **Pre-emptive Check:** Before writing code that uses a new library, check `package.json` or `requirements.txt`.
2. **Auto-Install:** If a library is missing, execute the install command (e.g., `npm install <pkg>` or `pip install <pkg>`) in the terminal.
3. **Version Matching:** Always install versions compatible with the existing project dependencies.
4. **Verification:** After installation, run a quick build check to ensure the environment is still stable.