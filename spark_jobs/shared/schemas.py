"""Schemas y constantes compartidas entre los Spark jobs."""

# Columnas del formato long
LONG_COLS = [
    "transaction_id",
    "date",
    "store_id",
    "customer_id",
    "category_id",
    "category_name",
    "year_month",
]

# Columnas del formato basket
BASKET_COLS = [
    "transaction_id",
    "date",
    "store_id",
    "customer_id",
    "categories",
    "basket_size",
    "year_month",
]

# Archivos de transacciones y sus sucursales
TRANSACTION_FILES = {
    "102_Tran.csv": 102,
    "103_Tran.csv": 103,
    "107_Tran.csv": 107,
    "110_Tran.csv": 110,
}
