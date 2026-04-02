import streamlit as st
import pandas as pd
import unicodedata
import re
from pathlib import Path
import base64
import plotly.graph_objects as go
# =========================================================
# CONSTANTS
# =========================================================
REPL_MAP = {
    r"\'ea": "ê", r"\'e9": "é", r"\'e8": "è", r"\'b": "",
    r"\'ef": "ï", r"\'e7": "ç", r"\'e2": "â", r"\'9c": "œ",
    r"\'e0": "à", r"\'ee": "î",
}
SELECTOR_MAP = {
    "Menuiseries extérieures": "Extérieure",
    "Menuiserie intérieure": "Intérieure",
    "Revêtements de sol": "Sol",
    "Revêtements murs et plafonds": "Murs et plafonds",
    "Charpente - Ossature": "Charpente - Ossature",
    "Maçonnerie - Gros œuvre": "Maçonnerie - Gros œuvre",
    "Plomberie": "Plomberie",
    "Electricité": "Electricité",
    "Chauffage - Ventilation - Climatisation": "Chauffage - Ventilation - Climatisation",
}
CATEGORY_MERGE_MAP = {
    "Revêtements de sol": "Revêtements intérieurs",
    "Revêtements murs et plafonds": "Revêtements intérieurs",
    "Menuiseries extérieures": "Menuiseries",
    "Menuiserie intérieure": "Menuiseries",
    "Charpente - Ossature": "Structure",
    "Maçonnerie - Gros œuvre": "Structure",
    "Plomberie": "Réseaux techniques",
    "Electricité": "Réseaux techniques",
    "Chauffage - Ventilation - Climatisation": "Réseaux techniques",
}
LOW_CARBON_KEYWORDS = [
    "bas carbone", "chaume", "végétalisée", "biosourcé", "biosourcée",
    "laine", "chanvre", "ouate de cellulose",
]
NONE_SENTINEL = "— Aucune sélection —"
NO_COLUMN = "— Pas de colonne correspondante —"
REGIONS_FRANCE = [
    "Auvergne-Rhône-Alpes",
    "Bourgogne-Franche-Comté",
    "Bretagne",
    "Centre-Val de Loire",
    "Corse",
    "Grand Est",
    "Hauts-de-France",
    "Île-de-France",
    "Normandie",
    "Nouvelle-Aquitaine",
    "Occitanie",
    "Pays de la Loire",
    "Provence-Alpes-Côte d'Azur",
]
EXPECTED_COMPANY_COLS = [
    "Entreprise", "Catégorie", "Domaines d\u2019intervention",
    "Activité principale", "Prestations détaillées",
    "Localisation (siège)", "Régions couvertes", "Lien",
]
# Navy / white palette
NAVY = "#0d2559"
NAVY_LIGHT = "#122b54"
NAVY_MID = "#1a3a6b"
WHITE = "#ffffff"
OFF_WHITE = "#f0f2f6"
ACCENT_BLUE = "#4a90d9"
ACCENT_GREEN = "#5cb85c"
COMPANIES_FILE = "liste_dentreprises.xlsx"
DOCUMENTATION_FILE = "documentation_revert.pdf"
# =========================================================
# THEME
# =========================================================
def inject_theme():
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {NAVY}; color: {WHITE}; }}
        section[data-testid="stSidebar"] {{ background-color: {NAVY_LIGHT}; }}
        header[data-testid="stHeader"] {{ background-color: {NAVY} !important; }}
        button[data-baseweb="tab"] {{ color: {WHITE} !important; }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            border-bottom-color: {ACCENT_BLUE} !important;
            color: {ACCENT_BLUE} !important;
        }}
        .stSelectbox label, .stRadio label, .stCheckbox label,
        .stNumberInput label, .stTextInput label, .stTextArea label,
        .stMultiSelect label, .stSlider label, .stFileUploader label {{
            color: {WHITE} !important;
        }}
        [data-testid="stMetricValue"] {{ color: {WHITE} !important; }}
        [data-testid="stMetricLabel"] {{ color: #b0bec5 !important; }}
        .stMarkdown, .stMarkdown p, .stMarkdown li,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
        .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {{
            color: {WHITE} !important;
        }}
        div[data-testid="stNotification"] {{
            background-color: {NAVY_LIGHT} !important; color: {WHITE} !important;
        }}
        .stDataFrame {{ border: 1px solid {NAVY_MID}; border-radius: 6px; }}
        .stRadio div[role="radiogroup"] label span {{ color: {WHITE} !important; }}
        hr {{ border-color: {NAVY_MID} !important; }}
        .stButton > button {{ border: 1px solid {ACCENT_BLUE}; color: {WHITE}; }}
        .stButton > button:hover {{
            background-color: {NAVY_MID}; border-color: {WHITE};
        }}
        .stButton > button[kind="primary"] {{
            background-color: {ACCENT_BLUE}; color: {WHITE};
        }}
        details summary span {{ color: {WHITE} !important; }}
        details {{ border-color: {NAVY_MID} !important; }}
        .stCaption, small {{ color: #90a4ae !important; }}
        .stTabs [data-testid="stTabContent"] {{ background-color: {NAVY}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
# =========================================================
# LOGO
# =========================================================
def render_logo():
    logo_path = Path(__file__).parent / "revert_logo.svg"
    if logo_path.exists():
        b64 = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
        st.markdown(
            f"""
            <div style="width:100%;background-color:{NAVY};text-align:center;
                        padding:32px 0 20px 0;margin-bottom:4px;">
                <img src="data:image/svg+xml;base64,{b64}"
                     style="width:clamp(280px,45%,600px);height:auto;" />
                <div style="color:#b0bec5;font-size:0.95em;letter-spacing:0.08em;
                            margin-top:12px;text-transform:uppercase;">
                    Chiffrage sinistre — Comparateur carbone
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.title("Chiffrage sinistre — Comparateur carbone")
# =========================================================
# UTILITY FUNCTIONS
# =========================================================
def normalize_text(value: str) -> str:
    if pd.isna(value):
        return ""
    text = str(value).lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text
NORMALIZED_LOW_CARBON_KEYWORDS = [normalize_text(x) for x in LOW_CARBON_KEYWORDS]
def is_low_carbon_option(row: pd.Series) -> bool:
    text = f"{row.get('Sous_categorie', '')} {row.get('Produit_process', '')}"
    text_norm = normalize_text(text)
    keyword_match = any(kw in text_norm for kw in NORMALIZED_LOW_CARBON_KEYWORDS)
    emissions = row.get("Emissions_CO2")
    emissions_rule = pd.notna(emissions) and float(emissions) <= 0
    return keyword_match or emissions_rule
def split_categories(cell_value: str) -> list:
    if pd.isna(cell_value):
        return []
    text = str(cell_value).strip()
    parts = re.split(r"[,;]+", text)
    return [p.strip() for p in parts if p.strip()]
# =========================================================
# DATA LOADING — default HTML
# =========================================================
@st.cache_data
def load_df(html_path: str) -> pd.DataFrame:
    tables = pd.read_html(html_path)
    if not tables:
        raise ValueError("No tables found in the HTML file")
    df = tables[0].copy()
    df.columns = [
        "Categorie", "Sous_categorie", "Produit_process",
        "Unite", "Type_prestation", "Prestation", "Emissions_CO2",
    ]
    df = df.iloc[1:].reset_index(drop=True)
    for col in df.columns:
        if df[col].dtype == object:
            s = df[col].astype(str)
            for pat, repl in REPL_MAP.items():
                s = s.str.replace(pat, repl, regex=False)
            df[col] = s
    df["Emissions_CO2"] = pd.to_numeric(df["Emissions_CO2"], errors="coerce")
    df["Categorie_old"] = df["Categorie"]
    df["Selector"] = df["Categorie"].map(SELECTOR_MAP)
    df["Categorie"] = df["Categorie"].replace(CATEGORY_MERGE_MAP)
    return df
# =========================================================
# DATA LOADING — alternate user file
# =========================================================
def load_alternate_file(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".html") or name.endswith(".htm"):
        tables = pd.read_html(uploaded_file)
        if not tables:
            raise ValueError("Aucune table trouvée dans le fichier HTML.")
        return tables[0]
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    elif name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    else:
        raise ValueError("Format non supporté. Utilisez .html, .xlsx ou .csv.")
def apply_column_mapping(raw_df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    target_cols = [
        "Categorie", "Sous_categorie", "Produit_process",
        "Unite", "Type_prestation", "Prestation", "Emissions_CO2",
    ]
    df = pd.DataFrame()
    for target in target_cols:
        source = mapping.get(target)
        if source and source != NO_COLUMN and source in raw_df.columns:
            df[target] = raw_df[source].astype(str)
        else:
            df[target] = ""
    df["Emissions_CO2"] = pd.to_numeric(df["Emissions_CO2"], errors="coerce")
    df["Categorie_old"] = df["Categorie"]
    df["Selector"] = df["Categorie"].map(SELECTOR_MAP).fillna("")
    df["Categorie"] = df["Categorie"].replace(CATEGORY_MERGE_MAP)
    return df
# =========================================================
# DATA LOADING — companies Excel
# =========================================================
@st.cache_data
def load_companies() -> pd.DataFrame:
    path = Path(__file__).parent / COMPANIES_FILE
    if not path.exists():
        return pd.DataFrame(columns=EXPECTED_COMPANY_COLS)
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].fillna("")
    return df

def _save_companies(df: pd.DataFrame):
    """Write the companies DataFrame back to the Excel file and clear cache."""
    file_path = Path(__file__).parent / COMPANIES_FILE
    df.to_excel(file_path, index=False, engine="openpyxl")
    load_companies.clear()

def filter_companies(companies_df: pd.DataFrame, categories: list) -> pd.DataFrame:
    if companies_df.empty or "Catégorie" not in companies_df.columns:
        return pd.DataFrame()
    cats_norm = {normalize_text(c) for c in categories if c}
    if not cats_norm:
        return pd.DataFrame()
    def _matches(cell):
        parts = split_categories(cell)
        return bool(cats_norm & {normalize_text(p) for p in parts})
    return companies_df[companies_df["Catégorie"].apply(_matches)].reset_index(drop=True)
# =========================================================
# BUILD CANDIDATES
# =========================================================
def build_candidates(filtered_df: pd.DataFrame) -> pd.DataFrame:
    candidates = (
        filtered_df[
            ["Categorie", "Categorie_old", "Selector",
             "Sous_categorie", "Produit_process", "Unite",
             "Type_prestation", "Prestation", "Emissions_CO2"]
        ]
        .dropna(subset=["Produit_process", "Emissions_CO2"])
        .drop_duplicates()
        .copy()
    )
    if candidates.empty:
        return candidates
    candidates["Option_famille"] = candidates.apply(
        lambda row: "Option bas carbone" if is_low_carbon_option(row) else "Standard",
        axis=1,
    )
    candidates = candidates.sort_values(
        ["Option_famille", "Emissions_CO2", "Produit_process"],
        ascending=[True, True, True],
    ).reset_index(drop=True)
    return candidates
def get_reduction_label(pct: float) -> str:
    if pct > 40:
        return "Réduction basse carbone"
    elif pct >= 20:
        return "Réduction performante"
    return "Réduction standard"
def get_reduction_color(pct: float) -> str:
    if pct > 40:
        return "#2e7d32"
    elif pct >= 20:
        return "#f9a825"
    return "#e65100"
# =========================================================
# CALLBACKS for mutual-exclusivity
# =========================================================
def _on_std_change(key_prefix: str):
    lc_key = f"lc_radio_{key_prefix}"
    if st.session_state.get(f"std_radio_{key_prefix}") != NONE_SENTINEL:
        st.session_state[lc_key] = NONE_SENTINEL
def _on_lc_change(key_prefix: str):
    std_key = f"std_radio_{key_prefix}"
    if st.session_state.get(f"lc_radio_{key_prefix}") != NONE_SENTINEL:
        st.session_state[std_key] = NONE_SENTINEL
# =========================================================
# SIDEBAR: COMPANY BROWSER
# =========================================================
def _get_company_categories(companies_df: pd.DataFrame) -> list:
    if companies_df.empty or "Catégorie" not in companies_df.columns:
        return []
    cats = set()
    for cell in companies_df["Catégorie"].dropna():
        for part in split_categories(str(cell)):
            if part:
                cats.add(part)
    return sorted(cats)

def _company_matches_region(row, region: str) -> bool:
    val = str(row.get("Régions couvertes", ""))
    parts = [p.strip() for p in val.split(",") if p.strip()]
    region_norm = normalize_text(region)
    known_region_norms = {normalize_text(r) for r in REGIONS_FRANCE}
    for part in parts:
        part_norm = normalize_text(part)
        if part_norm == region_norm:
            return True
        if part_norm not in known_region_norms:
            return True
    return False

def render_sidebar_companies(companies_df: pd.DataFrame, current_category: str):
    with st.sidebar:
        st.markdown(
            f'<div style="background:{ACCENT_BLUE};color:{WHITE};padding:10px 14px;'
            f'border-radius:8px;font-weight:700;font-size:1.05em;margin-bottom:10px;">'
            f'🏢 Entreprises</div>',
            unsafe_allow_html=True,
        )
        all_sidebar_cats = _get_company_categories(companies_df)
        sidebar_cats = st.multiselect(
            "Filtrer par catégorie(s)",
            all_sidebar_cats if all_sidebar_cats else ["(aucune)"],
            default=[],
            key="sidebar_company_cats",
        )
        region_options = ["Toutes régions"] + REGIONS_FRANCE
        selected_region = st.selectbox(
            "Filtrer par région",
            region_options,
            index=0,
            key="sidebar_region",
        )
        filtered = filter_companies(companies_df, sidebar_cats)
        if not sidebar_cats:
            st.info("Sélectionnez une ou plusieurs catégories pour voir les entreprises.")
            return
        if selected_region != "Toutes régions":
            filtered = filtered[
                filtered.apply(lambda r: _company_matches_region(r, selected_region), axis=1)
            ].reset_index(drop=True)
        if filtered.empty:
            st.info("Aucune entreprise pour cette sélection.")
            return
        st.caption(f"{len(filtered)} entreprise(s) trouvée(s)")
        for idx, row in filtered.iterrows():
            name = str(row.get("Entreprise", "")).strip() or f"Entreprise {idx + 1}"
            with st.expander(name, expanded=False):
                for field in [
                    "Activité principale",
                    "Domaines d\u2019intervention",
                    "Prestations détaillées",
                    "Localisation (siège)",
                    "Régions couvertes",
                ]:
                    val = str(row.get(field, "")).strip()
                    if val.startswith("\u2019") or val.startswith("'"):
                        val = val[1:].strip()
                    if val:
                        display_val = val.replace("\n", "<br>")
                        display_val = re.sub(
                            r"(?<!\A)\s*(\d+\.\s)", r"<br>\1", display_val
                        )
                        st.markdown(
                            f"**{field}**<br>"
                            f"<span style='color:#b0bec5;'>{display_val}</span>",
                            unsafe_allow_html=True,
                        )
                link = str(row.get("Lien", "")).strip()
                if link:
                    st.markdown(f"**Lien** : [{link}]({link})")
# =========================================================
# RENDER: KEYWORD SEARCH
# =========================================================
def _make_search_entry(row: pd.Series, qty: float, price=None):
    """Build a basket entry dict from a search-result row."""
    emissions_per_unit = float(row["Emissions_CO2"])
    unit = str(row["Unite"]) if pd.notna(row.get("Unite")) else ""
    return {
        "Categorie": str(row.get("Categorie", "")),
        "Categorie_old": str(row.get("Categorie_old", "")),
        "Selector": str(row.get("Selector", "")),
        "Sous_categorie": str(row.get("Sous_categorie", "")),
        "Type_prestation": str(row.get("Type_prestation", "")),
        "Prestation": str(row.get("Prestation", "")),
        "Option_famille": (
            "Option bas carbone" if is_low_carbon_option(row) else "Standard"
        ),
        "Produit_process": str(row.get("Produit_process", "")),
        "Unite": unit,
        "Quantite": float(qty),
        "Emissions_specifiques": emissions_per_unit,
        "kg_CO2_total": emissions_per_unit * qty,
        "Prix_unitaire": price if price and price > 0 else None,
        "Prix_total": (price * qty) if price and price > 0 else None,
    }

def render_search(df: pd.DataFrame):
    st.subheader("Recherche par mot-clé")
    query = st.text_input(
        "Entrez un ou plusieurs mots-clés (séparés par des espaces)",
        key="search_query",
        placeholder="ex. laine chanvre plomberie",
    )
    if not query or not query.strip():
        st.info("Saisissez un mot-clé pour lancer la recherche.")
        return
    keywords = query.strip().lower().split()
    str_cols = [c for c in df.columns if df[c].dtype == object]
    mask = pd.Series(False, index=df.index)
    for kw in keywords:
        kw_norm = normalize_text(kw)
        col_mask = pd.Series(False, index=df.index)
        for col in str_cols:
            col_mask |= df[col].apply(lambda v: kw_norm in normalize_text(v))
        mask |= col_mask
    results = df[mask].copy().reset_index(drop=True)
    if results.empty:
        st.warning(f"Aucun résultat pour « {query} ».")
        return

    # Deduplicate: show one row per unique Produit_process
    unique_products = (
        results.drop_duplicates(subset=["Produit_process"])
        .sort_values(["Categorie_old", "Produit_process"])
        .reset_index(drop=True)
    )
    st.markdown(f"**{len(unique_products)}** produit(s) trouvé(s) pour « {query} »")
    display = unique_products[
        ["Categorie_old", "Sous_categorie", "Produit_process", "Unite",
         "Emissions_CO2"]
    ].copy()
    display = display.rename(columns={
        "Categorie_old": "Catégorie", "Sous_categorie": "Sous-catégorie",
        "Produit_process": "Produit / process", "Unite": "Unité",
        "Emissions_CO2": "Émissions CO₂ (kg / unité)",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

    # ---- Add-to-basket from search results ----
    st.markdown("---")
    st.markdown("##### Ajouter un résultat à une configuration")

    # Step 1: choose a product
    product_labels = [
        f"{i+1}. {row['Produit_process']} — {float(row['Emissions_CO2']):.2f} kg CO₂ / {row['Unite']}"
        for i, row in unique_products.iterrows()
    ]
    chosen_idx = st.selectbox(
        "Produit",
        range(len(product_labels)),
        format_func=lambda i: product_labels[i],
        key="search_add_product",
    )
    chosen_product_name = unique_products.iloc[chosen_idx]["Produit_process"]

    # Step 2: show available prestations for that product
    product_rows = results[results["Produit_process"] == chosen_product_name].reset_index(drop=True)
    prestation_options = product_rows["Prestation"].dropna().unique().tolist()
    if len(prestation_options) > 1:
        chosen_prestation = st.selectbox(
            "Prestation",
            prestation_options,
            key="search_add_prestation",
        )
    elif len(prestation_options) == 1:
        chosen_prestation = prestation_options[0]
        st.caption(f"Prestation : {chosen_prestation}")
    else:
        chosen_prestation = None
        st.caption("Aucune prestation disponible pour ce produit.")

    # Get the final row matching both product and prestation
    if chosen_prestation is not None:
        final_rows = product_rows[product_rows["Prestation"] == chosen_prestation]
        chosen_row = final_rows.iloc[0]
    else:
        chosen_row = product_rows.iloc[0]

    unit = str(chosen_row["Unite"]) if pd.notna(chosen_row.get("Unite")) else ""
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        s_qty = st.number_input(
            f"Quantité ({unit})", min_value=0.0, value=1.0, step=1.0,
            key="search_add_qty",
        )
    with s_col2:
        s_price = st.number_input(
            f"Prix unitaire (€ / {unit}) — optionnel",
            min_value=0.0, value=0.0, step=0.01, key="search_add_price",
        )
    btn_s1, btn_s2 = st.columns(2)
    with btn_s1:
        if st.button("➕ Ajouter à **Configuration 1**", key="search_add_c1",
                      type="primary", use_container_width=True):
            entry = _make_search_entry(chosen_row, s_qty, s_price if s_price > 0 else None)
            st.session_state.setdefault("basket_config_1", []).append(entry)
            st.rerun()
    with btn_s2:
        if st.button("➕ Ajouter à **Configuration 2**", key="search_add_c2",
                      type="secondary", use_container_width=True):
            entry = _make_search_entry(chosen_row, s_qty, s_price if s_price > 0 else None)
            st.session_state.setdefault("basket_config_2", []).append(entry)
            st.rerun()
# =========================================================
# RENDER: FULL DATASET TABLES
# =========================================================
def render_full_dataset(df: pd.DataFrame):
    with st.expander("📂 Données carbone — ensemble du référentiel", expanded=False):
        st.markdown(f"**{len(df)}** lignes au total")
        display = df[
            ["Categorie_old", "Sous_categorie", "Produit_process", "Unite",
             "Type_prestation", "Prestation", "Emissions_CO2"]
        ].copy()
        display = display.rename(columns={
            "Categorie_old": "Catégorie", "Sous_categorie": "Sous-catégorie",
            "Produit_process": "Produit / process", "Unite": "Unité",
            "Type_prestation": "Type de prestation",
            "Emissions_CO2": "Émissions CO₂ (kg / unité)",
        })
        st.dataframe(display, use_container_width=True, hide_index=True, height=600)

def render_full_companies(companies_df: pd.DataFrame):
    with st.expander("🏢 Liste complète des entreprises", expanded=False):
        st.markdown(f"**{len(companies_df)}** entreprise(s) au total")
        if not companies_df.empty:
            st.dataframe(companies_df, use_container_width=True, hide_index=True, height=600)
        else:
            st.info("Aucune entreprise dans le répertoire.")
# =========================================================
# RENDER: CATEGORY-ONLY MODE
# =========================================================
def render_category_browse(df: pd.DataFrame, key_prefix: str):
    categories = sorted(df["Categorie"].dropna().unique().tolist())
    cat = st.selectbox("Catégorie", categories, key=f"{key_prefix}_cat_browse")
    filtered = df[df["Categorie"] == cat]
    products = (
        filtered[["Categorie_old", "Sous_categorie", "Produit_process", "Unite", "Emissions_CO2"]]
        .dropna(subset=["Produit_process", "Emissions_CO2"])
        .drop_duplicates()
        .sort_values(["Sous_categorie", "Emissions_CO2"])
        .reset_index(drop=True)
    )
    products = products.rename(columns={
        "Categorie_old": "Catégorie d'origine", "Sous_categorie": "Sous-catégorie",
        "Produit_process": "Produit / process", "Unite": "Unité",
        "Emissions_CO2": "Émissions CO₂ (kg / unité)",
    })
    st.write(f"**{len(products)}** produits trouvés dans la catégorie **{cat}**")
    st.dataframe(products, use_container_width=True, hide_index=True)
# =========================================================
# RENDER: TWO-COLUMN PRODUCT SELECTION
# =========================================================
def render_product_selection(candidates: pd.DataFrame, key_prefix: str):
    if candidates.empty:
        st.warning("Aucun produit correspondant à cette sélection.")
        return None
    std_df = candidates[candidates["Option_famille"] == "Standard"].reset_index(drop=True)
    lc_df = candidates[candidates["Option_famille"] == "Option bas carbone"].reset_index(drop=True)
    def _labels(sub_df):
        labels = [NONE_SENTINEL]
        for _, row in sub_df.iterrows():
            labels.append(
                f"{row['Produit_process']}  —  "
                f"{float(row['Emissions_CO2']):.2f} kg CO₂ / {row['Unite']}"
            )
        return labels
    std_labels = _labels(std_df)
    lc_labels = _labels(lc_df)
    st.markdown("**Produits disponibles** — sélectionnez directement dans l'une des deux colonnes")
    col_std, col_lc = st.columns(2)
    with col_std:
        st.markdown(
            f'<div style="background:{NAVY_MID};padding:8px 12px;border-radius:6px;'
            f'margin-bottom:4px;color:{WHITE};"><b>Standard</b></div>',
            unsafe_allow_html=True,
        )
        if std_df.empty:
            st.caption("Aucune option standard disponible.")
            std_choice = NONE_SENTINEL
        else:
            std_choice = st.radio(
                "Standard", std_labels, key=f"std_radio_{key_prefix}",
                on_change=_on_std_change, args=(key_prefix,),
                label_visibility="collapsed",
            )
    with col_lc:
        st.markdown(
            f'<div style="background:#1b5e20;padding:8px 12px;border-radius:6px;'
            f'margin-bottom:4px;color:{WHITE};"><b>Option bas carbone</b></div>',
            unsafe_allow_html=True,
        )
        if lc_df.empty:
            st.caption("Aucune option bas carbone disponible.")
            lc_choice = NONE_SENTINEL
        else:
            lc_choice = st.radio(
                "Bas carbone", lc_labels, key=f"lc_radio_{key_prefix}",
                on_change=_on_lc_change, args=(key_prefix,),
                label_visibility="collapsed",
            )
    if std_choice != NONE_SENTINEL:
        idx = std_labels.index(std_choice) - 1
        return std_df.iloc[idx]
    elif lc_choice != NONE_SENTINEL:
        idx = lc_labels.index(lc_choice) - 1
        return lc_df.iloc[idx]
    else:
        st.info("Veuillez sélectionner un produit dans l'une des deux colonnes.")
        return None
# =========================================================
# RENDER: SELECTION PANEL
# =========================================================
def render_selection_panel(df: pd.DataFrame):
    KP = "shared"
    for cfg in ("config_1", "config_2"):
        bk = f"basket_{cfg}"
        if bk not in st.session_state:
            st.session_state[bk] = []
    mode = st.radio(
        "Mode de sélection",
        ["Chiffrage détaillé", "Recherche par catégorie"],
        key=f"mode_{KP}", horizontal=True,
    )
    if mode == "Recherche par catégorie":
        render_category_browse(df, KP)
        return
    categories = sorted(df["Categorie"].dropna().unique().tolist())
    cat = st.selectbox("Catégorie", categories, key=f"cat_{KP}")
    st.session_state["_current_category"] = cat
    d1 = df[df["Categorie"] == cat]
    selector_options = sorted(
        [x for x in d1["Selector"].dropna().unique().tolist() if x != ""]
    )
    sel_value = None
    if selector_options:
        sel_value = st.selectbox("Sélecteur", selector_options, key=f"sel_{KP}")
        d2 = d1[d1["Selector"] == sel_value]
    else:
        d2 = d1
    sous_cats = sorted(d2["Sous_categorie"].dropna().unique().tolist())
    if not sous_cats:
        st.info("Aucune sous-catégorie disponible pour cette sélection.")
        return
    sous_cat = st.selectbox("Sous-catégorie", sous_cats, key=f"scat_{KP}")
    d3 = d2[d2["Sous_categorie"] == sous_cat]
    type_prests = sorted(d3["Type_prestation"].dropna().unique().tolist())
    if not type_prests:
        st.info("Aucun type de prestation disponible.")
        return
    type_prest = st.selectbox("Type de prestation", type_prests, key=f"tp_{KP}")
    d4 = d3[d3["Type_prestation"] == type_prest]
    prests = sorted(d4["Prestation"].dropna().unique().tolist())
    if not prests:
        st.info("Aucune prestation disponible.")
        return
    prest = st.selectbox("Prestation", prests, key=f"prest_{KP}")
    d5 = d4[d4["Prestation"] == prest]
    candidates = build_candidates(d5)
    selected_row = render_product_selection(candidates, KP)
    if selected_row is None:
        return
    unit = str(selected_row["Unite"]) if pd.notna(selected_row["Unite"]) else ""
    emissions_per_unit = float(selected_row["Emissions_CO2"])
    use_price = st.checkbox(f"Ajouter un prix unitaire (€ / {unit})", key=f"use_price_{KP}")
    price_per_unit = 0.0
    if use_price:
        price_per_unit = st.number_input(
            f"Prix (€ / {unit})", min_value=0.0, value=0.0, step=0.01, key=f"price_{KP}",
        )
    qty = st.number_input(
        f"Quantité ({unit})", min_value=0.0, value=1.0, step=1.0, key=f"qty_{KP}",
    )
    emissions_total = emissions_per_unit * qty
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric(f"kg CO₂ / {unit}", f"{emissions_per_unit:.2f}")
    with col_m2:
        st.metric("kg CO₂ total", f"{emissions_total:.2f}")
    if use_price and price_per_unit > 0:
        st.metric("Coût estimé (€)", f"{price_per_unit * qty:.2f}")
    def _make_entry():
        return {
            "Categorie": str(selected_row["Categorie"]),
            "Categorie_old": str(selected_row["Categorie_old"]),
            "Selector": "" if sel_value is None else str(sel_value),
            "Sous_categorie": str(selected_row["Sous_categorie"]),
            "Type_prestation": str(selected_row["Type_prestation"]),
            "Prestation": str(prest),
            "Option_famille": str(selected_row["Option_famille"]),
            "Produit_process": str(selected_row["Produit_process"]),
            "Unite": unit,
            "Quantite": float(qty),
            "Emissions_specifiques": emissions_per_unit,
            "kg_CO2_total": emissions_total,
            "Prix_unitaire": price_per_unit if (use_price and price_per_unit > 0) else None,
            "Prix_total": (price_per_unit * qty) if (use_price and price_per_unit > 0) else None,
        }
    st.markdown("---")
    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("➕ Ajouter à **Configuration 1**", key="add_config_1",
                      type="primary", use_container_width=True):
            st.session_state["basket_config_1"].append(_make_entry())
            st.rerun()
    with btn2:
        if st.button("➕ Ajouter à **Configuration 2**", key="add_config_2",
                      type="secondary", use_container_width=True):
            st.session_state["basket_config_2"].append(_make_entry())
            st.rerun()
# =========================================================
# RENDER: BASKET
# =========================================================
def _render_basket(config_key: str):
    basket_key = f"basket_{config_key}"
    basket = st.session_state.get(basket_key, [])
    if not basket:
        st.info("Aucune ligne ajoutée.")
        return
    # Build an editable DataFrame with the columns the user can change
    edit_rows = []
    for i, row in enumerate(basket):
        edit_rows.append({
            "Produit / process": row.get("Produit_process", ""),
            "Catégorie": row.get("Categorie", ""),
            "Famille": row.get("Option_famille", ""),
            "Unité": row.get("Unite", ""),
            "Quantité": float(row.get("Quantite", 0)),
            "Émissions (kg CO₂/u)": float(row.get("Emissions_specifiques", 0)),
            "Prix unitaire (€)": float(row.get("Prix_unitaire", 0) or 0),
        })
    edit_df = pd.DataFrame(edit_rows)

    st.caption(
        "Modifiez directement les cellules ci-dessous (quantité, prix, émissions…). "
        "Cliquez ensuite sur « Appliquer les modifications »."
    )
    edited = st.data_editor(
        edit_df,
        use_container_width=True,
        hide_index=False,
        num_rows="dynamic",
        key=f"basket_editor_{config_key}",
        column_config={
            "Produit / process": st.column_config.TextColumn(disabled=True),
            "Catégorie": st.column_config.TextColumn(disabled=True),
            "Famille": st.column_config.TextColumn(disabled=True),
            "Unité": st.column_config.TextColumn(disabled=True),
            "Quantité": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
            "Émissions (kg CO₂/u)": st.column_config.NumberColumn(step=0.01, format="%.4f"),
            "Prix unitaire (€)": st.column_config.NumberColumn(min_value=0.0, step=0.01, format="%.2f"),
        },
    )

    # Detect if user changed an emissions value
    emissions_changed = False
    if len(edited) == len(edit_df):
        for i in range(len(edited)):
            orig = edit_df.iloc[i]["Émissions (kg CO₂/u)"]
            new_val = edited.iloc[i]["Émissions (kg CO₂/u)"]
            if abs(float(new_val) - float(orig)) > 1e-6:
                emissions_changed = True
                break
    if emissions_changed:
        st.warning(
            "⚠️ **Attention** : vous avez modifié une valeur d'émissions. "
            "Cette valeur provient normalement de la base de données environnementale "
            "(INIES). En la modifiant manuellement, les résultats ne refléteront plus "
            "les données de référence. Procédez uniquement si vous disposez de valeurs "
            "plus précises ou spécifiques à votre projet."
        )

    if st.button("💾 Appliquer les modifications", key=f"apply_edit_{config_key}",
                  type="primary", use_container_width=True):
        new_basket = []
        for i in range(len(edited)):
            row_ed = edited.iloc[i]
            # Get the original basket entry for non-editable fields if it exists
            if i < len(basket):
                orig = basket[i].copy()
            else:
                # New row added via data_editor — build a minimal entry
                orig = {
                    "Categorie": str(row_ed.get("Catégorie", "")),
                    "Categorie_old": str(row_ed.get("Catégorie", "")),
                    "Selector": "",
                    "Sous_categorie": "",
                    "Type_prestation": "",
                    "Prestation": "",
                    "Option_famille": str(row_ed.get("Famille", "")),
                    "Produit_process": str(row_ed.get("Produit / process", "")),
                    "Unite": str(row_ed.get("Unité", "")),
                }
            qty = float(row_ed["Quantité"])
            emi = float(row_ed["Émissions (kg CO₂/u)"])
            price = float(row_ed["Prix unitaire (€)"])
            orig["Quantite"] = qty
            orig["Emissions_specifiques"] = emi
            orig["kg_CO2_total"] = emi * qty
            orig["Prix_unitaire"] = price if price > 0 else None
            orig["Prix_total"] = (price * qty) if price > 0 else None
            new_basket.append(orig)
        st.session_state[basket_key] = new_basket
        st.rerun()

    # ---- Computed totals (read-only summary) ----
    basket_df = pd.DataFrame(basket)
    total_co2 = float(basket_df["kg_CO2_total"].sum())
    st.markdown(f"**Total CO₂ : {total_co2:.2f} kg**")
    all_have_price = all(
        r.get("Prix_unitaire") is not None and r.get("Prix_total") is not None
        for r in basket
    )
    if all_have_price:
        total_price = sum(r["Prix_total"] for r in basket if r.get("Prix_total") is not None)
        st.markdown(f"**Coût total : {total_price:.2f} €**")
    else:
        st.warning(
            "**Coût total indisponible** — renseignez un prix unitaire pour chaque "
            "ligne dans le tableau ci-dessus, puis appliquez les modifications."
        )

    by_cat = (
        basket_df.groupby("Categorie", as_index=False)["kg_CO2_total"]
        .sum().sort_values("kg_CO2_total", ascending=False)
    )
    st.markdown("**Répartition CO₂ par catégorie :**")
    st.dataframe(by_cat.rename(columns={"kg_CO2_total": "kg CO₂ total"}).round(2),
                 use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🗑️ Vider le panier", key=f"clr_{config_key}"):
            st.session_state[basket_key].clear()
            st.rerun()
    with c2:
        if basket:
            csv_data = basket_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Exporter CSV", data=csv_data,
                               file_name=f"chiffrage_{config_key}.csv",
                               mime="text/csv", key=f"dl_{config_key}")
# =========================================================
# RENDER: RUNNING TOTALS
# =========================================================
def render_running_totals():
    b1 = st.session_state.get("basket_config_1", [])
    b2 = st.session_state.get("basket_config_2", [])
    t1 = sum(r["kg_CO2_total"] for r in b1) if b1 else 0.0
    t2 = sum(r["kg_CO2_total"] for r in b2) if b2 else 0.0
    def _pt(b):
        if not b:
            return None
        if all(r.get("Prix_total") is not None for r in b):
            return sum(r["Prix_total"] for r in b)
        return None
    p1, p2 = _pt(b1), _pt(b2)
    c1, cs, c2 = st.columns([5, 1, 5])
    with c1:
        price_html_1 = (
            f"<div style='font-size:1.3em;color:{WHITE};'>💶 <b>{p1:.2f}</b> €</div>"
            if p1 is not None else
            ("<div style='font-size:0.85em;color:#90a4ae;'>⚠️ Prix incomplets</div>" if b1 else "")
        )
        st.markdown(
            f"""<div style="padding:12px 16px;border:2px solid {ACCENT_BLUE};border-radius:8px;
            background:{NAVY_LIGHT};">
            <div style="font-weight:700;color:{ACCENT_BLUE};margin-bottom:6px;">
            Configuration 1 — {len(b1)} ligne(s)</div>
            <div style="font-size:1.3em;color:{WHITE};">🏭 <b>{t1:.2f}</b> kg CO₂</div>
            {price_html_1}</div>""",
            unsafe_allow_html=True,
        )
    with cs:
        st.markdown(
            '<div style="display:flex;align-items:center;justify-content:center;'
            'height:100%;font-size:1.5em;color:#5c6bc0;">vs</div>',
            unsafe_allow_html=True,
        )
    with c2:
        price_html_2 = (
            f"<div style='font-size:1.3em;color:{WHITE};'>💶 <b>{p2:.2f}</b> €</div>"
            if p2 is not None else
            ("<div style='font-size:0.85em;color:#90a4ae;'>⚠️ Prix incomplets</div>" if b2 else "")
        )
        st.markdown(
            f"""<div style="padding:12px 16px;border:2px solid #7e57c2;border-radius:8px;
            background:{NAVY_LIGHT};">
            <div style="font-weight:700;color:#7e57c2;margin-bottom:6px;">
            Configuration 2 — {len(b2)} ligne(s)</div>
            <div style="font-size:1.3em;color:{WHITE};">🏭 <b>{t2:.2f}</b> kg CO₂</div>
            {price_html_2}</div>""",
            unsafe_allow_html=True,
        )
# =========================================================
# RENDER: COMPARISON (with bar chart)
# =========================================================
def render_comparison():
    b1 = st.session_state.get("basket_config_1", [])
    b2 = st.session_state.get("basket_config_2", [])
    if not b1 and not b2:
        st.info("Ajoutez des lignes dans au moins une configuration pour voir la comparaison.")
        return
    df1 = pd.DataFrame(b1) if b1 else pd.DataFrame()
    df2 = pd.DataFrame(b2) if b2 else pd.DataFrame()
    total1 = float(df1["kg_CO2_total"].sum()) if not df1.empty else 0.0
    total2 = float(df2["kg_CO2_total"].sum()) if not df2.empty else 0.0
    def _spt(bl):
        if not bl:
            return None
        if all(r.get("Prix_total") is not None for r in bl):
            return sum(r["Prix_total"] for r in bl)
        return None
    price1, price2 = _spt(b1), _spt(b2)
    if total1 == 0 and total2 == 0:
        better_label = worse_label = "—"
    elif total1 <= total2:
        better_label, worse_label = "Configuration 1", "Configuration 2"
    else:
        better_label, worse_label = "Configuration 2", "Configuration 1"
    baseline = max(total1, total2)
    best = min(total1, total2)
    reduction_pct = ((baseline - best) / baseline * 100) if baseline > 0 else 0.0
    label = get_reduction_label(reduction_pct)
    color = get_reduction_color(reduction_pct)
    st.subheader("Résumé comparatif")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Configuration 1")
        st.metric("kg CO₂ total", f"{total1:.2f}")
        if price1 is not None:
            st.metric("Coût total (€)", f"{price1:.2f}")
        elif b1:
            st.caption("⚠️ Prix incomplets — coût total indisponible")
        st.caption(f"{len(b1)} ligne(s)")
    with c2:
        st.markdown("##### Configuration 2")
        st.metric("kg CO₂ total", f"{total2:.2f}")
        if price2 is not None:
            st.metric("Coût total (€)", f"{price2:.2f}")
        elif b2:
            st.caption("⚠️ Prix incomplets — coût total indisponible")
        st.caption(f"{len(b2)} ligne(s)")
    st.divider()
    if total1 == total2:
        st.info("Les deux configurations ont le même bilan carbone.")
    elif total1 == 0.0 or total2 == 0.0:
        filled = "Configuration 1" if total1 > 0 else "Configuration 2"
        st.info(f"Seule la **{filled}** contient des lignes. Remplissez les deux pour comparer.")
    else:
        st.markdown(
            f"""<div style="padding:16px 24px;border:2px solid {color};border-radius:10px;
            text-align:center;margin-bottom:12px;background:{NAVY_LIGHT};">
            <div style="font-size:0.95em;color:#b0bec5;">
            <b>{better_label}</b> offre une réduction de</div>
            <div style="font-size:2.2em;font-weight:bold;color:{color};margin:4px 0;">
            {reduction_pct:.1f} %</div>
            <div style="font-size:1.1em;font-weight:600;color:{color};">{label}</div>
            <div style="font-size:0.85em;color:#90a4ae;margin-top:6px;">
            par rapport à {worse_label} ({abs(total1-total2):.2f} kg CO₂ en moins)</div>
            </div>""",
            unsafe_allow_html=True,
        )
    if price1 is not None and price2 is not None:
        pd_ = price2 - price1
        cheaper = "Configuration 1" if pd_ >= 0 else "Configuration 2"
        st.markdown(f"**{cheaper}** est moins chère de **{abs(pd_):.2f} €**.")
    st.divider()
    st.subheader("Comparaison par catégorie")
    # Use Categorie_old (the 13 original categories) for the breakdown
    cat_col = "Categorie_old" if (
        (not df1.empty and "Categorie_old" in df1.columns)
        or (not df2.empty and "Categorie_old" in df2.columns)
    ) else "Categorie"
    cats1 = df1.groupby(cat_col)["kg_CO2_total"].sum() if not df1.empty else pd.Series(dtype=float)
    cats2 = df2.groupby(cat_col)["kg_CO2_total"].sum() if not df2.empty else pd.Series(dtype=float)
    all_cats = sorted(set(cats1.index.tolist()) | set(cats2.index.tolist()))
    if all_cats:
        rows = [{"Catégorie": c, "Config 1 (kg CO₂)": round(cats1.get(c, 0), 2),
                 "Config 2 (kg CO₂)": round(cats2.get(c, 0), 2),
                 "Δ (kg CO₂)": round(cats2.get(c, 0) - cats1.get(c, 0), 2)} for c in all_cats]
        comp_df = pd.DataFrame(rows)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

        # --- Stacked bar chart (1 bar per config, coloured by category) ---
        st.subheader("Répartition des émissions par catégorie")
        # Build one stacked bar per configuration
        fig_bar = go.Figure()
        for cat_name in all_cats:
            v1 = cats1.get(cat_name, 0)
            v2 = cats2.get(cat_name, 0)
            fig_bar.add_trace(go.Bar(
                name=cat_name,
                x=["Configuration 1", "Configuration 2"],
                y=[v1, v2],
                text=[f"{v1:.1f}" if v1 > 0 else "", f"{v2:.1f}" if v2 > 0 else ""],
                textposition="inside",
            ))
        fig_bar.update_layout(
            barmode="stack",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
            yaxis_title="kg CO₂ eq",
            margin=dict(l=40, r=40, t=40, b=100),
            height=450,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # --- Pie charts (one per configuration) ---
        st.subheader("Répartition par configuration")
        pie1, pie2 = st.columns(2)
        with pie1:
            st.markdown("##### Configuration 1")
            values1 = [cats1.get(c, 0) for c in all_cats]
            if sum(values1) > 0:
                fig_p1 = go.Figure(go.Pie(
                    labels=all_cats, values=values1,
                    textinfo="label+percent", hole=0.35,
                ))
                fig_p1.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=350,
                )
                st.plotly_chart(fig_p1, use_container_width=True)
            else:
                st.info("Aucune donnée.")
        with pie2:
            st.markdown("##### Configuration 2")
            values2 = [cats2.get(c, 0) for c in all_cats]
            if sum(values2) > 0:
                fig_p2 = go.Figure(go.Pie(
                    labels=all_cats, values=values2,
                    textinfo="label+percent", hole=0.35,
                ))
                fig_p2.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=350,
                )
                st.plotly_chart(fig_p2, use_container_width=True)
            else:
                st.info("Aucune donnée.")
    st.divider()
    st.subheader("Détails par configuration")
    d1, d2 = st.columns(2)
    for col_w, df_x, lbl in [(d1, df1, "Configuration 1"), (d2, df2, "Configuration 2")]:
        with col_w:
            st.markdown(f"**{lbl}**")
            if not df_x.empty:
                show = df_x[["Categorie", "Produit_process", "Option_famille",
                             "Quantite", "kg_CO2_total"]].copy()
                show = show.rename(columns={"Produit_process": "Produit",
                                            "Option_famille": "Famille",
                                            "Quantite": "Qté", "kg_CO2_total": "kg CO₂"}).round(2)
                st.dataframe(show, use_container_width=True, hide_index=True)
            else:
                st.info("Vide")
# =========================================================
# RENDER: ALTERNATE DATA SOURCE
# =========================================================
def render_data_source_settings():
    st.subheader("Source de données")
    st.markdown(
        "Par défaut, l'application utilise **carbon_data.html**. "
        "Vous pouvez charger un fichier alternatif ci-dessous."
    )
    uploaded = st.file_uploader(
        "Charger un fichier (.html, .xlsx, .csv)",
        type=["html", "htm", "xlsx", "xls", "csv"],
        key="alt_file_upload",
    )
    if uploaded is None:
        if "alt_df" in st.session_state:
            del st.session_state["alt_df"]
            del st.session_state["alt_mapping"]
        st.info("Aucun fichier alternatif chargé — utilisation de la source par défaut.")
        return
    try:
        raw_df = load_alternate_file(uploaded)
    except Exception as e:
        st.error(f"Erreur lors du chargement : {e}")
        return
    st.success(f"Fichier chargé : **{len(raw_df)}** lignes, **{len(raw_df.columns)}** colonnes")
    st.dataframe(raw_df.head(5), use_container_width=True, hide_index=True)
    st.markdown("##### Correspondance des colonnes")
    st.caption(
        "Pour chaque champ, choisissez la colonne correspondante dans votre fichier. "
        "Si aucune colonne ne correspond, sélectionnez « Pas de colonne correspondante »."
    )
    field_labels = {
        "Categorie": "Catégorie",
        "Sous_categorie": "Sous-catégorie",
        "Produit_process": "Produit / process",
        "Unite": "Unité",
        "Type_prestation": "Type de prestation",
        "Prestation": "Prestation",
        "Emissions_CO2": "Émissions CO₂",
    }
    col_options = [NO_COLUMN] + list(raw_df.columns)
    mapping = {}
    for field_key, field_label in field_labels.items():
        mapping[field_key] = st.selectbox(
            f"{field_label} →",
            col_options,
            key=f"map_{field_key}",
        )
    if st.button("✅ Appliquer ce mapping", key="apply_mapping", type="primary"):
        try:
            mapped_df = apply_column_mapping(raw_df, mapping)
            st.session_state["alt_df"] = mapped_df
            st.session_state["alt_mapping"] = mapping
            st.success(
                f"Données alternatives activées — {len(mapped_df)} lignes prêtes."
            )
        except Exception as e:
            st.error(f"Erreur lors du mapping : {e}")
# =========================================================
# RENDER: ADD COMPANY FORM
# =========================================================
def render_add_company():
    st.subheader("Ajouter une entreprise")
    st.markdown(
        "Remplissez les champs ci-dessous pour ajouter une entreprise au répertoire. "
        "Seul le nom est obligatoire."
    )
    companies_df = load_companies()
    all_original_cats = _get_company_categories(companies_df)
    entreprise_name = st.text_input(
        "Entreprise", placeholder="Nom de l'entreprise", key="add_co_Entreprise",
    )
    selected_cats = st.multiselect(
        "Catégorie(s)",
        all_original_cats,
        help="Sélectionnez une ou plusieurs catégories.",
        key="add_co_categories",
    )
    other_fields = {
        "Domaines d\u2019intervention": ("text_area", "Domaines d\u2019intervention", 80),
        "Activité principale": ("text_input", "Activité principale", None),
        "Prestations détaillées": ("text_area", "Prestations détaillées", 80),
        "Localisation (siège)": ("text_input", "Localisation (siège)", None),
        "Régions couvertes": ("text_input", "Régions couvertes", None),
        "Lien": ("text_input", "Site web (URL)", None),
    }
    other_values = {}
    for col_name, (widget_type, placeholder, height) in other_fields.items():
        if widget_type == "text_area":
            other_values[col_name] = st.text_area(
                col_name, placeholder=placeholder, key=f"add_co_{col_name}",
                height=height,
            )
        else:
            other_values[col_name] = st.text_input(
                col_name, placeholder=placeholder, key=f"add_co_{col_name}",
            )
    if st.button("💾 Enregistrer l'entreprise", key="save_company", type="primary"):
        if not entreprise_name.strip():
            st.warning("Veuillez au moins renseigner le nom de l'entreprise.")
            return
        file_path = Path(__file__).parent / COMPANIES_FILE
        try:
            if file_path.exists():
                existing = pd.read_excel(file_path)
                existing.columns = [str(c).strip() for c in existing.columns]
            else:
                existing = pd.DataFrame(
                    columns=EXPECTED_COMPANY_COLS + ["Ajouté par"]
                )
            new_values = {
                "Entreprise": entreprise_name.strip(),
                "Catégorie": ", ".join(selected_cats),
            }
            new_values.update(other_values)
            new_values["Ajouté par"] = "LIGNE AJOUTÉE PAR L'UTILISATEUR"
            new_row = {}
            for col in existing.columns:
                new_row[col] = new_values.get(col, "")
            for col in new_values:
                if col not in new_row:
                    new_row[col] = new_values[col]
            new_df = pd.concat(
                [existing, pd.DataFrame([new_row])], ignore_index=True
            )
            new_df.to_excel(file_path, index=False, engine="openpyxl")
            load_companies.clear()
            st.success(
                f"✅ **{entreprise_name}** a été ajoutée au répertoire."
            )
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")
# =========================================================
# RENDER: EDIT / DELETE COMPANIES
# =========================================================
def render_manage_companies():
    """Spreadsheet-style editor to modify or delete enterprise rows."""
    st.subheader("Modifier / supprimer des entreprises")
    st.markdown(
        "Sélectionnez une entreprise pour modifier ses informations, "
        "ou supprimez des lignes du répertoire."
    )
    companies_df = load_companies()
    if companies_df.empty:
        st.info("Le répertoire est vide.")
        return

    # Display the full table in an editable data editor
    st.markdown("##### Tableau éditable")
    st.caption(
        "Modifiez directement les cellules ci-dessous, puis cliquez sur "
        "« Enregistrer les modifications » pour sauvegarder."
    )
    edited_df = st.data_editor(
        companies_df,
        use_container_width=True,
        hide_index=False,
        num_rows="dynamic",
        key="company_editor",
    )

    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button("💾 Enregistrer les modifications", key="save_edits", type="primary",
                      use_container_width=True):
            try:
                _save_companies(edited_df)
                st.success("✅ Modifications enregistrées.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")
    with col_reset:
        if st.button("🔄 Annuler (recharger)", key="reset_edits",
                      use_container_width=True):
            load_companies.clear()
            st.rerun()

    st.divider()

    # Quick delete by row number
    st.markdown("##### Supprimer une entreprise par numéro de ligne")
    max_idx = len(companies_df) - 1
    del_idx = st.number_input(
        "Numéro de ligne à supprimer (visible dans l'index du tableau ci-dessus)",
        min_value=0, max_value=max_idx, value=0, step=1, key="del_row_idx",
    )
    if 0 <= del_idx <= max_idx:
        target_name = str(companies_df.iloc[del_idx].get("Entreprise", "")).strip()
        st.caption(f"Entreprise sélectionnée : **{target_name}**")
    if st.button("🗑️ Supprimer cette ligne", key="delete_row"):
        try:
            updated = companies_df.drop(index=del_idx).reset_index(drop=True)
            _save_companies(updated)
            st.success(f"✅ Ligne {del_idx} supprimée.")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
# =========================================================
# RENDER: DOCUMENTATION
# =========================================================
def render_documentation():
    """Show a download link for the documentation PDF."""
    doc_path = Path(__file__).parent / DOCUMENTATION_FILE
    if doc_path.exists():
        with open(doc_path, "rb") as f:
            pdf_data = f.read()
        st.download_button(
            "📄 Télécharger la documentation (PDF)",
            data=pdf_data,
            file_name=DOCUMENTATION_FILE,
            mime="application/pdf",
            key="dl_documentation",
        )
    else:
        st.info(
            f"Le fichier de documentation **{DOCUMENTATION_FILE}** n'a pas été trouvé "
            f"dans le répertoire de l'application. Il sera disponible prochainement."
        )
# =========================================================
# MAIN
# =========================================================
def _ensure_dark_mode():
    config_dir = Path(__file__).parent / ".streamlit"
    config_file = config_dir / "config.toml"
    if not config_file.exists():
        config_dir.mkdir(exist_ok=True)
        config_file.write_text(
            '[theme]\nbase = "dark"\n'
            'primaryColor = "#4a90d9"\n'
            'backgroundColor = "#0d2559"\n'
            'secondaryBackgroundColor = "#122b54"\n'
            'textColor = "#ffffff"\n'
        )

def main():
    _ensure_dark_mode()
    st.set_page_config(
        page_title="REVERT — Chiffrage sinistre",
        page_icon="🏗️",
        layout="wide",
    )
    inject_theme()
    render_logo()
    # Load default carbon data
    default_df = load_df("carbon_data.html")
    df = st.session_state.get("alt_df", default_df)
    st.session_state["_carbon_categories"] = (
        df["Categorie"].dropna().unique().tolist()
    )
    st.session_state["_carbon_categories_old"] = sorted(
        df["Categorie_old"].dropna().unique().tolist()
    )
    # Load company data
    companies_df = load_companies()
    # Sidebar: company browser
    current_cat = st.session_state.get("_current_category", "")
    render_sidebar_companies(companies_df, current_cat)
    # Main tabs
    (tab_chiffrage, tab_search, tab_baskets, tab_cmp,
     tab_source, tab_add_co, tab_manage_co) = st.tabs([
        "🔧 Sélection produit",
        "🔍 Recherche",
        "📋 Paniers (Config 1 & 2)",
        "📊 Comparaison",
        "⚙️ Source de données",
        "🏢 Ajouter entreprise",
        "✏️ Modifier entreprises",
    ])
    with tab_chiffrage:
        render_selection_panel(df)
        st.divider()
        st.subheader("Totaux en cours")
        render_running_totals()
    with tab_search:
        render_search(df)
    with tab_baskets:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Configuration 1")
            _render_basket("config_1")
        with c2:
            st.subheader("Configuration 2")
            _render_basket("config_2")
    with tab_cmp:
        render_comparison()
    with tab_source:
        render_data_source_settings()
    with tab_add_co:
        render_add_company()
    with tab_manage_co:
        render_manage_companies()
    # Full datasets at the bottom
    st.divider()
    render_full_dataset(df)
    render_full_companies(companies_df)
    # Documentation
    st.divider()
    render_documentation()

if __name__ == "__main__":
    main()
