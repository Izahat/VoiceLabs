# VoiceLabs — Design System & Redesign Specification

**Status:** design specification only. No application code is changed by this document.

**Product direction:** Premium Modern AI Voice Studio

## Scope and product constraints

VoiceLabs is a local-first voice workspace for three active jobs:

1. **Voice Design:** create speech from text using voice attributes.
2. **Voice Cloning:** create a voice profile from audio, video, or a microphone recording, then synthesize text with it.
3. **Transcription:** turn an audio/video file or supported URL into text with timestamps.

The redesign must preserve the existing working controls and API behavior: file upload, URL input, microphone recording, language selection, voice parameters, text input, synthesis, transcription, copy, download, theme selection, interface language selection, and persisted jobs/assets.

These features are not active and must not be presented as available actions:

- Gemini or other text translation.
- Automatic video dubbing.
- Speaker diarization.

They may appear only in a clearly labelled roadmap or “planned” area. They must not appear as active tabs, active buttons, progress stages, or enabled form controls.

The visual system is designed for a desktop-first SaaS workspace, while every workflow must remain usable on a narrow mobile screen.

## 1. Product visual identity

### Brand idea

VoiceLabs should feel like a focused professional studio for shaping, recording, and inspecting voice. It should communicate precision, calm control, local processing, and high-quality output.

### Brand attributes

- **Premium:** deliberate spacing, restrained surfaces, precise typography, confident controls.
- **Technical but human:** model/runtime information is available, but never dominates the creative task.
- **Local-first:** make privacy and local processing visible and reassuring.
- **Focused:** one clear primary action per workflow.
- **Quietly expressive:** use waveform and audio details as the expressive layer instead of decorative gradients.

### Avoid

- Emoji as interface icons.
- Neon glow, heavy gradients, glassmorphism, and excessive blur.
- Generic “AI magic” copy.
- Multiple competing primary buttons.
- Unavailable features shown beside active features.
- Every section wrapped in an identical card.

### Voice and copy

Use direct, calm, action-oriented copy:

- “Describe the voice” rather than “Voice Design Parameters”.
- “Choose a reference” rather than “Upload Audio or Video for Cloning”.
- “Start transcription” rather than “Start Transcription” everywhere in uppercase.
- “Preparing the model…” when weights are being loaded.
- “Your file stays in this local workspace” where local processing is relevant.

Headings use sentence case. Uppercase is reserved for small eyebrow labels and metadata, not primary section titles.

## 2. Color system

Use semantic tokens so components never depend directly on a raw hex value. Dark mode is the strongest visual experience; light mode uses the same structure and contrast hierarchy rather than being a separate design.

### Dark theme tokens

| Token | Value | Use |
|---|---|---|
| color-bg | #0B0D10 | Application background |
| color-bg-subtle | #101318 | Secondary background, tab rail |
| color-surface | #171B21 | Main panels and cards |
| color-surface-raised | #1D232B | Modal, popover, selected surface |
| color-surface-hover | #242B35 | Hover and active surface |
| color-border | #2A323D | Default borders |
| color-border-strong | #3A4552 | Focus-adjacent and emphasized borders |
| color-text | #F5F7FA | Primary text |
| color-text-muted | #B3BBC7 | Secondary text |
| color-text-subtle | #808A99 | Hints, metadata, inactive labels |
| color-accent | #A994FF | Accent text and selected states |
| color-accent-strong | #805FE8 | Primary button background |
| color-accent-hover | #9072F2 | Primary button hover |
| color-accent-soft | rgba(169, 148, 255, 0.12) | Selected background |
| color-focus | #C9BCFF | Keyboard focus ring |
| color-success | #36D399 | Completed states |
| color-warning | #F5C451 | Cautions and model preparation |
| color-danger | #F27786 | Errors and destructive actions |
| color-info | #69A8F9 | Informational states |

### Light theme tokens

