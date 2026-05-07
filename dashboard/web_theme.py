from __future__ import annotations


_THEME_STYLES = '''
    :root {
      color-scheme: light;
      --bg: #FAF6F1;
      --bg-warm: #F4ECE2;
      --panel: #FFFFFF;
      --surface-2: #F4ECE2;
      --ink: #1F1714;
      --ink-2: #3D2F26;
      --muted: #7A6A5C;
      --muted-2: #A8998A;
      --line: #EADFD2;
      --line-strong: #D8C7B5;
      --accent: #B85B2E;
      --accent-hover: #9E4A22;
      --accent-soft: #FBE5D2;
      --accent-ink: #7A3712;
      --warn: #C77A1A;
      --warn-soft: #FCEFD3;
      --success: #4F7042;
      --success-soft: #E4EED8;
      --danger: #B0413A;
      --danger-soft: #F6DAD6;
      --shadow-1: 0 1px 2px rgba(31,23,20,.04), 0 1px 0 rgba(31,23,20,.02);
      --shadow-2: 0 8px 28px -12px rgba(31,23,20,.18), 0 2px 6px -2px rgba(31,23,20,.06);
      --shadow-focus: 0 0 0 3px rgba(184,91,46,.22);
      --r-sm: 6px;
      --r-md: 10px;
      --r-lg: 14px;
      --r-xl: 20px;
      --r-pill: 999px;
      --font-sans: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif;
      --font-display: "Fraunces", Georgia, "Times New Roman", serif;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      background:
        radial-gradient(1200px 600px at 100% -10%, rgba(184,91,46,.06), transparent 60%),
        radial-gradient(800px 500px at -10% 110%, rgba(199,122,26,.05), transparent 60%),
        var(--bg);
      color: var(--ink);
      font-family: var(--font-sans);
      font-size: 14px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { color: var(--accent-hover); }
    code {
      background: var(--surface-2);
      border-radius: 4px;
      color: var(--ink-2);
      font-size: 12.5px;
      padding: 2px 6px;
    }
    h1, h2, h3 {
      font-family: var(--font-display);
      color: var(--ink-2);
      letter-spacing: -0.01em;
    }
    /* ---- Shell ---- */
    .layout {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 252px minmax(0, 1fr);
      grid-template-rows: 64px 1fr;
      grid-template-areas:
        "topbar topbar"
        "sidebar main";
    }
    .topbar {
      grid-area: topbar;
      position: sticky;
      top: 0;
      z-index: 20;
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 0 28px;
      background: rgba(255,255,255,.82);
      backdrop-filter: saturate(140%) blur(10px);
      border-bottom: 1px solid var(--line);
    }
    .brand-mark {
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: var(--font-display);
      font-weight: 700;
      font-size: 17px;
      color: var(--ink-2);
      letter-spacing: -0.01em;
    }
    .brand-mark .leaf {
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: linear-gradient(135deg, var(--accent), #D9824A);
      display: grid;
      place-items: center;
      box-shadow: var(--shadow-1);
      color: #fff;
    }
    .brand-tag {
      color: var(--muted);
      font-family: var(--font-sans);
      font-weight: 500;
      font-size: 12px;
      letter-spacing: .12em;
      text-transform: uppercase;
      padding-left: 12px;
      border-left: 1px solid var(--line);
      margin-left: 4px;
    }
    .topbar-meta {
      margin-left: auto;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .meta-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: var(--r-pill);
      background: var(--bg-warm);
      border: 1px solid var(--line);
      color: var(--ink-2);
      font-size: 12.5px;
      font-weight: 500;
    }
    .meta-pill .dot {
      width: 7px; height: 7px; border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 0 3px rgba(79,112,66,.18);
    }
    .meta-pill code { background: transparent; padding: 0; color: var(--muted); white-space: nowrap; }
    .meta-pill svg { width: 14px; height: 14px; flex: 0 0 14px; color: var(--muted); }
    .brand-mark .leaf svg { width: 16px; height: 16px; }
    .sidebar {
      grid-area: sidebar;
      border-right: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,.6), rgba(255,255,255,0));
      padding: 24px 14px 32px;
      position: sticky;
      top: 64px;
      align-self: start;
      max-height: calc(100vh - 64px);
      overflow-y: auto;
    }
    .nav-group { margin-bottom: 22px; }
    .nav-group-label {
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .14em;
      text-transform: uppercase;
      color: var(--muted-2);
      margin: 0 12px 8px;
    }
    .nav-link {
      position: relative;
      display: flex;
      align-items: center;
      gap: 10px;
      border-radius: var(--r-md);
      color: var(--ink-2);
      padding: 9px 12px;
      text-decoration: none;
      font-size: 14px;
      font-weight: 500;
      transition: background-color .15s ease, color .15s ease;
    }
    .nav-link + .nav-link { margin-top: 2px; }
    .nav-link:hover { background: var(--bg-warm); color: var(--ink); }
    .nav-link svg { width: 18px; height: 18px; flex: 0 0 18px; color: var(--muted); }
    .nav-link[aria-current="page"] {
      background: var(--accent-soft);
      color: var(--accent-ink);
      font-weight: 600;
    }
    .nav-link[aria-current="page"] svg { color: var(--accent); }
    .nav-link[aria-current="page"]::before {
      content: "";
      position: absolute;
      left: -14px;
      top: 8px; bottom: 8px;
      width: 3px;
      border-radius: 0 3px 3px 0;
      background: var(--accent);
    }
    main {
      grid-area: main;
      padding: 32px 40px 64px;
      max-width: 1280px;
      width: 100%;
    }
    /* ---- Page header ---- */
    .breadcrumb {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12.5px;
      color: var(--muted);
      margin: 0 0 12px;
    }
    .breadcrumb a { color: var(--muted); }
    .breadcrumb a:hover { color: var(--accent); }
    .breadcrumb .sep { color: var(--muted-2); }
    .breadcrumb .current { color: var(--ink-2); font-weight: 600; }
    h1 {
      font-size: 32px;
      line-height: 1.1;
      font-weight: 700;
      margin: 0 0 10px;
    }
    .lede {
      color: var(--muted);
      font-size: 15px;
      margin: 0 0 28px;
      max-width: 760px;
    }
    h2 { font-weight: 600; }
    h3 { font-weight: 600; font-family: var(--font-sans); }
    /* ---- Grids ---- */
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
    }
    /* ---- Buttons ---- */
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 0 0 24px;
    }
    .action-link,
    .action-form button,
    .run-control-form button,
    .curation-form button,
    .settings-form button,
    .rollback-form button,
    .search-form button,
    .recommendation-form button,
    .pattern-form button {
      background: var(--accent);
      border: 1px solid transparent;
      border-radius: var(--r-md);
      color: #ffffff;
      cursor: pointer;
      font-family: inherit;
      font-size: 13.5px;
      font-weight: 600;
      line-height: 1.2;
      padding: 10px 16px;
      text-decoration: none;
      box-shadow: 0 1px 0 rgba(255,255,255,.18) inset, var(--shadow-1);
      transition: background-color .15s ease, box-shadow .15s ease, transform .05s ease;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .action-link:hover,
    .action-form button:hover,
    .run-control-form button:hover,
    .curation-form button:hover,
    .settings-form button:hover,
    .rollback-form button:hover,
    .search-form button:hover,
    .recommendation-form button:hover,
    .pattern-form button:hover { background: var(--accent-hover); color: #fff; }
    .action-link:focus-visible,
    button:focus-visible { outline: none; box-shadow: var(--shadow-focus); }
    .action-link:active, button:active { transform: translateY(1px); }
    .action-link.secondary,
    a.action-link[href^="/exports/"] {
      background: var(--panel);
      color: var(--ink-2);
      border-color: var(--line-strong);
      box-shadow: var(--shadow-1);
    }
    .action-link.secondary:hover,
    a.action-link[href^="/exports/"]:hover { background: var(--bg-warm); color: var(--ink); }
    .action-form { margin: 0; }
    /* ---- Run controls ---- */
    .run-controls {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-bottom: 18px;
    }
    .run-control-form {
      display: grid;
      gap: 12px;
    }
    .run-control-form button { justify-self: start; }
    /* ---- Cards / Panels ---- */
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--r-lg);
      padding: 22px;
      min-height: 132px;
      box-shadow: var(--shadow-1);
      transition: box-shadow .2s ease, transform .2s ease;
    }
    .panel h2 {
      font-size: 13px;
      font-weight: 600;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
      margin: 0 0 12px;
      font-family: var(--font-sans);
    }
    .panel.feature {
      box-shadow: var(--shadow-2);
      border-color: var(--line);
      position: relative;
      overflow: hidden;
    }
    .panel.feature::before {
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 3px;
      background: linear-gradient(90deg, var(--accent), #E08858);
    }
    .metric {
      font-family: var(--font-display);
      font-size: 36px;
      font-weight: 600;
      letter-spacing: -0.02em;
      line-height: 1.05;
      color: var(--ink-2);
      margin: 0 0 8px;
      font-feature-settings: "tnum";
    }
    .metric.muted { color: var(--muted-2); font-weight: 500; }
    .muted { color: var(--muted); }
    .notice {
      background: var(--warn-soft);
      border-color: rgba(199,122,26,.35);
    }
    .notice h2 { color: var(--warn); }
    .panel.healthy { background: linear-gradient(180deg, var(--success-soft), var(--panel) 70%); border-color: rgba(79,112,66,.3); }
    .panel.healthy .metric { color: var(--success); }
    .panel.degraded { background: linear-gradient(180deg, var(--warn-soft), var(--panel) 70%); border-color: rgba(199,122,26,.35); }
    .panel.degraded .metric { color: var(--warn); }
    .panel.failing { background: linear-gradient(180deg, var(--danger-soft), var(--panel) 70%); border-color: rgba(176,65,58,.3); }
    .panel.failing .metric { color: var(--danger); }
    .wide-panel { margin-top: 18px; }
    /* ---- Empty state ---- */
    .empty-state {
      display: flex;
      align-items: center;
      gap: 14px;
      color: var(--muted);
      font-size: 13.5px;
    }
    .empty-state-icon {
      width: 36px; height: 36px; flex: 0 0 36px;
      border-radius: 10px;
      background: var(--bg-warm);
      display: grid; place-items: center;
      color: var(--muted-2);
    }
    /* ---- Lists ---- */
    .compact-list,
    .video-list {
      margin: 0;
      padding-left: 18px;
    }
    .compact-list li + li {
      margin-top: 8px;
    }
    .compact-list li::marker { color: var(--accent); }
    .video-list {
      list-style: none;
      padding-left: 0;
    }
    .video-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
      border-top: 1px solid var(--line);
      padding: 14px 0;
    }
    .video-row:first-child { border-top: 0; padding-top: 4px; }
    .video-caption {
      font-weight: 600;
      color: var(--ink-2);
      margin: 0 0 4px;
    }
    .video-row a {
      color: var(--accent);
      font-weight: 600;
    }
    .content-list {
      display: grid;
      gap: 18px;
    }
    .scraped-card-header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
    }
    .scraped-card-header h2 {
      margin: 0 0 6px;
      color: var(--ink-2);
      font-size: 16px;
      font-family: var(--font-sans);
      text-transform: none;
      letter-spacing: 0;
    }
    .metadata-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin: 18px 0;
      padding: 14px 0;
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }
    .metadata-grid dt {
      color: var(--muted);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .08em;
      margin: 0 0 4px;
      text-transform: uppercase;
    }
    .metadata-grid dd {
      margin: 0;
      color: var(--ink-2);
      font-size: 13.5px;
      overflow-wrap: anywhere;
    }
    .table-scroll {
      overflow-x: auto;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: var(--r-lg);
      background: var(--panel);
    }
    .data-table {
      border-collapse: collapse;
      min-width: 1180px;
      width: 100%;
    }
    .data-table th,
    .data-table td {
      border-top: 1px solid var(--line);
      font-size: 13px;
      line-height: 1.4;
      padding: 12px 14px;
      text-align: left;
      vertical-align: top;
    }
    .data-table thead th {
      background: var(--surface-2);
      border-top: 0;
      color: var(--muted);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .08em;
      text-transform: uppercase;
      position: sticky;
      top: 0;
    }
    .data-table tbody tr:hover td { background: var(--bg-warm); }
    .data-table a {
      color: var(--accent);
      font-weight: 600;
    }
    h3 {
      font-size: 14px;
      font-weight: 600;
      color: var(--ink-2);
      margin: 16px 0 8px;
    }
    .output-links {
      min-width: 180px;
    }
    /* ---- Forms ---- */
    .curation-form {
      border-top: 1px solid var(--line);
      display: grid;
      gap: 14px;
      padding-top: 16px;
      margin-top: 4px;
    }
    .curation-form fieldset {
      border: 0;
      margin: 0;
      padding: 0;
    }
    .curation-form legend,
    .field-label {
      color: var(--muted);
      display: grid;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .08em;
      text-transform: uppercase;
      gap: 6px;
    }
    .label-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      margin-top: 8px;
    }
    .check-label {
      align-items: center;
      display: inline-flex;
      gap: 8px;
      font-size: 13px;
      font-weight: 400;
      letter-spacing: 0;
      text-transform: none;
      color: var(--ink-2);
      padding: 6px 10px;
      border-radius: var(--r-pill);
      background: var(--bg-warm);
      border: 1px solid var(--line);
    }
    .check-label input { accent-color: var(--accent); }
    .field-label input,
    .field-label textarea {
      background: var(--panel);
      border: 1px solid var(--line-strong);
      border-radius: var(--r-md);
      color: var(--ink);
      font: inherit;
      font-size: 14px;
      letter-spacing: 0;
      text-transform: none;
      font-weight: 400;
      padding: 10px 12px;
      width: 100%;
      transition: border-color .15s ease, box-shadow .15s ease;
    }
    .field-label input:focus,
    .field-label textarea:focus {
      border-color: var(--accent);
      box-shadow: var(--shadow-focus);
      outline: none;
    }
    .field-label textarea {
      min-height: 80px;
      resize: vertical;
      font-family: var(--font-sans);
    }
    .curation-form button { justify-self: start; }
    .settings-form {
      display: grid;
      gap: 16px;
    }
    .settings-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    .settings-form select,
    .recommendation-form select,
    .recommendation-form input {
      background: var(--panel);
      border: 1px solid var(--line-strong);
      border-radius: var(--r-md);
      color: var(--ink);
      font: inherit;
      padding: 10px 12px;
      width: 100%;
      transition: border-color .15s ease, box-shadow .15s ease;
    }
    .settings-form select:focus,
    .recommendation-form select:focus,
    .recommendation-form input:focus {
      border-color: var(--accent);
      box-shadow: var(--shadow-focus);
      outline: none;
    }
    .settings-form button,
    .rollback-form button { justify-self: start; }
    .history-list {
      display: grid;
      gap: 14px;
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .history-item {
      border-top: 1px solid var(--line);
      padding-top: 14px;
    }
    .rollback-form {
      display: grid;
      gap: 10px;
      margin-top: 12px;
    }
    .recommendation-list {
      display: grid;
      gap: 18px;
    }
    .recommendation-header,
    .pattern-header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
    }
    .recommendation-header h2,
    .pattern-header h2 {
      color: var(--ink-2);
      font-family: var(--font-sans);
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0;
      text-transform: none;
      margin: 0 0 4px;
    }
    .status-pill {
      background: var(--bg-warm);
      border: 1px solid var(--line);
      border-radius: var(--r-pill);
      color: var(--muted);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .06em;
      line-height: 1;
      padding: 7px 11px;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .status-pill.ok { background: var(--success-soft); color: var(--success); border-color: rgba(79,112,66,.3); }
    .status-pill.warn { background: var(--warn-soft); color: var(--warn); border-color: rgba(199,122,26,.35); }
    .status-pill.err { background: var(--danger-soft); color: var(--danger); border-color: rgba(176,65,58,.3); }
    .status-pill.accent { background: var(--accent-soft); color: var(--accent-ink); border-color: rgba(184,91,46,.3); }
    .search-form {
      display: grid;
      gap: 14px;
    }
    .search-form input {
      background: var(--panel);
      border: 1px solid var(--line-strong);
      border-radius: var(--r-md);
      color: var(--ink);
      font: inherit;
      font-size: 15px;
      padding: 12px 14px;
      width: 100%;
      transition: border-color .15s ease, box-shadow .15s ease;
    }
    .search-form input:focus {
      border-color: var(--accent);
      box-shadow: var(--shadow-focus);
      outline: none;
    }
    .search-form button { justify-self: start; }
    .facet-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px 16px;
    }
    .search-result-list {
      display: grid;
      gap: 14px;
    }
    .search-result-header {
      align-items: start;
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(0, 1fr) auto;
    }
    .recommendation-form {
      align-items: end;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }
    .pattern-list {
      display: grid;
      gap: 18px;
    }
    .pattern-form {
      border-top: 1px solid var(--line);
      display: grid;
      gap: 14px;
      margin-top: 16px;
      padding-top: 16px;
    }
    .pattern-form-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    .pattern-form button { justify-self: start; }
    /* ---- Responsive ---- */
    @media (max-width: 960px) {
      .layout {
        grid-template-columns: 1fr;
        grid-template-rows: 64px auto 1fr;
        grid-template-areas:
          "topbar"
          "sidebar"
          "main";
      }
      .sidebar {
        position: static;
        max-height: none;
        border-right: 0;
        border-bottom: 1px solid var(--line);
        padding: 14px 16px;
        display: flex;
        gap: 6px;
        overflow-x: auto;
      }
      .nav-group { margin: 0; flex: 0 0 auto; }
      .nav-group-label { display: none; }
      .nav-link { white-space: nowrap; padding: 8px 12px; }
      .nav-link[aria-current="page"]::before { display: none; }
      .topbar { padding: 0 16px; }
      .brand-tag { display: none; }
      .topbar-meta .meta-pill:not(.primary) { display: none; }
      main { padding: 24px 18px; }
      .grid { grid-template-columns: 1fr; }
      .video-row { grid-template-columns: 1fr; }
      .scraped-card-header,
      .run-controls,
      .settings-grid,
      .pattern-form-grid,
      .facet-grid,
      .metadata-grid { grid-template-columns: 1fr; }
    }
'''.strip()


def render_theme_styles() -> str:
    return _THEME_STYLES
