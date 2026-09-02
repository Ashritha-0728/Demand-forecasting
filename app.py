from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.model import forecast_demand

import pandas as pd
import io
import json


app = FastAPI(title="Retail Demand Forecasting")


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# File used to permanently store manually recorded sales
RECORDED_SALES_FILE = BASE_DIR / "recorded_sales.json"


app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)


# ============================================================
# STORAGE
# ============================================================

uploaded_dataframe = None


def load_recorded_sales():
    """
    Load manually recorded sales from the local JSON file.
    If the file does not exist or cannot be read, start with
    an empty list.
    """

    if not RECORDED_SALES_FILE.exists():
        return []

    try:
        with open(
            RECORDED_SALES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, list):
                return data

            return []

    except (json.JSONDecodeError, OSError):
        return []


def save_recorded_sales():
    """
    Save manually recorded sales to the local JSON file.
    """

    with open(
        RECORDED_SALES_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            recorded_sales,
            file,
            indent=4
        )


# Load saved sales when the server starts
recorded_sales = load_recorded_sales()


# ============================================================
# PAGES
# ============================================================

@app.get("/")
def home():
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


@app.get("/options")
def options():
    return FileResponse(
        FRONTEND_DIR / "options.html"
    )


@app.get("/upload")
def upload():
    return FileResponse(
        FRONTEND_DIR / "upload.html"
    )


@app.get("/data-check")
def data_check():
    return FileResponse(
        FRONTEND_DIR / "data-check.html"
    )


@app.get("/forecast-setup")
def forecast_setup():
    return FileResponse(
        FRONTEND_DIR / "forecast-setup.html"
    )


@app.get("/forecast")
def forecast_page():
    return FileResponse(
        FRONTEND_DIR / "forecast.html"
    )


@app.get("/record")
def record_page():
    return FileResponse(
        FRONTEND_DIR / "record.html"
    )


@app.get("/recorded-forecast")
def recorded_forecast_page():
    return FileResponse(
        FRONTEND_DIR / "recorded-forecast.html"
    )

@app.get("/quick-estimate")
def quick_estimate_page():
    return FileResponse(
        FRONTEND_DIR / "quick-estimate.html"
    )

@app.get("/quick-estimate")
def quick_estimate():
    return FileResponse(FRONTEND_DIR / "quick-estimate.html")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "running"
    }


# ============================================================
# UPLOAD FILE
# ============================================================

