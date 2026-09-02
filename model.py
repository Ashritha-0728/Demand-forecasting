import pandas as pd
import numpy as np


# ==========================================================
# ACCURACY METRICS
# ==========================================================

def calculate_metrics(actual, predicted):
    """
    Calculate forecasting accuracy metrics.
    """

    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)

    mae = np.mean(
        np.abs(actual - predicted)
    )

    rmse = np.sqrt(
        np.mean((actual - predicted) ** 2)
    )

    non_zero = actual != 0

    if np.any(non_zero):

        mape = np.mean(
            np.abs(
                (actual[non_zero] - predicted[non_zero])
                / actual[non_zero]
            )
        ) * 100

    else:

        mape = 0.0

    return {
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "mape": round(float(mape), 2)
    }


# ==========================================================
# FULL FORECAST MODEL
# ==========================================================

def create_forecast_values(
    daily_sales,
    future_dates
):
    """
    Full forecasting method used when enough
    historical data is available.

    Uses:
    - recent demand
    - day-of-week pattern
    - trend
    """

    recent_window = min(
        28,
        len(daily_sales)
    )

    recent_sales = daily_sales.tail(
        recent_window
    )

    recent_average = float(
        recent_sales.mean()
    )

    # ------------------------------------------------------
    # Day-of-week pattern
    # ------------------------------------------------------

    daily_df = daily_sales.to_frame(
        name="sales"
    )

    daily_df["day_of_week"] = (
        daily_df.index.dayofweek
    )

    weekday_average = (
        daily_df
        .groupby("day_of_week")["sales"]
        .mean()
    )

    overall_average = float(
        daily_sales.mean()
    )

    if overall_average == 0:

        weekday_factors = {
            day: 1.0
            for day in range(7)
        }

    else:

        weekday_factors = {
            day: float(
                weekday_average.get(
                    day,
                    overall_average
                ) / overall_average
            )
            for day in range(7)
        }

    # ------------------------------------------------------
    # Trend
    # ------------------------------------------------------

    if len(daily_sales) >= 28:

        recent_14 = float(
            daily_sales.tail(14).mean()
        )

        previous_14 = float(
            daily_sales.iloc[-28:-14].mean()
        )

        if previous_14 > 0:

            trend_ratio = (
                recent_14 /
                previous_14
            )

        else:

            trend_ratio = 1.0

        trend_ratio = max(
            0.85,
            min(1.15, trend_ratio)
        )

    else:

        trend_ratio = 1.0

    # ------------------------------------------------------
    # Predictions
    # ------------------------------------------------------

    predictions = []

    total_days = len(future_dates)

    for i, future_date in enumerate(
        future_dates
    ):

        day_of_week = (
            future_date.dayofweek
        )

        weekday_factor = (
            weekday_factors.get(
                day_of_week,
                1.0
            )
        )

        trend_progress = (
            i / max(total_days - 1, 1)
        )

        trend_factor = (
            1
            + (trend_ratio - 1)
            * trend_progress
        )

        prediction = (
            recent_average
            * weekday_factor
            * trend_factor
        )

        prediction = max(
            0,
            float(prediction)
        )

        predictions.append(
            prediction
        )

    return predictions


# ==========================================================
# LIMITED-HISTORY FORECAST
# ==========================================================

def create_limited_history_forecast(
    daily_sales,
    future_dates
):
    """
    Forecast when less than 28 historical days
    are available.

    Uses:
    - recent average demand
    - small trend adjustment

    It intentionally does NOT attempt to learn
    weekday seasonality because there is not enough
    historical data to do that reliably.
    """

    historical_days = len(daily_sales)

    # ------------------------------------------------------
    # Very limited data: use average
    # ------------------------------------------------------

    if historical_days <= 6:

        base_demand = float(
            daily_sales.mean()
        )

        return [
            max(
                0,
                round(base_demand, 2)
            )
            for _ in future_dates
        ]


    # ------------------------------------------------------
    # 7–27 days:
    # calculate recent trend
    # ------------------------------------------------------

    recent_window = min(
        7,
        historical_days
    )

    recent_average = float(
        daily_sales.tail(
            recent_window
        ).mean()
    )

    previous_start = max(
        0,
        historical_days - 14
    )

    previous_end = max(
        0,
        historical_days - 7
    )

    previous_period = daily_sales.iloc[
        previous_start:previous_end
    ]

    if len(previous_period) > 0:

        previous_average = float(
            previous_period.mean()
        )

    else:

        previous_average = recent_average


    # ------------------------------------------------------
    # Calculate limited trend
    # ------------------------------------------------------

    if previous_average > 0:

        trend_ratio = (
            recent_average /
            previous_average
        )

    else:

        trend_ratio = 1.0


    # Keep limited-history changes conservative
    trend_ratio = max(
        0.90,
        min(1.10, trend_ratio)
    )


    # ------------------------------------------------------
    # Generate predictions
    # ------------------------------------------------------

    predictions = []

    total_days = len(future_dates)

    for i, future_date in enumerate(
        future_dates
    ):

        trend_progress = (
            i / max(total_days - 1, 1)
        )

        trend_factor = (
            1
            + (trend_ratio - 1)
            * trend_progress
        )

        prediction = (
            recent_average
            * trend_factor
        )

        predictions.append(
            max(
                0,
                float(prediction)
            )
        )

    return predictions


# ==========================================================
# MAIN FORECAST FUNCTION
# ==========================================================