| Token | Value | Use |
|---|---|---|
| color-bg | #F6F7F9 | Application background |
| color-bg-subtle | #EEF0F4 | Secondary background, tab rail |
| color-surface | #FFFFFF | Main panels and cards |
| color-surface-raised | #FFFFFF | Modal and selected surface |
| color-surface-hover | #F2F0FA | Hover and active surface |
| color-border | #E1E5EB | Default borders |
| color-border-strong | #C8CED8 | Emphasized borders |
| color-text | #171A20 | Primary text |
| color-text-muted | #5F6978 | Secondary text |
| color-text-subtle | #7B8492 | Hints and metadata |
| color-accent | #6E50D8 | Accent text and selected states |
| color-accent-strong | #6848D7 | Primary button background |
| color-accent-hover | #5738C5 | Primary button hover |
| color-accent-soft | rgba(110, 80, 216, 0.10) | Selected background |
| color-focus | #5C3FC4 | Keyboard focus ring |
| color-success | #168A5A | Completed states |
| color-warning | #A86C00 | Cautions |
| color-danger | #C73E51 | Errors |
| color-info | #246DB5 | Informational states |

### Color rules

- Primary text must meet at least WCAG AA contrast against its surface.
- Do not use color-text-subtle for essential instructions.
- Use violet for action and selection, not for every decoration.
- Success, warning, danger, and info colors must always be paired with text or an icon; color alone is not sufficient.
- Do not introduce a second brand accent for audio, video, or language.

## 3. Typography system

Use the existing Inter family if it is available. Load it as a variable font where possible. Fallback: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif.

| Style | Size / line height | Weight | Use |
|---|---:|---:|---|
| Display | 32 / 40px | 600 | Workspace title, only when needed |
| Page title | 24 / 32px | 600 | Screen title |
| Section title | 17 / 24px | 600 | Panel title |
| Body | 14 / 22px | 400 | Main copy and field help |
| Body strong | 14 / 22px | 500 | Important values and selected labels |
| Label | 13 / 18px | 500 | Form labels |
| Meta | 12 / 18px | 400 | File size, duration, timestamps |
| Eyebrow | 11 / 16px | 600 | Optional section metadata, uppercase with 0.08em tracking |
| Code/time | 12 / 18px | 500 | Technical identifiers and timestamps |

Use font weights 400, 500, and 600 as the normal range. Reserve 700 for the product wordmark or exceptional emphasis. Avoid all-caps for full sentences.

## 4. Spacing scale

Use a 4px base scale:

~~~
space-1   4px
space-2   8px
space-3  12px
space-4  16px
space-5  20px
space-6  24px
space-7  32px
space-8  40px
space-9  48px
space-10 64px
space-11 80px
~~~

Rules:

- Field label to field: space-2.
- Fields inside one form group: space-4.
- Separate logical groups: space-6.
- Panel padding: space-6 desktop, space-4 mobile.
- Page header to workspace: space-7 desktop, space-5 mobile.
- Use whitespace to show hierarchy before adding borders.

## 5. Border radius system

~~~
radius-control  8px   inputs, compact buttons, badges
radius-card    12px   cards and upload areas
radius-panel   16px   workspace panels and result containers
radius-modal   16px   dialogs and drawers
radius-pill    999px  chips and status indicators
~~~

Avoid mixing many nearly identical radii. A selected control may use the same radius as its unselected state with only border and background changing.

## 6. Shadows and elevation

Use borders and surface contrast as the primary depth system. Shadows are subtle and should never look luminous.

~~~
elevation-1: 0 1px 2px rgba(7, 10, 15, 0.08)
elevation-2: 0 8px 24px rgba(7, 10, 15, 0.12)
elevation-3: 0 18px 48px rgba(7, 10, 15, 0.20)
~~~

Dark mode uses lower-opacity shadows and slightly lighter raised surfaces. Do not use violet shadows except for a restrained focus ring.

## 7. Icon system

Use a Lucide-style icon library with a consistent 1.75–2px stroke. Recommended sizes:

- 16px for metadata and compact controls.
- 18px for form and navigation controls.
- 20px for buttons and section titles.
- 24px for empty states and primary tool identity.

Never use emoji as functional icons. Icons must have a stable meaning and not change by operating system. Icon-only buttons require an accessible name and a tooltip. Decorative icons are hidden from assistive technology.

Suggested icon mapping:

