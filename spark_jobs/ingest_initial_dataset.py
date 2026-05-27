"""
Ingesta inicial del dataset de supermercado — Sección 2.
=========================================================
Lee el dataset crudo (ya extraído en data/DataSet/) y lo transforma en dos
representaciones Parquet particionadas por store_id y year_month:

  data/processed/transactions_long/     — una fila por (transacción, categoría)
  data/processed/transactions_basket/   — una fila por transacción (canasta array)
  data/processed/catalog/               — catálogo de productos

Idempotente: usa mode("overwrite") a nivel de partición.
Distribuible: reemplazar la ruta local por hdfs:// o s3:// sin cambiar lógica.
"""

import hashlib
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, IntegerType, StringType, StructField, StructType

# ---------------------------------------------------------------------------
# Rutas (pueden sobreescribirse con variables de entorno en producción)
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
RAW_PATH = BASE / "data" / "DataSet"
PROCESSED = BASE / "data" / "processed"
LONG_OUT = PROCESSED / "transactions_long"
BASKET_OUT = PROCESSED / "transactions_basket"
CATALOG_OUT = PROCESSED / "catalog"


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("supermercado-ingest")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )


def load_categories(spark: SparkSession):
    """
    Lee Categories.csv (id|nombre, sin header).
    Retorna DataFrame con columnas: category_id INT, category_name STRING.
    """
    schema = StructType(
        [
            StructField("category_id", IntegerType(), False),
            StructField("category_name", StringType(), False),
        ]
    )
    return spark.read.csv(
        str(RAW_PATH / "Products" / "Categories.csv"),
        sep="|",
        header=False,
        schema=schema,
        encoding="latin-1",
    )


def load_product_catalog(spark: SparkSession):
    """
    Lee ProductCategory.csv (v.Code_pr|v.code, CON header).
    Retorna DataFrame: product_code INT, category_id INT.
    """
    df = spark.read.csv(
        str(RAW_PATH / "Products" / "ProductCategory.csv"),
        sep="|",
        header=True,
        encoding="latin-1",
    )
    return df.withColumnRenamed("v.Code_pr", "product_code").withColumnRenamed(
        "v.code", "category_id"
    ).select(
        F.col("product_code").cast(IntegerType()),
        F.col("category_id").cast(IntegerType()),
    )


def load_transactions(spark: SparkSession, categories_df):
    """
    Lee los 4 archivos *_Tran.csv (date|store_id|customer_id|cats, sin header).
    Construye DataFrames basket y long.
    """
    from spark_jobs.shared.schemas import TRANSACTION_FILES

    tx_schema = StructType(
        [
            StructField("date", StringType(), False),
            StructField("store_id", IntegerType(), False),
            StructField("customer_id", IntegerType(), False),
            StructField("categories_raw", StringType(), False),
        ]
    )

    frames = []
    for fname in TRANSACTION_FILES:
        fpath = str(RAW_PATH / "Transactions" / fname)
        frames.append(spark.read.csv(fpath, sep="|", header=False, schema=tx_schema))

    raw = frames[0]
    for f in frames[1:]:
        raw = raw.union(f)

    # Parsear categorías y construir transaction_id
    raw = (
        raw.withColumn("categories", F.split(F.col("categories_raw"), " ").cast(ArrayType(IntegerType())))
        .withColumn("basket_size", F.size(F.col("categories")))
        .withColumn(
            "transaction_id",
            F.sha2(F.concat_ws("|", F.col("date"), F.col("store_id"), F.col("customer_id")), 256).substr(1, 16),
        )
        .withColumn("year_month", F.date_format(F.to_date(F.col("date")), "yyyy-MM"))
        .drop("categories_raw")
    )

    # Basket: una fila por transacción
    basket = raw.select("transaction_id", "date", "store_id", "customer_id", "categories", "basket_size", "year_month")

    # Long: explode + join con nombres de categoría
    long = (
        raw.select(
            "transaction_id", "date", "store_id", "customer_id",
            F.explode("categories").alias("category_id"), "year_month",
        )
        .join(categories_df, on="category_id", how="left")
    )

    return basket, long


def write_parquet(df, path: Path, mode: str = "overwrite") -> None:
    df.write.partitionBy("store_id", "year_month").mode(mode).parquet(str(path))


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    print("Cargando catálogo de categorías...")
    categories = load_categories(spark)
    categories.cache()

    print("Cargando catálogo de productos...")
    catalog = load_product_catalog(spark)

    print("Procesando transacciones...")
    basket, long = load_transactions(spark, categories)

    print(f"Escribiendo basket → {BASKET_OUT}")
    write_parquet(basket, BASKET_OUT)

    print(f"Escribiendo long → {LONG_OUT}")
    write_parquet(long, LONG_OUT)

    print(f"Escribiendo catálogo → {CATALOG_OUT}")
    catalog.write.mode("overwrite").parquet(str(CATALOG_OUT))

    # Validación rápida
    count_long = long.count()
    count_basket = basket.count()
    print(f"Ingesta completada: {count_basket} transacciones / {count_long} líneas")

    spark.stop()


if __name__ == "__main__":
    main()
