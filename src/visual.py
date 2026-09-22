from typing import Dict, List
import altair as alt
import pandas as pd
from src.config import TEAM_PALETTE, FREE_AGENT_COLOR


def get_owner_color_map(unique_teams: List[str]) -> Dict[str, str]:
    """Map team names to distinct colors with Free Agent as neutral slate."""
    owner_colors = {'Free Agent': FREE_AGENT_COLOR}
    for i, team in enumerate(unique_teams):
        owner_colors[team] = TEAM_PALETTE[i % len(TEAM_PALETTE)]
    return owner_colors


def build_interactive_position_chart(
    pos_data: pd.DataFrame,
    unique_teams: List[str],
    owner_colors: Dict[str, str],
    chart_width: int = 860,
    chart_height: int = 520
) -> alt.Chart:
    """
    Build a high-performance, responsive Altair scatter plot.
    Loads CDN headshots asynchronously directly in the client browser without Pi CPU overhead.
    """
    if pos_data.empty:
        return alt.Chart(pd.DataFrame()).mark_text()

    df_plot = pos_data.copy()
    owner_counts = df_plot['current_owner'].value_counts()
    df_plot['owner_legend_label'] = df_plot['current_owner'].apply(lambda o: f"{o} ({owner_counts.get(o, 0)})")

    # Fast direct CDN URLs (resolved by client browser in parallel)
    if 'headshot_url' not in df_plot.columns:
        df_plot['headshot_url'] = df_plot.apply(
            lambda r: f"https://sleepercdn.com/images/team_logos/nfl/{str(r.get('nfl_team', 'FA')).lower()}.png"
            if r.get('position') == 'DEF' or str(r.get('player_id')) == str(r.get('nfl_team'))
            else f"https://sleepercdn.com/content/nfl/players/{r['player_id']}.jpg",
            axis=1
        )

    # Axis Domain Bounds
    x_min = float(df_plot['mean_points'].min())
    x_max = float(df_plot['mean_points'].max())
    y_min = float(df_plot['std_points'].min())
    y_max = float(df_plot['std_points'].max())

    x_margin = max(1.8, (x_max - x_min) * 0.08)
    y_margin = max(1.2, (y_max - y_min) * 0.08)

    x_domain = [max(0.0, x_min - x_margin), x_max + x_margin]
    y_domain = [max(-0.5, y_min - y_margin), y_max + y_margin]

    x_med = float(df_plot['mean_points'].median())
    y_med = float(df_plot['std_points'].median())

    # Legend order and palette mapping
    ordered_owners = (['Free Agent'] if 'Free Agent' in df_plot['current_owner'].values else []) + sorted([o for o in df_plot['current_owner'].unique() if o != 'Free Agent'])
    domain_labels = [f"{o} ({owner_counts.get(o, 0)})" for o in ordered_owners]
    range_colors = [owner_colors.get(o, FREE_AGENT_COLOR) for o in ordered_owners]

    # 1. Median Reference Lines
    rule_x = alt.Chart(pd.DataFrame({'x': [x_med]})).mark_rule(
        strokeDash=[4, 4],
        color='#94a3b8',
        size=1.2,
        opacity=0.75
    ).encode(x=alt.X('x:Q', scale=alt.Scale(domain=x_domain)))

    rule_y = alt.Chart(pd.DataFrame({'y': [y_med]})).mark_rule(
        strokeDash=[4, 4],
        color='#94a3b8',
        size=1.2,
        opacity=0.75
    ).encode(y=alt.Y('y:Q', scale=alt.Scale(domain=y_domain)))

    # 2. Outer colored ring / base node
    node_base = alt.Chart(df_plot).mark_circle(
        size=260,
        opacity=0.9
    ).encode(
        x=alt.X(
            'mean_points:Q',
            title='Mean Points (FPTS)',
            scale=alt.Scale(domain=x_domain),
            axis=alt.Axis(gridColor='#e2e8f0', titleFontWeight='bold', titleFontSize=12, labelFontSize=10.5)
        ),
        y=alt.Y(
            'std_points:Q',
            title='Standard Deviation (SD)',
            scale=alt.Scale(domain=y_domain),
            axis=alt.Axis(gridColor='#e2e8f0', titleFontWeight='bold', titleFontSize=12, labelFontSize=10.5)
        ),
        color=alt.Color(
            'owner_legend_label:N',
            title='Fantasy Owner',
            scale=alt.Scale(domain=domain_labels, range=range_colors),
            legend=alt.Legend(
                titleFontSize=11.5,
                titleFontWeight='bold',
                labelFontSize=10.5,
                symbolSize=100,
                orient='right'
            )
        )
    )

    # 3. Fast Browser-Loaded CDN Headshots
    headshots_layer = alt.Chart(df_plot).mark_image(
        width=26,
        height=26
    ).encode(
        x=alt.X('mean_points:Q', scale=alt.Scale(domain=x_domain)),
        y=alt.Y('std_points:Q', scale=alt.Scale(domain=y_domain)),
        url='headshot_url:N'
    )

    # 4. Interactive Hover Tooltip Trigger
    hover_layer = alt.Chart(df_plot).mark_circle(
        size=300,
        opacity=0.001
    ).encode(
        x=alt.X('mean_points:Q', scale=alt.Scale(domain=x_domain)),
        y=alt.Y('std_points:Q', scale=alt.Scale(domain=y_domain)),
        tooltip=[
            alt.Tooltip('player_name:N', title='Player'),
            alt.Tooltip('position:N', title='Position'),
            alt.Tooltip('nfl_team:N', title='NFL Team'),
            alt.Tooltip('current_owner:N', title='Fantasy Owner'),
            alt.Tooltip('injury_status:N', title='Injury Status'),
            alt.Tooltip('mean_points:Q', title='Mean FPTS', format='.2f'),
            alt.Tooltip('std_points:Q', title='Std Dev (SD)', format='.2f'),
            alt.Tooltip('cv:Q', title='Volatility (CV)', format='.2f'),
            alt.Tooltip('max_points:Q', title='Max FPTS', format='.2f'),
            alt.Tooltip('min_points:Q', title='Min FPTS', format='.2f'),
            alt.Tooltip('total_points:Q', title='Total FPTS', format='.2f'),
            alt.Tooltip('games_played:Q', title='Games Played')
        ]
    )

    chart = (rule_x + rule_y + node_base + headshots_layer + hover_layer).properties(
        width=chart_width,
        height=chart_height
    ).configure_view(
        stroke='#cbd5e1'
    ).configure_axis(
        domainColor='#cbd5e1'
    )

    return chart