| Meaning | Icon |
|---|---|
| Voice Design | WandSparkles or SlidersHorizontal |
| Voice Cloning | AudioWaveform |
| Transcription | FileText |
| Upload | UploadCloud |
| Record | Mic |
| Stop | Square |
| Play | Play |
| Download | Download |
| Settings | Settings2 |
| Theme | Sun, Moon, Monitor |
| Success | CheckCircle2 |
| Error | CircleAlert |
| Warning | TriangleAlert |
| Close | X |

## 8. Button styles and states

### Variants

- **Primary:** solid violet; one per workflow view. Used for Generate Audio, Synthesize, and Start Transcription.
- **Secondary:** neutral raised surface with border. Used for Browse files, Preview, or secondary actions.
- **Tertiary:** text-only, used for Copy, Replace, Reset, and contextual actions.
- **Destructive:** danger border/text, only for deleting or discarding a persisted item.
- **Icon button:** square control for theme, settings, close, play, and overflow.

### Sizes

- Small: 32px height, only for dense metadata actions.
- Default: 40px height.
- Prominent: 44px height.
- Mobile primary action: minimum 48px height when fixed or sticky.

### States

Every button needs default, hover, pressed, focus-visible, disabled, and loading states. Loading replaces the icon with a spinner and changes the label to a truthful action state, for example “Preparing model…” or “Generating audio…”. A disabled button must still have readable text and should be accompanied by nearby guidance when the reason is not obvious.

## 9. Input, select, and textarea styles

All controls use the same 40px default height, radius-control, 1px border, and color-surface background.

Each field has:

1. Visible label.
2. Optional help text.
3. Control.
4. Inline validation message when needed.

Rules:

- Use real labels, not placeholder text as the only label.
- Placeholder text is an example, never an instruction required to understand the field.
- Focus changes border and adds a 2px color-focus outer ring.
- Error adds a danger border, error icon, and text explanation.
- Disabled fields retain readable text and explain why they are unavailable.
- Selects must preserve the Auto-detect option for transcription.
- Textarea uses a minimum height of 120px for speech text and shows an optional character count.
- Avoid the current mix of browser-native and custom appearance unless the same behavior is implemented for all selects.

## 10. Cards and surfaces

Use three surface roles instead of wrapping every section in an identical card:

1. **Workspace panel:** a large functional region with a title, content, and optional footer action.
2. **Inset surface:** a quiet background for fields, selected files, waveform, and metadata.
3. **Result surface:** a stronger raised area that makes the generated artifact the visual focus.

Cards should have one clear purpose. Do not split a short form into many equally weighted boxes. Use dividers only between truly different groups.

## 11. Navigation and application shell

### Desktop shell

~~~
┌──────────────────────────────────────────────────────────────┐
│ Brand / workspace status                 Theme  Settings     │
├───────────────┬──────────────────────────────────────────────┤
│ Create voice  │ Page title + short explanation                │
│  Voice Design │                                              │
│  Voice Clone  │        Active workspace                       │
│ Transcribe   │                                              │
│ Recent Jobs  │                                              │
│ Voice Profiles│                                              │
│               │                                              │
└───────────────┴──────────────────────────────────────────────┘
~~~

Use a compact left navigation at desktop widths above 960px. “Create voice” is a navigation group containing Voice Design and Voice Cloning. Transcribe is a peer destination. Recent Jobs and Voice Profiles expose persisted data.

At widths below 960px, collapse the sidebar into a top navigation or menu. Keep the current task name visible at all times.

The header should contain:

- VoiceLabs wordmark with a consistent icon.
- Local processing/status indicator, if runtime health is available.
- Theme control.
- Settings control.

Do not show planned features as active navigation items.

## 12. Tabs

Tabs are appropriate inside a task group, not as the entire information architecture. Use them for:

- Voice Design / Voice Cloning under “Create voice”.
- Optional “Setup / Result” only when it reflects actual state.

Tab behavior:

- Use semantic tablist, tab, and tabpanel roles when tabs are implemented as tabs.
- Active tab needs text, color, and a visible indicator; do not rely on a subtle shadow only.
- Preserve the active tab when changing theme or language.
- Keyboard navigation must work with Tab and arrow keys.

