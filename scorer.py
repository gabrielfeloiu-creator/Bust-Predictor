import pandas as pd
from data_loader import merge_all
from rookies import rookies_2026

# Positional age decline thresholds based on historical NFL performance curves.
# Players past these ages are increasingly likely to underperform their ADP.
rbDeclineAge = 28
wrDeclineAge = 29
teDeclineAge = 30

# Standard min-max normalization scales any series to a 0-100 range.
# Used by every scoring function so all sub-scores are on the same scale
# before being combined into the final bust score.
def min_max_normalize(series):
    return (series - series.min()) / (series.max() - series.min()) * 100


# Scores bust risk based on how far past their positional decline age a player is.
# Young players score 0 (no age risk). Values are clipped at 0 so players
# under the threshold are never penalized for being young.
# Weight: 25% — age is the single most reliable predictor of decline.
def score_age(df):
    threshold_map = {'WR': wrDeclineAge, 'RB': rbDeclineAge, 'TE': teDeclineAge}
    thresholds = df['position'].map(threshold_map)
    years_past_peak = df['Age'] - thresholds
    years_past_peak = years_past_peak.clip(lower=0)
    return min_max_normalize(years_past_peak)

# Scores bust risk based on games played as a proxy for injury history.
# games_pct = games played / 17 (full season). Inverted so missing more
# games = higher risk. Capped at 60 to prevent injury score from single-handedly
# dominating a player's bust score (e.g. Malik Nabers — elite talent, 4 games).
# Weight: 10%
def score_injury(df):
    games_pct = df['G_x'] / 17
    games_pct = games_pct.clip(upper=1)
    injury_risk = 1 - games_pct
    injury_score = min_max_normalize(injury_risk)
    return injury_score.clip(upper=60)


# Scores bust risk based on TD rate relative to opportunities.
# High TD rates are unsustainable — players who scored many TDs per target
# or carry are likely to regress to the mean the following season.
# WR/TE: TD / targets. RB: TD / carries. Position-specific to reflect
# how touchdowns are generated differently by role.
# Weight: 10%
def score_td_regression(df):
    td_rate = pd.Series(0.0, index=df.index)
    td_rate.loc[df['position'].isin(['WR', 'TE'])] = df['TD_x'] / df['Tgt']
    td_rate.loc[df['position'] == 'RB'] = df['TD_y'] / df['Att']
    td_rate.fillna(0, inplace=True)
    return min_max_normalize(td_rate)


# Scores bust risk based on role/opportunity, adjusted for efficiency.
# High volume = lower bust risk (inverted after normalizing).
# WR/TE: targets + Y/Tgt efficiency bonus (* 20 scaling factor).
#   Rewards receivers who produced a lot per target even with low volume
#   (e.g. Luther Burden in a crowded 2025 Chicago WR room).
# RB: carries + targets + Y/A efficiency bonus (* 30 scaling factor).
# Weight: 20%
def score_role_share(df):
    volume = pd.Series(0.0, index=df.index)
    # WR/TE — targets adjusted by yards per target efficiency
    ytgt = pd.to_numeric(df['Y/Tgt'], errors='coerce').fillna(0).clip(lower=0)
    ytgt_normalized = min_max_normalize(ytgt)
    volume.loc[df['position'].isin(['WR', 'TE'])] = (
        df['Tgt'].fillna(0) + (ytgt_normalized * 20)
    )
    ya = pd.to_numeric(df['Y/A'], errors='coerce').fillna(0).clip(lower=0)
    ya_normalized = min_max_normalize(ya)
    volume.loc[df['position'] == 'RB'] = (
        df['Att'].fillna(0) + df['Tgt'].fillna(0) + (ya_normalized * 30)
    )
    volume.fillna(0, inplace=True)
    normalized_volume = min_max_normalize(volume)
    role_score = 100 - normalized_volume
    return role_score


