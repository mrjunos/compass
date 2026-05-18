# CompanyBrain — Design Prompt
> For AI design tools (v0, Galileo, Figma AI, Anima, etc.)
> This prompt defines a complete design system and detailed prototype for CompanyBrain.

---

## Product identity

**CompanyBrain** is an AI-first operational brain for small businesses. It knows everything about a company — its people, clients, projects, decisions, communications — and answers questions, surfaces insights, and takes actions. It feels like the most intelligent member of the team: always available, never forgets, anticipates what you need.

The product has two entry points:
- **Web app** — the command center. Dense, data-rich, built for focus.
- **WhatsApp** — frictionless access on the go. Ask anything in natural language and get a cited, structured answer.

The visual language must communicate: **intelligence, trust, precision, and calm authority**. Not a chatbot. Not a dashboard. A brain.

---

## Part 1 — Design System

### 1.1 Philosophy: The Nocturnal Architect

The design system is called **The Nocturnal Architect**. Core beliefs:

- **Information is a precious material.** Treat it with editorial restraint.
- **Light is intelligence.** In a deep dark environment, only meaningful content is illuminated. The AI's responses glow; chrome is invisible.
- **No lines.** Hierarchy through tonal depth, never borders. Space is the separator.
- **Data visualization as first-class UI.** Charts, timelines, entity graphs, and status indicators are not decorations — they are the primary interface.

### 1.2 Color tokens

```
VOID          #0e0e13    — the infinite background, used sparingly
BACKGROUND    #131318    — main canvas
SURFACE       #1b1b20    — primary workbench layer
SURFACE_HIGH  #2a292f    — cards, active elements, hover states
SURFACE_HIGHEST #35343a — selected state, popovers

OUTLINE       #424753    — ghost borders at 15–20% opacity only
OUTLINE_MUTED #8c909e    — metadata separators

ON_SURFACE    #e4e1e9    — primary text (never pure white #ffffff)
ON_DIM        #c2c6d5    — secondary text, descriptions
ON_MUTED      #909094    — tertiary text, timestamps, metadata

PRIMARY       #acc7ff    — blue, AI responses, links, key actions
PRIMARY_CONT  #508ff8    — gradient endpoint for CTAs
PRIMARY_DARK  #005bbf    — pressed/active state for primary elements

SECONDARY     #cebdff    — purple, AI suggestions, insight chips
SECONDARY_CONT #4f319c   — suggestion chip backgrounds

TERTIARY      #49e095    — green, success states, connected status, positive data

ERROR         #ffb4ab    — red-pink, errors, disconnected, critical alerts
ERROR_CONT    #93000a    — error container backgrounds

AMBER         #F7B84F    — warnings, caution, pending human review
```

