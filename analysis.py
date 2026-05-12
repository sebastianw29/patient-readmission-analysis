import numpy as np
import pandas as pd
import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import warnings, pickle
warnings.filterwarnings('ignore')
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── 1. LOAD & CLEAN ──────────────────────────────────────────────────────────
df = pd.read_csv('diabetic_data.csv', na_values=['?'])
print(f"Raw shape: {df.shape}")

df = df[~df['discharge_disposition_id'].isin([11, 19, 20, 21])].copy()
print(f"After removing expired: {df.shape}")

df = df.sort_values('encounter_id').drop_duplicates(subset='patient_nbr', keep='first').copy()
print(f"After dedup (1/patient): {df.shape}")

df['readmit_30'] = (df['readmitted'] == '<30').astype(int)
print(f"30-day readmit rate: {df['readmit_30'].mean()*100:.1f}%")

# ── 2. ICD-9 → CATEGORY MAP (Strack et al. 2014, Table 2) ───────────────────
def map_diag(code):
    if pd.isna(code): return 'Other'
    code = str(code).strip()
    if code.startswith('V') or code.startswith('E'): return 'Other'
    try: c = float(code)
    except ValueError: return 'Other'
    if (390 <= c <= 459) or c == 785: return 'Circulatory'
    if (460 <= c <= 519) or c == 786: return 'Respiratory'
    if (520 <= c <= 579) or c == 787: return 'Digestive'
    if 250 <= c < 251:                return 'Diabetes'
    if 800 <= c <= 999:               return 'Injury'
    if 710 <= c <= 739:               return 'Musculoskeletal'
    if (580 <= c <= 629) or c == 788: return 'Genitourinary'
    if 140 <= c <= 239:               return 'Neoplasms'
    return 'Other'

df['diag_cat'] = df['diag_1'].apply(map_diag)

# ── 3. FEATURE GROUPS ────────────────────────────────────────────────────────
age_order  = ['[0-10)','[10-20)','[20-30)','[30-40)','[40-50)',
               '[50-60)','[60-70)','[70-80)','[80-90)','[90-100)']
los_bins   = [0,2,4,6,8,11,15]; los_labels = ['1-2','3-4','5-6','7-8','9-11','12-14']
med_bins   = [0,5,10,15,20,25,81]; med_labels = ['1-5','6-10','11-15','16-20','21-25','26+']

df['los_group'] = pd.cut(df['time_in_hospital'], bins=los_bins, labels=los_labels)
df['med_group'] = pd.cut(df['num_medications'],  bins=med_bins, labels=med_labels)
df['prior_inpatient'] = df['number_inpatient'].clip(0,5)
df['A1C'] = df['A1Cresult'].fillna('None')

overall_rate = df['readmit_30'].mean() * 100
N = len(df)

print(f"\nFinal: {N:,} patients | overall rate: {overall_rate:.1f}%")
print(df['diag_cat'].value_counts())

# ── 4. AGGREGATE STATS ───────────────────────────────────────────────────────
age_stats   = df.groupby('age',             observed=True)['readmit_30'].agg(['mean','count']).reindex(age_order)
age_stats['mean'] *= 100

diag_stats  = df.groupby('diag_cat')['readmit_30'].agg(['mean','count']).sort_values('mean', ascending=False)
diag_stats['mean'] *= 100

los_stats   = df.groupby('los_group',       observed=True)['readmit_30'].agg(['mean','count'])
los_stats['mean'] *= 100

med_stats   = df.groupby('med_group',       observed=True)['readmit_30'].agg(['mean','count'])
med_stats['mean'] *= 100

a1c_order   = ['None','Norm','>7','>8']
a1c_stats   = df.groupby('A1C')['readmit_30'].agg(['mean','count']).reindex(a1c_order)
a1c_stats['mean'] *= 100

race_stats  = df.groupby('race')['readmit_30'].agg(['mean','count']).sort_values('mean', ascending=False)
race_stats['mean'] *= 100

inpat_stats = df.groupby('prior_inpatient')['readmit_30'].agg(['mean','count'])
inpat_stats['mean'] *= 100

# ── 5. COLORS ───────────────────────────────────────────────────────────────
C_NAVY='#1E3A5F'; C_BLUE='#2563EB'; C_RED='#DC2626'
C_AMBER='#D97706'; C_GREEN='#059669'; C_LIGHT='#EFF6FF'; C_SLATE='#94A3B8'

# ══════════════════════════════════════════════════════════════════════════════
# FIG 1 — Four Key Predictors  (2×2)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.patch.set_facecolor('#0F172A')
fig.suptitle(
    f'Patient 30-Day Readmission Risk — Four Key Predictors\n'
    f'UCI Diabetes 130-US Hospitals Dataset  |  N = {N:,} patients  |  1999–2008',
    fontsize=14, fontweight='bold', color='#F1F5F9', y=0.99)

