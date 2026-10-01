#!/usr/bin/env python
# coding: utf-8

from pathlib import Path
import base64
import mimetypes

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


app_directory = Path(__file__).resolve().parent
image_extensions = {".png", ".jpg", ".jpeg", ".webp"}


def find_local_image(names):
	normalized_names = {name.replace(" ", "").replace("_", "").replace("-", "") for name in names}
	for path in app_directory.iterdir():
		normalized_stem = path.stem.casefold().replace(" ", "").replace("_", "").replace("-", "")
		if path.is_file() and path.suffix.casefold() in image_extensions and normalized_stem in normalized_names:
			return path
	return None


local_logo = find_local_image({"image", "images", "logo"})
local_background = find_local_image({"bg image", "images bg", "bg", "background"})
st.set_page_config(page_title="Netflix Analytics", page_icon=str(local_logo) if local_logo else "N", layout="wide")

logo_upload = st.sidebar.file_uploader("Logo image", type=["png", "jpg", "jpeg", "webp"], key="logo_image")
background_upload = st.sidebar.file_uploader("Background image", type=["png", "jpg", "jpeg", "webp"], key="background_image")
logo_image = logo_upload if logo_upload is not None else local_logo
background_image = background_upload if background_upload is not None else local_background

background_css = ""
if background_image is not None:
	if isinstance(background_image, Path):
		image_bytes = background_image.read_bytes()
		image_type = mimetypes.guess_type(background_image.name)[0] or "image/png"
	else:
		image_bytes = background_image.getvalue()
		image_type = background_image.type
	encoded_background = base64.b64encode(image_bytes).decode("ascii")
	background_css = f'url("data:{image_type};base64,{encoded_background}")'

theme_css = """
	<style>
	@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
	:root { --ink: #f5f5f1; --muted: #b8b8b8; --accent: #e50914; --coral: #b20710; }
	html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
	h1, h2, h3 { font-family: 'Manrope', sans-serif; color: var(--ink); letter-spacing: 0; }
	.stApp { background: linear-gradient(rgba(8, 8, 10, .88), rgba(8, 8, 10, .96)), __BACKGROUND_IMAGE__, #0b0b0d; background-size: cover; background-position: center; background-attachment: fixed; }
	.stApp header { background: transparent; }
	[data-testid="stMainBlockContainer"] { max-width: 1400px; padding-left: 2rem; padding-right: 2rem; }
	[data-testid="stSidebar"] { background: #101010; border-right: 1px solid #2b2b2b; }
	[data-testid="stSidebar"] * { color: #f5f5f1; }
	[data-testid="stSidebar"] [data-baseweb="select"] > div { color: #f5f5f1; background: #1c1c1c; border-color: #414141; }
	[data-testid="stMetric"] { background: rgba(20, 20, 22, .94); border: 1px solid #343434; border-left: 3px solid #e50914; padding: 16px 18px; border-radius: 4px; }
	[data-testid="stMetricLabel"] { color: #b8b8b8; }
	[data-testid="stMetricValue"] { color: #fff; font-family: 'Manrope', sans-serif; }
	[data-testid="stCaptionContainer"] { color: #b8b8b8; }
	[data-testid="stExpander"] { background: rgba(20, 20, 22, .94); border: 1px solid #343434; border-radius: 4px; }
	[data-testid="stFileUploader"] section { border-color: #6b2529; }
	[data-testid="stDataFrame"] { border: 1px solid #343434; }
	</style>
	"""
theme_css = theme_css.replace("__BACKGROUND_IMAGE__", background_css or "none")
st.markdown(theme_css, unsafe_allow_html=True)

title_column, logo_column = st.columns([5, 1])
with title_column:
	st.title("Netflix Analytics")
	st.caption("Revenue, subscription ratings, and viewing trends")
with logo_column:
	if logo_image is not None:
		st.image(logo_image, width=112)

required_columns = {
	"Watch_Date",
	"Region",
	"Monthly_Revenue",
	"Rating",
	"Subscription_Plan",
	"Category",
}
local_csv = app_directory / "netflix.csv"
uploaded_csv = st.sidebar.file_uploader("Netflix data (CSV)", type=["csv"])

try:
	if uploaded_csv is not None:
		netflix = pd.read_csv(uploaded_csv)
		data_source = uploaded_csv.name
	elif local_csv.exists():
		netflix = pd.read_csv(local_csv)
		data_source = local_csv.name
	else:
		st.info("Upload your Netflix CSV in the sidebar to explore the dashboard.")
		st.stop()
except Exception as error:
	st.error(f"Could not read the CSV: {error}")
	st.stop()

missing_columns = required_columns.difference(netflix.columns)
if missing_columns:
	st.error("Missing required columns: " + ", ".join(sorted(missing_columns)))
	st.stop()

netflix = netflix.copy()
netflix["Watch_Date"] = pd.to_datetime(netflix["Watch_Date"], errors="coerce")
for column in ("Monthly_Revenue", "Rating"):
	netflix[column] = pd.to_numeric(netflix[column], errors="coerce")
for column in ("Region", "Subscription_Plan", "Category"):
	netflix[column] = netflix[column].fillna("Unknown").astype(str)

