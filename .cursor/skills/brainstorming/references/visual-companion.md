# Visual Companion Guide

Browser-based visual brainstorming companion for showing mockups, diagrams, and
options during design exploration.

In Cursor, the visual companion uses the `cursor-ide-browser` MCP server to
render and display visual content in the user's browser.

## Availability Check

Before using the visual companion, verify `cursor-ide-browser` MCP is
available. If the MCP server is not configured, not responding, or requires
re-authentication:

- **Not configured:** Do not offer the visual companion. Proceed with
  text-only brainstorming. If the user explicitly asks for visual content,
  explain: "`cursor-ide-browser` MCP is not configured in this project. Add it
  in Cursor MCP settings to enable the visual companion."
- **Auth required/expired:** Stop and instruct: "`cursor-ide-browser` MCP
  requires (re-)authentication. Authenticate in Cursor MCP settings and
  restart." Do not retry or silently degrade.
- **Unresponsive:** Stop and instruct: "`cursor-ide-browser` MCP is not
  responding. Check that the MCP server is running and restart if needed."

Only offer the visual companion when the MCP server is confirmed available.

## When to Use

Decide per-question, not per-session. The test: **would the user understand
this better by seeing it than reading it?**

**Use the browser** when the content itself is visual:

- **UI mockups** — wireframes, layouts, navigation structures, component designs
- **Architecture diagrams** — system components, data flow, relationship maps
- **Side-by-side visual comparisons** — comparing two layouts, two color schemes,
  two design directions
- **Design polish** — when the question is about look and feel, spacing, visual
  hierarchy
- **Spatial relationships** — state machines, flowcharts, entity relationships
  rendered as diagrams

**Use the chat** when the content is text or tabular:

- **Requirements and scope questions** — "what does X mean?", "which features
  are in scope?"
- **Conceptual A/B/C choices** — picking between approaches described in words
- **Tradeoff lists** — pros/cons, comparison tables
- **Technical decisions** — API design, data modeling, architectural approach
  selection
- **Clarifying questions** — anything where the answer is words, not a visual
  preference

A question *about* a UI topic is not automatically a visual question. "What
kind of wizard do you want?" is conceptual — use the chat. "Which of these
wizard layouts feels right?" is visual — use the browser.

## How It Works in Cursor

Use the `cursor-ide-browser` MCP tools to present visual content:

1. **Navigate** — use `browser_navigate` to open a local HTML file or data URL
   with your visual content
2. **Snapshot** — use `browser_snapshot` to verify the content renders correctly
3. **Screenshot** — use `browser_take_screenshot` for visual verification
4. **Interact** — the user can view and interact with the content in their
   browser; use `browser_snapshot` to read the current state

### Presenting Visual Options

To show mockups, layouts, or visual comparisons:

1. Write an HTML file to the project directory (e.g., under a temporary
   `.brainstorm/` directory) with the visual content
2. Use `browser_navigate` to open the file
3. Include clickable options so the user can indicate their preference
4. Read the page state with `browser_snapshot` after the user interacts

### Content Guidelines

- **Options layout**: Present choices as distinct clickable regions with clear
  labels (A, B, C)
- **Mockups**: Use HTML/CSS to create wireframe-quality representations — focus
  on layout and hierarchy, not pixel-perfect design
- **Diagrams**: Use SVG or CSS-based diagrams for architecture and flow
  visualizations
- **Comparisons**: Use side-by-side layouts (`display: flex` or CSS grid) to
  show alternatives

### Artifact Preservation

After brainstorming completes, relocate visual artifacts from `.brainstorm/`
to `docs/designs/` alongside the design doc:

1. Rename each artifact to match the design doc's date-topic stem:
   `YYYY-MM-DD-<topic>-<label>.html` (e.g., `2026-04-15-wizard-layout-comparison.html`)
2. Add relative-path references to each companion artifact in the design doc
   (e.g., `See [layout comparison](2026-04-15-wizard-layout-comparison.html)`)
3. Commit the relocated artifacts with the design doc
4. Remove the now-empty `.brainstorm/` directory
