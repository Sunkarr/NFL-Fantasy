import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from src.config import DEFAULT_LEAGUE_ID, DB_PATH
    from src.sync import run_full_sync

    return DEFAULT_LEAGUE_ID, mo, run_full_sync


@app.cell
def _(mo):
    mo.md("""
    # 🏈 Sleeper Fantasy Football — Data Synchronizer

    Sync your Sleeper league rosters, weekly matchup results, and player boxscores into the local SQLite database (`data/fantasy.db`).
    """)
    return


@app.cell
def _(DEFAULT_LEAGUE_ID, mo):
    league_id_input = mo.ui.text(
        value=DEFAULT_LEAGUE_ID,
        label="League ID",
        placeholder="Enter Sleeper League ID"
    )
    sync_mode_dropdown = mo.ui.dropdown(
        options=["incremental", "full"],
        value="incremental",
        label="Sync Mode"
    )
    force_players_checkbox = mo.ui.checkbox(
        value=False,
        label="Force refresh players database (~5MB)"
    )
    sync_button = mo.ui.button(
        label="⚡ Start Sync",
        kind="success"
    )

    mo.vstack([
        mo.hstack([league_id_input, sync_mode_dropdown]),
        mo.hstack([force_players_checkbox, sync_button]),
    ])
    return (
        force_players_checkbox,
        league_id_input,
        sync_button,
        sync_mode_dropdown,
    )


@app.cell
def _(
    force_players_checkbox,
    league_id_input,
    mo,
    run_full_sync,
    sync_button,
    sync_mode_dropdown,
):
    if sync_button.value:
        with mo.status.spinner("Syncing Sleeper data..."):
            _res = run_full_sync(
                league_id=league_id_input.value.strip(),
                force_refresh_players=force_players_checkbox.value,
                mode=sync_mode_dropdown.value
            )
        mo.output.replace(
            mo.md(
                f"""
                ### ✅ Sync Successful!
                - **Season:** {_res['season']} (Week {_res['current_week']})
                - **Players in DB:** {_res['players']:,}
                - **Matchup records synced:** {_res['matchup_points']:,}
                - **NFL Boxscores synced:** {_res['nfl_stats']:,}
                """
            )
        )
    return


if __name__ == "__main__":
    app.run()