**Gradient rule:** Primary CTAs use a 135° linear gradient from `PRIMARY` (#acc7ff) to `PRIMARY_CONT` (#508ff8). Never a flat hex.

**Glass rule:** Floating modals use `SURFACE` at 70% opacity + `backdrop-blur: 20px`. Context bleeds through.

### 1.3 Typography

Three typefaces, each with a strict purpose:

| Face | Use | Never use for |
|---|---|---|
| **Inter** (sans-serif) | Body, headlines, UI labels, all prose | Code, raw data |
| **JetBrains Mono** (monospace) | Code blocks, session IDs, API keys, raw AI data, timestamps in metadata | Any human-readable prose |
| **Space Grotesk** (display) | `label-sm`, `label-md` metadata chips, section headers, connector type badges | Long body text |

**Scale:**
```
display-lg    3.5rem / 700 — welcome states, zero-data screens
display-sm    2.25rem / 600 — page headers
headline-lg   1.5rem  / 600 — section titles
headline-md   1.25rem / 600 — card headers
body-lg       1rem    / 400 — main body, chat messages
body-md       0.875rem / 400 — secondary content, descriptions
label-md      0.75rem  / 500 / Space Grotesk — metadata, badges
label-sm      0.625rem / 500 / Space Grotesk — micro-labels, sub-captions
mono-sm       0.75rem  / JetBrains Mono — IDs, timestamps, tokens
```

### 1.4 Surfaces and elevation

```
Layer 0   VOID (#0e0e13)         — absolute background, rarely used
Layer 1   BACKGROUND (#131318)   — main canvas
Layer 2   SURFACE (#1b1b20)      — sidebar, persistent navigation
Layer 3   SURFACE_HIGH (#2a292f) — cards, modules, input fields
Layer 4   SURFACE_HIGHEST (#35343a) — selected rows, open dropdowns, tooltips
Layer 5   Glass (SURFACE at 70% + blur 20px) — floating modals, command palette
```

**Shadow rule:** Ambient only. Use `rgba(from ON_SURFACE, 0.06)` at `blur: 48px, spread: -8px`. Never pure black shadows. Never shadows on buttons.

### 1.5 Component library

#### Buttons

```
PRIMARY_BTN   gradient(PRIMARY → PRIMARY_CONT, 135°), radius: 8px,
              label-md uppercase, height: 40px, px: 20px
              hover: opacity +10%, no shadow

SECONDARY_BTN transparent, ghost border (OUTLINE at 20%), radius: 8px
              label-md, height: 40px, px: 20px
              hover: SURFACE_HIGH background

GHOST_BTN     no background, no border, ON_MUTED text
              hover: ON_DIM text, subtle underline

ICON_BTN      32×32px, SURFACE_HIGH background, radius: 8px
              hover: SURFACE_HIGHEST

DANGER_BTN    ERROR_CONT background, ERROR text
              used only for destructive confirmations
```

#### Input fields

```
BASE    SURFACE background, no border, radius: 4px
        ON_DIM placeholder text, body-md
        height: 44px, px: 16px

FOCUS   ghost border (PRIMARY at 40%, 1px), helper text → PRIMARY color

CHAT    special: full-width, SURFACE background, radius: 12px
        multiline auto-grow, JetBrains Mono for message content
        send button floats inside right edge
```

#### Cards

```
STANDARD    SURFACE_HIGH background, radius: 16px, no borders
            padding: 24px, ambient shadow

DATA_CARD   asymmetric: header 100%, content 65% / metadata 35%
            SURFACE_HIGH bg, radius: 16px

ENTITY_CARD compact: 72px height, SURFACE background
            left: colored type indicator (4px strip)
            hover: SURFACE_HIGH background shift (no animation jump)

ACTION_CARD AMBER at 8% opacity background, radius: 12px
            left border: 3px solid AMBER
            "Aprobar" (PRIMARY gradient btn) / "Rechazar" (ghost)
```

#### AI-specific components

```
THINKING_INDICATOR  Three dots, PRIMARY color, slow pulse (1.4s ease-in-out)
                    "CompanyBrain está analizando..." label in label-sm / ON_MUTED

STREAM_CURSOR       1px × 1em blinking vertical bar, PRIMARY color
                    appears at text insertion point during streaming response

SOURCE_CHIP         SURFACE_HIGHEST bg, OUTLINE ghost border at 15%
                    document icon + doc name in mono-sm
                    click → expands inline with section excerpt

SUGGESTION_CHIP     SECONDARY_CONT bg, SECONDARY text, radius: 9999px
                    "💡" prefix, label-md / Space Grotesk
                    hover: SECONDARY_CONT at 70%, glow effect

STATUS_DOT          8px circle: TERTIARY = connected, AMBER = syncing,
                    ERROR = disconnected, ON_MUTED = inactive
                    paired with mono-sm status text

INSIGHT_BADGE       SECONDARY_CONT bg, radius: 6px, label-sm
                    used on sidebar items with unread alerts count
```

#### Data visualization

All charts: dark-first, no white backgrounds, axes in ON_MUTED, gridlines in OUTLINE at 10% opacity.

```
ACTIVITY_TIMELINE   horizontal, event dots in TERTIARY/AMBER/ERROR by type
                    last-contact marker with days-ago label in mono-sm

ENTITY_MINI_GRAPH   force-directed, client nodes (PRIMARY) → project nodes (SECONDARY)
                    → decision nodes (TERTIARY), ON_MUTED edge lines
                    hover node: expand with label tooltip

STATUS_SPARKLINE    thin 2px line, PRIMARY color, no fill
                    SURFACE_HIGH background panel, 7-day or 30-day view

METRIC_RING         donut chart, 120px, single metric + center label
                    TERTIARY fill, SURFACE_HIGH track

ALERT_HEATMAP       calendar-style grid, cell color: AMBER → ERROR by severity
                    used in Alerts overview screen
```

#### Navigation

```
SIDEBAR             width: 240px, SURFACE background (Layer 2)
                    logo + product name at top, nav items, user avatar at bottom
                    active item: SURFACE_HIGH bg + PRIMARY left border (2px)
                    hover: SURFACE_HIGH bg

NAV_ITEM            height: 40px, px: 16px, radius: 8px
                    icon (20px) + label in body-md
                    badge: INSIGHT_BADGE floated right for alerts count

TOPBAR              height: 56px, SURFACE background
                    breadcrumb left, connection status + model name right
                    no visible border — tonal separation from content below
```

---

## Part 2 — Prototype: All Screens

### Screen 1 — Chat (main)

**Purpose:** The primary interface. Ask anything about the company.

**Layout:** Left sidebar (240px) + main area. Main area is asymmetric: response column 65%, context panel 35% (slides in when source citations exist).

**Elements:**
- **Zero state:** `display-lg` headline "¿Qué quieres saber de tu empresa?" centered. Below: 3 `SUGGESTION_CHIP` example prompts ("¿Quiénes son nuestros clientes activos?", "¿Qué decisiones tomamos este mes?", "¿Hay proyectos en riesgo?"). CompanyBrain logomark above in 64px, slow breathing glow in PRIMARY.
- **Message thread:** User messages right-aligned, SURFACE_HIGHEST bg, body-lg. AI messages left-aligned, no bubble — prose on BACKGROUND directly. AI messages have `COMPASS INTELLIGENCE` label above in label-sm / Space Grotesk / ON_MUTED, with 20px AI icon.
- **Source citations:** `SOURCE_CHIP` row below each AI message. On click, a 35%-wide context panel slides in from right showing the exact doc section with highlighted text.
- **ActionCard:** When AI proposes an action (e.g., draft email), it appears below the message as an `ACTION_CARD` with amber left border, action summary, and two buttons.
- **Suggestion chips:** `SUGGESTION_CHIP` rows for follow-up questions auto-generated by the AI.
- **Input area:** Bottom-anchored, SURFACE bg, radius: 12px. Paperclip icon for file attachment, send arrow. `SHIFT+ENTER` label in mono-sm / ON_MUTED on the right. Session info (session ID, message count) in mono-sm below.
- **Thinking state:** Between sending and first token: `THINKING_INDICATOR` replaces message area. Source chip skeletons pulse in SURFACE_HIGH.
- **Streaming:** Text appears word by word with `STREAM_CURSOR` at insertion point.

---

### Screen 2 — Knowledge Base

**Purpose:** View and manage indexed documents. Trigger entity extraction.

**Layout:** Full-width, two sections: document grid above, extraction status below.

**Elements:**
- **Header:** "Base de Conocimiento" in headline-lg, "+ Agregar documento" PRIMARY_BTN right-aligned.
- **Document grid:** 3-column grid of `DATA_CARD`s. Each card: document icon (colored by type: PDF=ERROR, MD=TERTIARY, TXT=ON_MUTED), filename in headline-md, doc type badge in label-sm / Space Grotesk, page count in mono-sm, indexed date. Bottom: "Ver estructura" ghost btn + "Extraer entidades" secondary btn.
- **Extraction status banner:** When extraction runs, a SURFACE_HIGH full-width bar appears below header with progress: "Extrayendo entidades de servicios.md... 3/5 documentos" + thin PRIMARY progress bar.
- **Empty state:** Illustration of a glowing document node, `display-sm` "Ningún documento indexado aún", body-md instruction, drop zone with dashed ghost border (OUTLINE at 20%).
- **Drag & drop overlay:** When file is dragged over, full-screen BACKGROUND at 80% opacity + SURFACE_HIGH centered panel with dashed border + drop icon in PRIMARY.

---

### Screen 3 — Entities Dashboard

**Purpose:** Structured memory view — People, Clients, Projects, Decisions as live entities.

**Layout:** Full-width. Horizontal tab bar at top. Tab content below.

**Tab bar:** "Personas", "Clientes", "Proyectos", "Decisiones" — Space Grotesk label-md, active: PRIMARY underline (2px).

**People tab:**
- Compact list of `ENTITY_CARD`s. Left strip: SECONDARY color. Avatar initials circle in SECONDARY_CONT. Name in body-lg, role in label-md / ON_MUTED. Email + phone in mono-sm. `source_doc` chip bottom-right. "+ Agregar persona" ghost btn at top.

**Clients tab:**
- Same structure but left strip color: TERTIARY (active), AMBER (prospect), ERROR (inactive).
- Each card: client name, contact name, status badge, `last_contact_at` in mono-sm with color indicator (TERTIARY if < 14 days, AMBER if 14–30, ERROR if > 30 or null).
- Click → Client Detail (Screen 3b).

**Projects tab:**
- Cards with left strip: TERTIARY (active), PRIMARY (completed), AMBER (paused), ERROR (cancelled).
- Project name, client name link, status badge, deadline in mono-sm. If deadline < 7 days away: AMBER AMBER badge "Vence pronto".
- Last update age displayed as "Actualizado hace 3 días" in mono-sm.

**Decisions tab:**
- Timeline layout instead of grid. Vertical line in OUTLINE, decision nodes as circles in TERTIARY/AMBER/ERROR by impact.
- Each node: decision title in body-lg, date in mono-sm, made_by in label-md. Expand → context + outcome text.

**Zero state (any tab):** Glowing empty node illustration, "No hay [entidades] aún", "Agrega documentos para extraer automáticamente" body-md, link to Knowledge Base.

---

### Screen 3b — Client / Project Detail

**Purpose:** Deep dive on a single entity.

**Layout:** Asymmetric. Left: 60% main info. Right: 40% related entities sidebar.

**Client detail left:**
- Header: client name in headline-lg, status badge. Edit icon ghost btn.
- Contact info row: email, phone, contact person — all in mono-sm.
- `ACTIVITY_TIMELINE`: horizontal timeline of last contacts/interactions (placeholder if empty).
- Notes section: markdown-rendered, editable on click.
- Linked projects: compact `ENTITY_CARD` list.

**Right sidebar:**
- "Decisiones relacionadas" — filtered decisions list.
- "Documentos fuente" — SOURCE_CHIPs linking back to original docs.
- "Acciones pendientes" — ACTION_CARDs if any actions are pending for this client.

---

### Screen 4 — Connectors

**Purpose:** Connect CompanyBrain to live data sources.

**Layout:** Full-width. Connector cards grid + event feed.

**Elements:**
- **Header:** "Conectores" headline-lg, "+ Conectar" PRIMARY_BTN.
- **Connector cards:** Large `DATA_CARD`s, 2-column grid. Each card: connector logo (WhatsApp green, Gmail red, GCal blue) at 40px, connector name in headline-md, type badge (Space Grotesk). Status row: `STATUS_DOT` + "Conectado", "Sincronizando…" or "Desconectado" + last sync time in mono-sm. Message count / events processed in mono-sm. Two actions: "Sincronizar ahora" secondary btn, toggle switch (TERTIARY when on).
- **WhatsApp card special:** Shows "Último mensaje recibido: hace 2h" + phone number in mono-sm.
- **Empty state:** 4 greyed-out connector cards (WhatsApp, Gmail, GCal, Slack) as placeholders. "Conecta tus herramientas" overlay. Click any → setup modal.
- **Setup modal:** Glass overlay, centered panel. Step indicator at top (1/3, 2/3, 3/3). Form fields per connector type. "Verificar conexión" PRIMARY_BTN. Connection test result: TERTIARY checkmark or ERROR with message.
- **Event feed:** Right side, 35% width, "Últimos eventos" label-sm. Scrollable list of raw events in mono-sm: timestamp + event type + sender + preview. TERTIARY for processed, ON_MUTED for pending.

---

### Screen 5 — Actions

**Purpose:** Review and approve AI-proposed actions before execution.

**Layout:** Split. Left 55%: pending actions. Right 45%: action detail + preview.

**Elements:**
- **Header:** "Acciones propuestas" headline-lg. Filter tabs: "Pendientes" (AMBER count badge), "Aprobadas", "Rechazadas".
- **Action list:** `ACTION_CARD` for each pending. Shows: action type icon (email, calendar, task), summary line in body-md, proposed time in mono-sm, originating session chip. AMBER left border for pending, TERTIARY for approved, OUTLINE for rejected.
- **Selected action detail (right):**
  - Full action title in headline-md.
  - "Propuesto en respuesta a:" quote block in body-md italics, SURFACE background, OUTLINE left border.
  - For `draft_email`: full email preview — To, Subject, Body rendered in SURFACE_HIGH card.
  - For `create_calendar_event`: mini calendar widget showing the proposed slot, attendees list.
  - For `create_task`: task card preview with due date and assignee.
  - Action buttons: "Aprobar y ejecutar" PRIMARY_BTN + "Rechazar" DANGER_BTN (secondary style).
  - After approval: `THINKING_INDICATOR` while executing, then TERTIARY success state "Ejecutado correctamente".
- **Empty state:** "No hay acciones pendientes" + TERTIARY checkmark illustration.

---

### Screen 6 — Alerts

**Purpose:** Proactive intelligence — triggered alerts and rule configuration.

**Layout:** Full width. Top: alert rules configuration. Bottom: triggered events feed.

**Elements:**
- **"Reglas activas" section:** Horizontal row of compact rule cards. Each: rule name, threshold ("sin contacto > 30 días"), delivery badge (Web / WhatsApp / Ambos), toggle. "+ Nueva regla" ghost btn.
- **Alert event feed:** Table layout. Columns: severity dot, entity type + name (link to entity detail), message, triggered time in mono-sm, dismiss button.
  - Severity: ERROR = critical (project deadline missed, client lost), AMBER = warning (approaching threshold), TERTIARY = informational.
  - Rows are dismissible — fade out on dismiss.
- **"Vista de calor" section:** `ALERT_HEATMAP` — last 30 days as calendar grid. Cell intensity = number of alerts that day. Hover cell → tooltip with alert summary.
- **Zero state:** "El sistema está monitoreando tu empresa" body-md, TERTIARY shield illustration, list of active rules as proof.

---

### Screen 7 — Daily Digest

**Purpose:** Daily/weekly AI-generated summary of company state.

**Layout:** Article-style. Full-width, max 720px centered, generous padding.

**Elements:**
- **Header:** Date in mono-sm / ON_MUTED. "Resumen diario" in display-sm. Subtitle: "Generado por CompanyBrain a las 8:00 AM" in body-md / ON_DIM.
- **Metrics row:** 4 `METRIC_RING` charts side by side: active clients, active projects, pending actions, open alerts. Each ring: TERTIARY fill, SURFACE_HIGH track, center number in headline-lg, label below in label-sm.
- **Digest sections:** AI-generated prose in body-lg, organized under Space Grotesk headers: "Clientes", "Proyectos", "Decisiones recientes", "Atención requerida". Each section cites entities as inline chips (ENTITY_CARD compact inline).
- **"Atención requerida" section:** Highlighted with AMBER subtle background. Bullet list of items needing human action — each with an inline CTA chip.
- **Footer:** "¿Algo incorrecto?" ghost link. "Enviar por WhatsApp" secondary btn. "Ver historial de resúmenes" ghost link.

---

### Screen 8 — Onboarding (First-time setup)

**Purpose:** Guide a new user from zero to first insight in under 10 minutes.

**Layout:** Full-screen, centered, step wizard. Progress bar at top.

**Steps:**

**Step 1 — Welcome (display-lg "Bienvenido a CompanyBrain")**
- Logomark animated: circle expanding from VOID to glow state.
- Tagline: "Tu empresa, toda en un cerebro." body-lg / ON_DIM.
- "Empezar configuración" PRIMARY_BTN.

**Step 2 — Upload first documents**
- headline-md "Agrega documentos de tu empresa". body-md instruction.
- Large drop zone (SURFACE_HIGH, dashed ghost border, document icon in PRIMARY).
- "Arrastra PDFs, Markdown, o archivos TXT". Supported formats in mono-sm.
- Skip link for users who want to connect integrations first.

**Step 3 — Connect integrations (optional)**
- headline-md "Conecta tus herramientas".
- 4 integration cards (WhatsApp, Gmail, GCal, Slack) in a 2×2 grid with "Conectar" secondary btn each.
- "Saltar por ahora" ghost btn.

**Step 4 — First extraction**
- Progress animation: documents being processed. Each doc shows extraction status: THINKING_INDICATOR → TERTIARY checkmark.
- Extracted entity counts appear live: "3 clientes encontrados", "2 proyectos", "5 decisiones".

**Step 5 — First question**
- "CompanyBrain está listo." headline-lg, TERTIARY glow.
- Pre-filled chat input with suggested first question pulled from extracted entities.
- "Pregunta esto" PRIMARY_BTN.

---

## Key interaction patterns

### Streaming AI responses
Text appears word-by-word. As text streams in, source chips materialize below one by one. The right context panel slides in after the first source is identified — not after the full response. This makes the AI feel like it's thinking in real time, not retrieving a cached answer.

### Human-in-the-loop approval
When an `ACTION_CARD` appears in chat, the input field dims and shows "Revisa la acción propuesta antes de continuar" in label-sm / AMBER. The send button is still active — user can keep chatting. The action card persists until explicitly approved or rejected.

### Entity linking
Wherever an entity name appears (client, project, person) in any AI response, it is rendered as a subtle inline link — PRIMARY text, no underline, hover shows mini `ENTITY_CARD` tooltip. Click navigates to Entity Detail.

### Connector sync states
Connectors pulse their `STATUS_DOT` with a slow animation (2s ease-in-out) while syncing. The sidebar nav item for Connectors shows a spinning sync icon during active sync. Never a blocking loading overlay — always optimistic UI.

### Notification delivery
New alerts cause the sidebar "Alertas" nav item to gain an `INSIGHT_BADGE` with count. No browser push notifications for MVP — the badge is the primary signal. WhatsApp delivery is the secondary signal for mobile.

---

## Responsiveness notes

The web app targets desktop (1280px+) as primary. Tablets (768px–1280px): sidebar collapses to icons only, context panels become bottom sheets. Mobile is out of scope — WhatsApp is the mobile interface.

---

## What this product is NOT

- Not a dashboard with KPIs. Metrics appear in context, not as primary UI.
- Not a chatbot. The interface is a command center, the chat is one modality.
- Not generic. Every label, prompt, and empty state is in Spanish, for a LATAM founder managing a real company.
- Not loud. No gradients on backgrounds, no color overload, no animations for decoration. Animation serves information, never aesthetics.
