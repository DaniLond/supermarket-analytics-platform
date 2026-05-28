"""
Ingesta inicial del dataset de supermercado
"""

import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _spark_path(p: Path) -> str:
    if platform.system() != "Windows":
        return p.as_posix()
    import ctypes

    # Caso 1: el path ya existe (archivo de entrada o dir ya creado)
    if p.exists():
        buf = ctypes.create_unicode_buffer(32768)
        ret = ctypes.windll.kernel32.GetShortPathNameW(str(p), buf, len(buf))
        return buf.value.replace("\\", "/") if ret else p.as_posix()

    # Caso 2: directorio de salida que aún no existe — crearlo
    if not p.suffix:
        p.mkdir(parents=True, exist_ok=True)
        buf = ctypes.create_unicode_buffer(32768)
        ret = ctypes.windll.kernel32.GetShortPathNameW(str(p), buf, len(buf))
        return buf.value.replace("\\", "/") if ret else p.as_posix()

    # Caso 3: ruta de archivo en dir que puede no existir — subir hasta encontrar ancestro
    existing, tail = p.parent, [p.name]
    while not existing.exists():
        tail.insert(0, existing.name)
        existing = existing.parent
    buf = ctypes.create_unicode_buffer(32768)
    ret = ctypes.windll.kernel32.GetShortPathNameW(str(existing), buf, len(buf))
    if not ret:
        return p.as_posix()
    return (Path(buf.value) / Path(*tail)).as_posix()

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, IntegerType, StringType, StructField, StructType

from spark_jobs.shared.schemas import TRANSACTION_FILES

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE = ROOT
RAW_PATH = BASE / "data" / "DataSet"
PROCESSED = BASE / "data" / "processed"
LONG_OUT = PROCESSED / "transactions_long"
BASKET_OUT = PROCESSED / "transactions_basket"
CATALOG_OUT = PROCESSED / "catalog"


# ---------------------------------------------------------------------------
# SparkSession
# ---------------------------------------------------------------------------
def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("supermercado-ingest")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "4g")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
        .getOrCreate()
    )


# ---------------------------------------------------------------------------
# Carga del catálogo
# ---------------------------------------------------------------------------
def load_categories(spark: SparkSession):
    """
    Lee Categories.csv
    """
    schema = StructType(
        [
            StructField("category_id", IntegerType(), nullable=False),
            StructField("category_name", StringType(), nullable=False),
        ]
    )
    return spark.read.csv(
        _spark_path(RAW_PATH / "Products" / "Categories.csv"),
        sep="|",
        header=False,
        schema=schema,
        encoding="iso-8859-1",
    )


def load_product_catalog(spark: SparkSession):
    """
    Lee ProductCategory.csv.
    """
    raw = spark.read.csv(
        _spark_path(RAW_PATH / "Products" / "ProductCategory.csv"),
        sep="|",
        header=True,
        encoding="iso-8859-1",
    )
    return (
        raw.withColumnRenamed("v.Code_pr", "product_code")
        .withColumnRenamed("v.code", "category_id")
        .select(
            F.col("product_code").cast(IntegerType()).alias("product_code"),
            F.col("category_id").cast(IntegerType()).alias("category_id"),
        )
        .dropna()
    )


# ---------------------------------------------------------------------------
# Carga y transformación de transacciones
# ---------------------------------------------------------------------------
def load_transactions(spark: SparkSession, categories_df, product_catalog_df):
    """
    Lee los 4 archivos *_Tran.csv y construye las representaciones basket y long.
    """
    tx_schema = StructType(
        [
            StructField("date", StringType(), nullable=False),
            StructField("store_id", IntegerType(), nullable=False),
            StructField("customer_id", IntegerType(), nullable=False),
            StructField("products_raw", StringType(), nullable=True),
        ]
    )

    frames = [
        spark.read.csv(
            _spark_path(RAW_PATH / "Transactions" / fname),
            sep="|",
            header=False,
            schema=tx_schema,
        )
        for fname in TRANSACTION_FILES
    ]
    raw = frames[0]
    for f in frames[1:]:
        raw = raw.union(f)

    raw = (
        raw.withColumn(
            "products",
            F.expr(
                "filter(transform(split(trim(products_raw), ' '), x -> cast(x as int)), x -> x is not null)"
            ),
        )
        .withColumn(
            "transaction_id",
            F.sha2(
                F.concat_ws("|", F.col("date"), F.col("store_id"), F.col("customer_id")),
                256,
            ).substr(1, 16),
        )
        .withColumn("year_month", F.date_format(F.to_date(F.col("date")), "yyyy-MM"))
        .drop("products_raw")
        .filter(F.size(F.col("products")) > 0)
    )
    raw.cache()

    tx_categories = (
        raw.select(
            "transaction_id", "date", "store_id", "customer_id", "year_month",
            F.explode("products").alias("product_code"),
        )
        .join(product_catalog_df, on="product_code", how="inner")
        .select("transaction_id", "date", "store_id", "customer_id", "year_month", "category_id")
        .distinct()  # una fila por (transaccion, categoria)
    )
    tx_categories.cache()

    long = tx_categories.join(categories_df, on="category_id", how="left")

    basket = (
        tx_categories
        .groupBy("transaction_id", "date", "store_id", "customer_id", "year_month")
        .agg(F.sort_array(F.collect_set("category_id")).alias("categories"))
        .withColumn("basket_size", F.size(F.col("categories")))
        .filter(F.col("basket_size") > 0)
    )

    return basket, long


