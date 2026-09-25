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


def _abbreviate_name(full_name: str) -> str:
    """Turn 'Patrick Mahomes' into 'P. Mahomes'."""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {' '.join(parts[1:])}"
    return full_name


def build_interactive_position_chart(
    pos_data: pd.DataFrame,
    unique_teams: List[str],
    owner_colors: Dict[str, str],
    chart_width: int = 860,
    chart_height: int = 500
) -> alt.Chart:
    """
    Build a crisp, high-performance Altair scatter plot with:
    - Real player headshots on the scatter coordinates
    - Colored fantasy owner aura halos around avatars
    - Visible fantasy owner color legend
    - Median reference dashed lines
    - Comprehensive hover tooltips
    """
    if pos_data.empty:
        return alt.Chart(pd.DataFrame()).mark_text()

    df_plot = pos_data.copy()
    owner_counts = df_plot['current_owner'].value_counts()
    df_plot['owner_legend_label'] = df_plot['current_owner'].apply(lambda o: f"{o} ({owner_counts.get(o, 0)})")
    df_plot['short_name'] = df_plot['player_name'].apply(_abbreviate_name)
    df_plot['owner_color'] = df_plot['current_owner'].apply(lambda o: owner_colors.get(o, FREE_AGENT_COLOR))

    # Axis Domain Bounds with padding
    x_min = float(df_plot['mean_points'].min())
    x_max = float(df_plot['mean_points'].max())
    y_min = float(df_plot['std_points'].min())
    y_max = float(df_plot['std_points'].max())

    x_margin = max(2.0, (x_max - x_min) * 0.12)
    y_margin = max(1.5, (y_max - y_min) * 0.12)

    x_domain = [max(0.0, x_min - x_margin), x_max + x_margin + 2.5]
    y_domain = [max(0.0, y_min - y_margin), y_max + y_margin]

    x_med = float(df_plot['mean_points'].median())
    y_med = float(df_plot['std_points'].median())

    # Legend order and palette mapping
    ordered_owners = sorted([o for o in df_plot['current_owner'].unique() if o != 'Free Agent'])
    if 'Free Agent' in df_plot['current_owner'].values:
        ordered_owners.append('Free Agent')

    domain_labels = [f"{o} ({owner_counts.get(o, 0)})" for o in ordered_owners]
    range_colors = [owner_colors.get(o, FREE_AGENT_COLOR) for o in ordered_owners]

    # Shared encodings
    base = alt.Chart(df_plot).encode(
        x=alt.X(
            'mean_points:Q',
            title='Mean Points (FPTS)',
            scale=alt.Scale(domain=x_domain),
            axis=alt.Axis(
                gridColor='#e2e8f0',
                titleFontWeight='bold',
                titleFontSize=12,
                labelFontSize=10.5,
                tickCount=10
            )
        ),
        y=alt.Y(
            'std_points:Q',
            title='Standard Deviation (SD)',
            scale=alt.Scale(domain=y_domain),
            axis=alt.Axis(
                gridColor='#e2e8f0',
                titleFontWeight='bold',
                titleFontSize=12,
                labelFontSize=10.5,
                tickCount=8
            )
        )
    )

    # 1. Median Reference Lines
    rule_x = alt.Chart(pd.DataFrame({'x': [x_med]})).mark_rule(
        strokeDash=[4, 4],
        color='#94a3b8',
        size=1.2,
        opacity=0.8
    ).encode(x=alt.X('x:Q', scale=alt.Scale(domain=x_domain)))

    rule_y = alt.Chart(pd.DataFrame({'y': [y_med]})).mark_rule(
        strokeDash=[4, 4],
        color='#94a3b8',
        size=1.2,
        opacity=0.8
    ).encode(y=alt.Y('y:Q', scale=alt.Scale(domain=y_domain)))

    # 2. Owner Color Halos behind Headshots
    owner_halos = base.mark_circle(
        size=420,
        opacity=0.9
    ).encode(
        color=alt.Color(
            'owner_legend_label:N',
            title='Fantasy Owner',
            scale=alt.Scale(domain=domain_labels, range=range_colors),
            legend=alt.Legend(
                titleFontSize=11.5,
                titleFontWeight='bold',
                labelFontSize=10.5,
                symbolSize=110,
                orient='top',
                columns=4,
                labelLimit=250
            )
        )
    )

    # 3. Headshot Avatars
    player_images = base.mark_image(
        width=26,
        height=26
    ).encode(
        url='headshot_url:N',
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

    # 4. Text Labels for Player Names
    player_labels = base.mark_text(
        align='left',
        baseline='middle',
        dx=16,
        fontSize=10.5,
        fontWeight=600,
        color='#1e293b',
        opacity=0.95
    ).encode(
        text='short_name:N'
    )

    chart = (rule_x + rule_y + owner_halos + player_images + player_labels).properties(
        width=chart_width,
        height=chart_height
    ).configure_view(
        stroke='#cbd5e1'
    ).configure_axis(
        domainColor='#cbd5e1'
    )

    return chart
