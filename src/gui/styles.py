"""Shared Qt stylesheet generation for the LCCN Harvester application.

Defines two complete Catppuccin-inspired color palettes and a single
``generate_stylesheet`` function that produces the full application QSS string
for any palette.

Color palettes:
    ``CATPPUCCIN_DARK`` — High-contrast dark theme based on Tailwind Gray scale.
    ``CATPPUCCIN_LIGHT`` — High-contrast light theme based on Tailwind Slate scale.

Usage::

    from .styles import generate_stylesheet, CATPPUCCIN_DARK, CATPPUCCIN_LIGHT
    app.setStyleSheet(generate_stylesheet(CATPPUCCIN_LIGHT))

The ``DEFAULT_STYLESHEET`` constant holds a pre-generated fallback stylesheet
(using the dark palette) used when ``generate_stylesheet`` raises an exception.

Design notes:
- QSS property selectors (``QLabel[class="Card"]``) require ``unpolish`` /
  ``polish`` calls after a dynamic property changes.  See ``_set_sidebar_status``
  in ``modern_window.py`` for the pattern.
- SVG-based combo-box arrows are written to a temp file by ``get_svg_file`` so
  QSS ``url(...)`` references resolve correctly on all platforms.
"""

CATPPUCCIN_DARK = {
    # ── Surface hierarchy ──────────────────────────────────────────────
    # Each level is one step lighter than the one below it so depth reads
    # naturally even without shadows:  bg < surface < surface2.
    "bg": "#111827",               # Tailwind Gray-900 — deepest application background
    "surface": "#1f2937",          # Tailwind Gray-800 — cards and panels
    "surface2": "#374151",         # Tailwind Gray-700 — raised panel headers / inputs

    # ── Border tokens ─────────────────────────────────────────────────
    "border": "#4b5563",           # Tailwind Gray-600 — standard structural lines
    "border_strong": "#6b7280",    # Tailwind Gray-500 — strong dividers and focus rings

    # ── Text tokens ───────────────────────────────────────────────────
    # Both text levels are identical here so all text stays maximally legible
    # on the dark backgrounds; muted text is differentiated via font-weight
    # or font-size instead of color.
    "text": "#f9fafb",             # Tailwind Gray-50 — crisp primary text
    "text_muted": "#f9fafb",       # Same as text — white-on-dark contrast requirement

    # ── Semantic state colours ────────────────────────────────────────
    "primary": "#3b82f6",          # Blue — interactive / accent
    "success": "#22c55e",          # Green — success / online
    "warning": "#f59e0b",          # Amber — warning / paused
    "danger": "#ef4444",           # Red — error / offline / destructive action

    # ── Interactive state colours ─────────────────────────────────────
    "hover": "#374151",            # Gray-700 — hover background overlay
    "focus": "#60a5fa",            # Blue-400 — focus ring / active tint
    "shadow": "#030712",           # Near-black — simulates a CSS box-shadow drop border
}

CATPPUCCIN_LIGHT = {
    # ── Surface hierarchy ──────────────────────────────────────────────
    "bg": "#f3f4f6",               # Tailwind Gray-100 — subtle application background
    "surface": "#ffffff",          # Pure white — cards and panels
    "surface2": "#f8fafc",         # Slate-50 — raised panel headers / inputs

    # ── Border tokens ─────────────────────────────────────────────────
    "border": "#cbd5e1",           # Slate-300 — sharp visible structural lines
    "border_strong": "#94a3b8",    # Slate-400 — strong dividers and focus rings

    # ── Text tokens ───────────────────────────────────────────────────
    # Same rationale as the dark palette: both levels use maximum-contrast text.
    "text": "#0f172a",             # Slate-900 — near-black primary text
    "text_muted": "#0f172a",       # Same as text — black-on-light contrast requirement

    # ── Semantic state colours ────────────────────────────────────────
    # Slightly darker shades compared to the dark palette for light-bg legibility.
    "primary": "#2563eb",          # Blue — interactive / accent
    "success": "#16a34a",          # Green — success / online
    "warning": "#d97706",          # Amber — warning / paused
    "danger": "#dc2626",           # Red — error / offline / destructive action

    # ── Interactive state colours ─────────────────────────────────────
    "hover": "#f1f5f9",            # Slate-100 — hover background overlay
    "focus": "#3b82f6",            # Blue-500 — focus ring / active tint
    "shadow": "#e2e8f0",           # Slate-200 — simulates a CSS box-shadow drop border
}

DEFAULT_THEME = CATPPUCCIN_DARK
# CATPPUCCIN_THEME is kept as a legacy alias so older call-sites do not break
# after the rename; new code should reference CATPPUCCIN_DARK / CATPPUCCIN_LIGHT.
CATPPUCCIN_THEME = DEFAULT_THEME

