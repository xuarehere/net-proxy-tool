# Implementation Plan: competition-material

- [x] 1. Write `tools/demo.py`
  - A temporary configuration, the local observation gateway, one request and the connections it saw
  - A local origin as the fallback when the network is unavailable
  - One narrated line per step
  - _Requirements: 1.1–1.5_

- [x] 2. Write the Devpost entry
  - The description, the facts and the honest four-stage timeline
  - The links, the screenshots and the environment notes
  - _Requirements: 2.1–2.3, 3.4–3.5_

- [x] 3. Write the video script, the social post, the blog draft and the checklist
  - The script names every screen and every expected result
  - The checklist separates the automated work from the maintainer's remaining steps
  - _Requirements: 3.1–3.5_

- [x] 4. Validate and commit Task 15 (commit `543c74e`)
  - [x] 4.1 Run the demo and confirm it leaves nothing behind (`LocalGateway.live_count()` is 0 afterwards)
  - [x] 4.2 Run the full suite, the stdlib check and the secret scans
  - [x] 4.3 Create one local commit for `tools/demo.py` and the specification; the drafts stay in `scratch/`
  - _Requirements: 1.1–1.5, 4.1–4.5_