@app.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...)
):

    global uploaded_dataframe

    contents = await file.read()

    try:

        filename = file.filename.lower()

        # CSV
        if filename.endswith(".csv"):

            df = pd.read_csv(
                io.BytesIO(contents)
            )

        # Excel
        elif filename.endswith(
            (".xlsx", ".xls")
        ):

            df = pd.read_excel(
                io.BytesIO(contents)
            )

        else:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "Please upload a CSV or Excel file."
                }
            )

        # Empty file
        if df.empty:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "The uploaded file is empty."
                }
            )

        # Clean column names
        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        # Save dataframe temporarily
        uploaded_dataframe = df.copy()

        # ----------------------------------------------------
        # AUTOMATIC COLUMN DETECTION
        # ----------------------------------------------------

        columns = list(df.columns)

        lower_columns = {
            column: column.lower().strip()
            for column in columns
        }

        def find_column(keywords):

            for column in columns:

                name = lower_columns[column]

                for keyword in keywords:

                    if keyword in name:
                        return column

            return ""

        date_column = find_column([
            "date",
            "day",
            "timestamp"
        ])

        store_column = find_column([
            "store",
            "shop",
            "branch",
            "outlet"
        ])

        product_column = find_column([
            "product",
            "item",
            "sku",
            "product_name",
            "item_name"
        ])

        quantity_column = find_column([
            "quantity",
            "qty",
            "units",
            "sales",
            "sold"
        ])
                # ----------------------------------------------------
        # REQUIRED COLUMN VALIDATION
        # ----------------------------------------------------

        missing_columns = []

        if not date_column:
            missing_columns.append("date")

        if not store_column:
            missing_columns.append("store")

        if not product_column:
            missing_columns.append("product/item")

        if not quantity_column:
            missing_columns.append("sales/quantity")

        if missing_columns:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "We could not identify the required column(s): "
                    + ", ".join(missing_columns)
                    + ". Please upload a file containing date, store, product/item, and sales/quantity columns."
                }
            )
        # SALES / QUANTITY VALUE VALIDATION
        numeric_values = pd.to_numeric(
            df[quantity_column],
            errors="coerce"
        )

        invalid_values = (
            numeric_values.isna()
            & df[quantity_column].notna()
        )

        if invalid_values.any():
            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "The sales/quantity column contains invalid values. "
                    "Please make sure all sales or quantity values are numbers."
                }
            )
        # DATE VALUE VALIDATION
        date_values = pd.to_datetime(
            df[date_column],
            errors="coerce"
        )

        invalid_dates = (
        date_values.isna()
        | df[date_column].isna()
        | (df[date_column].astype(str).str.strip() == "")
    )

        if invalid_dates.any():
            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "The date column contains invalid values. "
                    "Please make sure all date values are valid dates."
                }
            )
        # STORE VALUE VALIDATION
        invalid_stores = (
            df[store_column].isna()
            | (df[store_column].astype(str).str.strip() == "")
        )

        if invalid_stores.any():
            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "The store column contains missing or blank values. "
                    "Please make sure all store values are provided."
                }
            )
        # PRODUCT VALUE VALIDATION
        invalid_products = (
            df[product_column].isna()
            | (df[product_column].astype(str).str.strip() == "")
        )

        if invalid_products.any():
            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "The product/item column contains missing or blank values. "
                    "Please make sure all product/item values are provided."
                }
            )
        # NEGATIVE SALES / QUANTITY VALIDATION
        negative_values = numeric_values < 0

        if negative_values.any():
            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "The sales/quantity column contains negative values. "
                    "Please make sure all sales or quantity values are zero or greater."
                }
            )
        # ----------------------------------------------------
        # VALUES FOR DROPDOWNS
        # ----------------------------------------------------

        stores = []
        products = []

        if store_column:

            stores = (
                df[store_column]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

        if product_column:

            products = (
                df[product_column]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "filename": file.filename,

            "rows": len(df),

            "columns": columns,

            "preview": (
                df.head(5)
                .fillna("")
                .astype(str)
                .to_dict(
                    orient="records"
                )
            ),

            "detection": {

                "date": {
                    "column": date_column
                },

                "store": {
                    "column": store_column
                },

                "product": {
                    "column": product_column
                },

                "quantity": {
                    "column": quantity_column
                }

            },

            "options": {

                "stores": stores,

                "products": products

            }

        }

    except Exception as e:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                f"Could not read the file: {str(e)}"
            }
        )


# ============================================================
# GET STORE / PRODUCT OPTIONS
# ============================================================

@app.post("/forecast-options")
async def forecast_options(data: dict):

    global uploaded_dataframe

    if uploaded_dataframe is None:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                "No uploaded sales data is available."
            }
        )

    try:

        store_column = data.get(
            "store_column"
        )

        product_column = data.get(
            "product_column"
        )

        stores = []
        products = []

        if (
            store_column
            and store_column
            in uploaded_dataframe.columns
        ):

            stores = (
                uploaded_dataframe[
                    store_column
                ]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

        if (
            product_column
            and product_column
            in uploaded_dataframe.columns
        ):

            products = (
                uploaded_dataframe[
                    product_column
                ]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

        return {

            "stores": stores,

            "products": products

        }

    except Exception as e:

        return JSONResponse(
            status_code=400,
            content={
                "error": str(e)
            }
        )


# ============================================================
# MANUAL SALES RECORDING
# ============================================================

# ------------------------------------------------------------
# ADD A SALES RECORD
# ------------------------------------------------------------

@app.post("/record-sale")
async def record_sale(data: dict):

    try:

        date = str(
            data.get("date", "")
        ).strip()

        store = str(
            data.get("store", "")
        ).strip()

        product = str(
            data.get("product", "")
        ).strip()

        quantity = data.get(
            "quantity"
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not date:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "Please select a date."
                }
            )

        if not store:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "Please enter a store."
                }
            )

        if not product:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "Please enter a product."
                }
            )

        if quantity is None:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "Please enter the quantity sold."
                }
            )

        try:

            quantity = float(quantity)

        except (ValueError, TypeError):

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "Quantity must be a number."
                }
            )

        if quantity < 0:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "Quantity cannot be negative."
                }
            )

        # ----------------------------------------------------
        # CREATE RECORD
        # ----------------------------------------------------

        record = {

            "date": date,

            "store": store,

            "product": product,

            "quantity": quantity

        }

        recorded_sales.append(
            record
        )

        # Permanently save the record
        save_recorded_sales()

        return {

            "message":
            "Sale recorded successfully.",

            "record":
            record,

            "total_records":
            len(recorded_sales)

        }

    except Exception as e:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                str(e)
            }
        )