def dark_ax_light(ax):
    ax.set_facecolor('#1E293B')
    ax.tick_params(colors='#CBD5E1', labelsize=8)
    for s in ax.spines.values(): s.set_edgecolor('#334155')
    ax.xaxis.label.set_color('#94A3B8'); ax.yaxis.label.set_color('#94A3B8')
    ax.title.set_color('#F1F5F9')

# A — Age
ax = axes[0,0]; dark_ax_light(ax)
vals = age_stats['mean'].values
bars = ax.bar(range(len(vals)), vals,
              color=[C_RED if v > overall_rate else C_BLUE for v in vals],
              edgecolor='#0F172A', linewidth=0.7, width=0.72)
ax.set_xticks(range(len(age_order)))
ax.set_xticklabels([a.replace('[','').replace(')','') for a in age_order], fontsize=8, rotation=30, ha='right')
ax.axhline(overall_rate, color='white', linestyle='--', linewidth=1.4, alpha=0.6)
ax.set_title('A  |  Readmission Rate by Age Group', fontweight='bold', color='#F1F5F9', loc='left', pad=6)
ax.set_ylabel('30-Day Readmission Rate (%)')
ax.yaxis.grid(True, alpha=0.15); ax.set_axisbelow(True)
red_p  = mpatches.Patch(color=C_RED,  label=f'Above avg ({overall_rate:.1f}%)')
blue_p = mpatches.Patch(color=C_BLUE, label='Below avg')
leg = ax.legend(handles=[red_p, blue_p], fontsize=8, loc='upper left')
leg.get_frame().set_facecolor('#334155'); leg.get_frame().set_edgecolor('#475569')
for text in leg.get_texts(): text.set_color('#F1F5F9')
for bar, val in zip(bars, vals):
    if not np.isnan(val):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=7, color='#CBD5E1')

# B — Diagnosis
ax = axes[0,1]; dark_ax_light(ax)
d = diag_stats.sort_values('mean')
ax.barh(range(len(d)), d['mean'].values,
        color=[C_RED if v > overall_rate else C_BLUE for v in d['mean'].values],
        edgecolor='#0F172A', linewidth=0.6, height=0.65)
ax.set_yticks(range(len(d))); ax.set_yticklabels(d.index, fontsize=9)
ax.axvline(overall_rate, color='white', linestyle='--', linewidth=1.4, alpha=0.6)
ax.set_title('B  |  Readmission Rate by Primary Diagnosis', fontweight='bold', color='#F1F5F9', loc='left', pad=6)
ax.set_xlabel('30-Day Readmission Rate (%)')
ax.xaxis.grid(True, alpha=0.15); ax.set_axisbelow(True)
for i, (val, n) in enumerate(zip(d['mean'].values, d['count'].values)):
    ax.text(val+0.1, i, f'{val:.1f}%  (n={n:,})', va='center', fontsize=8, color='#CBD5E1')
ax.set_xlim(0, d['mean'].max()*1.45)

# C — Length of Stay (dual axis)
ax  = axes[1,0]; dark_ax_light(ax)
ax2 = ax.twinx()
ax2.set_facecolor('#1E293B')
ax2.tick_params(colors='#CBD5E1', labelsize=8)
ax2.yaxis.label.set_color('#94A3B8')
for s in ax2.spines.values(): s.set_edgecolor('#334155')
los_r = los_stats['mean'].values
los_n = los_stats['count'].values
ax.bar(range(len(los_r)), los_r,
       color=plt.cm.Blues(np.linspace(0.45, 0.95, len(los_r))),
       edgecolor='#0F172A', linewidth=0.6, width=0.62)
ax2.plot(range(len(los_n)), los_n, 'o-', color=C_RED, linewidth=2, markersize=6, label='# Patients')
ax.set_xticks(range(len(los_labels)))
ax.set_xticklabels([f'{l} days' for l in los_labels], fontsize=9)
ax.axhline(overall_rate, color='white', linestyle='--', linewidth=1.2, alpha=0.6, label=f'Avg {overall_rate:.1f}%')
ax.set_title('C  |  Length of Stay vs Readmission Risk', fontweight='bold', color='#F1F5F9', loc='left', pad=6)
ax.set_ylabel('30-Day Readmission Rate (%)', color='#93C5FD')
ax2.set_ylabel('Patient Count', color=C_RED)
ax.yaxis.grid(True, alpha=0.15); ax.set_axisbelow(True)
h1,l1 = ax.get_legend_handles_labels(); h2,l2 = ax2.get_legend_handles_labels()
leg = ax.legend(h1+h2, l1+l2, fontsize=8, loc='upper right')
leg.get_frame().set_facecolor('#334155'); leg.get_frame().set_edgecolor('#475569')
for text in leg.get_texts(): text.set_color('#F1F5F9')
for i, val in enumerate(los_r):
    ax.text(i, val+0.2, f'{val:.1f}%', ha='center', va='bottom', fontsize=8, color='#CBD5E1')

