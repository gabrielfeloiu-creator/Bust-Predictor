import pandas as pd
import requests


'''
This is commented out until the ADP data from the pre-2026 season comes in 
def load_adp():
    url = requests.get('https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=12&year=2027')
    parsed = url.json()
    df = pd.DataFrame(parsed['players'])
    filtered_df = df[~df['position'].isin(['QB', 'K', 'PK', 'DEF'])]
    df_final = filtered_df[['player_id', 'name', 'position', 'team', 'adp']]
    return df_final
'''

# Loads 2026 ADP data from a FantasyPros CSV export.
# Strips positional rank suffix from POS column (e.g. 'RB1' -> 'RB'),
# filters out QBs, kickers, and DSTs, and renames columns for consistency.
def load_adp():
    df = pd.read_csv('fantasy.csv')
    df['position'] = df['POS'].str[:2]
    filtered_df = df[~df['position'].isin(['QB', 'DS'])]
    filtered_df = filtered_df.rename(columns={'AVG': 'adp'})
    filtered_df['adp'] = filtered_df['adp'].astype(float)
    df_final = filtered_df[['Player', 'adp', 'position', 'Team']]
    df_final = df_final.rename(columns={'Player': 'name', 'Team': 'team'})
    return df_final

# Loads 2025 season fantasy stats from Pro Football Reference.
# Filters out QBs since the scoring model is built for skill positions only.
# Computes FPPG (fantasy points per game) to normalize across players
# who missed games due to injury — raw PPR totals alone are misleading.
def load_fantasy_stats():
    df = pd.read_csv('fantasy_2025.csv')
    filtered_df = df[df['FantPos'] != 'QB']
    df_final = filtered_df[['Player', 'FantPos', 'Age','G', 'PPR', 'OvRank']]
    df_final['FPPG'] = df_final['PPR'] / df_final['G']
    return df_final

# Loads 2025 receiving stats from Pro Football Reference.
# Keeps target share and efficiency metrics (Y/R, Y/Tgt) which are used
# in score_role_share() to reward efficient receivers with low volume.
def load_receving():
    df = pd.read_csv('receiving_2025.csv')
    filtered_df = df[df['Pos'] != 'QB']
    df_final = filtered_df[['Player', 'Pos', 'Tgt','Rec', 'TD', 'Yds', 'Y/R', 'Y/Tgt']]
    numeric_cols = df_final.select_dtypes(include='number').columns
    df_final[numeric_cols] = df_final[numeric_cols].astype(float)
    return df_final


# Loads 2025 rushing stats from Pro Football Reference.
# Y/A (yards per attempt) is kept as an efficiency signal for RBs 
# used in score_role_share() to avoid penalizing efficient backs
# who had low carry volume due to timeshares or injury.
def load_rushing():
    df = pd.read_csv('rushing_2025.csv')
    filtered_df = df[df['Pos'] != 'QB']
    df_final = filtered_df[['Player', 'Att','Y/A', 'TD', 'G', 'Y/G', 'Yds']]
    numeric_cols = df_final.select_dtypes(include='number').columns
    df_final[numeric_cols] = df_final[numeric_cols].astype(float)
    return df_final

# Fetches player headshot URLs from the nflverse public GitHub release.
# This is a free, community-maintained dataset that includes headshot URLs
# for all active NFL players. Used to populate player card images.
def load_headshots():
    url = 'https://github.com/nflverse/nflverse-data/releases/download/players/players.csv'
    df = pd.read_csv(url, low_memory=False)
    df = df[['display_name', 'headshot']].copy()
    df = df.rename(columns={'display_name': 'name'})
    df['name_clean'] = df['name'].apply(normalize_name)
    return df

# Normalize player names for consistent merging across data sources.
# Strips PFR suffixes (*+), common name suffixes (Jr., Sr.), 
# and maps known aliases (Hollywood Brown -> Marquise Brown)
def normalize_name(name):
    if not isinstance(name, str):
        return ''
    while True:
        if name[-1] != '*' and name[-1] != '+':
            break
        l = len(name)
        name = name[:l-1]
    name = name.lower()
    for suffix in [' sr.', ' jr.', ' ii', ' iii', ' iv']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    aliases = {
    'hollywood brown': 'marquise brown',
    'd.k. metcalf': 'dk metcalf',
    'd.j. moore': 'dj moore'
    }
    name = aliases.get(name, name)
    return name

# Merges all data sources into a single unified dataframe anchored on ADP.
# Uses left joins throughout so every player in the ADP data is preserved,
# even if they're missing from one or more stat tables (injured, rookie, etc.).
# Duplicates can arise when a player appears in multiple PFR tables, 
# drop_duplicates keeps the first occurrence after the merge.
def merge_all():
    adp_df = load_adp()
    fantasy_df = load_fantasy_stats()
    receiving_df = load_receving()
    rushing_df = load_rushing()
    headshots_df = load_headshots()
    adp_df['name_clean'] = adp_df['name'].apply(normalize_name)
    fantasy_df['name_clean'] = fantasy_df['Player'].apply(normalize_name)
    receiving_df['name_clean'] = receiving_df['Player'].apply(normalize_name)
    rushing_df['name_clean'] = rushing_df['Player'].apply(normalize_name)
    merge1 = pd.merge(adp_df, fantasy_df, on='name_clean', how='left')
    merge2 = pd.merge(merge1, receiving_df, on='name_clean', how='left')
    final = pd.merge(merge2, rushing_df, on='name_clean', how='left')
    final = pd.merge(final, headshots_df[['name_clean', 'headshot']], on='name_clean', how='left')
    final = final.drop_duplicates(subset=['name_clean'], keep='first')
    return final

if __name__ == "__main__":
    df = merge_all()

                       