# Requirements Document: competition-material

## Introduction

The Kiroween entry needs material a reviewer can read and a demo a reviewer can watch. The material must describe what the tool does, show that it works, and tell the truth about how it was built.

## Requirements

### Requirement 1: A demo that runs without preparation

**User Story:** As a reviewer, I want one command that shows the whole flow, so that I can see the tool work in a minute.

#### Acceptance Criteria

1. THE repository SHALL provide `tools/demo.py`.
2. THE demo SHALL start the local observation gateway, save it as a gateway, send a request through it and show the connections it saw.
3. THE demo SHALL work without an existing proxy, and SHALL fall back to a local origin when the network is unavailable.
4. THE demo SHALL use a temporary configuration and SHALL NOT change the configuration of the operator.
5. THE demo SHALL print one narrated step per action, so that a recording can follow it.

### Requirement 2: An honest story

**User Story:** As a reviewer, I want to know how the project was actually built, so that I can judge the work.

#### Acceptance Criteria

1. THE Devpost write-up SHALL name the four stages of the work: Antigravity for the base versions, Codex for v1.4.0 to v1.4.3, Kiro for the specifications and the safety work, and Claude Code for the v1.5.0 features.
2. THE write-up SHALL NOT claim that one tool did everything.
3. THE write-up SHALL describe the measurable facts: the test count, the platforms, the zero runtime dependencies and the proxy isolation.

### Requirement 3: The submission set

**User Story:** As the maintainer, I want every document the submission needs in one place, so that nothing is forgotten.

#### Acceptance Criteria

1. `scratch/kiroween/` SHALL hold the Devpost write-up, the video script, the social post, the blog draft and the submission checklist.
2. The video script SHALL name every screen and every command in order, with the expected result.
3. The checklist SHALL separate what the automation produced from what the maintainer still has to do, and SHALL list the items that need a person: the Devpost account, the recording, the push, the pull request, the tag and the release.
4. None of the material SHALL contain a real address, a host name, an account name or a token.
5. The material SHALL be written in English, with a Chinese outline where the submission expects it.

## Testing strategy

`tools/demo.py` is exercised by running it: it must finish with a reported result and leave no listener behind. The documents are reviewed by reading them against the checklist.
