import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List


def compute_player_aggregates(df_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Compute mean, std, median, min, max, total points, coefficient of variation (CV),
    positional rank, and pivot weekly points per player.
    """
    if df_stats is None or df_stats.empty:
        return pd.DataFrame()

    agg = df_stats.groupby(['player_id', 'player_name', 'position', 'nfl_team', 'injury_status', 'current_owner']).agg(
        games_played=('points', 'count'),
        total_points=('points', 'sum'),
        mean_points=('points', 'mean'),
        std_points=('points', lambda x: float(np.std(x, ddof=1)) if len(x) > 1 else 0.0),
        median_points=('points', 'median'),
        min_points=('points', 'min'),
        max_points=('points', 'max'),
        total_pass_yd=('pass_yd', 'sum'),
        total_pass_td=('pass_td', 'sum'),
        total_rush_yd=('rush_yd', 'sum'),
        total_rush_td=('rush_td', 'sum'),
        total_rec=('rec', 'sum'),
        total_rec_yd=('rec_yd', 'sum'),
        total_rec_td=('rec_td', 'sum')
    ).reset_index()

    agg['mean_points'] = agg['mean_points'].round(2)
    agg['std_points'] = agg['std_points'].fillna(0.0).round(2)
    agg['total_points'] = agg['total_points'].round(2)
    agg['median_points'] = agg['median_points'].round(2)
    agg['cv'] = np.where(agg['mean_points'] > 0, (agg['std_points'] / agg['mean_points']).round(2), 0.0)

    # Positional Rank within each position based on mean points
    agg['pos_rank'] = agg.groupby('position')['mean_points'].rank(ascending=False, method='min').astype(int)

    # Consistency 3-Tier Classification
    def classify_consistency(sd: float) -> str:
        if sd < 4.5:
            return "🟢 Rock Solid"
        elif sd < 9.0:
            return "🟡 Moderate"
        else:
            return "🔴 Boom / Bust"

    agg['consistency_tier'] = agg['std_points'].apply(classify_consistency)

    # Pivot weekly points
    pivot_w = df_stats.pivot(index='player_id', columns='week', values='points').add_prefix('Week ').reset_index()
    merged = pd.merge(agg, pivot_w, on='player_id', how='left')

    # Headshot URLs
    merged['headshot_url'] = merged.apply(
        lambda r: f"https://sleepercdn.com/images/team_logos/nfl/{str(r['nfl_team']).lower()}.png"
        if r['position'] == 'DEF' or str(r['player_id']) == str(r['nfl_team'])
        else f"https://sleepercdn.com/content/nfl/players/{r['player_id']}.jpg",
        axis=1
    )

    return merged.sort_values(by='mean_points', ascending=False)


def get_team_roster_analytics(
    team_name: str,
    df_rosters: pd.DataFrame,
    df_player_stats: pd.DataFrame,
    df_teams: pd.DataFrame
) -> Dict[str, Any]:
    """
    Extract comprehensive roster analytics for a specific fantasy team:
    - Sleeper-ordered Starters: QB -> RB -> RB -> WR -> WR -> TE -> FLEX -> K -> DEF
    - Bench ordered by position & PPG
    - Top-10 elite asset metrics
    - Positional output breakdown and total PPG
    - Starters and bench injury breakdown
    """
    if df_rosters is None or df_rosters.empty or df_player_stats is None or df_player_stats.empty:
        return {}

    team_info = df_teams[df_teams['team_name'] == team_name].iloc[0] if df_teams is not None and not df_teams.empty and team_name in df_teams['team_name'].values else None

    # Filter roster
    roster_rows = df_rosters[df_rosters['team_name'] == team_name].copy()
    if roster_rows.empty:
        return {}

    # Merge with full player stats
    merged = roster_rows.merge(df_player_stats, on='player_id', how='left', suffixes=('', '_stat'))

    # Fill default values for players with 0 games yet
    merged['mean_points'] = merged['mean_points'].fillna(0.0)
    merged['std_points'] = merged['std_points'].fillna(0.0)
    merged['total_points'] = merged['total_points'].fillna(0.0)
    merged['pos_rank'] = merged['pos_rank'].fillna(99).astype(int)
    merged['consistency_tier'] = merged['consistency_tier'].fillna('🟢 Rock Solid')
    merged['injury_status'] = merged['injury_status'].fillna('Healthy')

    starters_raw = merged[merged['is_starter'] == 1].copy()
    bench_raw = merged[merged['is_starter'] == 0].copy()

    # Slot assignment for starters (Sleeper lineup style)
    ordered_starters = []
    # 1. QB
    for _, r in starters_raw[starters_raw['position'] == 'QB'].sort_values(by='mean_points', ascending=False).iterrows():
        d = r.to_dict(); d['slot'] = 'QB'; ordered_starters.append(d)
    # 2. RB
    for i, (_, r) in enumerate(starters_raw[starters_raw['position'] == 'RB'].sort_values(by='mean_points', ascending=False).iterrows()):
        d = r.to_dict(); d['slot'] = 'RB' if i < 2 else 'FLEX'; ordered_starters.append(d)
    # 3. WR
    for i, (_, r) in enumerate(starters_raw[starters_raw['position'] == 'WR'].sort_values(by='mean_points', ascending=False).iterrows()):
        d = r.to_dict(); d['slot'] = 'WR' if i < 2 else 'FLEX'; ordered_starters.append(d)
    # 4. TE
    for i, (_, r) in enumerate(starters_raw[starters_raw['position'] == 'TE'].sort_values(by='mean_points', ascending=False).iterrows()):
        d = r.to_dict(); d['slot'] = 'TE' if i < 1 else 'FLEX'; ordered_starters.append(d)
    # 5. K
    for _, r in starters_raw[starters_raw['position'] == 'K'].sort_values(by='mean_points', ascending=False).iterrows():
        d = r.to_dict(); d['slot'] = 'K'; ordered_starters.append(d)
    # 6. DEF
    for _, r in starters_raw[starters_raw['position'] == 'DEF'].sort_values(by='mean_points', ascending=False).iterrows():
        d = r.to_dict(); d['slot'] = 'DEF'; ordered_starters.append(d)

    slot_order = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4, 'FLEX': 5, 'K': 6, 'DEF': 7}
    ordered_starters.sort(key=lambda x: (slot_order.get(x['slot'], 99), -float(x.get('mean_points') or 0)))
    starters_df = pd.DataFrame(ordered_starters)

    # Bench ordering: QB -> RB -> WR -> TE -> K -> DEF
    pos_order = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4, 'K': 5, 'DEF': 6}
    bench_list = bench_raw.to_dict('records')
    for b in bench_list:
        b['slot'] = 'BN'
    bench_list.sort(key=lambda x: (pos_order.get(x['position'], 99), -float(x.get('mean_points') or 0)))
    bench_df = pd.DataFrame(bench_list)

    starter_ppg = float(starters_df['mean_points'].sum()) if not starters_df.empty else 0.0
    bench_ppg = float(bench_df['mean_points'].sum()) if not bench_df.empty else 0.0
    total_roster_fpts = float(merged['total_points'].sum())

    # Positional PPG sums for starters
    pos_breakdown = starters_df.groupby('position')['mean_points'].sum().to_dict() if not starters_df.empty else {}

    # Top-10 Elite assets
    top_10_count = int((merged['pos_rank'] <= 10).sum() if not merged.empty else 0)
    top_5_count = int((merged['pos_rank'] <= 5).sum() if not merged.empty else 0)

    # Injury count
    injured_status_list = ['Questionable', 'Out', 'IR', 'PUP', 'Doubtful', 'DNR', 'NA']
    injured_count = sum(merged['injury_status'].isin(injured_status_list))
    starter_injured_count = sum(starters_df['injury_status'].isin(injured_status_list)) if not starters_df.empty else 0
    total_starters_count = len(starters_df)

    return {
        'team_name': team_name,
        'owner_name': team_info['owner_name'] if team_info is not None else team_name,
        'wins': int(team_info['wins']) if team_info is not None else 0,
        'losses': int(team_info['losses']) if team_info is not None else 0,
        'total_fpts': float(team_info['fpts']) if team_info is not None else total_roster_fpts,
        'fpts_against': float(team_info['fpts_against']) if team_info is not None and 'fpts_against' in team_info else 0.0,
        'starter_ppg': round(starter_ppg, 2),
        'bench_ppg': round(bench_ppg, 2),
        'top_10_count': top_10_count,
        'top_5_count': top_5_count,
        'pos_breakdown': pos_breakdown,
        'injured_count': injured_count,
        'starter_injured_count': starter_injured_count,
        'total_starters_count': total_starters_count,
        'starters_df': starters_df,
        'bench_df': bench_df,
        'all_roster_df': merged
    }


def get_league_overview_analytics(
    df_teams: pd.DataFrame,
    df_rosters: pd.DataFrame,
    df_player_stats: pd.DataFrame
) -> Dict[str, Any]:
    """
    Compute comprehensive league standings and comparison metrics:
    - Standings table ordered by Wins DESC, then Points For DESC
    - Points For (PF), Points Against (PA), Point Differential (+/-)
    - Starter PPG, Bench Depth PPG, Top-10 Elite Asset Counts, Roster Health
    - Composite Power Rating
    - League summary KPIs (Actual league average PF per team/week & current starter projection)
    """
    if df_teams is None or df_teams.empty:
        return {}

    standings = []
    total_pf_sum = 0.0
    total_games_sum = 0

    for idx, r in df_teams.reset_index(drop=True).iterrows():
        t_name = r['team_name']
        an = get_team_roster_analytics(t_name, df_rosters, df_player_stats, df_teams)
        pf = float(r['fpts'])
        pa = float(r['fpts_against']) if 'fpts_against' in r else 0.0
        diff = round(pf - pa, 2)
        total_games = max(1, r['wins'] + r['losses'])
        win_pct = round(r['wins'] / total_games, 3)

        total_pf_sum += pf
        total_games_sum += total_games

        # Composite Power Score (0 - 100)
        # 40% Win %, 35% Starter PPG relative, 25% Total PF relative
        power_score = round((win_pct * 40.0) + (min(1.0, an['starter_ppg'] / 200.0) * 35.0) + (min(1.0, pf / 400.0) * 25.0), 1)

        total_roster = len(an['all_roster_df'])
        healthy_count = total_roster - an['injured_count']
        starter_injured = an['starter_injured_count']
        starters_total = an['total_starters_count']

        standings.append({
            'rank': idx + 1,
            'team_name': t_name,
            'owner_name': r['owner_name'],
            'wins': int(r['wins']),
            'losses': int(r['losses']),
            'win_pct': win_pct,
            'pf': pf,
            'pa': pa,
            'diff': diff,
            'starter_ppg': an['starter_ppg'],
            'bench_ppg': an['bench_ppg'],
            'top_10_count': an['top_10_count'],
            'top_5_count': an['top_5_count'],
            'healthy_count': healthy_count,
            'total_roster_count': total_roster,
            'starter_injured_count': starter_injured,
            'starters_total': starters_total,
            'power_score': power_score
        })

    df_standings = pd.DataFrame(standings)

    # Actual historical average scored per team/week (e.g. 1654.98 / 12 = 137.9 FPTS)
    actual_league_avg_ppg = round(total_pf_sum / max(1, total_games_sum), 1)
    
    leader_team = df_standings.iloc[0]
    high_pf_team = df_standings.sort_values(by='pf', ascending=False).iloc[0]
    tough_sched_team = df_standings.sort_values(by='pa', ascending=False).iloc[0]
    deepest_bench_team = df_standings.sort_values(by='bench_ppg', ascending=False).iloc[0]

    return {
        'standings_df': df_standings,
        'avg_starter_ppg': actual_league_avg_ppg,
        'leader_team': leader_team,
        'high_pf_team': high_pf_team,
        'tough_sched_team': tough_sched_team,
        'deepest_bench_team': deepest_bench_team
    }