## 13. File upload and dropzone

The dropzone is a functional control, not a decorative div.

### Default state

- Dashed border with quiet inset surface.
- Upload icon.
- Primary instruction: “Drop an audio or video file here”.
- Secondary action: “Browse files”.
- Accepted formats and size limit.
- Local-processing reassurance.

### Drag state

- Violet border and subtle violet surface tint.
- Copy changes to “Release to upload”.
- No large glow or animated border.

### Selected state

- File name, type, size, duration when available.
- Audio preview when the browser can play it.
- Replace and remove actions.
- Clear error if the file is unsupported or too large.

Keyboard users must be able to focus the dropzone and open the file picker with Enter or Space. The hidden file input remains the native source of truth.

## 14. Audio recorder

Preserve hold-to-record behavior, but add a full keyboard-accessible start/stop alternative.

States:

1. Idle: Record reference with microphone icon.
2. Permission: Allow microphone access to record a reference.
3. Preparing: Preparing microphone…
4. Recording: timer, waveform, Release to stop plus a visible Stop button.
5. Recorded: preview, duration, Replace, Use this recording.
6. Too short/error: clear explanation and retry.

The waveform is a functional feedback surface. It should not overpower the recording control or use a persistent neon glow.

## 15. Audio player and waveform

The result player is a compact production control:

- Play/pause button.
- Seekable waveform or timeline.
- Elapsed and total time.
- Volume control where supported.
- Download action.
- Optional Create another action.

Waveform colors use the violet accent plus neutral contrast. The player must remain readable in both themes. Any custom waveform must have a text alternative containing duration and playback controls.

## 16. Progress and loading states

Differentiate model loading from job processing:

- **Model loading:** indeterminate spinner, “Downloading model…” or “Loading model from cache…”.
- **File preparation:** “Extracting audio…” only when extraction is occurring.
- **Transcription:** “Transcribing audio…”.
- **Synthesis:** “Generating speech…”.
- **Complete:** show result immediately.

Only display a multi-step timeline when the backend exposes real stages. Do not show Translate, Merge, or “Analyzing speakers” in active workflows when those capabilities are disabled.

Progress requirements:

- Use aria-live="polite" for status text.
- Use a determinate bar only for a trustworthy percentage.
- Use an indeterminate bar for unknown duration.
- Disable duplicate submission while processing.
- Provide Cancel when the operation can safely be cancelled.
- Preserve the input if an operation fails.
- Provide Retry without forcing the user to start over.

## 17. Success, error, and warning states

Use a consistent notice component with icon, title, message, and optional action.

- **Success:** “Audio is ready” plus Play and Download.
- **Error:** explain what happened, what the user can do, and whether the input is still preserved.
- **Warning:** model download size, long processing time, or unsupported capability.
- **Info:** local processing, cache reuse, or expected output format.

Never rely on a browser alert() for product-critical errors. Inline errors belong next to the affected workflow; global errors can use a toast with an accessible live region.

## 18. Result cards

Every result card follows the same structure:

~~~
Result header: status + title + metadata
Primary artifact: audio player, waveform, or transcription text
Metadata: language, duration, file type, created time
Actions: Download / Copy / Create another / Open in history
~~~

The result should be visually stronger than the setup form but not use a large decorative gradient. Preserve the result when the user changes tabs unless they explicitly reset it.

## 19. Modal system

Use a modal only for focused settings or confirmation. Larger workflows should be pages or workspace panels.

Requirements:

- Semantic dialog role and accessible name.
- Focus moves into the dialog and returns to the trigger on close.
- Escape closes the dialog.
- Clicking the overlay closes only when the interaction is non-destructive.
- Body scroll is locked while open.
- Close button has an accessible name.
- On mobile, the modal may become a bottom sheet or full-screen panel.

Settings changes may remain immediate, but the UI must make that behavior clear. Do not show a Save button unless changes are actually staged.

## 20. Tooltips

Use tooltips only for icon-only controls or technical terms that need a short explanation. Do not put essential instructions only in a tooltip.

