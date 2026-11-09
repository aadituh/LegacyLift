# LegacyLift interface direction

This is an operating workspace for people inspecting COBOL modernization drafts. Preserve the original LegacyLift logo, navy/teal identity, account behavior, source content, saved runs and honest verification states.

## Tokens and layout

Palette: ink #172e44, navy #102a43, teal #087c88, paper #f5f7fa, border #dbe3eb; purple/blue/amber distinguish COPY/CALL/PERFORM. Dark mode uses the existing semantic tokens with tested contrast. Manrope carries interface text; JetBrains Mono identifies actual source code and filenames.

Use wide space for code comparisons. Reading and project-management surfaces use a narrower measure. Keep body explanations below about 75 characters per line. File actions stay beside their files. Supporting metadata is quieter than the next meaningful action.

```text
Upload:    project creation (compact when working)
           current project + file browser | next action + optional sample
           saved projects

Convert:   project context + source controls
           COBOL                 | Python draft
           dependency map (whole row, grouped branches)
           review notes          | output checks
           AI findings (whole row, selected file expanded)

Graph:                 current program
                  /          |          \
             COPY group   CALL group   PERFORM group
             definitions  programs     local routines
```

The distinguishing element is the source-to-dependency map: three explicit branches, readable grouped file lists, and an inspector linking each reference back to original source. Avoid a wrapped grid that implies connections between targets.

## Motion and interaction

Use Motion's lightweight React features for navigation/selection indicators, short route fades and guide/inspector reveals. Default 160–200 ms; animate opacity and small transforms. Respect reduced motion, provide immediate states, never loop decorative graph edges or animate code while it is being edited. Native keyboard controls, focus restoration and source locations remain functional without animation.

## Research applied

- Vercel web interface guidelines: https://github.com/vercel-labs/web-interface-guidelines
- Linear's interface refresh: https://linear.app/now/behind-the-latest-design-refresh
- Motion accessibility: https://motion.dev/docs/react-accessibility
- React Flow layout guidance: https://reactflow.dev/learn/layouting/layouting
- IBM COBOL program structure: https://developer.ibm.com/tutorials/my-first-cobol-app/
- Python control-flow tutorial: https://docs.python.org/3/tutorial/controlflow.html

This is a refinement of an established product; the graph and guidance are purpose-built, while typography and branding remain familiar.