# ---------------------------------------------------------------------------
# Escritura Parquet
# ---------------------------------------------------------------------------
def write_parquet(df, path: Path) -> None:
    """
    Escribe un DataFrame como Parquet particionado por store_id y year_month.
    """
    if platform.system() == "Windows":
        _write_parquet_pyarrow(df, path)
    else:
        df.write.partitionBy("store_id", "year_month").mode("overwrite").parquet(
            _spark_path(path)
        )


def _write_parquet_pyarrow(df, path: Path) -> None:
    """Colecta el DataFrame por store_id y escribe con pyarrow (sin Hadoop).
    """
    import shutil
    import pyarrow as pa
    import pyarrow.parquet as pq

    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)

    stores = [r[0] for r in df.select("store_id").distinct().orderBy("store_id").collect()]
    for store_id in stores:
        chunk = df.filter(F.col("store_id") == store_id).toPandas()
        if chunk.empty:
            continue
        table = pa.Table.from_pandas(chunk, preserve_index=False)
        pq.write_to_dataset(
            table,
            root_path=str(path),
            partition_cols=["store_id", "year_month"],
            existing_data_behavior="overwrite_or_ignore",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    print("=" * 60)
    print("Supermercado Analytics — Ingesta inicial")
    print("=" * 60)

    print("\n[1/4] Cargando catálogo de categorías...")
    categories = load_categories(spark)
    categories.cache()
    n_cats = categories.count()
    print(f"      {n_cats} categorías cargadas")

    print("\n[2/4] Cargando catálogo de productos...")
    catalog = load_product_catalog(spark)
    catalog.cache()

    print("\n[3/4] Procesando transacciones (4 sucursales)...")
    basket, long = load_transactions(spark, categories, catalog)

    basket.cache()
    long.cache()

    print("\n[4/4] Escribiendo Parquet...")
    print(f"      basket  ->{BASKET_OUT}")
    write_parquet(basket, BASKET_OUT)

    print(f"      long    ->{LONG_OUT}")
    write_parquet(long, LONG_OUT)

    print(f"      catalog ->{CATALOG_OUT}")
    if platform.system() == "Windows":
        import pyarrow as pa, pyarrow.parquet as pq
        pdf = catalog.toPandas()
        CATALOG_OUT.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(pdf, preserve_index=False),
                       str(CATALOG_OUT / "catalog.parquet"))
    else:
        catalog.write.mode("overwrite").parquet(_spark_path(CATALOG_OUT))

    print("\n-- Validacion --")
    n_basket = basket.count()
    n_long = long.count()
    date_range = long.agg(F.min("date").alias("min_date"), F.max("date").alias("max_date")).collect()[0]
    stores = [r["store_id"] for r in basket.select("store_id").distinct().orderBy("store_id").collect()]

    print(f"  Transacciones (basket) : {n_basket:,}")
    print(f"  Líneas de categoría    : {n_long:,}")
    print(f"  Rango de fechas        : {date_range['min_date']}  -> {date_range['max_date']}")
    print(f"  Sucursales             : {stores}")
    print(f"  Avg. categorías/canasta: {n_long / n_basket:.2f}")
    print("\nIngesta completada exitosamente.")

    spark.stop()


if __name__ == "__main__":
    main()