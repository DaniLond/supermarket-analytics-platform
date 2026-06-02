"""
Entrenamiento de segmentación K-Means
"""

from pathlib import Path

from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BASE = Path(__file__).resolve().parent.parent
LONG_PATH = BASE / "data" / "processed" / "transactions_long"
KMEANS_OUT = BASE / "data" / "models" / "kmeans"
CLUSTERS_OUT = BASE / "data" / "processed" / "customer_clusters.parquet"


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("supermercado-segmentation")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.default.parallelism", "4")
        .config("spark.driver.memory", "2g")
        .config("spark.executor.memory", "2g")
        .config("spark.sql.adaptive.enabled", "false")
        .config("spark.sql.parquet.enableVectorizedReader", "false")
        .config("spark.sql.codegen.wholeStage", "false")
        .getOrCreate()
    )


def build_features(spark: SparkSession):
    long = spark.read.option("mergeSchema", "true").parquet(str(LONG_PATH))
    reference_date = long.agg(F.max("date")).collect()[0][0]

    features = (
        long.groupBy("customer_id")
        .agg(
            F.countDistinct("transaction_id").alias("frequency"),
            F.count("category_id").alias("total_categories_bought"),
            F.countDistinct("category_id").alias("unique_categories"),
            F.count("category_id").alias("_total_items"),
            F.datediff(F.lit(reference_date), F.max("date")).alias("recency_days"),
            F.countDistinct("date").alias("active_days"),
        )
        .withColumn(
            "avg_basket_size",
            F.when(F.col("frequency") > 0,
                   (F.col("_total_items") / F.col("frequency")).cast("double"))
            .otherwise(0.0),
        )
        .drop("_total_items")
    )
    return features


def find_optimal_k(scaled_df, k_range=range(2, 7)):
    """Silhouette-based K selection. Receives pre-scaled DataFrame."""
    evaluator = ClusteringEvaluator(
        predictionCol="prediction",
        featuresCol="scaled_features",
        metricName="silhouette",
    )
    best_k, best_score = 2, -1.0
    for k in k_range:
        km = KMeans(k=k, seed=42, featuresCol="scaled_features", predictionCol="prediction")
        model = km.fit(scaled_df)
        preds = model.transform(scaled_df)
        score = evaluator.evaluate(preds)
        print(f"  k={k}  silhouette={score:.4f}  wssse={model.summary.trainingCost:.2f}",
              flush=True)
        if score > best_score:
            best_score, best_k = score, k
    print(f"Mejor k={best_k}  score={best_score:.4f}", flush=True)
    return best_k


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    print("Construyendo features de clientes...", flush=True)
    features = build_features(spark).na.fill(0)

    feature_cols = [
        "frequency", "total_categories_bought", "unique_categories",
        "avg_basket_size", "recency_days", "active_days",
    ]
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_features")
    scaler = StandardScaler(
        inputCol="raw_features", outputCol="scaled_features",
        withStd=True, withMean=True,
    )

    assembled = assembler.transform(features)
    scaler_model = scaler.fit(assembled)
    scaled = scaler_model.transform(assembled).cache()

    n_customers = scaled.count()
    print(f"Clientes totales: {n_customers}", flush=True)

    print("Buscando K óptimo (k=2..6)...", flush=True)
    best_k = find_optimal_k(scaled)
    print(f"K óptimo: {best_k}", flush=True)

    print(f"Entrenando KMeans final con k={best_k}...", flush=True)
    km = KMeans(k=best_k, seed=42, featuresCol="scaled_features", predictionCol="cluster")
    km_model = km.fit(scaled)

    print("Guardando modelo K-Means...", flush=True)
    KMEANS_OUT.parent.mkdir(parents=True, exist_ok=True)
    km_model.write().overwrite().save(str(KMEANS_OUT))

    print("Guardando clusters de clientes...", flush=True)
    CLUSTERS_OUT.parent.mkdir(parents=True, exist_ok=True)
    clusters = km_model.transform(scaled).select("customer_id", "cluster", *feature_cols)
    clusters.write.mode("overwrite").parquet(str(CLUSTERS_OUT))

    scaled.unpersist()
    spark.stop()
    print(f"Entrenamiento completado: {n_customers} clientes segmentados.", flush=True)


if __name__ == "__main__":
    main()