# Scores bust risk based on the gap between 2026 ADP and 2025 overall finish rank.
# A player being drafted highly in 2026 who finished poorly in 2025 is a red flag.
# Players with no OvRank (didn't qualify for PFR rankings) are assigned their
# positional median rank + 20 penalty rather than dropped entirely.
# Weight: 10%
def score_adp_vs_finish(df):
    df['OvRank'] = pd.to_numeric(df['OvRank'], errors='coerce')
    medRB = df.loc[df['position'] == 'RB', 'OvRank'].median()
    df.loc[(df['position'] == 'RB') & (df['OvRank'].isna()), 'OvRank'] = medRB + 20
    medWR = df.loc[df['position'] == 'WR', 'OvRank'].median()
    df.loc[(df['position'] == 'WR') & (df['OvRank'].isna()), 'OvRank'] = medWR + 20
    medTE = df.loc[df['position'] == 'TE', 'OvRank'].median()
    df.loc[(df['position'] == 'TE') & (df['OvRank'].isna()), 'OvRank'] = medTE + 20
    gap = df['OvRank'] - df['adp']
    return min_max_normalize(gap)


# Scores bust risk based on fantasy points per game in 2025.
# FPPG is injury-resistant — it captures true per-game value regardless
# of games missed. Inverted so elite FPPG = lower bust risk.
# Weight: 25% — second most important signal alongside age.
def score_fppg(df):
    fppg = pd.to_numeric(df['FPPG'], errors='coerce')
    fppg = fppg.round(2)
    fppg = fppg.fillna(0)
    normalized = min_max_normalize(fppg)
    fppg_score = 100 - normalized
    return fppg_score


# Master scoring function. Separates veterans from rookies, scores each group
# differently, then combines into a single sorted dataframe.
#
# Veterans: scored across all 6 inputs with the following weights:
#   Age (25%) + FPPG (25%) + Role Share (20%) + Injury (10%) +
#   TD Regression (10%) + ADP vs Finish (10%) = 100%
#
# Rookies: scored manually via opportunity_score in rookies_2026.py,
#   inverted to bust_score (high opportunity = low bust risk).
#   No 2025 NFL data exists for true rookies so the model can't score them.
#
# Players with no data (injury, retirement) are flagged or dropped.
# Final output is filtered to ADP <= 120 and sorted by bust_score descending.

def compute_bust_scores(df):
    rookie_names = [r['name'] for r in rookies_2026]
    veterans_df = df[~df['name_clean'].isin(rookie_names)].copy()
    veterans_df = veterans_df.reset_index(drop=True)
    age_scoreV = score_age(veterans_df)
    injury_scoreV = score_injury(veterans_df)
    td_scoreV = score_td_regression(veterans_df)
    role_scoreV = score_role_share(veterans_df)
    adp_finish_scoreV = score_adp_vs_finish(veterans_df)
    fppg_scoreV = score_fppg(veterans_df)
    veterans_df['bust_score'] = (
        age_scoreV * 0.25 +
        injury_scoreV * 0.10 + 
        td_scoreV * 0.10 +
        role_scoreV * 0.20 + 
        adp_finish_scoreV * 0.10+
        fppg_scoreV * 0.25
    )
    veterans_df['data_flag'] = 'ok'
    veterans_df['score_age'] = age_scoreV.round(1)
    veterans_df['score_injury'] = injury_scoreV.round(1)
    veterans_df['score_td'] = td_scoreV.round(1)
    veterans_df['score_role'] = role_scoreV.round(1)
    veterans_df['score_adp'] = adp_finish_scoreV.round(1)
    veterans_df['score_fppg'] = fppg_scoreV.round(1)
    rookies_df = pd.DataFrame(rookies_2026)
    rookies_df['bust_score'] = 100 - rookies_df['opportunity_score']
    rookies_df['data_flag'] = 'rookie'
    rookies_df['FPPG'] = 0
    veterans_df.loc[veterans_df['bust_score'].isna(), 'data_flag'] = 'insufficient'
    retirees = ['amari cooper']
    veterans_df = veterans_df[~veterans_df['name_clean'].isin(retirees)].copy()
    veterans_df = veterans_df.dropna(subset=['bust_score'])
    final_df = pd.concat([veterans_df, rookies_df])
    final_df = final_df[final_df['adp'] <= 120]
    final_df = final_df.sort_values(by='bust_score', ascending=False)
    return final_df


# Entry point: merges all data sources then runs the scoring pipeline.
def get_scored_players():
    df = merge_all()
    df = compute_bust_scores(df)
    return df

if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    result = get_scored_players()
    result['FPPG'] = result['FPPG'].round(2)
    print(result[['name', 'adp', 'position', 'bust_score', 'FPPG', 'data_flag']].to_string())