# D — Prior Inpatient Visits
ax = axes[1,1]; dark_ax_light(ax)
iv = inpat_stats['mean'].values
lv = [str(int(x)) if x < 5 else '5+' for x in inpat_stats.index]
ax.bar(range(len(iv)), iv,
       color=plt.cm.RdYlGn_r(np.linspace(0.15, 0.85, len(iv))),
       edgecolor='#0F172A', linewidth=0.6, width=0.65)
ax.plot(range(len(iv)), iv, 'D--', color='#F1F5F9', markersize=6, linewidth=1.5, label='Trend')
ax.axhline(overall_rate, color='#94A3B8', linestyle='--', linewidth=1.2, label=f'Avg {overall_rate:.1f}%')
ax.set_xticks(range(len(lv))); ax.set_xticklabels([f'{l} visits' for l in lv], fontsize=9)
ax.set_title('D  |  Prior Inpatient Visits vs Readmission', fontweight='bold', color='#F1F5F9', loc='left', pad=6)
ax.set_ylabel('30-Day Readmission Rate (%)')
ax.yaxis.grid(True, alpha=0.15); ax.set_axisbelow(True)
leg = ax.legend(fontsize=8)
leg.get_frame().set_facecolor('#334155'); leg.get_frame().set_edgecolor('#475569')
for text in leg.get_texts(): text.set_color('#F1F5F9')
for bar, val in zip(ax.patches, iv):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.2,
            f'{val:.1f}%', ha='center', va='bottom', fontsize=8, color='#CBD5E1')

plt.tight_layout(rect=[0,0,1,0.96])
plt.savefig('fig_key_predictors.png', dpi=150, bbox_inches='tight',
            facecolor=fig.get_facecolor())
plt.show()
plt.close()
print("Saved: fig_key_predictors.png")

# ══════════════════════════════════════════════════════════════════════════════
# FIG 2 — Full Dashboard (dark)
# ══════════════════════════════════════════════════════════════════════════════
fig2 = plt.figure(figsize=(17,10))
fig2.patch.set_facecolor('#0F172A')
gs = GridSpec(2,3,figure=fig2,hspace=0.45,wspace=0.35)

def dark_ax(ax):
    ax.set_facecolor('#1E293B')
    ax.tick_params(colors='#CBD5E1',labelsize=8)
    for s in ax.spines.values(): s.set_edgecolor('#334155')
    ax.xaxis.label.set_color('#94A3B8'); ax.yaxis.label.set_color('#94A3B8')
    ax.title.set_color('#F1F5F9')

# Donut
ax = fig2.add_subplot(gs[0,0]); dark_ax(ax)
ct_yes = int((df['readmit_30']==1).sum())
ct_gt  = int((df['readmitted']=='>30').sum())
ct_no  = int((df['readmitted']=='NO').sum())
wedges,texts,autos = ax.pie(
    [ct_yes,ct_gt,ct_no], labels=['<30 days','>30 days','No readmit'],
    colors=[C_RED,C_AMBER,'#334155'], autopct='%1.1f%%', startangle=90,
    pctdistance=0.72, wedgeprops=dict(width=0.52,edgecolor='#0F172A',linewidth=2.5))
for t in texts:  t.set_color('#CBD5E1'); t.set_fontsize(8)
for a in autos:  a.set_color('white');   a.set_fontsize(9); a.set_fontweight('bold')
ax.set_title(f'Readmission Breakdown\n({N:,} patients)', fontweight='bold')

# Race
ax = fig2.add_subplot(gs[0,1]); dark_ax(ax)
rc = race_stats.dropna()
ax.barh(range(len(rc)), rc['mean'].values,
        color=[C_RED if v>overall_rate else '#3B82F6' for v in rc['mean'].values],
        height=0.6, edgecolor='#0F172A')
ax.set_yticks(range(len(rc))); ax.set_yticklabels(rc.index, fontsize=8)
ax.axvline(overall_rate, color='white', linestyle='--', lw=1, alpha=0.6)
ax.set_title('Readmission Rate by Race', fontweight='bold')
ax.set_xlabel('30-Day Readmission Rate (%)')
ax.xaxis.grid(True, alpha=0.15); ax.set_axisbelow(True)
for i,(val,n) in enumerate(zip(rc['mean'].values, rc['count'].values)):
    ax.text(val+0.05, i, f'{val:.1f}%', va='center', color='#CBD5E1', fontsize=8)