Tooltips must appear on hover and focus, stay within the viewport, and remain readable in both themes. The underlying control still needs an accessible name.

## 21. Status badges and chips

Use pill-shaped chips for compact, scannable state:

- Ready — success tint.
- Processing — info or accent tint.
- Loading model — warning tint.
- Failed — danger tint.
- Local — neutral/accent tint.
- EN, RU, AZ — neutral language chip.
- Duration and file type — neutral metadata chip.

Each chip must include text. Do not use color alone to distinguish state.

## 22. Empty states

Empty states must explain the next action, not only say “No data”.

Examples:

- Recent Jobs: “Your completed voice and transcription jobs will appear here.” + “Start a workflow”.
- Voice Profiles: “Create a reusable voice from a short reference recording.” + “Clone a voice”.
- Result preview: “Your generated audio will appear here.” + a short explanation of the current input requirement.

Use one quiet icon and one primary action. Do not fill empty space with decorative illustrations until the action is clear.

## 23. Responsive behavior

### Breakpoints

- >= 1200px: full desktop shell, sidebar, two-column workspace.
- 960–1199px: compact sidebar or collapsible navigation, two-column workspace when content allows.
- 640–959px: single-column workspace, full-width panels, top navigation.
- < 640px: mobile layout, stacked sections, sticky primary action.

### Mobile rules

- Panel padding reduces to 16px.
- Two-column field rows become one column.
- Result actions stack vertically with 48px touch targets.
- File preview and filename must not overflow horizontally.
- Primary action remains visible after the user finishes input, either by natural placement or a sticky bottom action bar.
- Modal becomes a full-height or bottom-sheet surface.
- Never require drag-and-drop; Browse and Record remain first-class controls.

## 24. Accessibility and focus states

Target WCAG 2.2 AA behavior, subject to implementation testing.

- Use semantic headings in a logical order.
- Every input has a real label and, where needed, help text linked with aria-describedby.
- Use semantic buttons for actions and links for navigation.
- Dropzones and language options must be keyboard reachable.
- Use :focus-visible with a 2px ring and 2px offset.
- Do not remove the browser outline without replacing it.
- Keep touch targets at least 44×44px for primary interactions.
- Provide aria-busy and live status for long-running work.
- Announce success and errors without moving focus unexpectedly.
- Respect prefers-reduced-motion.
- Keep text readable at 200% zoom and allow responsive reflow.
- Test keyboard order, modal focus management, screen-reader names, and contrast in both themes.

## 25. Animation and transition rules

Motion is smooth and restrained:

- Fast control transitions: 120–160ms.
- Panel and modal transitions: 180–240ms.
- Use ease-out for entering and ease-in for leaving.
- Animate opacity and small translations, not layout-heavy properties.
- Use a subtle waveform animation only while recording or playing.
- Use a spinner for indeterminate work; never fake precise progress with a decorative animation.
- Disable or reduce motion under prefers-reduced-motion: reduce.

# Redesigned workflow layouts

## Voice Design

### User goal

Create a natural-sounding voice from text and a small set of understandable attributes.

### Desktop layout

~~~
Page header: Voice Design
Short copy: Describe the voice, then preview the generated speech.

┌──────────────────────────────┬───────────────────────────────┐
│ Input and configuration      │ Preview and result             │
│                              │                               │
│ Text                         │ Empty preview state            │
│ Language                     │ “Your generated audio         │
│ Voice attributes             │  will appear here.”            │
│  Gender / Age                │                               │
│  Pitch / Style / Accent      │ On result:                     │
│  Advanced instruction        │ audio player + metadata        │
│                              │ Download / Create another     │
│ [Generate audio]             │                               │
└──────────────────────────────┴───────────────────────────────┘
~~~

### Required behavior

- The language field is required and clearly labelled.
- Text input shows a useful example and optional character count.
- Existing gender, age, pitch, style, and accent controls remain available.
- Advanced/custom instruction is an optional expandable control when supported by the current backend.
- The primary button is disabled only when required input is missing, with a short explanation nearby.
- The right panel changes from empty state to model loading, generation, and audio result.

## Voice Cloning

