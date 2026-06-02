"""
Entrenamiento de reglas de asociación FP-Growth
"""

from pathlib import Path

from pyspark.ml.fpm import FPGrowth
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, LongType, StringType, StructField, StructType

BASE = Path(__file__).resolve().parent.parent
BASKET_PATH = BASE / "data" / "processed" / "transactions_basket"
RULES_OUT = BASE / "data" / "models" / "association_rules.parquet"

MIN_SUPPORT = 0.01
MIN_CONFIDENCE = 0.3


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("supermercado-recommender")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.default.parallelism", "4")
        .config("spark.driver.memory", "2g")
        .config("spark.executor.memory", "2g")
        .config("spark.sql.adaptive.enabled", "false")
        .config("spark.sql.parquet.enableVectorizedReader", "false")
        .config("spark.sql.codegen.wholeStage", "false")
        .getOrCreate()
    )


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    print("Cargando canastas de transacciones...", flush=True)
    # Schema explícito: LongType acepta tanto int32 (upcast) como int64 (match directo).
    # Evita CANNOT_MERGE_INCOMPATIBLE_DATA_TYPE cuando coexisten archivos INT32 e INT64 en disco.
    basket_schema = StructType([
        StructField("transaction_id", StringType(), True),
        StructField("date", StringType(), True),
        StructField("customer_id", LongType(), True),
        StructField("categories", ArrayType(LongType()), True),
        StructField("basket_size", LongType(), True),
    ])
    basket = spark.read.schema(basket_schema).parquet(str(BASKET_PATH))
    basket = basket.withColumn("categories", F.col("categories").cast("array<int>"))

    n_baskets = basket.count()
    print(f"Canastas totales: {n_baskets}", flush=True)

    print(
        f"Entrenando FP-Growth (minSupport={MIN_SUPPORT}, minConfidence={MIN_CONFIDENCE})...",
        flush=True,
    )
    fp = FPGrowth(
        itemsCol="categories",
        minSupport=MIN_SUPPORT,
        minConfidence=MIN_CONFIDENCE,
        numPartitions=4,
    )
    model = fp.fit(basket)

    rules = model.associationRules
    RULES_OUT.parent.mkdir(parents=True, exist_ok=True)
    rules.write.mode("overwrite").parquet(str(RULES_OUT))

    n_rules = rules.count()
    print(f"Reglas de asociación generadas: {n_rules}", flush=True)
    rules.orderBy(F.col("lift").desc()).show(10, truncate=False)

    spark.stop()
    print("Entrenamiento FP-Growth completado.", flush=True)


if __name__ == "__main__":
    main()