# A1C
ax = fig2.add_subplot(gs[0,2]); dark_ax(ax)
a1c_v = a1c_stats['mean'].values
bars_a = ax.bar(range(4), a1c_v,
                color=['#475569','#3B82F6',C_AMBER,C_RED],
                edgecolor='#0F172A', linewidth=0.5, width=0.6)
ax.set_xticks(range(4)); ax.set_xticklabels(a1c_order, fontsize=9)
ax.axhline(overall_rate, color='white', linestyle='--', lw=1, alpha=0.6)
ax.set_title('Readmission Rate by HbA1c Result', fontweight='bold')
ax.set_ylabel('30-Day Readmission Rate (%)')
ax.yaxis.grid(True, alpha=0.15); ax.set_axisbelow(True)
for bar,val,n in zip(bars_a, a1c_v, a1c_stats['count'].values):
    if not np.isnan(val):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                f'{val:.1f}%\n(n={int(n):,})', ha='center', va='bottom', color='white', fontsize=7.5)

# LOS histogram overlay
ax = fig2.add_subplot(gs[1,0:2]); dark_ax(ax)
los_r_v  = df[df['readmit_30']==1]['time_in_hospital']
los_nr_v = df[df['readmit_30']==0]['time_in_hospital']
bins = np.arange(0.5,15.5,1)
ax.hist(los_nr_v, bins=bins, alpha=0.55, color='#3B82F6', density=True,
        label=f'Not Readmitted (n={len(los_nr_v):,})', edgecolor='#0F172A')
ax.hist(los_r_v,  bins=bins, alpha=0.70, color=C_RED, density=True,
        label=f'Readmitted <30d (n={len(los_r_v):,})', edgecolor='#0F172A')
ax.axvline(los_r_v.mean(),  color=C_RED,    linestyle='--', lw=1.5,
           label=f'Readmit mean = {los_r_v.mean():.1f}d')
ax.axvline(los_nr_v.mean(), color='#3B82F6', linestyle='--', lw=1.5,
           label=f'Non-readmit mean = {los_nr_v.mean():.1f}d')
ax.set_xlabel('Length of Stay (days)'); ax.set_ylabel('Density')
ax.set_title('Length of Stay Distribution by Readmission Status', fontweight='bold')
ax.legend(fontsize=8); ax.yaxis.grid(True,alpha=0.15); ax.set_axisbelow(True)
ax.set_xticks(range(1,15))

# Bubble: diagnosis volume vs risk
ax = fig2.add_subplot(gs[1,2]); dark_ax(ax)
bubble_colors=['#DC2626','#F97316','#D97706','#3B82F6','#6366F1','#8B5CF6','#EC4899','#059669','#14B8A6']
for i,(cat,row) in enumerate(diag_stats.iterrows()):
    sz = (row['count']/diag_stats['count'].max())*800+80
    ax.scatter(row['count'], row['mean'], s=sz,
               color=bubble_colors[i%len(bubble_colors)], alpha=0.85,
               edgecolor='white', linewidth=0.8)
    ax.annotate(cat,(row['count'],row['mean']),
                xytext=(4,3), textcoords='offset points',
                color='#CBD5E1', fontsize=7.5)
ax.axhline(overall_rate, color='white', linestyle='--', lw=1, alpha=0.5)
ax.set_xlabel('Patient Volume (n)'); ax.set_ylabel('30-Day Readmit Rate (%)')
ax.set_title('Diagnosis: Volume vs Risk', fontweight='bold')
ax.xaxis.grid(True,alpha=0.15); ax.yaxis.grid(True,alpha=0.15); ax.set_axisbelow(True)

fig2.text(0.5,0.005,
    'Source: Strack et al. (2014) | UCI ML Repository Dataset #296 | CC BY 4.0 | 130 US Hospitals 1999–2008',
    ha='center', color='#475569', fontsize=8)

plt.savefig('fig_dashboard.png', dpi=150, bbox_inches='tight',
            facecolor=fig2.get_facecolor())
plt.show()
plt.close()
print("Saved: fig_dashboard.png")

# ── 6. PICKLE ────────────────────────────────────────────────────────────────
with open('stats.pkl','wb') as f:
    pickle.dump({'df':df,'N':N,'overall_rate':overall_rate,
                 'age_stats':age_stats,'diag_stats':diag_stats,
                 'los_stats':los_stats,'med_stats':med_stats,
                 'a1c_stats':a1c_stats,'race_stats':race_stats,
                 'inpat_stats':inpat_stats}, f)
print("Done.")