### User goal

Create a reusable voice profile and synthesize text with it.

### Desktop layout

~~~
Page header: Voice Cloning
Short copy: Use a short, clear reference to create a reusable voice.

┌──────────────────────────────┬───────────────────────────────┐
│ Reference and configuration  │ Voice profile / result          │
│                              │                               │
│ Upload reference             │ Empty state or reference       │
│ [Browse files]               │ preview                        │
│ or                           │                               │
│ [Record reference]           │ After cloning:                 │
│ waveform + timer             │ profile name/status            │
│ file preview                 │ audio player                   │
│                              │ Download / Create another      │
│ Text to synthesize           │                               │
│ Text language                │                               │
│ [Create voice and synthesize]│                               │
└──────────────────────────────┴───────────────────────────────┘
~~~

### Required behavior

- Preserve upload of audio and video.
- Preserve microphone recording and hold-to-record behavior, with an accessible start/stop alternative.
- Show file preview before processing.
- Explain accepted formats and recommend a clean 3–10 second reference when applicable.
- Make the two backend phases visible: creating the voice profile and synthesizing text.
- Keep text and language input when a reference is selected.
- Preserve the selected reference and text if cloning or synthesis fails.

## Transcription

### User goal

Turn one audio/video file or supported URL into readable text quickly and confidently.

### Desktop layout

~~~
Page header: Transcription
Short copy: Upload media or paste a supported URL.

┌──────────────────────────────┬───────────────────────────────┐
│ Source and configuration      │ Transcript preview              │
│                              │                               │
│ Source                       │ Empty state                    │
│ [Upload file] [Paste URL]    │ “Your transcript will appear    │
│ selected source preview      │  here after processing.”        │
│                              │                               │
│ Language [Auto-detect]       │ On result:                     │
│                              │ language + duration             │
│ [Start transcription]        │ full text                       │
│                              │ timestamp segments              │
│                              │ Copy / New transcription         │
└──────────────────────────────┴───────────────────────────────┘
~~~

### Required behavior

- File and URL are two source modes, not two competing anonymous cards.
- Keep Auto-detect as the actual default option after languages load.
- Do not show an enabled diarization control; diarization is planned, not active.
- Progress copy must never claim speaker analysis when it is not running.
- Show real or clearly indeterminate model/file progress.
- Results include language, duration, full text, and timestamp segments.
- Copy feedback is announced and remains visible long enough to understand.
- Provide retry without clearing the selected source.

## Settings

Use a settings drawer on desktop and a full-screen sheet on mobile. Preserve:

- Light, dark, and system theme.
- English, Russian, and Azerbaijani interface language.

Organize settings into:

1. **Appearance:** theme and interface language.
2. **Workspace:** local processing explanation and storage/cache information when available.
3. **Planned capabilities:** translation, automatic video dubbing, and speaker diarization shown as roadmap items only.

Do not expose backend model switching unless it is already supported as a real user setting. Runtime/model health may be read-only status information.

## Recent Jobs / History

This is a new frontend surface for data already persisted by the backend.

### Layout

- Page header with Recent Jobs and a Start a workflow action.
- Filter chips: All, Voice Design, Voice Cloning, Transcription.
- Job rows/cards containing type, status, language, created time, duration, and output availability.
- Row actions: Open result, Download asset, Retry when safe.
- Empty, loading, error, and pagination states.

On desktop use a dense table/list; on mobile use stacked cards. Do not invent translation or dubbing rows for jobs that cannot currently be created.

## Voice Profiles

This surface exposes persisted cloned voice profiles.

### Layout

- Page header with Voice Profiles and Clone a new voice.
- Profile card with name/identifier, created time, reference type, duration, and preview action.
- Primary action: Use this voice opens the synthesis workflow with the profile selected.
- Secondary actions: Rename if supported, remove only with confirmation, and inspect source metadata.
- Empty state explains how to create the first profile.

If the current API does not yet expose profile listing, keep this as a UI contract for the existing persistence model and add the smallest read-only endpoint needed later. Do not change backend behavior as part of the design-only phase.

# Proposed application shell