# ------------------------------------------------------------
# GET ALL RECORDED SALES
# ------------------------------------------------------------

@app.get("/recorded-sales")
def get_recorded_sales():

    global recorded_sales

    # Reload the latest saved records from JSON.
    # This ensures that records already stored in
    # recorded_sales.json appear on the local-host page.
    recorded_sales = load_recorded_sales()

    return recorded_sales


# ------------------------------------------------------------
# DELETE ONE RECORDED SALE
# ------------------------------------------------------------

@app.delete("/recorded-sales/{index}")
def delete_recorded_sale(index: int):

    if (
        index < 0
        or index >= len(recorded_sales)
    ):

        return JSONResponse(
            status_code=404,
            content={
                "error":
                "Sales record not found."
            }
        )

    deleted_record = (
        recorded_sales.pop(index)
    )

    # Permanently save the change
    save_recorded_sales()

    return {

        "message":
        "Sales record deleted.",

        "record":
        deleted_record,

        "total_records":
        len(recorded_sales)

    }


# ------------------------------------------------------------
# CLEAR ALL RECORDED SALES
# ------------------------------------------------------------

@app.delete("/recorded-sales")
def clear_recorded_sales():

    recorded_sales.clear()

    # Permanently save the empty list
    save_recorded_sales()

    return {

        "message":
        "All recorded sales have been cleared.",

        "total_records":
        0

    }


# ============================================================
# FORECAST FROM RECORDED SALES
# ============================================================

@app.post("/forecast-recorded")
async def forecast_recorded(data: dict):

    if not recorded_sales:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                "No recorded sales are available for forecasting."
            }
        )

    try:

        store = str(
            data.get(
                "store",
                "__all__"
            )
        )

        product = str(
            data.get(
                "product",
                "__all__"
            )
        )

        days = int(
            data.get(
                "days",
                30
            )
        )

        if days <= 0:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                    "Forecast period must be greater than 0."
                }
            )

        # ----------------------------------------------------
        # CONVERT RECORDED SALES TO DATAFRAME
        # ----------------------------------------------------

        df = pd.DataFrame(
            recorded_sales
        )

        df["store"] = (
            df["store"]
            .astype(str)
            .str.strip()
        )

        df["product"] = (
            df["product"]
            .astype(str)
            .str.strip()
        )

        # ----------------------------------------------------
        # FORECAST
        # ----------------------------------------------------

        result = forecast_demand(

            df=df,

            date_column="date",

            quantity_column="quantity",

            store_column="store",

            product_column="product",

            store=store,

            product=product,

            days=days

        )

        return result

    except Exception as e:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                str(e)
            }
        )


# ============================================================
# NORMAL FORECAST FROM UPLOADED DATA
# ============================================================

@app.post("/forecast")
async def create_forecast(data: dict):

    global uploaded_dataframe

    if uploaded_dataframe is None:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                "No uploaded sales data is available."
            }
        )

    try:

        # ----------------------------------------------------
        # Get settings selected by the user
        # ----------------------------------------------------

        date_column = data.get(
            "dateColumn"
        )

        store_column = data.get(
            "storeColumn"
        )

        product_column = data.get(
            "productColumn"
        )

        quantity_column = data.get(
            "quantityColumn"
        )

        store = data.get(
            "store",
            "__all__"
        )

        product = data.get(
            "product",
            "__all__"
        )

        days = int(
            data.get(
                "days",
                30
            )
        )

        # ----------------------------------------------------
        # Generate forecast
        # ----------------------------------------------------

        result = forecast_demand(

            df=uploaded_dataframe,

            date_column=date_column,

            quantity_column=quantity_column,

            store_column=store_column,

            product_column=product_column,

            store=store,

            product=product,

            days=days

        )

        return result

    except Exception as e:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                str(e)
            }
        )


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "backend.app:app",

        host="127.0.0.1",

        port=8000,

        reload=True

    )