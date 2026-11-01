Add a new tool named $ARGUMENTS following docs/specs/outils.md:
1. Pydantic input and output models, typed errors.
2. Register its permissions in configs/policies.yaml (least privilege).
3. Unit tests for success, each error, and permission denial.
4. Update docs/specs/outils.md.
Then use the test-runner agent. Report changed files only.
