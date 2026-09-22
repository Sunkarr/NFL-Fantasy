import base64
import io
from pathlib import Path
from typing import Dict, Optional, List
import requests
from PIL import Image, ImageDraw, ImageOps
import altair as alt
import pandas as pd
from src.config import HEADSHOTS_DIR, TEAM_PALETTE, FREE_AGENT_COLOR


def get_player_image(player_id: str, nfl_team: str = 'FA', position: str = 'QB') -> Optional[Image.Image]:
    """Retrieve player headshot or defense team logo."""
    HEADSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Defenses (use team logo)
    if position == 'DEF' or str(player_id).upper() == str(nfl_team).upper():
        team_key = str(nfl_team).lower()
        cache_path = HEADSHOTS_DIR / f"team_{team_key}.png"
        if cache_path.exists():
            try:
                return Image.open(cache_path).convert('RGBA')
            except Exception:
                pass
        
        try:
            r = requests.get(f"https://sleepercdn.com/images/team_logos/nfl/{team_key}.png", timeout=2.5)
            if r.status_code == 200 and len(r.content) > 500:
                img = Image.open(io.BytesIO(r.content)).convert('RGBA')
                img.save(cache_path)
                return img
        except Exception:
            pass
        return None

    # 2. Individual Players
    cache_path = HEADSHOTS_DIR / f"{player_id}.png"
    if cache_path.exists():
        try:
            cached_img = Image.open(cache_path).convert('RGBA')
            if cached_img.size != (150, 150):
                return cached_img
        except Exception:
            pass

    try:
        r = requests.get(f"https://sleepercdn.com/content/nfl/players/{player_id}.jpg", timeout=2.5)
        if r.status_code == 200 and len(r.content) > 1000:
            img = Image.open(io.BytesIO(r.content)).convert('RGBA')
            img.save(cache_path)
            return img
    except Exception:
        pass

    return None


def create_circular_avatar_data_uri(
    img: Optional[Image.Image],
    border_color_hex: str,
    size: int = 140,
    border_width: int = 6,
    initials: str = '?'
) -> str:
    """Crop image to circle with antialiased supersampling and colored border, returning base64 data URI."""
    if img is None:
        img = Image.new('RGBA', (size, size), (241, 245, 249, 255))
        draw = ImageDraw.Draw(img)
        draw.text((size // 3, size // 3), initials, fill=(71, 85, 105, 255))

    img = ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)
    
    scale = 2
    big_size = size * scale
    big_mask = Image.new('L', (big_size, big_size), 0)
    draw_big_mask = ImageDraw.Draw(big_mask)
    draw_big_mask.ellipse((0, 0, big_size, big_size), fill=255)
    mask = big_mask.resize((size, size), Image.Resampling.LANCZOS)

    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask=mask)

    draw_border = ImageDraw.Draw(output)
    h = border_color_hex.lstrip('#')
    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    for i in range(border_width):
        draw_border.ellipse((i, i, size - 1 - i, size - 1 - i), outline=rgb + (255,))

    buf = io.BytesIO()
    output.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')


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
    Build a clean, minimalist interactive Altair chart optimized for a 14" MacBook Pro:
    - Shows fantasy owner player counts in the legend e.g. "Free Agent (12)"
    - No graph title
    - Embedded high-res circular player headshots with colored team rings
    - Comprehensive hover tooltips with detailed stats
    - Median reference dashed lines
    """
    if pos_data.empty:
        return alt.Chart(pd.DataFrame()).mark_text()

    # Pre-generate base64 circular avatars and calculate owner player counts
    df_plot = pos_data.copy()
    owner_counts = df_plot['current_owner'].value_counts()
    df_plot['owner_legend_label'] = df_plot['current_owner'].apply(lambda o: f"{o} ({owner_counts.get(o, 0)})")

    avatar_uris = []
    for _, row in df_plot.iterrows():
        p_id = str(row['player_id'])
        nfl_t = str(row['nfl_team'])
        pos = str(row['position'])
        owner = str(row['current_owner'])
        col = owner_colors.get(owner, FREE_AGENT_COLOR)
        init = row['player_name'][:2].upper() if row['player_name'] else '?'
        raw_img = get_player_image(p_id, nfl_t, pos)
        avatar_uris.append(create_circular_avatar_data_uri(raw_img, border_color_hex=col, size=140, border_width=6, initials=init))
    df_plot['avatar_uri'] = avatar_uris

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

    # Legend order and palette mapping with counts
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

    # 2. Legend layer for Fantasy Owner colors with player counts
    legend_layer = alt.Chart(df_plot).mark_point(
        size=110,
        filled=True
    ).encode(
        x=alt.X(
            'mean_points:Q',
            title='Mean Points (FPTS)',
            scale=alt.Scale(domain=x_domain),
            axis=alt.Axis(gridColor='#e2e8f0', titleFontWeight='bold', titleFontSize=11.5, labelFontSize=10.5)
        ),
        y=alt.Y(
            'std_points:Q',
            title='Standard Deviation (SD)',
            scale=alt.Scale(domain=y_domain),
            axis=alt.Axis(gridColor='#e2e8f0', titleFontWeight='bold', titleFontSize=11.5, labelFontSize=10.5)
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

    # 3. Embedded Circular Player Headshots Layer
    headshots_layer = alt.Chart(df_plot).mark_image(
        width=36,
        height=36
    ).encode(
        x=alt.X('mean_points:Q', scale=alt.Scale(domain=x_domain)),
        y=alt.Y('std_points:Q', scale=alt.Scale(domain=y_domain)),
        url='avatar_uri:N',
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

    chart = (rule_x + rule_y + legend_layer + headshots_layer).properties(
        width=chart_width,
        height=chart_height
    ).configure_view(
        stroke='#cbd5e1'
    ).configure_axis(
        domainColor='#cbd5e1'
    )

    return chart
