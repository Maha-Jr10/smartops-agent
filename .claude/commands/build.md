Build phase $ARGUMENTS of the project ("all" means phases 1 to 5 in order).

For each phase N:
1. Read only `.claude/phases/phase-N.md` and the files it names.
2. Create a task list from it and work through it.
3. Run the test-runner agent (`make ci`), then the reviewer agent on the diff. Fix what they report.
4. Tick the phase in README "Avancement", commit with a conventional commit message.
5. Move to the next phase without asking, unless you need a secret, a decision only we can make, or the spec contradicts itself. Then stop and ask one question.

At the very end, run `.claude/phases/final-check.md`.
