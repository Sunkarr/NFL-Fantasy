import marimo

__generated_with = "0.24.2"
app = marimo.App(
    width="full",
    app_title="🏈 NFL Fantasy Analytics"
)


@app.cell
def _():
    import marimo as mo
    import pandas as pd

    from src.config import DB_PATH, DEFAULT_LEAGUE_ID, VERSION
    from src.db import load_league_data
    from src.stats import compute_player_aggregates, get_league_overview_analytics, get_team_roster_analytics
    from src.visual import build_interactive_position_chart, get_owner_color_map

    # Lightweight observer: update document title & link icon without busy polling loop
    head_favicon = mo.Html(
        """
        <script>
        (function() {
            function setFavicon() {
                document.title = "🏈 NFL Fantasy Analytics";
                var link = document.querySelector("link[rel*='icon']");
                if (!link) {
                    link = document.createElement('link');
                    link.rel = 'shortcut icon';
                    document.getElementsByTagName('head')[0].appendChild(link);
                }
                if (link.getAttribute('href') !== 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🏈</text></svg>') {
                    link.type = 'image/svg+xml';
                    link.href = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🏈</text></svg>';
                }
            }
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', setFavicon);
            } else {
                setFavicon();
            }
            setTimeout(setFavicon, 1000);
            setTimeout(setFavicon, 3000);
        })();
        </script>
        """
    )

    return (
        DB_PATH,
        DEFAULT_LEAGUE_ID,
        VERSION,
        build_interactive_position_chart,
        compute_player_aggregates,
        get_league_overview_analytics,
        get_owner_color_map,
        get_team_roster_analytics,
        head_favicon,
        load_league_data,
        mo,
    )


@app.cell
def _(head_favicon):
    head_favicon
    return


@app.cell
def _(
    DB_PATH,
    DEFAULT_LEAGUE_ID,
    compute_player_aggregates,
    get_owner_color_map,
    load_league_data,
):
    df_teams, df_current_rosters, df_matchups, df_nfl_stats = load_league_data(DB_PATH, DEFAULT_LEAGUE_ID)
    df_player_stats = compute_player_aggregates(df_nfl_stats) if df_nfl_stats is not None else None

    unique_teams = sorted([t for t in df_teams['team_name'].unique()]) if df_teams is not None and not df_teams.empty else []
    owner_colors = get_owner_color_map(unique_teams)
    return (
        df_current_rosters,
        df_player_stats,
        df_teams,
        owner_colors,
        unique_teams,
    )


@app.cell
def _(df_teams, mo):
    if df_teams is None or df_teams.empty:
        mo.stop(
            mo.md(
                """
                > ⚠️ **No data found in `data/fantasy.db`!**  
                > Please run `python downloader.py` to populate the database.
                """
            )
        )
    return


@app.cell
def _(mo):
    # Top tab navigation in requested order with clean empty tab containers
    nav_tabs = mo.ui.tabs({
        "🏆 League Overview": mo.md(""),
        "🛡️ Team Analytics": mo.md(""),
        "📊 Position Scatter": mo.md("")
    })
    nav_tabs
    return (nav_tabs,)


@app.cell
def _(df_teams, mo, nav_tabs):
    if nav_tabs.value == "📊 Position Scatter":
        pos_select = mo.ui.radio(
            options=["QB", "RB", "WR", "TE", "DEF", "K"],
            value="QB",
            inline=True,
            label="Position:"
        )
        min_pts_slider = mo.ui.slider(
            start=0,
            stop=20,
            step=1,
            value=3,
            label="Min Avg Points:"
        )
        limit_slider = mo.ui.slider(
            start=10,
            stop=35,
            step=5,
            value=20,
            label="Max Players:"
        )
        _filter_bar = mo.hstack([pos_select, min_pts_slider, limit_slider], justify="start", align="center", gap=2)
        team_dropdown = None
    elif nav_tabs.value == "🛡️ Team Analytics":
        pos_select = None
        min_pts_slider = None
        limit_slider = None

        _team_options = {}
        if df_teams is not None and not df_teams.empty:
            for _, _r_team in df_teams.iterrows():
                _team_options[f"{_r_team['team_name']} ({_r_team['wins']}-{_r_team['losses']})"] = _r_team['team_name']

        team_dropdown = mo.ui.dropdown(
            options=_team_options,
            value=list(_team_options.keys())[0] if _team_options else None,
            label="Select Team:"
        )
        _filter_bar = mo.hstack([team_dropdown], justify="start", align="center", gap=2)
    else:
        pos_select = None
        min_pts_slider = None
        limit_slider = None
        team_dropdown = None
        _filter_bar = None

    _filter_bar if _filter_bar is not None else mo.md("")
    return limit_slider, min_pts_slider, pos_select, team_dropdown


