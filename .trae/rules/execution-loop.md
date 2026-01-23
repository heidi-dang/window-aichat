# Autonomous Execution Loop

Whenever a task is assigned, you MUST follow this loop without user intervention:

1. **Analysis:** Scan the codebase to understand existing architecture.
2. **Plan:** State your multi-step plan in one concise block.
3. **Write:** Modify or create all necessary files.
4. **Environment:** If a library is missing, run the install command automatically.
5. **Verify:** Run the build/dev command. 
6. **Debug:** If the terminal output contains "Error", "Fail", or "Warning", immediately analyze the log and apply a fix. Repeat until the log is clear.
7. **Complete:** Only notify the user once the code is running and error-free.