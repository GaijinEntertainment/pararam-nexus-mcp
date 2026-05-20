# Pararam Message Formatting Reference

Use this reference when composing text for `send_message` or `edit_post`.

## Core Rules For Agents

- Do not use Markdown headings (`#`, `##`, `###`). Pararam does not support them.
- Use `**bold**` section titles instead of headings.
- Prefer plain bullets or numbered lists for structure.
- Keep tool descriptions concise; use the `pararam://formatting` MCP resource only when the task needs details.

## Mentions

- `@user` mentions a user.
- `@@role` mentions a role.
- `@all` mentions all users in the chat.
- `@online` mentions online users.
- `@admin` mentions all admins.
- `@groups` mentions all roles.

Use `@all`, `@online`, `@admin`, and `@groups` only when the user explicitly asks to notify everyone,
online users, chat admins, or groups/roles. Prefer targeted user or role mentions otherwise.
Before sending any message with `@all`, `@online`, `@admin`, or `@groups`, ask the user for explicit confirmation.

## Hashtags And Alerts

- `#example` creates a hashtag.
- `#eta` creates a reminder.
- `#shareedit` enables collaborative editing for the post.
- `#snd_call`, `#snd_ok`, `#snd_fail`, and `#snd_silent` choose the notification sound.

## Links, Tooltips, And Colors

- Markdown-style link: `[label](https://example.com)`.
- Tooltip: `[visible text](tooltip text)`.
- Colored text: `[#RRGGBB](text)` or `[#red](text)`.
- Colored bullet: `[#2E7D32](●)`.
- Phone link: `[#tel](+7 952 67 47 180)`.

## Quotes, Code, And Inline Code

- One-line quote: `> quoted text`.
- Inline code or inline monospace: `` `text` ``.
- Multiline block or code fence: start a separate line with three backticks.
- For syntax highlighting, use a language after the opening backticks, for example ` ```python `.

## Tables

Tables are supported with Markdown table syntax. Keep them simple.
Colors may not render inside table cells, so do not rely on colored markers in tables.

## Checkboxes And Spoilers

- Empty checkbox: `[ ](task text)`.
- Checked checkbox: `[x](task text)`.
- Spoiler: `[#spoiler](hidden text)`.

## Attach Long Text

To send text as an attachment, start a line with `/paste filename`.