~~~
AppShell
├── AppHeader
│   ├── BrandMark + VoiceLabs
│   ├── LocalStatusChip
│   ├── ThemeButton
│   └── SettingsButton
├── PrimaryNavigation
│   ├── Create voice
│   │   ├── Voice Design
│   │   └── Voice Cloning
│   ├── Transcription
│   ├── Recent Jobs
│   └── Voice Profiles
└── MainContent
    ├── Breadcrumb / PageHeader
    └── WorkspaceLayout
        ├── SetupPanel
        └── PreviewPanel
~~~

On mobile, PrimaryNavigation becomes a compact top control or bottom navigation. SetupPanel and PreviewPanel stack vertically, with the primary action kept visible.

# Page hierarchy

~~~
VoiceLabs
├── Create voice
│   ├── Voice Design
│   └── Voice Cloning
├── Transcription
├── Recent Jobs
├── Voice Profiles
└── Settings
    ├── Appearance
    ├── Workspace
    └── Planned capabilities
~~~

Current features are first-class destinations. Planned features are informational only and are never mixed into the active workflow hierarchy.

# Reusable component hierarchy

~~~
AppShell
├── AppHeader
├── PrimaryNavigation
├── PageHeader
├── WorkspaceLayout
│   ├── SetupPanel
│   └── PreviewPanel
├── NavigationTabs
├── FormField
│   ├── TextInput
│   ├── TextArea
│   ├── Select
│   └── FieldMessage
├── FileDropzone
│   ├── FilePickerButton
│   ├── FilePreview
│   └── FileActions
├── AudioRecorder
│   ├── RecorderButton
│   ├── RecordingTimer
│   └── Waveform
├── AudioPlayer
├── ProgressState
├── StatusChip
├── Notice
├── ResultCard
├── EmptyState
├── JobList / JobCard
├── VoiceProfileCard
├── Modal / Drawer
├── Tooltip
└── Toast / LiveRegion
~~~

All three primary workflows should compose the same primitives instead of implementing separate upload, error, progress, and result patterns.

# Most important design decisions

1. **Clarify the product:** VoiceLabs is an active local voice and transcription studio, not an active video-dubbing pipeline.
2. **Make one action dominant:** each workflow has one clear primary action and a visible reason when it is unavailable.
3. **Use a real workspace layout:** input/configuration on the left and preview/result on the right at desktop widths.
4. **Treat states as product UI:** model loading, processing, errors, and completion are explicit and truthful.
5. **Use violet with restraint:** graphite/neutral surfaces carry the interface; violet signals action and selection.
6. **Replace emoji with a consistent icon system:** the interface should look stable across operating systems.
7. **Design for reuse:** shared components eliminate the current duplicated dropzone and result behavior.
8. **Make local processing visible:** trust and privacy are part of the product experience.
9. **Do not expose unavailable functionality:** translation, automatic video dubbing, and diarization remain roadmap items.
10. **Make persistence visible:** Recent Jobs and Voice Profiles give the existing SQLite-backed data a usable frontend.

# Recommended implementation order

This is a design sequence, not an instruction to start implementation in this phase.

1. Establish semantic design tokens for both themes, typography, spacing, radii, elevation, focus, and motion.
2. Rebuild the application shell and navigation around the three active workflows.
3. Create shared accessible primitives: buttons, fields, select, notice, tabs, modal, dropzone, and result card.
4. Redesign Transcription first: source mode, true Auto-detect, truthful progress, result preview, copy, and retry.
5. Redesign Voice Design using the same setup/result structure.
6. Redesign Voice Cloning with explicit reference, recording, profile, synthesis, and preview states.
7. Add Recent Jobs and Voice Profiles using existing persistence data without changing backend behavior.
8. Finish settings, full localization coverage, responsive behavior, keyboard navigation, focus management, and reduced-motion support.
9. Remove or isolate stale frontend references to disabled video dubbing and translation so they cannot appear in active UI.
10. Validate both themes and every primary workflow at desktop, tablet, mobile, keyboard-only, zoomed, slow-network, model-loading, success, and error states.

The next implementation phase should begin only after this specification is approved; this document intentionally does not modify application code.