st.sidebar.markdown("### Refine view")
filters = (
	("Region", "Region"),
	("Subscription plan", "Subscription_Plan"),
	("Category", "Category"),
)
filtered = netflix.copy()
for label, column in filters:
	options = sorted(filtered[column].unique().tolist())
	selection = st.sidebar.selectbox(label, ["All"] + options, key=column)
	if selection != "All":
		filtered = filtered[filtered[column] == selection]

st.caption(f"Source: {data_source} · {len(filtered):,} of {len(netflix):,} records")

metric_columns = st.columns(2)
metric_columns[0].metric("Records", f"{len(filtered):,}")
metric_columns[1].metric(
	"Total revenue",
	f"{filtered['Monthly_Revenue'].sum():,.2f}",
)
metric_columns = st.columns(2)
metric_columns[0].metric("Average rating", f"{filtered['Rating'].mean():.2f}" if filtered["Rating"].notna().any() else "N/A")
metric_columns[1].metric("Regions", f"{filtered['Region'].nunique():,}")

chart_colors = ["#e50914", "#f5f5f1", "#b20710", "#ff4d57", "#9a9a9a", "#70060c"]


def style_axis(axis, horizontal=False):
	axis.set_axisbelow(True)
	axis.grid(axis="x" if horizontal else "y", color="#383838", linewidth=0.8)
	axis.spines[["top", "right", "left", "bottom"]].set_visible(False)
	axis.tick_params(colors="#d0d0d0", length=0, pad=7)


def show_revenue_chart(data, group_column, title):
	totals = data.groupby(group_column)["Monthly_Revenue"].sum().dropna().sort_values()
	if totals.empty:
		st.info("No revenue values available for this selection.")
		return
	figure, axis = plt.subplots(figsize=(7, 3.5))
	axis.barh(totals.index.astype(str), totals.values, color=chart_colors[0], height=0.62)
	axis.set_facecolor("#171717")
	axis.set_title(title, loc="left", fontsize=13, color="#f5f5f1", pad=14, fontweight="bold")
	axis.set_xlabel("Revenue", color="#b8b8b8", labelpad=8)
	style_axis(axis, horizontal=True)
	figure.patch.set_facecolor("#171717")
	figure.tight_layout()
	st.pyplot(figure, width="stretch")
	plt.close(figure)


def show_subscription_charts(data):
	totals = data.groupby("Subscription_Plan")["Rating"].sum().dropna().sort_values(ascending=False)
	if totals.empty:
		st.info("No rating values available for this selection.")
		return
	figure, (bar_axis, pie_axis) = plt.subplots(1, 2, figsize=(10, 4))
	bar_axis.set_facecolor("#171717")
	pie_axis.set_facecolor("#171717")
	bar_axis.bar(totals.index.astype(str), totals.values, color=chart_colors[: len(totals)], width=0.62)
	bar_axis.set_title("Rating total by plan", loc="left", fontsize=13, color="#f5f5f1", pad=14, fontweight="bold")
	bar_axis.set_ylabel("Rating total", color="#b8b8b8")
	style_axis(bar_axis)
	pie_axis.pie(
		totals.values,
		labels=totals.index.astype(str),
		colors=chart_colors[: len(totals)],
		startangle=90,
		counterclock=False,
		wedgeprops={"width": 0.42, "edgecolor": "#171717", "linewidth": 2},
		autopct="%1.0f%%",
		pctdistance=0.78,
		textprops={"color": "#f5f5f1", "fontsize": 9},
	)
	pie_axis.set_title("Rating share by plan", loc="left", fontsize=13, color="#f5f5f1", pad=14, fontweight="bold")
	figure.patch.set_facecolor("#171717")
	figure.tight_layout()
	st.pyplot(figure, width="stretch")
	plt.close(figure)


def show_monthly_chart(data):
	dated_data = data.dropna(subset=["Watch_Date", "Monthly_Revenue"])
	monthly = dated_data.groupby(dated_data["Watch_Date"].dt.to_period("M"))["Monthly_Revenue"].sum()
	if monthly.empty:
		st.info("No valid watch dates and revenue values available for this selection.")
		return
	figure, axis = plt.subplots(figsize=(12, 3.8))
	axis.set_facecolor("#171717")
	axis.plot(monthly.index.astype(str), monthly.values, color=chart_colors[0], linewidth=2.5, marker="o", markersize=5)
	axis.fill_between(range(len(monthly)), monthly.values, color=chart_colors[0], alpha=0.1)
	axis.set_xticks(range(len(monthly)))
	axis.set_xticklabels(monthly.index.astype(str), rotation=35, ha="right")
	axis.set_title("Revenue by month", loc="left", fontsize=13, color="#f5f5f1", pad=14, fontweight="bold")
	axis.set_ylabel("Revenue", color="#b8b8b8")
	style_axis(axis)
	figure.patch.set_facecolor("#171717")
	figure.tight_layout()
	st.pyplot(figure, width="stretch")
	plt.close(figure)


left_column, right_column = st.columns(2)
with left_column:
	show_revenue_chart(filtered, "Region", "Revenue by region")
with right_column:
	show_revenue_chart(filtered, "Category", "Revenue by category")

st.markdown("#### Subscription ratings")
show_subscription_charts(filtered)

st.markdown("#### Revenue trend")
show_monthly_chart(filtered)

with st.expander("Explore records"):
	st.dataframe(filtered, width="stretch", hide_index=True)