def generate_stylesheet(theme: dict) -> str:
    """Build the complete application QSS stylesheet for the given theme palette.

    The returned string contains rules for every custom widget class used in the
    application (nav buttons, cards, status pills, form inputs, progress bars,
    dialogs, etc.) and is applied to the ``QApplication`` instance.

    Args:
        theme: A palette dict such as ``CATPPUCCIN_DARK`` or ``CATPPUCCIN_LIGHT``
               containing the semantic color keys (``bg``, ``surface``,
               ``primary``, etc.).

    Returns:
        A multi-line QSS stylesheet string ready for ``app.setStyleSheet()``.
    """
    # Short alias — all QSS f-string substitutions use `t['key']` notation.
    t = theme

    def hex_to_rgba(hex_str: str, alpha: float) -> str:
        """Convert a ``#RRGGBB`` color to a CSS ``rgba(...)`` string.

        Args:
            hex_str: A six-digit hex color string (with or without the ``#`` prefix).
            alpha: Opacity value between 0.0 and 1.0.

        Returns:
            An ``rgba(r, g, b, alpha)`` CSS string.
        """
        hex_str = hex_str.lstrip("#")
        if len(hex_str) != 6:
            raise ValueError(f"Expected a 6-digit hex color, got {hex_str!r}")
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"

    def get_svg_file(svg_string, color_hex, name):
        """Write a tinted SVG to a temp file and return its POSIX path.

        QSS ``url()`` references must point to real files on disk; this helper
        replaces the ``CURRENT_COLOR`` placeholder in the SVG with the
        requested hex color, caches the result in the system temp directory,
        and returns the path.  Backslashes are normalised to forward slashes
        so the path is valid in QSS on all platforms.

        Args:
            svg_string: Raw SVG text with ``CURRENT_COLOR`` as the stroke.
            color_hex: Target hex color string (e.g. ``"#6b7280"``).
            name: Short identifier used to build a unique temp file name
                  (e.g. ``"chevron_down"``).

        Returns:
            Absolute POSIX-style path to the written SVG file.
        """
        import os
        import tempfile

        # Substitute the placeholder with the desired tint color.
        colored = svg_string.replace('CURRENT_COLOR', color_hex)
        temp_dir = tempfile.gettempdir()
        # Include color in filename so different tints get separate cached files.
        filename = f"{name}_{color_hex.replace('#', '')}.svg"
        # Normalise path separators: QSS url() requires forward slashes.
        path = os.path.join(temp_dir, filename).replace('\\', '/')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(colored)
        return path

    # Minimal inline SVGs used only inside QSS url() calls for combo/spin arrows.
    # ``CURRENT_COLOR`` is a deliberate placeholder — it is not the SVG standard
    # "currentColor"; get_svg_file replaces this token with the real hex tint
    # before writing the SVG to disk, so QSS can reference a real file path.
    chevron_down = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='CURRENT_COLOR' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>"
    chevron_up = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='CURRENT_COLOR' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='18 15 12 9 6 15'></polyline></svg>"

    # Note: all curly braces in this f-string must be doubled ({{ }}) to
    # produce literal braces in the output QSS; single braces are Python
    # f-string substitution markers.
    return f"""/* --- Global Base --- */
QWidget {{
    background-color: {t['bg']}; /* App Background */
    color: {t['text']};            /* Text Primary */
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    font-size: 14px;
}}

/* Prevent blocky background rectangles behind text labels */
QLabel {{
    background: transparent;
    color: {t['text']};
}}

/* --- Sidebar: Gradient Depth ---
   The sidebar uses border-right rather than a full border so only the
   edge that abuts the content area is visually separated.              */
QFrame#Sidebar {{
    background-color: {t['bg']};
    border-right: 1px solid {t['border']};
}}

QLabel#SidebarTitle {{
    color: {t['primary']}; /* Primary blue ties the app name to the brand accent */
    font-size: 18px;
    font-weight: 800;
    padding: 20px 0;
    margin-bottom: 20px; /* Creates breathing room between the title and the first nav item */
    qproperty-alignment: AlignCenter;
}}

/* Sidebar Navigation Buttons
   Three selector forms are provided (class attribute, CSS class, objectName)
   to ensure the rule fires regardless of how the property was assigned in
   Python (setProperty("class",...) vs setObjectName(...)).               */
QPushButton[class="NavButton"], QPushButton.NavButton, QPushButton#NavButton {{
    background-color: transparent;
    color: {t['text_muted']};
    text-align: left;
    padding: 12px 20px; 
    border: none;
    border-left: 3px solid transparent; 
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 2px;
    outline: none;
}}

QPushButton[class="NavButton"]:hover, QPushButton.NavButton:hover, QPushButton#NavButton:hover {{
    background-color: {t['hover']}; 
    color: {t['text']};
    border-left: 3px solid transparent;
}}

QPushButton[class="NavButton"]:checked, QPushButton.NavButton:checked, QPushButton#NavButton:checked {{
    background-color: {hex_to_rgba(t['primary'], 0.1)};
    color: {t['primary']}; 
    border-left: 3px solid {t['primary']};
}}

QPushButton[class="NavButton"]:pressed, QPushButton.NavButton:pressed, QPushButton#NavButton:pressed {{
    background-color: {hex_to_rgba(t['primary'], 0.15)};
    color: {t['primary']};
    border-left: 3px solid {t['primary']};
}}

QPushButton[class="NavButton"]:focus, QPushButton.NavButton:focus, QPushButton#NavButton:focus {{
    border-left: 3px solid {t['primary']};
    background-color: {hex_to_rgba(t['primary'], 0.1)};
    color: {t['text']};
}}

/* Tooltips
   Hard-coded black/white is intentional — tooltips must be legible on both
   the dark and light themes without re-theming; a fixed high-contrast pair
   achieves this without a conditional.  The primary-colour border anchors
   the tooltip visually to the active theme accent.                        */
QToolTip {{
    background-color: #000000; /* Fixed black — readable over any theme background */
    color: #ffffff;            /* Fixed white — maximum contrast on the black bg */
    border: 1px solid {t['primary']}; /* Accent border ties tooltip chrome to the theme */
    padding: 4px 8px;
    border-radius: 4px; /* Softens the tooltip box to match the general 8px rounding language */
}}

/* --- Header / Content --- */
QWidget#ContentArea {{
    background-color: {t['bg']}; /* Matches the app background so the content area blends seamlessly */
}}

QLabel#PageTitle {{
    font-size: 26px;  /* Larger than card titles to establish a clear typographic hierarchy */
    font-weight: 800;
    color: {t['text']};
    margin-bottom: 20px; /* Separates the page heading from the first card below it */
    letter-spacing: 0.2px; /* Slight tracking improves readability at large sizes */
}}

/* --- Cards / Panels: The Space Context ---
   border-bottom is intentionally 2px (vs 1px sides) to simulate a CSS
   box-shadow drop by making the bottom edge slightly heavier.           */
QFrame[class="Card"], QFrame.Card {{
    background-color: {t['surface']}; 
    border: 1px solid {t['border']}; 
    border-bottom: 2px solid {t['shadow']}; /* Simulated Box Shadow Drop */
    border-radius: 12px;
}}

/* Static cards should not react to the pointer; hover is reserved for real controls. */
QFrame[class="Card"]:hover, QFrame.Card:hover,
QFrame#HarvestBanner:hover, QFrame#HelpHeader:hover {{
    border: 1px solid {t['border']};
    border-bottom: 2px solid {t['shadow']};
}}

/* Special Styling for Live Panel to make it a focal point */
QFrame#LivePanel {{
    background-color: {t['surface']};
    border: 1px solid {t['primary']}; 
    border-top: 2px solid {t['primary']}; 
}}

QLabel[class="CardTitle"], QLabel.CardTitle {{
    color: {t['text_muted']}; /* Muted so the card value (number) is the visual focal point */
    font-size: 14px;          /* Smaller than the value label to maintain visual hierarchy */
    font-weight: 700;
    letter-spacing: 0.2px;
}}

QLabel[class="CardValue"], QLabel.CardValue {{
    color: {t['text']};
    font-size: 32px;  /* Large numeric display — the primary information on a stat card */
    font-weight: 800; /* Extra-bold so the number reads instantly at a glance */
}}

QLabel[class="CardHelper"], QLabel.CardHelper {{
    color: {t['text_muted']};
    font-size: 11px;
}}

/* --- Database Browser Tabs ---
   Scoped to #DatabaseBrowserTabs so these overrides only affect the
   browser dialog and do not accidentally restyle other QTabWidgets.    */
QTabWidget#DatabaseBrowserTabs::pane {{
    border: 1px solid {t['border']};
    border-radius: 8px;
    top: -1px; /* Pulls the pane up by 1px so the selected tab's bottom border merges with the pane border */
}}

QTabWidget#DatabaseBrowserTabs QTabBar::tab {{
    background-color: {t['surface2']}; /* Slightly raised surface so inactive tabs read as "behind" the pane */
    color: {t['text_muted']};          /* Muted text signals these tabs are inactive */
    border: 1px solid {t['border']};
    border-bottom: 1px solid {t['border']};
    border-top-left-radius: 8px;  /* Only round the top corners — bottom attaches flush to the pane */
    border-top-right-radius: 8px;
    min-width: 120px;  /* Ensures tab labels never collapse to unreadable widths */
    padding: 10px 18px;
    margin-right: 6px; /* Gap between tabs to make them visually distinct units */
    font-size: 13px;
    font-weight: 800;
}}

QTabWidget#DatabaseBrowserTabs QTabBar::tab:hover {{
    color: {t['text']};
    border: 1px solid {t['primary']};
    background-color: {t['hover']};
}}

QTabWidget#DatabaseBrowserTabs QTabBar::tab:selected {{
    background-color: {t['primary']}; /* Solid accent fill makes the active table immediately obvious */
    color: #ffffff;                   /* White on blue for WCAG-compliant contrast on the selected tab */
    border: 1px solid {t['primary']};
    border-bottom: 1px solid {t['primary']}; /* Matches the pane border so tab and pane appear as one surface */
}}

QLabel[class="ActivityLabel"], QLabel.ActivityLabel {{
    color: {t['text_muted']};
    font-weight: 600;
    font-size: 13px;
}}

QLabel[class="ActivityValue"], QLabel.ActivityValue {{
    color: {t['text']};
    font-family: Menlo, Monaco, 'Courier New', monospace; /* Monospace keeps numeric columns aligned vertically */
    font-size: 13px;
}}

QLabel[class="SectionTitle"], QLabel.SectionTitle {{
    color: {t['text_muted']};
    font-size: 18px;
    font-weight: bold;
}}

QLabel[class="DropIcon"], QLabel.DropIcon {{
    font-size: 48px;
    border: none;
    background: transparent;
}}

QLabel[class="DropText"], QLabel.DropText {{
    font-size: 14px;
    font-weight: bold;
    color: {t['warning']}; /* Amber signals "action needed" without being an error */
    border: none;
    background: transparent;
}}

QLabel[class="DropHint"], QLabel.DropHint {{
    font-size: 11px;
    color: {t['text_muted']};
    border: none;
    background: transparent;
}}

QLabel[class="HelperText"], QLabel.HelperText {{
    font-size: 12px;
    color: {t['text_muted']};
    background: transparent;
    border: none;
}}

/* --- Status Pills ---
   Pills are display-only badges rendered via QLabel rather than QPushButton.
   The base rule is intentionally colourless (text_muted); the [state="..."]
   sub-rules below override the colour for each known harvest state.     */
QLabel[class="StatusPill"], QLabel.StatusPill {{
    background-color: transparent;
    color: {t['text_muted']};
    border-radius: 0;
    padding: 0;
    min-height: 0;
    max-height: 16777215;
    font-weight: bold;
    font-size: 11px;
    text-transform: uppercase;
    border: none;
}}

QLabel[class="StatusPill"][state="running"], QLabel.StatusPill[state="running"] {{
    color: {t['primary']};
}}

QLabel[class="StatusPill"][state="paused"], QLabel.StatusPill[state="paused"] {{
    color: {t['warning']};
}}

QLabel[class="StatusPill"][state="error"], QLabel.StatusPill[state="error"] {{
    color: {t['danger']};
}}

QLabel[class="StatusPill"][state="success"], QLabel.StatusPill[state="success"] {{
    color: {t['success']};
}}

QLabel[class="StatusPill"][state="idle"], QLabel.StatusPill[state="idle"] {{
    color: {t['text_muted']};
}}

/* --- Controls: Inputs ---
   All editable input types share the same base rule for visual consistency.
   The focus rule widens the border to 2px so it is clearly visible without
   changing the widget's layout dimensions (border grows inward in QSS).   */
QLineEdit, QSpinBox, QTextEdit, QPlainTextEdit {{
    background-color: {t['bg']};     /* Input sits on the base bg, visually inset below panels */
    border: 1px solid {t['border']}; /* Thin border provides affordance without being dominant */
    border-radius: 8px;
    padding: 12px;
    color: {t['text']};
    font-size: 14px;
}}

QLineEdit:focus, QSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {t['focus']};   /* 2px focus ring makes keyboard-focused inputs clearly visible */
    background-color: {t['surface']}; /* Slight bg lift on focus reinforces that the field is active */
}}

QLineEdit:read-only {{
    background-color: {t['surface2']}; /* Distinct fill communicates the field is not editable */
    color: {t['text_muted']};
    border: 1px solid {t['border']};
}}

/* Stronger Affordance for Dropdowns
   combobox-popup: 0 disables the OS-native popup so our custom QListView
   (installed by ConsistentComboBox.setView) is styled by the QSS rules
   below rather than by the OS theme.                                    */
QComboBox {{
    background-color: {t['bg']};
    border: 1px solid {t['border_strong']};
    border-radius: 8px;
    combobox-popup: 0; /* Disable the native OS popup so custom QListView styles apply */
    padding: 12px;
    color: {t['text']};
    font-size: 14px;
}}

QComboBox:hover {{
    background-color: {t['hover']};
}}

QComboBox:focus {{
    border: 2px solid {t['focus']};
    background-color: {t['surface']};
}}

/* Ensure dropdown menus don't inherit OS native green selections.
   This fallback rule fires when the popup view is NOT a QListView with a
   specific objectName (i.e. for combo boxes not using ConsistentComboBox). */
QComboBox QAbstractItemView {{
    background-color: {t['bg']};
    border: 1px solid {t['border']};
    selection-background-color: {t['hover']};
    selection-color: {t['text']};
    border-radius: 8px;
    outline: none;
    padding: 6px;
}}
QComboBox QAbstractItemView::item {{
    min-height: 24px;
    padding: 8px 12px;
    margin: 2px 0;
    border-radius: 8px;
    color: {t['text']};
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {t['hover']};
    color: {t['text']};
}}
QListView#ComboPopup {{
    background-color: {t['surface']};
    border: 1px solid {t['border_strong']};
    border-radius: 12px;
    padding: 6px;
    outline: none;
}}
QListView#ComboPopup::item {{
    min-height: 24px;
    padding: 8px 12px;
    margin: 2px 0;
    border-radius: 8px;
    color: {t['text']};
}}
QListView#ComboPopup::item:selected {{
    background-color: {t['hover']};
    color: {t['text']};
}}
QComboBox#ResultFormatCombo {{
    min-width: 168px;
    padding: 10px 38px 10px 14px;
}}
QComboBox#ResultFormatCombo QAbstractItemView {{
    background-color: {t['surface']};
    border: 1px solid {t['border_strong']};
    border-radius: 12px;
    padding: 6px;
    outline: none;
}}
QListView#ResultFormatComboPopup {{
    background-color: {t['surface']};
    border: 1px solid {t['border_strong']};
    border-radius: 12px;
    padding: 6px;
    outline: none;
}}
QComboBox#ResultFormatCombo QAbstractItemView::item {{
    min-height: 24px;
    padding: 8px 12px;
    margin: 2px 0;
    border-radius: 8px;
    color: {t['text']};
}}
QListView#ResultFormatComboPopup::item {{
    min-height: 24px;
    padding: 8px 12px;
    margin: 2px 0;
    border-radius: 8px;
    color: {t['text']};
}}
QComboBox#ResultFormatCombo QAbstractItemView::item:selected {{
    background-color: {t['hover']};
    color: {t['text']};
}}
QListView#ResultFormatComboPopup::item:selected {{
    background-color: {t['hover']};
    color: {t['text']};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;                             /* Enough room for a 16px icon with comfortable hit area */
    border-left: 1px solid {t['border_strong']}; /* Divider visually separates the arrow zone from the text */
    border-top-right-radius: 8px;    /* Matches the parent combo border-radius so corners align */
    border-bottom-right-radius: 8px;
    background: transparent;
}}
/* get_svg_file writes a tinted SVG to a temp file and returns its path;
   the path is then embedded directly into the QSS url() call. */
QComboBox::down-arrow {{
    image: url("{get_svg_file(chevron_down, t['text_muted'], 'chevron_down')}");
    width: 16px;
    height: 16px;
}}
QComboBox::down-arrow:on, QComboBox::down-arrow:hover, QComboBox::down-arrow:focus {{
    /* Use the focus (blue) tint when the combo is active or hovered. */
    image: url("{get_svg_file(chevron_down, t['focus'], 'chevron_down')}");
}}

/* Rank column combo — tighter padding than the global QComboBox rule so the
   numeric rank fits inside the narrow cell width in the targets table.
   max-width: 64px caps it to the fixed column width so it never overflows. */
QComboBox#RankCombo {{
    padding: 4px 24px 4px 8px; /* 24px right-pad leaves room for the drop-down arrow zone */
    min-width: 52px;            /* Wide enough for two-digit rank numbers */
    max-width: 64px;            /* Capped to match the fixed targets-table rank column width */
}}
QListView#RankComboPopup {{
    background-color: {t['surface']};
    border: 1px solid {t['border_strong']};
    border-radius: 12px;
    padding: 4px;
    outline: none;
}}
QListView#RankComboPopup::item {{
    min-height: 22px;
    padding: 6px 10px;
    margin: 1px 0;
    border-radius: 8px;
    color: {t['text']};
}}
QListView#RankComboPopup::item:selected {{
    background-color: {t['hover']};
    color: {t['text']};
}}

/* Clean up QSpinBox arrows to avoid dark system patches.
   The default Windows/macOS button backgrounds are opaque rectangles that
   clash with themed inputs; setting them transparent removes the patches
   while the SVG arrow images (below) provide the affordance.            */
QSpinBox::up-button, QSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 20px;
}}
QSpinBox::up-arrow {{
    image: url("{get_svg_file(chevron_up, t['text_muted'], 'chevron_up')}");
    width: 14px;
    height: 14px;
}}
QSpinBox::down-arrow {{
    image: url("{get_svg_file(chevron_down, t['text_muted'], 'chevron_down')}");
    width: 14px;
    height: 14px;
}}
QSpinBox::up-arrow:hover, QSpinBox::down-arrow:hover {{
    image: url("{get_svg_file(chevron_up, t['focus'], 'chevron_up')}");
}}


/* Scroll Areas
   Transparent background prevents the scroll area from painting its own
   background rectangle on top of the parent card's background colour.   */
QScrollArea[class="ScrollArea"], QScrollArea.ScrollArea {{
    background: transparent; /* Inherits parent card surface instead of painting its own bg */
    border: none;            /* Cards provide their own border; a second border here would double-border */
}}

/* Drag Zone (Input) */
QFrame#DragZone, QFrame[class="DragZone"] {{
    border: 2px dashed {t['border_strong']}; /* Dashed border is the conventional drop-target affordance */
    background-color: {t['surface']}14;      /* "14" is hex 20 — 8% opacity tint, just visible enough */
    border-radius: 16px;                     /* Larger radius than cards gives the zone a friendlier, open shape */
}}
QFrame#DragZone:hover, QFrame[class="DragZone"]:hover {{
    background-color: {t['hover']}26; /* "26" is hex 38 — 15% opacity, brighter than idle to signal readiness */
    border-color: {t['focus']};       /* Focus blue on hover signals the zone is ready to accept a drop */
}}

QFrame[class="DragZone"][state="ready"] {{
    border: 3px dashed {t['warning']}; /* Amber dashed border: file loaded, awaiting confirmation */
    background-color: {t['surface']};
}}
QFrame[class="DragZone"][state="ready"]:hover {{
    background-color: {t['hover']}26;
    border-color: {t['warning']}; /* Keep amber on hover so colour meaning stays consistent */
}}

QFrame[class="DragZone"][state="active"] {{
    border: 3px dashed {t['primary']}; /* Blue dashed: drag is in progress over the zone */
    background-color: {t['surface2']}; /* Slightly raised surface acknowledges the active drag */
}}

QFrame[class="DragZone"][state="success"] {{
    border: 3px solid {t['primary']};  /* Solid (not dashed) border signals the file has been accepted */
    background-color: {t['surface2']};
}}

/* Tables
   selection-background-color: transparent keeps the row highlight invisible
   because the targets table uses custom cell widgets (buttons, combos) that
   would look odd with a coloured highlight row behind them.              */
QTableWidget {{
    background-color: {t['surface']}; 
    alternate-background-color: {t['bg']};
    border: 1px solid {t['border']}; 
    border-radius: 8px;
    gridline-color: {t['border']}; 
    outline: none; /* Strip native focus brackets */
    selection-background-color: transparent;
    selection-color: {t['text']};
}}

QTableWidget::item {{
    border-bottom: 1px solid {t['border']};
    padding: 9px 10px;
    color: {t['text']};
    background: transparent;
}}

QTableWidget::item:selected {{
    background-color: transparent;
    color: {t['text']};
}}

QTableWidget::item:hover {{
    background-color: {t['hover']};
}}

QHeaderView::section {{
    background-color: {t['surface2']}; 
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid {t['border_strong']}; /* Subtle structural underline */
    font-weight: 700;
    color: {t['text']};
    font-size: 13px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background-color: {t['bg']};
    width: 12px;
    border-radius: 6px;
}}
QScrollBar::handle:vertical {{
    background-color: {t['border']};
    border-radius: 6px;
    border: 2px solid {t['bg']}; /* Pseudo padding */
}}
QScrollBar::handle:vertical:hover {{
    background-color: {t['border_strong']};
}}
QScrollBar:horizontal {{
    background-color: {t['bg']};
    height: 12px;
    border-radius: 6px;
}}
QScrollBar::handle:horizontal {{
    background-color: {t['border']};
    border-radius: 6px;
    border: 2px solid {t['bg']};
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {t['border_strong']};
}}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }} /* Hide scroll arrow buttons — not needed with modern mice/trackpads */
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}   /* Remove the trough fill between the handle and the scroll arrows */

/* --- BUTTON SYSTEM (VIBRANT) ---
   Three named variants sit above the base QPushButton rule:
     PrimaryButton — solid accent blue fill; used for the main call-to-action.
     SecondaryButton — neutral surface fill; used for supporting actions.
     DangerButton — red fill; used for destructive or irreversible actions.
   All three use three selector forms (attribute / class / objectName) for
   the same compatibility reason as NavButton above.                     */

QPushButton {{
    background-color: {t['surface2']}; /* Neutral surface fill: identifiable as a button without demanding attention */
    color: {t['text']};
    border-radius: 8px;                /* Consistent with input rounding — keeps all interactive elements cohesive */
    padding: 10px 20px;
    font-weight: 700;
    font-size: 14px;
    border: 1px solid {t['border_strong']}; /* Stronger border than cards so buttons read as interactive */
    outline: none;                          /* Remove the OS default dotted focus rectangle — focus is styled via :focus */
}}

QPushButton:hover {{
    background-color: {t['hover']};
    border-color: {t['primary']};
}}

QPushButton:pressed {{
    background-color: {t['surface']};
    border-color: {t['primary']};
}}

QPushButton:focus {{
    border: 2px solid {t['focus']};
    outline: none;
}}

/* 1. Primary: Blue Fill */
QPushButton[class="PrimaryButton"], QPushButton.PrimaryButton, QPushButton#PrimaryButton {{
    background-color: {t['primary']};
    color: #ffffff;                    /* White text ensures WCAG AA contrast on the blue fill */
    border: 1px solid transparent;    /* Transparent border keeps layout stable when state borders are added */
}}
QPushButton[class="PrimaryButton"]:hover, QPushButton.PrimaryButton:hover, QPushButton#PrimaryButton:hover {{
    background-color: {t['focus']};
}}
QPushButton[class="PrimaryButton"]:pressed, QPushButton.PrimaryButton:pressed, QPushButton#PrimaryButton:pressed {{
    background-color: {t['primary']};
    margin-top: 1px; /* 1px downward shift simulates a physical button press without a real shadow */
}}
QPushButton[class="PrimaryButton"]:disabled, QPushButton.PrimaryButton:disabled, QPushButton#PrimaryButton:disabled {{
    background-color: {t['hover']};
    color: {t['text_muted']};
    border: none;
}}

/* 2. Secondary: Neutral / Surface */
QPushButton[class="SecondaryButton"], QPushButton.SecondaryButton, QPushButton#SecondaryButton {{
    background-color: {t['surface2']};
    color: {t['text']};
    border: 1px solid {t['border_strong']};
}}
QPushButton[class="SecondaryButton"]:hover, QPushButton.SecondaryButton:hover, QPushButton#SecondaryButton:hover {{
    background-color: {t['hover']};
    border-color: {t['border_strong']};
}}
QPushButton[class="SecondaryButton"]:disabled, QPushButton.SecondaryButton:disabled, QPushButton#SecondaryButton:disabled {{
    background-color: {t['surface']};
    color: {t['text_muted']};
    border: 1px solid {t['border']};
}}

/* 3. Danger: Red Fill */
QPushButton[class="DangerButton"], QPushButton.DangerButton, QPushButton#DangerButton {{
    background-color: {t['danger']};
    color: #ffffff;                  /* White text on red maintains contrast and matches PrimaryButton convention */
    border: 1px solid transparent;  /* Transparent border keeps layout dimensions stable across states */
}}
QPushButton[class="DangerButton"]:hover, QPushButton.DangerButton:hover, QPushButton#DangerButton:hover {{
    background-color: {t['focus']};
}}
QPushButton[class="DangerButton"]:disabled, QPushButton.DangerButton:disabled, QPushButton#DangerButton:disabled {{
    background-color: {t['hover']};
    color: {t['text_muted']};
    border: none;
}}

/* Dashboard Profile Dock (right-side utility component)
   border-top is 2px (vs 1px sides) to mimic a raised-top effect,
   adding subtle depth without a real box-shadow.                   */
QFrame#DashboardProfilePanel {{
    background-color: {t['surface']};
    border: 1px solid {t['border']};
    border-top: 2px solid {t['border_strong']}; /* Heavier top edge creates a visual "lift" on the panel */
    border-radius: 14px;                         /* Larger radius than cards gives the dock a pill-like softness */
}}

QFrame#DashboardProfilePanel:hover {{
    border: 1px solid {t['border']};
    border-top: 2px solid {t['border_strong']};
}}

QLabel#DashboardProfileIcon {{
    background: transparent;
    border: none;
    border-radius: 9px; /* Slight radius clips the icon corners to match the panel's rounded shape */
    padding: 0;
}}

QLabel#DashboardProfileEyebrow {{
    color: {t['text_muted']};
    font-size: 10px;          /* Smaller than body text — this is a label-above-label ("eyebrow") pattern */
    font-weight: 800;
    letter-spacing: 0.9px;    /* Wide tracking gives all-caps or short eyebrow text better readability */
}}

QLabel#DashboardProfileMeta {{
    color: {t['text_muted']};
    font-size: 12px;
    font-weight: 600;
}}

QComboBox#DashboardProfileCombo {{
    min-height: 40px;
    padding: 6px 42px 6px 12px; /* 42px right-pad reserves room for the custom drop-down arrow button */
    border-radius: 12px;         /* Rounder than standard combos to fit the dock's softer aesthetic */
    background-color: {t['bg']};
    border: 1px solid {t['border']};
    color: {t['text']};
    font-weight: 600;
    selection-background-color: {t['primary']}; /* Blue selection highlight in editable mode */
    selection-color: #ffffff;
}}

QComboBox#DashboardProfileCombo:hover {{
    border-color: {t['primary']};
    background-color: {t['surface']};
}}

QComboBox#DashboardProfileCombo:focus {{
    border: 1px solid {t['primary']};
    background-color: {t['surface']};
}}

QComboBox#DashboardProfileCombo::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 40px;
    background-color: {t['surface']};
    border-left: 1px solid {t['border']};
    border-top-right-radius: 11px;
    border-bottom-right-radius: 11px;
}}

QComboBox#DashboardProfileCombo::down-arrow {{
    image: none; /* The profile combo uses a custom icon label instead of an SVG arrow */
    width: 0;
    height: 0;
}}

QComboBox#DashboardProfileCombo:on {{
    border-color: {t['primary']};
}}

QComboBox#DashboardProfileCombo:on::drop-down {{
    border-left-color: {t['primary']};
    background-color: {t['hover']};
}}

QPushButton#DashboardProfileAction {{
    min-height: 40px;
    padding: 8px 16px;
    border-radius: 10px;                         /* Slightly rounder than default buttons to match the dock panel */
    background-color: {t['surface']};
    color: {t['text_muted']};                    /* Muted text reduces visual weight for a secondary action */
    border: 1px solid {t['border']};
    border-top: 1px solid {t['border_strong']};  /* Stronger top edge echoes the panel's raised-top treatment */
    font-weight: 700;
}}

QPushButton#DashboardProfileAction:hover {{
    background-color: {t['hover']};
    border-color: {t['primary']};
    color: {t['text']};
}}

QPushButton#DashboardProfileAction:pressed {{
    background-color: {t['surface2']};
}}

/* Harvester Banner Success State
   The entire banner background turns green on completion so the outcome
   is visible at a glance without needing to read the status text.       */
QFrame#HarvestBanner[state="completed"] {{
    background-color: {t['success']}; /* Full green fill makes a completed harvest unmissable */
    border: 1px solid {t['success']}; /* Matching border removes the contrast gap at the edges */
}}

QFrame#HarvestBanner[state="completed"] QLabel {{
    color: {t['text']};
}}

/* --- Links & Utilities ---
   LinkButton renders as inline hyperlink text — no background or border so
   it visually blends into surrounding body copy.                          */
QPushButton[class="LinkButton"], QPushButton.LinkButton {{
    color: {t['primary']};          /* Primary blue matches conventional hyperlink colour */
    text-decoration: underline;     /* Underline distinguishes it from plain label text */
    background: transparent;        /* No fill so the button sits inline without a box */
    border: none;
}}
QPushButton[class="LinkButton"]:hover, QPushButton.LinkButton:hover {{
    color: {t['focus']};
}}

QFrame[class="Divider"], QFrame.Divider {{
    color: {t['border']};
    background-color: {t['border']};
    min-height: 1px; /* min + max both 1px forces the QFrame to be a single-pixel horizontal rule */
    max-height: 1px;
}}

/* --- Progress Bars ---
   TerminalProgressBar is the thin 8px progress strip shown in the harvest
   tab.  The [state="..."] sub-rules below change the chunk colour to match
   the current harvest state (running=blue, success=green, error/cancelled=red,
   paused=amber) so the bar itself communicates the outcome at a glance.  */
QProgressBar[class="TerminalProgressBar"], QProgressBar.TerminalProgressBar {{
    background-color: {t['surface']}; 
    height: 8px; 
    border-radius: 4px; 
    border: none;
}}
QProgressBar[class="TerminalProgressBar"]::chunk, QProgressBar.TerminalProgressBar::chunk {{
    background-color: {t['primary']}; 
    border-radius: 4px; 
}}
QProgressBar[class="TerminalProgressBar"][state="success"]::chunk, QProgressBar.TerminalProgressBar[state="success"]::chunk {{
    background-color: {t['success']}; 
}}
QProgressBar[class="TerminalProgressBar"][state="error"]::chunk, QProgressBar.TerminalProgressBar[state="error"]::chunk, QProgressBar[class="TerminalProgressBar"][state="cancelled"]::chunk, QProgressBar.TerminalProgressBar[state="cancelled"]::chunk {{
    background-color: {t['danger']}; 
}}
QProgressBar[class="TerminalProgressBar"][state="paused"]::chunk, QProgressBar.TerminalProgressBar[state="paused"]::chunk {{
    background-color: {t['warning']}; 
}}

/* --- Targets Tab Classes ---
   The Banner label is the informational strip at the top of the targets
   table with a left accent border (primary colour) that draws the eye. */
QLabel[class="Banner"], QLabel.Banner {{
    color: {t['text_muted']};
    background-color: {t['surface']};
    border-left: 3px solid {t['primary']};
    padding: 10px;
    border-radius: 6px;
    font-size: 11px;
}}

QWidget[class="SearchContainer"], QWidget.SearchContainer {{
    background-color: {t['surface']};
    border: 2px solid {t['border_strong']};
    border-radius: 10px;
    min-height: 44px;
}}
QWidget[class="SearchContainer"] QLineEdit, QWidget.SearchContainer QLineEdit {{
    background-color: transparent;
    border: none;
    color: {t['text']};
    padding: 10px 14px;
    min-width: 180px;
    font-size: 15px;
    font-weight: 600;
}}
QWidget[class="SearchContainer"] QLineEdit::placeholder, QWidget.SearchContainer QLineEdit::placeholder {{
    color: {t['text']};
}}
QWidget[class="SearchContainer"] QToolButton, QWidget.SearchContainer QToolButton {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: {t['text']};
    font-weight: bold;
    font-size: 16px;
    min-width: 32px;
    min-height: 32px;
    margin-right: 6px;
}}
QWidget[class="SearchContainer"] QToolButton:hover, QWidget.SearchContainer QToolButton:hover {{
    background-color: {t['hover']};
    color: {t['primary']};
}}
QWidget[class="SearchContainer"]:hover, QWidget.SearchContainer:hover {{
    border-color: {t['primary']};
}}
QWidget[class="SearchContainer"]:focus-within, QWidget.SearchContainer:focus-within {{
    border-color: {t['focus']};
    background-color: {t['surface']};
}}

QPushButton[class="IconButton"], QPushButton.IconButton {{
    background-color: {t['surface2']};
    color: {t['text']};
    border: 2px solid {t['border_strong']};
    border-radius: 8px;
    padding: 8px 12px;
}}
QPushButton[class="IconButton"]:hover, QPushButton.IconButton:hover {{
    background-color: {t['hover']};
    border-color: {t['primary']};
}}

/* --- Group Boxes ---
   margin-top + padding-top create the inset zone where the title label
   overlaps the top border — the standard QSS group-box title technique. */
QGroupBox {{
    background-color: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    margin-top: 14px;    /* Leaves space above the border for the title to sit in */
    padding-top: 14px;   /* Pushes group content below the title label */
}}
QGroupBox::title {{
    subcontrol-origin: margin; /* Positions the title relative to the margin area, not the border */
    subcontrol-position: top left;
    left: 10px;                /* Indents the title slightly from the left border */
    padding: 0 4px;            /* Horizontal padding clears the border behind the title text */
    color: {t['text_muted']};
    font-weight: bold;
    font-size: 13px;
}}

/* --- Harvest Tab Status Box ---
   The 4px left border is the primary status indicator — its colour changes
   per state (see sub-rules below) so users can scan the status at a glance
   without reading the text.                                               */
QFrame[class="HarvestStatus"], QFrame.HarvestStatus {{
    background-color: {t['surface']};
    border-radius: 8px;
    border: 1px solid {t['border_strong']};
    border-left: 4px solid {t['border']}; /* Thicker left accent; colour is overridden per harvest state */
}}
QFrame[class="HarvestStatus"][state="ready"], QFrame.HarvestStatus[state="ready"] {{
    border-left-color: {t['primary']};
}}
QFrame[class="HarvestStatus"][state="running"], QFrame.HarvestStatus[state="running"] {{
    border-left-color: {t['primary']};
}}
QFrame[class="HarvestStatus"][state="paused"], QFrame.HarvestStatus[state="paused"] {{
    border-left-color: {t['warning']};
}}
QFrame[class="HarvestStatus"][state="error"], QFrame.HarvestStatus[state="error"], QFrame.HarvestStatus[state="cancelled"] {{
    border-left-color: {t['danger']};
}}
QFrame[class="HarvestStatus"][state="completed"], QFrame.HarvestStatus[state="completed"] {{
    border-left-color: {t['success']};
}}

QLabel[class="StatusTitle"], QLabel.StatusTitle {{
    font-size: 16px; 
    font-weight: bold; 
    letter-spacing: 1px; 
    border: none;
    color: {t['text_muted']};
}}
QLabel[class="StatusTitle"][state="ready"], QLabel.StatusTitle[state="ready"] {{
    color: {t['primary']};
}}
QLabel[class="StatusTitle"][state="running"], QLabel.StatusTitle[state="running"] {{
    color: {t['primary']};
}}
QLabel[class="StatusTitle"][state="paused"], QLabel.StatusTitle[state="paused"] {{
    color: {t['warning']};
}}
QLabel[class="StatusTitle"][state="error"], QLabel.StatusTitle[state="error"], QLabel.StatusTitle[state="cancelled"] {{
    color: {t['danger']};
}}
QLabel[class="StatusTitle"][state="completed"], QLabel.StatusTitle[state="completed"] {{
    color: {t['success']};
}}

QLabel[class="StatusText"], QLabel.StatusText {{
    font-size: 14px; 
    font-weight: bold;
    color: {t['text_muted']};
}}
QLabel[class="StatusText"][state="ready"], QLabel.StatusText[state="ready"] {{
    color: {t['primary']};
}}
QLabel[class="StatusText"][state="running"], QLabel.StatusText[state="running"] {{
    color: {t['primary']};
}}
QLabel[class="StatusText"][state="paused"], QLabel.StatusText[state="paused"] {{
    color: {t['warning']};
}}
QLabel[class="StatusText"][state="error"], QLabel.StatusText[state="error"], QLabel.StatusText[state="cancelled"] {{
    color: {t['danger']};
}}
QLabel[class="StatusText"][state="completed"], QLabel.StatusText[state="completed"] {{
    color: {t['success']};
}}

/* ActiveToggle: toggles a target row between enabled (green) and disabled (red).
   Hover always shows focus-blue so the affordance remains obvious regardless of
   the current active/inactive state.                                           */
QPushButton#ActiveToggle[state="active"] {{
    background-color: {t['success']}; /* Green signals the target is currently enabled */
    border: none;
    border-radius: 6px;
}}
QPushButton#ActiveToggle[state="active"]:hover {{
    background-color: {t['focus']}; /* Blue on hover hints that a click will change the state */
}}
QPushButton#ActiveToggle[state="inactive"] {{
    background-color: {t['danger']}; /* Red signals the target is currently disabled */
    border: none;
    border-radius: 6px;
}}
QPushButton#ActiveToggle[state="inactive"]:hover {{
    background-color: {t['focus']}; /* Same blue-hover intent as the active state above */
}}

/* --- Shortcuts Dialog --- */
QFrame[class="ShortcutItem"] {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 6px; /* Small radius keeps the shortcut rows compact and scannable */
    padding: 8px;
    margin: 4px;        /* Small gap between rows prevents them from merging into a block */
}}
QFrame[class="ShortcutItem"]:hover {{
    background: {t['hover']};
    border: 1px solid {t['primary']}; /* Accent border on hover signals the item is interactive */
}}
QLabel#ShortcutKeys {{
    background: {t['bg']};  /* Inset background makes the key badge look like a rendered key cap */
    color: {t['primary']};  /* Blue text draws the eye to the key sequence first */
    font-size: 12px;
    font-weight: bold;
    padding: 6px 12px;
    border-radius: 4px;
    min-width: 120px;       /* Fixed min-width keeps key badges aligned across all rows */
}}
QLabel#ShortcutDesc {{
    color: {t['text']};
    font-size: 13px;
    padding-left: 10px;
}}
QLabel#DialogHeader {{
    color: {t['text']};
    font-size: 24px;
    font-weight: bold;
    padding: 10px;
}}
QLabel#DialogSubtitle {{
    color: {t['text_muted']};
    font-size: 12px;
    padding-bottom: 10px;
}}
QScrollArea[class="TransparentScroll"] {{
    background: transparent;
    border: none;
}}
QLabel#CategoryHeader {{
    color: {t['text']};
    font-size: 16px;
    font-weight: bold;
    padding: 8px;
    border-bottom: 2px solid {t['border_strong']}; /* Underline visually separates each category group */
    margin-top: 10px; /* Extra top margin spaces categories apart when the list is scrolled */
}}

/* --- Harvest Tab: Stat Tiles (File Statistics + MARC) ---
   StatTile widgets are fixed-height summary boxes (e.g. "Total ISBNs",
   "Records Found").  StatTileValue / StatTileValueSmall differ only in
   font-size so smaller numbers don't need a separate widget class.      */
QWidget[class="StatTile"] {{
    background-color: {t['surface2']}; /* Slightly raised surface distinguishes stat tiles from the page bg */
    border-radius: 8px;
    border: 1px solid {t['border']};
}}
QLabel[class="StatTileValue"] {{
    font-size: 22px;    /* Prominent number display — large but smaller than dashboard CardValue (32px) */
    font-weight: 700;
    color: {t['text']};
    background: transparent; /* Inherits the StatTile background without painting its own rectangle */
    border: none;
}}
QLabel[class="StatTileValueSmall"] {{
    font-size: 20px;    /* Slightly smaller variant for tiles where the number can be longer */
    font-weight: 700;
    color: {t['text']};
    background: transparent;
    border: none;
}}
QLabel[class="StatTileLabel"] {{
    font-size: 11px;
    color: {t['text_muted']};
    font-weight: 500;
    background: transparent;
    border: none;
}}
QLabel[class="StatTileLabelSmall"] {{
    font-size: 10px;
    color: {t['text_muted']};
    background: transparent;
    border: none;
}}

/* --- Harvest Tab: MARC Status Banner ---
   Inline info strip shown beneath the MARC import controls to report
   the current parser state (e.g. "File loaded", "Parsing…").         */
QLabel[class="MarcStatusBanner"] {{
    background-color: {t['surface2']}; /* Slightly raised bg frames the status text as a distinct info strip */
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;   /* Smaller than body text — secondary information, not the primary focus */
    color: {t['text_muted']};
}}

/* --- Harvest Tab: MARC Drop Zone ---
   Dashed border is the conventional drag-and-drop affordance; surface2
   background gives it a subtle inset appearance inside the card.      */
QFrame[class="MarcDropZone"] {{
    border: 2px dashed {t['border_strong']}; /* Dashed style distinguishes drop targets from solid-bordered cards */
    border-radius: 8px;
    background-color: {t['surface2']}; /* Slightly recessed surface cues users to "drop something here" */
}}
"""

# Pre-generated dark fallback stylesheet evaluated at module import time.
# Importing this constant does not trigger a redundant generation at runtime
# because Python caches the module; callers that always want the current
# theme should call generate_stylesheet(palette) directly.
DEFAULT_STYLESHEET = generate_stylesheet(CATPPUCCIN_DARK)
