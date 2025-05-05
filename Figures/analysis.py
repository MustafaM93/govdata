import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from linearmodels.panel import PanelOLS
import numpy as np

# ──────────────────────────────────────────────────────────────────────────────
# 0. Settings & folders
# ──────────────────────────────────────────────────────────────────────────────
sns.set(style="whitegrid")
plt.rcParams["figure.dpi"] = 120

os.makedirs("figures", exist_ok=True)
os.makedirs("output",   exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# 1. Load cleaned panel and fix up columns
# ──────────────────────────────────────────────────────────────────────────────
df = pd.read_csv("master_panel_cleaned.csv", dtype={"Country_Code": str})

# Ensure Year is integer
df["Year"] = df["Year"].astype(int, errors="ignore")

# Combine any duplicated Region / Income_Group columns, then drop the old ones
if "Region_x" in df.columns:
    df["Region"] = df["Region_y"].combine_first(df["Region_x"])
if "Income_Group_x" in df.columns:
    df["Income_Group"] = df["Income_Group_y"].combine_first(df["Income_Group_x"])
df = df.drop(columns=["Region_x", "Region_y", "Income_Group_x", "Income_Group_y"], errors="ignore")

# Unify Country_Name
if "Country Name" in df.columns:
    df = df.rename(columns={"Country Name": "Country_Name"})

# Convert public sector share from fraction → percent
if "Public_Sector_Employment_Share" in df.columns:
    df["Public_Sector_Employment_Share"] = df["Public_Sector_Employment_Share"] * 100

# Robustly compute log_GDP_Per_Capita if missing
if "log_GDP_Per_Capita" not in df.columns:
    if "WDI_GDP_Per_Capita" in df.columns:
        df["log_GDP_Per_Capita"] = np.log(df["WDI_GDP_Per_Capita"].clip(lower=1e-6))
    else:
        # try to find any GDP per capita column
        candidates = [c for c in df.columns if "GDP" in c.upper() and "PCAP" in c.upper()]
        if candidates:
            df["log_GDP_Per_Capita"] = np.log(df[candidates[0]].clip(lower=1e-6))
        else:
            df["log_GDP_Per_Capita"] = np.nan

# ──────────────────────────────────────────────────────────────────────────────
# 2. Choropleth: Government Effectiveness Over Time (with country‐name hover)
# ──────────────────────────────────────────────────────────────────────────────
choropleth_df = (
    df[["Country_Code", "Country_Name", "Year", "Government_Effectiveness"]]
      .dropna(subset=["Country_Code", "Year", "Government_Effectiveness"])
)
choropleth_df["Year"] = choropleth_df["Year"].astype(str)

fig = px.choropleth(
    choropleth_df,
    locations="Country_Code",
    locationmode="ISO-3",
    color="Government_Effectiveness",
    hover_name="Country_Name",
    hover_data={"Government_Effectiveness": ":.2f"},
    animation_frame="Year",
    range_color=[
        choropleth_df["Government_Effectiveness"].min(),
        choropleth_df["Government_Effectiveness"].max()
    ],
    color_continuous_scale="RdYlGn",
    title="Government Effectiveness Over Time (2000–2019)"
)
fig.update_layout(
    geo=dict(showframe=False, showcoastlines=False),
    margin=dict(l=0, r=0, t=50, b=0)
)
if fig.layout.sliders and fig.layout.sliders[0].steps:
    fig.layout.sliders[0].steps = sorted(
        fig.layout.sliders[0].steps,
        key=lambda step: int(step["label"])
    )
fig.write_html("figures/government_effectiveness_over_time.html")
fig.show()


# ──────────────────────────────────────────────────────────────────────────────
# 3. Government Effectiveness Trend by Region
# ──────────────────────────────────────────────────────────────────────────────
region_trend = df.groupby(["Year", "Region"])["Government_Effectiveness"].mean().reset_index()

plt.figure(figsize=(10, 6))
sns.lineplot(data=region_trend, x="Year", y="Government_Effectiveness", hue="Region", marker="o")
plt.title("Trend of Government Effectiveness by Region (2000–2019)")
plt.ylabel("Government Effectiveness (WGI Score)")
plt.tight_layout()
plt.savefig("figures/region_government_effectiveness_trend.png")
plt.show()

# ──────────────────────────────────────────────────────────────────────────────
# 4. Public Sector Employment Share by Region
# ──────────────────────────────────────────────────────────────────────────────
emp_trend = df.groupby(["Year", "Region"])["Public_Sector_Employment_Share"].mean().reset_index()

plt.figure(figsize=(10, 6))
sns.lineplot(
    data=emp_trend,
    x="Year",
    y="Public_Sector_Employment_Share",
    hue="Region",
    marker="o"
)
plt.title("Trend in Public Sector Employment Share by Region (2000–2019)")
plt.ylabel("Public Sector Employment Share (%)")
plt.tight_layout()
plt.savefig("figures/region_public_sector_share_trend.png")
plt.show()

# ──────────────────────────────────────────────────────────────────────────────
# 5. East Asia Focus: Gov. Effectiveness vs. Other Regions
# ──────────────────────────────────────────────────────────────────────────────
east_asia = df[df["Region"] == "East Asia & Pacific"]

plt.figure(figsize=(10, 6))
sns.lineplot(
    data=east_asia,
    x="Year",
    y="Government_Effectiveness",
    label="East Asia & Pacific",
    marker="o",
    ci="sd"
)
for region in df["Region"].unique():
    if region != "East Asia & Pacific":
        sns.lineplot(
            data=df[df["Region"] == region],
            x="Year",
            y="Government_Effectiveness",
            color="grey",
            alpha=0.2,
            linewidth=0.5
        )
plt.title("Government Effectiveness — Highlighting East Asia & Pacific (2000–2019)")
plt.ylabel("Government Effectiveness (WGI Score)")
plt.tight_layout()
plt.savefig("figures/east_asia_vs_world_gov_eff.png")
plt.show()

# ──────────────────────────────────────────────────────────────────────────────
# 6. Bureaucracy vs. Government Effectiveness (East Asia)
# ──────────────────────────────────────────────────────────────────────────────
ea_clean1 = east_asia.dropna(subset=["Public_Sector_Employment_Share", "Government_Effectiveness"])

plt.figure(figsize=(10, 6))
sns.regplot(
    data=ea_clean1,
    x="Public_Sector_Employment_Share",
    y="Government_Effectiveness",
    scatter_kws={"alpha": 0.6}
)
plt.title("Bureaucracy vs. Government Effectiveness\nEast Asia & Pacific (2000–2019)")
plt.xlabel("Public Sector Employment Share (%)")
plt.ylabel("Government Effectiveness (WGI Score)")
plt.tight_layout()
plt.savefig("figures/east_asia_bureaucracy_vs_gov_eff.png")
plt.show()

# ──────────────────────────────────────────────────────────────────────────────
# 7. Bureaucracy vs. Economic Prosperity (East Asia)
# ──────────────────────────────────────────────────────────────────────────────
if "log_GDP_Per_Capita" in df.columns:
    ea_clean2 = east_asia.dropna(subset=["Public_Sector_Employment_Share", "log_GDP_Per_Capita"])
    plt.figure(figsize=(10, 6))
    sns.regplot(
        data=ea_clean2,
        x="Public_Sector_Employment_Share",
        y="log_GDP_Per_Capita",
        scatter_kws={"alpha": 0.6},
        line_kws={}
    )
    plt.title("Bureaucracy vs. Economic Prosperity\nEast Asia & Pacific (2000–2019)")
    plt.xlabel("Public Sector Employment Share (%)")
    plt.ylabel("log GDP Per Capita")
    plt.tight_layout()
    plt.savefig("figures/east_asia_bureaucracy_vs_log_gdp.png")
    plt.show()
else:
    print("Skipping econ‐prosperity plot: 'log_GDP_Per_Capita' not available.")

# ──────────────────────────────────────────────────────────────────────────────
# 8. Panel OLS: Lagged Public Employment → Governance
# ──────────────────────────────────────────────────────────────────────────────
reg_vars = ["Government_Effectiveness", "Public_Sector_Employment_Share", "log_GDP_Per_Capita"]
df_panel = df.set_index(["Country_Code", "Year"])[reg_vars]

# Create lags before dropping
for lag in [1, 2, 3]:
    df_panel[f"Lag{lag}"] = df_panel.groupby(level=0)["Public_Sector_Employment_Share"].shift(lag)

models = {}
for lag in [1, 2, 3]:
    data = df_panel.dropna(subset=["Government_Effectiveness", f"Lag{lag}", "log_GDP_Per_Capita"])
    formula = (
        f"Government_Effectiveness ~ 1 + Lag{lag} + log_GDP_Per_Capita "
        "+ EntityEffects + TimeEffects"
    )
    model = PanelOLS.from_formula(formula, data=data)
    results = model.fit(cov_type="clustered", cluster_entity=True)
    models[lag] = results

# ──────────────────────────────────────────────────────────────────────────────
# 9. Plot Coefficients (Lag 1, 2, 3)
# ──────────────────────────────────────────────────────────────────────────────
lags, coefs, lower_ci, upper_ci = [], [], [], []

for lag, res in models.items():
    coef = res.params[f"Lag{lag}"]
    se   = res.std_errors[f"Lag{lag}"]
    lci  = coef - 1.96 * se
    uci  = coef + 1.96 * se
    lags.append(f"Lag {lag}")
    coefs.append(coef)
    lower_ci.append(lci)
    upper_ci.append(uci)

plt.figure(figsize=(8, 6))
plt.bar(
    lags,
    coefs,
    yerr=[np.subtract(coefs, lower_ci), np.subtract(upper_ci, coefs)],
    capsize=10,
    edgecolor="black"
)
plt.axhline(0, color="gray", linestyle="--")
plt.title("Impact of Lagged Public Employment on Government Effectiveness")
plt.ylabel("Coefficient Estimate")
plt.xlabel("Lagged Variable")
plt.tight_layout()
plt.savefig("figures/lagged_public_employment_effects.png")
plt.show()

# ──────────────────────────────────────────────────────────────────────────────
# Regional Small‑Multiples: Trends for Each WGI Indicator (2000–2019)
# ──────────────────────────────────────────────────────────────────────────────
wgi_cols = [
    "Government_Effectiveness",
    "Control_of_Corruption",
    "Regulatory_Quality",
    "Rule_Of_Law",
    "Political_Stability",
    "Voice_and_Accountability"
]

region_wgi = (
    df
    .groupby(["Year", "Region"])[wgi_cols]
    .mean()
    .reset_index()
    .melt(id_vars=["Year", "Region"], var_name="Indicator", value_name="Score")
)
region_wgi["Indicator_Label"] = region_wgi["Indicator"].str.replace("_", " ").str.title()

# 1. Draw facets **with** a legend built in
g = sns.relplot(
    data=region_wgi,
    x="Year", y="Score",
    kind="line",
    hue="Region",
    col="Indicator_Label",
    col_wrap=3,
    height=3.5, aspect=1.2,
    palette="tab10",
    legend="full",            # build legend
    facet_kws=dict(sharey=False, sharex=True)
)

# 2. Style each panel
for ax in g.axes.flat:
    ax.grid(True, linestyle=":", alpha=0.6)

g.set_titles("{col_name}")
g.set_axis_labels("Year", "Avg WGI Score")
g.fig.subplots_adjust(top=0.88, right=0.75)
g.fig.suptitle("Regional Trends by WGI Indicator (2000–2019)", fontsize=16)

# shrink the grid to make room
g.fig.subplots_adjust(right=0.75)

# grab handles & labels from any one axis
handles, labels = g.axes[0].get_legend_handles_labels()

plt.tight_layout(rect=[0, 0, 0.75, 0.95])
plt.savefig("figures/region_all_wgi_smallmultiples.png", dpi=300)
plt.show()