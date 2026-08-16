from __future__ import annotations

from pathlib import Path

import chainladder as cl
import pandas as pd


def load_triangle(
    path,
    *,
    origin_column="origin",
    development_column="development",
    value_column="values",
    filters=None,
    lob=None,
    company=None,
    company_column="GRNAME",
    valuation_year=None,
):
    """Load a reserving triangle into the standard origin/development/values format."""
    data = pd.read_csv(Path(path))

    filters = dict(filters or {})
    if lob is not None:
        filters["LOB"] = lob
    if company is not None:
        filters[company_column] = company

    for column, criterion in filters.items():
        if column not in data.columns:
            raise KeyError(f"Filter column {column!r} is not present in {path}")
        if callable(criterion):
            mask = data[column].map(criterion)
        elif isinstance(criterion, (list, tuple, set, frozenset)):
            mask = data[column].isin(criterion)
        else:
            mask = data[column].eq(criterion)
        data = data.loc[mask]

    required_columns = [origin_column, development_column, value_column]
    missing_columns = [column for column in required_columns if column not in data.columns]
    if missing_columns:
        raise KeyError(f"Missing triangle columns: {missing_columns}")

    if valuation_year is not None:
        data = data.loc[data[development_column].le(valuation_year)]

    triangle = (
        data.rename(
            columns={
                origin_column: "origin",
                development_column: "development",
                value_column: "values",
            }
        )[["origin", "development", "values"]]
        .groupby(["origin", "development"], as_index=False)["values"]
        .sum()
    )
    return triangle


def lag_triangle(triangle):
    """Remove the latest observed development period for each origin."""
    max_development = triangle.groupby("origin")["development"].transform("max")
    return triangle.loc[triangle["development"].ne(max_development)].copy()


class ReservingProjection:
    def __init__(
        self,
        data,
        development_params=None,
        method=cl.Chainladder,
        method_params=None,
    ):
        triangle = cl.Triangle(
            data,
            origin="origin",
            development="development",
            columns="values",
            cumulative=True,
        )
        development_params = development_params or {}
        method_params = method_params or {}
        self.triangle = cl.Development(**development_params).fit_transform(triangle)
        self.model = method(**method_params).fit(self.triangle)

    @property
    def claims_triangle(self):
        return self.triangle

    @property
    def ldf_triangle(self):
        return self.model.ldf_

    @property
    def ultimate_by_origin(self):
        ultimate = self.model.ultimate_.to_frame()
        ultimate.columns = ["ultimate"]
        return ultimate

    def percent_developed(self, valuation_age=10):
        full_triangle = self.model.full_triangle_.to_frame().iloc[:, :valuation_age]
        ultimate = self.model.ultimate_.to_frame().iloc[:, 0]
        return full_triangle.div(ultimate, axis=0)