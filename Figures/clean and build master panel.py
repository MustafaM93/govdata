import pandas as pd
import numpy as np
import re

# -----------------------
# Constants & Utilities
# -----------------------
MIN_YEAR = 2000
MAX_YEAR = 2019

def filter_years(df, year_col="Year"):
    return df[(df[year_col] >= MIN_YEAR) & (df[year_col] <= MAX_YEAR)]

def load_classifications(class_path):
    df = pd.read_excel(class_path)
    df = df.rename(columns={
        "Code": "Country_Code",
        "Economy": "Country_Name",
        "Region": "Region",
        "Income group": "Income_Group"
    })
    return df[["Country_Code", "Country_Name", "Region", "Income_Group"]]


# -----------------------
# Cleaning WDI Data
# -----------------------
def clean_wdi(path, class_df):
    df = pd.read_csv(path)
    region_codes = {
        "AFE","AFW","ARB","CEB","CSS","EAS","EAP","ECA","EMU","EUU",
        "FCS","HIC","HPC","IBD","IBT","IDA","IDX","LCN","LDC","LIC",
        "LMC","LMY","MEA","MIC","NAC","OED","OSS","PRE","PSS","SAS",
        "SSA","SSF","UMC","WLD"
    }
    df = df[~df["Country Code"].isin(region_codes)]
    year_map = {
        col: re.match(r"(\d{4})", col).group(1)
        for col in df.columns
        if re.match(r"^\d{4} \[YR\d{4}\]$", col)
    }
    df.rename(columns=year_map, inplace=True)
    year_cols = [str(y) for y in range(MIN_YEAR, MAX_YEAR + 1)]
    keep = ["Country Name", "Country Code", "Series Name", "Series Code"] + year_cols
    df = df[keep]
    df_long = df.melt(
        id_vars=["Country Name", "Country Code", "Series Name", "Series Code"],
        var_name="Year",
        value_name="Value"
    )
    df_long["Year"] = df_long["Year"].astype(int)
    df_long["Value"] = pd.to_numeric(df_long["Value"], errors="coerce")
    df_long.dropna(subset=["Value"], inplace=True)
    df_long = filter_years(df_long)
    df_long = df_long.merge(
        class_df,
        how="left",
        left_on="Country Code",
        right_on="Country_Code"
    )
    df_long.to_csv("cleaned_wdi.csv", index=False)
    print("✅ cleaned_wdi.csv written")


# -----------------------
# Cleaning WEO Data
# -----------------------
def clean_weo(path, class_df):
    df = pd.read_excel(path, sheet_name=0)
    df.columns = df.columns.astype(str).str.strip().str.replace(".0", "", regex=False)
    year_cols = [str(y) for y in range(MIN_YEAR, MAX_YEAR + 1)]
    keep = ["ISO", "Country", "WEO Subject Code", "Subject Descriptor", "Units"] + year_cols
    keep = [c for c in keep if c in df.columns]
    df = df[keep]
    df = df.melt(
        id_vars=["ISO", "Country", "WEO Subject Code", "Subject Descriptor", "Units"],
        var_name="Year",
        value_name="Value"
    )
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df.dropna(subset=["Value"], inplace=True)
    df = filter_years(df)
    df = df[df["WEO Subject Code"] == "NGDPDPC"]
    df = df.rename(columns={"ISO": "Country_Code"})
    df = df.merge(class_df, how="left", on="Country_Code")
    df.to_csv("cleaned_weo.csv", index=False)
    print("✅ cleaned_weo.csv written")


# -----------------------
# Cleaning WGI Data
# -----------------------
def clean_wgi(path, class_df):
    df = pd.read_excel(path)
    df = df.rename(columns={
        "code": "Country_Code",
        "countryname": "Country_Name",
        "year": "Year",
        "indicator": "Indicator",
        "estimate": "Value"
    })
    df["Year"] = df["Year"].astype(int)
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df.dropna(subset=["Value"], inplace=True)
    df = filter_years(df)

    # drop the raw Country_Name so merge brings in the classification version
    df = df.drop(columns=["Country_Name"], errors="ignore")
    df = df.merge(class_df, how="left", on="Country_Code")

    # normalize indicator codes
    df["Indicator"] = df["Indicator"].astype(str).str.upper().str.strip()

    df_wide = df.pivot_table(
        index=["Country_Code", "Country_Name", "Year", "Region", "Income_Group"],
        columns="Indicator",
        values="Value",
        aggfunc="first"
    ).reset_index()

    df_wide = df_wide.rename(columns={
        "CC": "Control_of_Corruption",
        "GE": "Government_Effectiveness",
        "PV": "Political_Stability",
        "RL": "Rule_Of_Law",
        "RQ": "Regulatory_Quality",
        "VA": "Voice_and_Accountability"
    })
    df_wide.to_csv("cleaned_wgi.csv", index=False)
    print("✅ cleaned_wgi.csv written")


