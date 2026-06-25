# History Scrub Prep

Use this toolkit to prepare a sensitive-data history rewrite without ever
committing the replacement manifest itself.

## Files

- `replacements.template.tsv`
  - Safe template for the local replacement manifest.
- `*.local.*`
  - Local working files only. These are gitignored.
- `reports/`
  - Optional local output directory for inventory reports. Also gitignored.

## Recommended Flow

1. Rotate any still-live credentials before rewriting history.
2. Generate a hashed inventory report:

   ```bash
   python3 scripts/history_scrub_inventory.py \
     --output security/history-scrub/history-scan.local.json
   ```

3. Create a local manifest from the template:

   ```bash
   cp security/history-scrub/replacements.template.tsv \
      security/history-scrub/replacements.local.tsv
   ```

4. Fill `replacements.local.tsv` with the exact old secret values that need to
   be removed and either the rotated replacement value or `***REMOVED***`.
5. Build the `git filter-repo` expressions file:

   ```bash
   python3 scripts/build_filter_repo_replace_text.py \
     --input security/history-scrub/replacements.local.tsv \
     --output security/history-scrub/filter-repo-replace.local.txt
   ```

6. Run the rewrite in a fresh mirror clone, not in the working checkout:

   ```bash
   git clone --mirror --no-local . ../organizing-life-services-ai-history-scrub.git
   cd ../organizing-life-services-ai-history-scrub.git
   git filter-repo \
     --sensitive-data-removal \
     --replace-text /absolute/path/to/security/history-scrub/filter-repo-replace.local.txt
   ```

7. Verify the rewritten clone with `gitleaks` and spot checks before force
   pushing updated refs.
8. After the rewrite is published, every old clone must be re-cloned or hard
   reset before anyone resumes work.

## Notes

- Keep the replacement manifest local. It contains the sensitive values that
  you are trying to purge from history.
- The inventory script records only hashes, lengths, file paths, and line
  numbers of suspected matches. It does not write raw secret values.
- Archived raw conversation exports can be scanned with the inventory script;
  it transparently reads `.gz` text files.

## Reference

- Official `git filter-repo` docs:
  https://github.com/newren/git-filter-repo/blob/main/Documentation/git-filter-repo.txt