def forecast_demand(
    df,
    date_column,
    quantity_column,
    store_column=None,
    product_column=None,
    store="__all__",
    product="__all__",
    days=30
):

    data = df.copy()

    # ======================================================
    # VALIDATE COLUMNS
    # ======================================================

    if (
        not date_column
        or date_column not in data.columns
    ):

        raise ValueError(
            "A valid date column is required."
        )

    if (
        not quantity_column
        or quantity_column not in data.columns
    ):

        raise ValueError(
            "A valid quantity column is required."
        )

    # ======================================================
    # CONVERT TYPES
    # ======================================================

    data[date_column] = pd.to_datetime(
        data[date_column],
        errors="coerce"
    )

    data[quantity_column] = pd.to_numeric(
        data[quantity_column],
        errors="coerce"
    )

    data = data.dropna(
        subset=[
            date_column,
            quantity_column
        ]
    )

    if data.empty:

        raise ValueError(
            "No valid sales records were found."
        )

    # ======================================================
    # STORE FILTER
    # ======================================================

    if (
        store != "__all__"
        and store_column
        and store_column in data.columns
    ):

        data = data[
            data[store_column]
            .astype(str)
            .str.strip()
            ==
            str(store).strip()
        ]

    # ======================================================
    # PRODUCT FILTER
    # ======================================================

    if (
        product != "__all__"
        and product_column
        and product_column in data.columns
    ):

        data = data[
            data[product_column]
            .astype(str)
            .str.strip()
            ==
            str(product).strip()
        ]

    if data.empty:

        raise ValueError(
            "No sales records were found "
            "for the selected store/product."
        )

    # ======================================================
    # DAILY SALES
    # ======================================================

    daily_sales = (
        data
        .set_index(date_column)
        [quantity_column]
        .resample("D")
        .sum()
    )

    daily_sales = daily_sales.asfreq(
        "D",
        fill_value=0
    )

    daily_sales = daily_sales.clip(
        lower=0
    )

    if daily_sales.empty:

        raise ValueError(
            "Could not calculate historical demand."
        )

    # ======================================================
    # HISTORICAL DATA SIZE
    # ======================================================

    historical_days = len(daily_sales)


    # ======================================================
    # DETERMINE FORECAST METHOD
    # ======================================================

    if historical_days < 7:

        forecast_method = (
            "baseline"
        )

        confidence = (
            "Very Limited"
        )

    elif historical_days < 28:

        forecast_method = (
            "limited_history"
        )

        confidence = (
            "Limited"
        )

    else:

        forecast_method = (
            "full"
        )

        confidence = (
            "Higher"
        )


    # ======================================================
    # BACKTESTING
    # ======================================================

    evaluation_days = min(
        7,
        max(0, historical_days - 28)
    )

    metrics = None

    if evaluation_days >= 3:

        training_data = daily_sales.iloc[
            :-evaluation_days
        ]

        actual_data = daily_sales.iloc[
            -evaluation_days:
        ]

        evaluation_dates = (
            actual_data.index
        )

        predicted_values = (
            create_forecast_values(
                training_data,
                evaluation_dates
            )
        )

        actual_values = (
            actual_data.values
        )

        metrics = calculate_metrics(
            actual_values,
            predicted_values
        )


    # ======================================================
    # FUTURE DATES
    # ======================================================

    last_date = (
        daily_sales.index.max()
    )

    future_dates = pd.date_range(
        start=last_date
        + pd.Timedelta(days=1),
        periods=days,
        freq="D"
    )


    # ======================================================
    # CHOOSE FORECAST METHOD
    # ======================================================

    if forecast_method == "full":

        predictions = (
            create_forecast_values(
                daily_sales,
                future_dates
            )
        )

    else:

        predictions = (
            create_limited_history_forecast(
                daily_sales,
                future_dates
            )
        )


    # ======================================================
    # FORECAST DATAFRAME
    # ======================================================

    forecast = pd.DataFrame({

        "date":
            future_dates.strftime(
                "%Y-%m-%d"
            ),

        "predicted_demand": [
            round(value, 2)
            for value in predictions
        ]

    })


    # ======================================================
    # SUMMARY
    # ======================================================

    total_forecast = round(
        float(
            forecast[
                "predicted_demand"
            ].sum()
        ),
        2
    )

    average_forecast = round(
        float(
            forecast[
                "predicted_demand"
            ].mean()
        ),
        2
    )


    # ======================================================
    # HIGHEST / LOWEST DAYS
    # ======================================================

    highest_row = forecast.loc[
        forecast[
            "predicted_demand"
        ].idxmax()
    ]

    lowest_row = forecast.loc[
        forecast[
            "predicted_demand"
        ].idxmin()
    ]


    # ======================================================
    # RETURN RESULT
    # ======================================================

    return {

        "forecast":
            forecast.to_dict(
                orient="records"
            ),

        "summary": {

            "total_demand":
                total_forecast,

            "average_daily_demand":
                average_forecast,

            "forecast_days":
                days,

            "last_historical_date":
                last_date.strftime(
                    "%Y-%m-%d"
                ),

            "historical_days":
                historical_days,

            "forecast_method":
                forecast_method,

            "confidence":
                confidence,

            "highest_demand_day": {

                "date":
                    highest_row["date"],

                "demand":
                    float(
                        highest_row[
                            "predicted_demand"
                        ]
                    )

            },

            "lowest_demand_day": {

                "date":
                    lowest_row["date"],

                "demand":
                    float(
                        lowest_row[
                            "predicted_demand"
                        ]
                    )

            }

        },

        "evaluation":
            metrics

    }