# -----------------------
# Cleaning ILO Data
# -----------------------
def clean_ilo(path, class_df):
    df = pd.read_csv(path, low_memory=False)
    df = df.rename(columns={
        "ref_area": "Country_Code",
        "time":     "Year",
        "classif2": "Sector",
        "obs_value":"Value"
    })
    df = df[df["Sector"].isin(["INS_SECTOR_PUB", "INS_SECTOR_PRI"])]
    df["Sector"] = df["Sector"].replace({
        "INS_SECTOR_PUB": "Public",
        "INS_SECTOR_PRI": "Private"
    })
    df_p = df.pivot_table(
        index=["Country_Code", "Year"],
        columns="Sector",
        values="Value",
        aggfunc="first"
    ).reset_index()
    df_p["Public_Sector_Employment_Share"] = (
        df_p["Public"] / (df_p["Public"] + df_p["Private"])
    )
    df_p["Year"] = df_p["Year"].astype(int)
    df_p = filter_years(df_p)
    df_p = df_p.merge(class_df, how="left", on="Country_Code")
    df_p.to_csv("cleaned_ilo.csv", index=False)
    print("✅ cleaned_ilo.csv written")


# -----------------------
# Build & Export Master Panel
# -----------------------
def build_panel():
    wdi = pd.read_csv("cleaned_wdi.csv")
    weo = pd.read_csv("cleaned_weo.csv")
    wgi = pd.read_csv("cleaned_wgi.csv")
    ilo = pd.read_csv("cleaned_ilo.csv")

    # prevent ILO from overwriting WGI classification
    ilo = ilo.drop(columns=["Country_Name", "Region", "Income_Group"], errors="ignore")

    wdi_wide = wdi.pivot_table(
        index=["Country_Code", "Year"],
        columns="Series Code",
        values="Value",
        aggfunc="first"
    ).reset_index()
    if "NY.GDP.PCAP.PP.KD" in wdi_wide.columns:
        wdi_wide = wdi_wide.rename(
            columns={"NY.GDP.PCAP.PP.KD": "WDI_GDP_Per_Capita"}
        )

    weo_wide = weo.pivot_table(
        index=["Country_Code", "Year"],
        columns="WEO Subject Code",
        values="Value",
        aggfunc="first"
    ).reset_index()

    panel = wgi.copy()
    panel = panel.merge(wdi_wide, on=["Country_Code", "Year"], how="left")
    panel = panel.merge(weo_wide, on=["Country_Code", "Year"], how="left")
    panel = panel.merge(ilo,       on=["Country_Code", "Year"], how="left")

    panel["Year"] = panel["Year"].astype(int)
    panel = filter_years(panel)

    if "Public_Sector_Employment_Share" in panel.columns:
        ok = panel["Public_Sector_Employment_Share"].le(1) | panel["Public_Sector_Employment_Share"].isna()
        panel = panel.loc[ok]

    if "WDI_GDP_Per_Capita" in panel.columns:
        panel["log_GDP_Per_Capita"] = panel["WDI_GDP_Per_Capita"].apply(
            lambda x: np.log(x) if pd.notnull(x) and x > 0 else np.nan
        )

    key_cols = [
        "Country_Code", "Country_Name", "Region", "Income_Group", "Year",
        "Government_Effectiveness", "Control_of_Corruption",
        "Political_Stability", "Rule_Of_Law", "Regulatory_Quality", "Voice_and_Accountability",
        "Public_Sector_Employment_Share", "WDI_GDP_Per_Capita", "log_GDP_Per_Capita"
    ]
    existing = [c for c in key_cols if c in panel.columns]
    rest     = [c for c in panel.columns if c not in existing]
    panel    = panel[existing + rest]

    panel.to_csv("master_panel_cleaned.csv", index=False)
    print(f"✅ master_panel_cleaned.csv ready ({panel.shape[0]} × {panel.shape[1]})")


# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    class_df = load_classifications("CLASS.xlsx")
    clean_wdi("WDI Data.csv",      class_df)
    clean_weo("WEOApr2024.xlsx",   class_df)
    clean_wgi("wgidataset.xlsx",   class_df)
    clean_ilo("ILO Data.csv",      class_df)
    build_panel()