@app.cell
def _(
    VERSION,
    build_interactive_position_chart,
    df_current_rosters,
    df_player_stats,
    df_teams,
    get_league_overview_analytics,
    get_team_roster_analytics,
    limit_slider,
    min_pts_slider,
    mo,
    nav_tabs,
    owner_colors,
    pos_select,
    team_dropdown,
    unique_teams,
):
    # Dynamic Git SHA retrieval
    import subprocess
    try:
        _git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        _git_sha = "latest"

    # Fixed Floating Bottom-Right Corner Badge with Version
    _fixed_corner_badge = mo.Html(
        f"""
        <div style="position: fixed; bottom: 14px; right: 16px; z-index: 9999; display: flex; align-items: center; gap: 8px; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border: 1px solid #e2e8f0; border-radius: 20px; padding: 6px 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 0.76rem; color: #475569;">
            <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.7);"></span>
            <span style="font-weight: 700; color: #0f172a;">v{VERSION}</span>
            <span style="color: #cbd5e1;">•</span>
            <span style="background: #f1f5f9; color: #334155; padding: 2px 7px; border-radius: 5px; font-family: monospace; font-weight: 700; font-size: 0.72rem;">{_git_sha}</span>
            <span style="color: #94a3b8; font-size: 0.7rem;">(09:00 / 18:30 CET)</span>
        </div>
        """
    )

    if nav_tabs.value == "📊 Position Scatter":
        _pos_code = pos_select.value if pos_select else "QB"
        _min_pts = min_pts_slider.value if min_pts_slider else 3
        _top_limit = limit_slider.value if limit_slider else 20

        _filtered_pos = df_player_stats[
            (df_player_stats['position'] == _pos_code) &
            (df_player_stats['mean_points'] >= _min_pts)
        ].sort_values(by='mean_points', ascending=False).head(_top_limit).copy()

        if _filtered_pos.empty:
            _content = mo.md("No players match the current criteria.")
        else:
            _content = build_interactive_position_chart(
                pos_data=_filtered_pos,
                unique_teams=unique_teams,
                owner_colors=owner_colors,
                chart_width=880,
                chart_height=520
            )

        _view = mo.vstack([_content, _fixed_corner_badge], gap=1)

    elif nav_tabs.value == "🛡️ Team Analytics":
        if team_dropdown is None or not team_dropdown.value:
            _view = mo.md("Please select a team.")
        else:
            _selected_team = team_dropdown.value
            _t = get_team_roster_analytics(_selected_team, df_current_rosters, df_player_stats, df_teams)

            if not _t:
                _view = mo.md(f"No roster data available for {_selected_team}.")
            else:
                # Sleek Unified KPI Box
                _pos_pills = []
                _pos_colors = {
                    'QB': '#f43f5e',
                    'RB': '#06b6d4',
                    'WR': '#3b82f6',
                    'TE': '#f59e0b',
                    'K': '#a855f7',
                    'DEF': '#64748b'
                }
                for _p in ['QB', 'RB', 'WR', 'TE', 'DEF', 'K']:
                    _val = _t['pos_breakdown'].get(_p, 0.0)
                    _p_col = _pos_colors.get(_p, '#64748b')
                    _pos_pills.append(
                        f"""
                        <div style="display:flex; align-items:center; gap:6px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:4px 10px;">
                            <span style="font-weight:700; font-size:0.75rem; color:{_p_col};">{_p}</span>
                            <span style="font-weight:600; font-size:0.82rem; color:#1e293b;">{_val:.1f} <span style="font-size:0.7rem; color:#94a3b8; font-weight:normal;">PPG</span></span>
                        </div>
                        """
                    )

                _kpi_box = mo.md(
                    f"""
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:18px 22px; margin-bottom:18px; box-shadow:0 1px 4px rgba(0,0,0,0.03); font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                        <!-- Top KPI Row -->
                        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:16px; padding-bottom:16px; border-bottom:1px solid #f1f5f9;">
                            <div>
                                <div style="font-size:0.76rem; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">Team Record</div>
                                <div style="font-size:1.45rem; font-weight:800; color:#0f172a; margin:2px 0;">{_t['wins']} - {_t['losses']}</div>
                                <div style="font-size:0.74rem; color:#94a3b8;">Total: {_t['total_fpts']:.1f} FPTS</div>
                            </div>
                            <div>
                                <div style="font-size:0.76rem; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">Starting PPG</div>
                                <div style="font-size:1.45rem; font-weight:800; color:#0f172a; margin:2px 0;">{_t['starter_ppg']:.1f} <span style="font-size:0.85rem; font-weight:600; color:#64748b;">FPTS</span></div>
                                <div style="font-size:0.74rem; color:#94a3b8;">Avg Starter Output / Wk</div>
                            </div>
                            <div>
                                <div style="font-size:0.76rem; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">Bench Depth</div>
                                <div style="font-size:1.45rem; font-weight:800; color:#0f172a; margin:2px 0;">{_t['bench_ppg']:.1f} <span style="font-size:0.85rem; font-weight:600; color:#64748b;">FPTS</span></div>
                                <div style="font-size:0.74rem; color:#94a3b8;">{len(_t['bench_df'])} Bench Options</div>
                            </div>
                            <div>
                                <div style="font-size:0.76rem; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">⭐ Top 10 Assets</div>
                                <div style="font-size:1.45rem; font-weight:800; color:#0f172a; margin:2px 0;">{_t['top_10_count']} <span style="font-size:0.85rem; font-weight:600; color:#64748b;">Players</span></div>
                                <div style="font-size:0.74rem; color:#94a3b8;">Top-10 at their position</div>
                            </div>
                            <div>
                                <div style="font-size:0.76rem; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">Roster Health</div>
                                <div style="font-size:1.45rem; font-weight:800; color:#0f172a; margin:2px 0;">{len(_t['all_roster_df']) - _t['injured_count']} <span style="font-size:0.95rem; font-weight:500; color:#94a3b8;">/ {len(_t['all_roster_df'])}</span></div>
                                <div style="font-size:0.74rem; color:#16a34a; font-weight:500;">{_t['injured_count']} Questionable / Out</div>
                            </div>
                        </div>

                        <!-- Bottom Positional Output Row -->
                        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-top:14px;">
                            <div style="font-size:0.74rem; font-weight:700; color:#64748b; text-transform:uppercase; margin-right:4px;">Starter Breakdown:</div>
                            {''.join(_pos_pills)}
                        </div>
                    </div>
                    """
                )

                # Slot Badge Generator
                def _get_slot_badge(slot_name):
                    _badges = {
                        'QB': '<span style="display:inline-block; width:44px; text-align:center; background:#f43f5e; color:#ffffff; font-weight:700; font-size:0.72rem; padding:3px 0; border-radius:6px;">QB</span>',
                        'RB': '<span style="display:inline-block; width:44px; text-align:center; background:#06b6d4; color:#ffffff; font-weight:700; font-size:0.72rem; padding:3px 0; border-radius:6px;">RB</span>',
                        'WR': '<span style="display:inline-block; width:44px; text-align:center; background:#3b82f6; color:#ffffff; font-weight:700; font-size:0.72rem; padding:3px 0; border-radius:6px;">WR</span>',
                        'TE': '<span style="display:inline-block; width:44px; text-align:center; background:#f59e0b; color:#ffffff; font-weight:700; font-size:0.72rem; padding:3px 0; border-radius:6px;">TE</span>',
                        'FLEX': '<span style="display:inline-block; width:44px; text-align:center; background:linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #f59e0b 100%); color:#ffffff; font-weight:800; font-size:0.68rem; padding:3px 0; border-radius:6px; letter-spacing:0.5px;">WRT</span>',
                        'K': '<span style="display:inline-block; width:44px; text-align:center; background:#a855f7; color:#ffffff; font-weight:700; font-size:0.72rem; padding:3px 0; border-radius:6px;">K</span>',
                        'DEF': '<span style="display:inline-block; width:44px; text-align:center; background:#64748b; color:#ffffff; font-weight:700; font-size:0.72rem; padding:3px 0; border-radius:6px;">DEF</span>',
                        'BN': '<span style="display:inline-block; width:44px; text-align:center; background:#e2e8f0; color:#475569; font-weight:700; font-size:0.72rem; padding:3px 0; border-radius:6px;">BN</span>'
                    }
                    return _badges.get(slot_name, f'<span style="display:inline-block; width:44px; text-align:center; background:#cbd5e1; color:#334155; font-weight:700; font-size:0.72rem; padding:3px 0; border-radius:6px;">{slot_name}</span>')

                # Proportional, harmonious column widths
                def _render_roster_table(df_subset, title_label):
                    if df_subset.empty:
                        return mo.md(f"<em>No {title_label.lower()} found.</em>")

                    _rows_html = []
                    for _, _r_player in df_subset.iterrows():
                        # Status Dot Badge
                        _st = str(_r_player['injury_status']).strip()
                        if _st == 'Healthy':
                            _st_badge = "<span style='display:inline-flex; align-items:center; justify-content:center; gap:6px; color:#16a34a; font-weight:600; font-size:0.78rem; white-space:nowrap;'><span style='width:7px; height:7px; border-radius:50%; background:#22c55e;'></span>Healthy</span>"
                        elif _st in ['Questionable', 'Doubtful']:
                            _st_badge = f"<span style='display:inline-flex; align-items:center; justify-content:center; gap:6px; color:#b45309; font-weight:600; font-size:0.78rem; white-space:nowrap;'><span style='width:7px; height:7px; border-radius:50%; background:#f59e0b;'></span>{_st}</span>"
                        elif _st == 'NA':
                            _st_badge = "<span style='display:inline-flex; align-items:center; justify-content:center; gap:6px; color:#64748b; font-weight:600; font-size:0.78rem; white-space:nowrap;'><span style='width:7px; height:7px; border-radius:50%; background:#94a3b8;'></span>Out</span>"
                        else:
                            _st_badge = f"<span style='display:inline-flex; align-items:center; justify-content:center; gap:6px; color:#dc2626; font-weight:600; font-size:0.78rem; white-space:nowrap;'><span style='width:7px; height:7px; border-radius:50%; background:#ef4444;'></span>{_st}</span>"

                        # Consistency Dot Badge
                        _sd_val = float(_r_player['std_points']) if pd.notna(_r_player['std_points']) else 0.0
                        if _sd_val < 4.5:
                            _cons_badge = f"<span style='display:inline-flex; align-items:center; gap:6px; color:#16a34a; font-weight:600; font-size:0.78rem; white-space:nowrap;'><span style='width:7px; height:7px; border-radius:50%; background:#22c55e;'></span>Rock Solid <span style='color:#94a3b8; font-size:0.72rem; font-weight:normal;'>({_sd_val:.2f})</span></span>"
                        elif _sd_val < 9.0:
                            _cons_badge = f"<span style='display:inline-flex; align-items:center; gap:6px; color:#b45309; font-weight:600; font-size:0.78rem; white-space:nowrap;'><span style='width:7px; height:7px; border-radius:50%; background:#f59e0b;'></span>Moderate <span style='color:#94a3b8; font-size:0.72rem; font-weight:normal;'>({_sd_val:.2f})</span></span>"
                        else:
                            _cons_badge = f"<span style='display:inline-flex; align-items:center; gap:6px; color:#dc2626; font-weight:600; font-size:0.78rem; white-space:nowrap;'><span style='width:7px; height:7px; border-radius:50%; background:#ef4444;'></span>Boom / Bust <span style='color:#94a3b8; font-size:0.72rem; font-weight:normal;'>({_sd_val:.2f})</span></span>"

                        # Positional rank badge
                        _rank_num = _r_player['pos_rank']
                        if _rank_num <= 3:
                            _rank_badge = f"<span style='background:#fef3c7; color:#b45309; border:1px solid #fde68a; border-radius:6px; padding:2px 8px; font-size:0.76rem; font-weight:700;'>#{_rank_num}</span>"
                        elif _rank_num <= 10:
                            _rank_badge = f"<span style='background:#f1f5f9; color:#0f172a; border:1px solid #cbd5e1; border-radius:6px; padding:2px 8px; font-size:0.76rem; font-weight:700;'>#{_rank_num}</span>"
                        else:
                            _rank_badge = f"<span style='color:#94a3b8; font-size:0.76rem;'>#{_rank_num}</span>"

                        _slot_html = _get_slot_badge(_r_player.get('slot', 'BN'))

                        # Range formatting
                        _min_val = _r_player['min_points']
                        _max_val = _r_player['max_points']
                        if pd.isna(_min_val) or pd.isna(_max_val):
                            _range_str = "—"
                        else:
                            _range_str = f"{_min_val:.1f} – {_max_val:.1f}"

                        _row = f"""
                        <tr style='border-bottom: 1px solid #f1f5f9;'>
                            <td style='padding:9px 8px; text-align:center; width:6%;'>{_slot_html}</td>
                            <td style='padding:9px 4px 9px 8px; width:4%; text-align:center;'>
                                <img src='{_r_player['headshot_url']}' style='width:38px; height:38px; min-width:38px; min-height:38px; max-width:38px; max-height:38px; aspect-ratio:1/1; border-radius:50%; object-fit:cover; border:1px solid #e2e8f0; display:block; margin:0 auto; box-sizing:border-box;' />
                            </td>
                            <td style='padding:9px 16px 9px 8px; text-align:left; width:34%;'>
                                <div style='font-weight:700; font-size:0.9rem; color:#0f172a;'>{_r_player['player_name']}</div>
                                <div style='font-size:0.76rem; color:#64748b;'>{_r_player['nfl_team']} • {_r_player['position']}</div>
                            </td>
                            <td style='padding:9px 10px; text-align:center; width:8%;'>{_rank_badge}</td>
                            <td style='padding:9px 14px; text-align:right; font-weight:700; font-size:0.92rem; color:#0f172a; width:11%;'>{_r_player['mean_points']:.2f}</td>
                            <td style='padding:9px 12px; text-align:left; width:15%;'>{_cons_badge}</td>
                            <td style='padding:9px 12px; text-align:right; color:#475569; font-size:0.82rem; width:11%;'>{_range_str}</td>
                            <td style='padding:9px 10px; text-align:center; width:11%;'>{_st_badge}</td>
                        </tr>
                        """
                        _rows_html.append(_row)

                    return mo.md(
                        f"""
                        <div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; overflow:hidden; margin-bottom:16px; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; box-shadow:0 1px 3px rgba(0,0,0,0.02); width:100%;'>
                            <div style='background:#f8fafc; padding:10px 16px; font-weight:700; font-size:0.88rem; color:#1e293b; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center;'>
                                <span>{title_label}</span>
                                <span style='font-size:0.75rem; font-weight:600; color:#64748b; background:#ffffff; border:1px solid #e2e8f0; padding:2px 8px; border-radius:12px;'>{len(df_subset)} Players</span>
                            </div>
                            <div style='overflow-x:auto;'>
                                <table style='width:100%; border-collapse:collapse; font-size:0.82rem;'>
                                    <thead>
                                        <tr style='background:#fafbfc; border-bottom:1px solid #e2e8f0; color:#64748b; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.4px;'>
                                            <th style='padding:9px 8px; text-align:center; width:6%;'>Slot</th>
                                            <th style='padding:9px 4px 9px 8px; width:4%;'></th>
                                            <th style='padding:9px 16px 9px 8px; text-align:left; width:34%;'>Player</th>
                                            <th style='padding:9px 10px; text-align:center; width:8%;'>Pos Rank</th>
                                            <th style='padding:9px 14px; text-align:right; width:11%;'>Mean FPTS</th>
                                            <th style='padding:9px 12px; text-align:left; width:15%;'>Consistency (SD)</th>
                                            <th style='padding:9px 12px; text-align:right; width:11%; line-height:1.2;'>
                                                <div style='font-weight:700; color:#475569;'>Range</div>
                                                <div style='font-size:0.68rem; color:#94a3b8; font-weight:normal; text-transform:none;'>Min – Max</div>
                                            </th>
                                            <th style='padding:9px 10px; text-align:center; width:11%;'>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {"".join(_rows_html)}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        """
                    )

                _view = mo.vstack([
                    _kpi_box,
                    _render_roster_table(_t['starters_df'], "⚡ Starting Lineup"),
                    _render_roster_table(_t['bench_df'], "🪑 Bench"),
                    _fixed_corner_badge
                ], gap=1)

    else:
        # League Overview Page
        _league_an = get_league_overview_analytics(df_teams, df_current_rosters, df_player_stats)

        if not _league_an:
            _view = mo.md("No league data available.")
        else:
            _standings = _league_an['standings_df']

            # Responsive HTML Grid for League KPI Cards (Works on mobile & desktop)
            _league_kpi_grid = mo.md(
                f"""
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:12px; width:100%; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                        <div style="font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase;">👑 1st Place Leader</div>
                        <div style="font-size:1.35rem; font-weight:800; color:#0f172a; margin:4px 0 2px 0;">{_league_an['leader_team']['team_name']}</div>
                        <div style="font-size:0.75rem; color:#94a3b8;">{_league_an['leader_team']['wins']}-{_league_an['leader_team']['losses']} • {_league_an['leader_team']['pf']:.1f} PF</div>
                    </div>
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                        <div style="font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase;">⚡ League Avg Starters</div>
                        <div style="font-size:1.35rem; font-weight:800; color:#0f172a; margin:4px 0 2px 0;">{_league_an['avg_starter_ppg']:.1f} <span style="font-size:0.85rem; font-weight:600; color:#64748b;">FPTS</span></div>
                        <div style="font-size:0.75rem; color:#94a3b8;">Avg Weekly Team Score</div>
                    </div>
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                        <div style="font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase;">🔥 Top Scoring Offense</div>
                        <div style="font-size:1.35rem; font-weight:800; color:#0f172a; margin:4px 0 2px 0;">{_league_an['high_pf_team']['team_name']}</div>
                        <div style="font-size:0.75rem; color:#94a3b8;">{_league_an['high_pf_team']['pf']:.1f} Points For</div>
                    </div>
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                        <div style="font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase;">🧱 Toughest Schedule</div>
                        <div style="font-size:1.35rem; font-weight:800; color:#0f172a; margin:4px 0 2px 0;">{_league_an['tough_sched_team']['team_name']}</div>
                        <div style="font-size:0.75rem; color:#94a3b8;">{_league_an['tough_sched_team']['pa']:.1f} Points Against</div>
                    </div>
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                        <div style="font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase;">🪑 Deepest Bench</div>
                        <div style="font-size:1.35rem; font-weight:800; color:#0f172a; margin:4px 0 2px 0;">{_league_an['deepest_bench_team']['team_name']}</div>
                        <div style="font-size:0.75rem; color:#94a3b8;">{_league_an['deepest_bench_team']['bench_ppg']:.1f} Bench PPG</div>
                    </div>
                </div>
                """
            )

            # Build Standings Table Rows with matching column alignments
            _standings_rows = []
            for _, _r_st in _standings.iterrows():
                _t_name = _r_st['team_name']
                _rank = _r_st['rank']
                if _rank == 1:
                    _rank_html = "<span style='background:#fef3c7; color:#b45309; border:1px solid #fde68a; border-radius:50%; width:28px; height:28px; display:inline-flex; align-items:center; justify-content:center; font-weight:800; font-size:0.8rem;'>🥇</span>"
                elif _rank == 2:
                    _rank_html = "<span style='background:#f1f5f9; color:#475569; border:1px solid #cbd5e1; border-radius:50%; width:28px; height:28px; display:inline-flex; align-items:center; justify-content:center; font-weight:800; font-size:0.8rem;'>🥈</span>"
                elif _rank == 3:
                    _rank_html = "<span style='background:#ffedd5; color:#c2410c; border:1px solid #fed7aa; border-radius:50%; width:28px; height:28px; display:inline-flex; align-items:center; justify-content:center; font-weight:800; font-size:0.8rem;'>🥉</span>"
                else:
                    _rank_html = f"<span style='color:#94a3b8; font-weight:700; font-size:0.85rem;'>#{_rank}</span>"

                _diff_val = _r_st['diff']
                if _diff_val > 0:
                    _diff_html = f"<span style='color:#16a34a; font-weight:700;'>+{_diff_val:.1f}</span>"
                elif _diff_val < 0:
                    _diff_html = f"<span style='color:#dc2626; font-weight:700;'>{_diff_val:.1f}</span>"
                else:
                    _diff_html = "<span style='color:#64748b;'>0.0</span>"

                _owner_col = owner_colors.get(_t_name, '#94a3b8')

                # CSS Micro-Dot Pinpoint Health Indicator (consistent with Consistency / Status dots)
                _healthy = _r_st['healthy_count']
                _total = _r_st['total_roster_count']
                _starter_inj = _r_st['starter_injured_count']
                _starters_needed = _r_st['starters_total']
                _st_details = _r_st.get('starter_inj_details', '')
                _bn_details = _r_st.get('bench_inj_details', '')

                if _healthy < _starters_needed:
                    _tooltip = f"CRITICAL SHORTAGE: Only {_healthy} healthy players available ({_starters_needed} starters needed)!"
                    _dot_color = "#991b1b"
                    _text_color = "#991b1b"
                    _extra_style = "background:#fee2e2; border:1px solid #fca5a5; padding:2px 8px; border-radius:12px;"
                elif _starter_inj > 0:
                    _tooltip = f"Starter Injured: {_st_details}"
                    _dot_color = "#ef4444"
                    _text_color = "#dc2626"
                    _extra_style = ""
                elif _healthy < _total:
                    _tooltip = f"Bench Injured: {_bn_details}"
                    _dot_color = "#f59e0b"
                    _text_color = "#b45309"
                    _extra_style = ""
                else:
                    _tooltip = "100% Healthy: Full roster fit and active"
                    _dot_color = "#22c55e"
                    _text_color = "#16a34a"
                    _extra_style = ""

                _health_html = f"""
                <span title="{_tooltip}" style="display:inline-flex; align-items:center; justify-content:center; gap:6px; color:{_text_color}; font-weight:600; font-size:0.8rem; white-space:nowrap; cursor:help; {_extra_style}">
                    <span style="width:7px; height:7px; min-width:7px; min-height:7px; border-radius:50%; background:{_dot_color}; display:inline-block;"></span>
                    <span>{_healthy} / {_total}</span>
                </span>
                """

                _row_html = f"""
                <tr style='border-bottom: 1px solid #f1f5f9;'>
                    <td style='padding:10px 12px; text-align:center; width:52px;'>{_rank_html}</td>
                    <td style='padding:10px 4px 10px 10px; width:24px; min-width:24px; max-width:24px; text-align:center;'>
                        <div style='width:10px; height:10px; min-width:10px; min-height:10px; aspect-ratio:1/1; border-radius:50%; background:{_owner_col}; margin:0 auto;'></div>
                    </td>
                    <td style='padding:10px 14px 10px 4px; text-align:left;'>
                        <div style='font-weight:700; font-size:0.88rem; color:#0f172a;'>{_t_name}</div>
                        <div style='font-size:0.75rem; color:#64748b;'>{_r_st['owner_name']}</div>
                    </td>
                    <td style='padding:10px 14px; text-align:center; width:110px;'>
                        <span style='font-weight:800; font-size:0.9rem; color:#0f172a;'>{_r_st['wins']} - {_r_st['losses']}</span>
                        <div style='font-size:0.72rem; color:#64748b;'>{_r_st['win_pct']:.3f}</div>
                    </td>
                    <td style='padding:10px 14px; text-align:right; font-weight:700; font-size:0.88rem; color:#0f172a; width:100px;'>{_r_st['pf']:.2f}</td>
                    <td style='padding:10px 14px; text-align:right; font-size:0.86rem; color:#64748b; width:100px;'>{_r_st['pa']:.2f}</td>
                    <td style='padding:10px 14px; text-align:right; font-size:0.86rem; width:80px;'>{_diff_html}</td>
                    <td style='padding:10px 14px; text-align:right; font-weight:600; color:#1e293b; width:90px;'>{_r_st['starter_ppg']:.1f}</td>
                    <td style='padding:10px 14px; text-align:right; color:#64748b; width:85px;'>{_r_st['bench_ppg']:.1f}</td>
                    <td style='padding:10px 14px; text-align:center; width:95px;'>
                        <span style='background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:3px 10px; font-weight:700; font-size:0.82rem; color:#0f172a;'>
                            ⭐ {_r_st['top_10_count']}
                        </span>
                    </td>
                    <td style='padding:10px 14px; text-align:center; width:85px;'>
                        {_health_html}
                    </td>
                    <td style='padding:10px 14px; text-align:center; width:95px;'>
                        <span style='background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; border-radius:8px; padding:3px 10px; font-weight:800; font-size:0.82rem;'>
                            {_r_st['power_score']:.1f}
                        </span>
                    </td>
                </tr>
                """
                _standings_rows.append(_row_html)

            _standings_table = mo.md(
                f"""
                <div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; overflow:hidden; margin-top:14px; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; box-shadow:0 1px 4px rgba(0,0,0,0.03);'>
                    <div style='background:#f8fafc; padding:12px 18px; font-weight:700; font-size:0.92rem; color:#0f172a; border-bottom:1px solid #e2e8f0;'>
                        🏆 League Standings & Power Rankings
                    </div>
                    <div style='overflow-x:auto;'>
                        <table style='width:100%; border-collapse:collapse; font-size:0.84rem;'>
                            <thead>
                                <tr style='background:#fafbfc; border-bottom:1px solid #e2e8f0; color:#64748b; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.5px;'>
                                    <th style='padding:10px 12px; text-align:center; width:52px;'>Rank</th>
                                    <th style='padding:10px 4px 10px 10px; width:24px; min-width:24px; max-width:24px;'></th>
                                    <th style='padding:10px 14px 10px 4px; text-align:left;'>Team / Manager</th>
                                    <th style='padding:10px 14px; text-align:center; width:110px;'>Record (Win %)</th>
                                    <th style='padding:10px 14px; text-align:right; width:100px;'>Points For (PF)</th>
                                    <th style='padding:10px 14px; text-align:right; width:100px;'>Points Against (PA)</th>
                                    <th style='padding:10px 14px; text-align:right; width:80px;'>Diff (+/-)</th>
                                    <th style='padding:10px 14px; text-align:right; width:90px;'>Starter PPG</th>
                                    <th style='padding:10px 14px; text-align:right; width:85px;'>Bench PPG</th>
                                    <th style='padding:10px 14px; text-align:center; width:95px;'>Top 10 Assets</th>
                                    <th style='padding:10px 14px; text-align:center; width:85px;'>Health</th>
                                    <th style='padding:10px 14px; text-align:center; width:95px;'>Power Index</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join(_standings_rows)}
                            </tbody>
                        </table>
                    </div>
                </div>
                """
            )

            _view = mo.vstack([
                _league_kpi_grid,
                _standings_table,
                _fixed_corner_badge
            ], gap=1)

    _view
    return


if __name__ == "__main__":
    app.run()
