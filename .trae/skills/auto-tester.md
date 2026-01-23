# Skill: Auto-Tester
**Description:** Use this skill whenever code is modified to ensure zero regressions.

## Instructions
1. **Identify Tests:** Scan the project for existing test suites (Jest, Vitest, PyTest, etc.).
2. **Execute:** If tests exist, run them immediately after a code change using the terminal.
3. **Draft Tests:** If no tests exist for the new logic, create a `.test` file automatically.
4. **Loop on Failure:** If a test fails, do not report back to the user. Read the stack trace, apply a fix to the source code, and re-run the tests.
5. **Success Criteria:** Only stop when all relevant tests pass with 100% success.