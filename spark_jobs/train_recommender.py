"""
Entrenamiento de reglas de asociación FP-Growth — Sección 8.
=============================================================
1. Carga transactions_basket desde Parquet (categorías como arrays).
2. Aplica FP-Growth (pyspark.ml.fpm.FPGrowth).
3. Persiste association_rules.parquet con antecedent, consequent, confidence, lift, support.
"""

from pathlib import Path

from pyspark.ml.fpm import FPGrowth
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BASE = Path(__file__).resolve().parent.parent
BASKET_PATH = BASE / "data" / "processed" / "transactions_basket"
RULES_OUT = BASE / "data" / "models" / "association_rules.parquet"

MIN_SUPPORT = 0.01
MIN_CONFIDENCE = 0.3


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("supermercado-recommender")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    print("Cargando canastas...")
    basket = spark.read.parquet(str(BASKET_PATH))

    # FPGrowth espera una columna de tipo Array<T>
    basket = basket.withColumn("categories", F.col("categories").cast("array<int>"))

    print(f"Entrenando FP-Growth (minSupport={MIN_SUPPORT}, minConfidence={MIN_CONFIDENCE})...")
    fp = FPGrowth(
        itemsCol="categories",
        minSupport=MIN_SUPPORT,
        minConfidence=MIN_CONFIDENCE,
    )
    model = fp.fit(basket)

    rules = model.associationRules
    rules.write.mode("overwrite").parquet(str(RULES_OUT))
    print(f"Reglas generadas: {rules.count()}")
    rules.orderBy(F.col("lift").desc()).show(20, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
