# Requirements Document: console-i18n

## Introduction

The console speaks Chinese today. v1.5.0 adds English: a browser that does not ask for Chinese gets English, and a toggle in the top bar switches the language at any time. The catalogue lives in one place, so the console and the API cannot drift apart.

## Glossary

- **Catalogue**: the table of message keys with their English and Simplified Chinese texts.
- **Key**: the stable name of one message, used by the page and by the script.
- **Language header**: the `X-NPT-Language` header that the browser sends with its API requests.

## Requirements

### Requirement 1: One catalogue for both languages

**User Story:** As a maintainer, I want one place that holds every message in both languages, so that a missing translation is a test failure and not a surprise.

#### Acceptance Criteria

1. THE repository SHALL provide `web/messages.py` with every message in English and Simplified Chinese.
2. EVERY key SHALL exist in both languages; a key may carry an empty text in one language only when the text is a separator.
3. THE catalogue SHALL be built from the sources in `tools/i18n/`, and the build SHALL fail when a key is missing in one language.
4. THE catalogue SHALL be checked by the test suite: every `data-i18n` key of the page and every translated call of the script must exist in it.

### Requirement 2: The browser chooses the language

**User Story:** As a user, I want the console in my language, so that I can read it without a translator.

#### Acceptance Criteria

1. WHEN the browser stored a language, THE Console SHALL use it.
2. OTHERWISE, WHEN the browser asks for a `zh` language, THE Console SHALL use Simplified Chinese, and for any other language it SHALL use English.
3. THE Console SHALL offer a toggle in the top bar that switches the language and remembers the choice.
4. THE Console SHALL set the `lang` attribute of the document to the language in use.
5. A browser whose storage is blocked SHALL still show the console.

### Requirement 3: Every visible text follows the language

**User Story:** As a user, I want no Chinese text left in the English console, so that the interface reads as one language.

#### Acceptance Criteria

1. EVERY static text of the page SHALL carry a `data-i18n` key.
2. EVERY text that the script builds SHALL come from the catalogue.
3. WHEN the language changes, THE Console SHALL re-render the tables, so that the dynamic text follows it.

### Requirement 4: The API answers in the language of the request

**User Story:** As an agent, I want the error messages in the language I asked for, so that my report reads as one language.

#### Acceptance Criteria

1. THE browser SHALL send the `X-NPT-Language` header with its API requests.
2. THE Console SHALL localize the `error` and `message` fields of an answer.
3. A message that the catalogue does not know SHALL be returned unchanged.
4. The error codes and the field names SHALL stay in English.

### Requirement 5: Tests

**User Story:** As a maintainer, I want the languages covered, so that a new message cannot be added in one language only.

#### Acceptance Criteria

1. THE test suite SHALL check that every key exists in both languages, that every marked element and every translated call is known, and that the API localizes its answers.
2. `packaging/test_browser_i18n.py` SHALL check both languages and the toggle in Chromium.
3. The browser checks that name Chinese text SHALL pin the Chinese language, so that they keep testing what they mean to test.
