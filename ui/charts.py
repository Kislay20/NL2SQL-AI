"""Dynamic Chart Generator for NL2SQL AI using Plotly Express.

Inspects query results to automatically construct insightful, beautiful visualizations
when tabular data is suitable for graphical representation.
"""

from __future__ import annotations

from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def generate_auto_chart(df: Optional[pd.DataFrame]) -> Optional[go.Figure]:
    """Inspect a DataFrame and generate an appropriate Plotly visualization.

    Args:
        df: Pandas DataFrame containing query results.

    Returns:
        Plotly Figure object if data is suitable for charting, otherwise None.
    """
    if df is None or df.empty or len(df) < 2:
        return None

    # Identify numeric and categorical columns
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    # Categorical/string columns (including dates or object types)
    categorical_cols = [col for col in df.columns if col not in numeric_cols]

    # Scenario 1: Exactly 2 columns - 1 categorical and 1 numeric (e.g., avg marks by department)
    if len(df.columns) == 2 and len(categorical_cols) == 1 and len(numeric_cols) == 1:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]

        clean_cat_title = cat_col.replace("_", " ").title()
        clean_num_title = num_col.replace("_", " ").title()

        fig = px.bar(
            df,
            x=cat_col,
            y=num_col,
            title=f"📊 {clean_num_title} by {clean_cat_title}",
            text=num_col,
            color=cat_col,
            color_discrete_sequence=px.colors.qualitative.Prism,
            labels={cat_col: clean_cat_title, num_col: clean_num_title},
        )

        fig.update_traces(
            texttemplate="%{text:.2f}" if df[num_col].dtype == "float64" else "%{text}",
            textposition="outside",
            marker_line_color="rgba(0,0,0,0.1)",
            marker_line_width=1,
        )

        fig.update_layout(
            template="plotly_white",
            xaxis_title=clean_cat_title,
            yaxis_title=clean_num_title,
            showlegend=False,
            margin=dict(l=40, r=40, t=50, b=40),
            hoverlabel=dict(bgcolor="white", font_size=12),
        )
        return fig

    # Scenario 2: Two numeric columns (e.g., marks vs attendance)
    if len(df.columns) == 2 and len(numeric_cols) == 2 and len(df) >= 3:
        x_col, y_col = numeric_cols[0], numeric_cols[1]
        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            title=f"📈 {y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}",
            trendline="ols",
            color_discrete_sequence=["#4F46E5"],
        )
        fig.update_layout(template="plotly_white", margin=dict(l=40, r=40, t=50, b=40))
        return fig

    # Scenario 3: 3 columns (e.g., student name, subject name, marks)
    if len(df.columns) == 3 and len(categorical_cols) == 2 and len(numeric_cols) == 1:
        cat_col1, cat_col2 = categorical_cols[0], categorical_cols[1]
        num_col = numeric_cols[0]

        fig = px.bar(
            df,
            x=cat_col1,
            y=num_col,
            color=cat_col2,
            barmode="group",
            title=f"📊 {num_col.replace('_', ' ').title()} grouped by {cat_col2.replace('_', ' ').title()}",
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig.update_layout(template="plotly_white", margin=dict(l=40, r=40, t=50, b=40))
        return fig

    return None
