"""
Entrenamiento de segmentación K-Means — Sección 7.
===================================================
1. Carga transactions_long desde Parquet.
2. Construye features por cliente.
3. Determina K óptimo (método del codo, k=2..8).
4. Entrena KMeans (Spark MLlib) y guarda modelo en data/models/kmeans/.
5. Persiste customer_clusters.parquet con cluster asignado.
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
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def build_features(spark: SparkSession):
    long = spark.read.parquet(str(LONG_PATH))
    reference_date = long.agg(F.max("date")).collect()[0][0]

    features = (
        long.groupBy("customer_id")
        .agg(
            F.countDistinct("transaction_id").alias("frequency"),
            F.count("category_id").alias("total_categories_bought"),
            F.countDistinct("category_id").alias("unique_categories"),
            F.avg(
                F.size(F.collect_list("category_id"))
            ).alias("avg_basket_size"),  # aproximación
            F.datediff(F.lit(reference_date), F.max("date")).alias("recency_days"),
            F.countDistinct("date").alias("active_days"),
        )
    )
    return features


def find_optimal_k(df, assembler, scaler, k_range=range(2, 9)):
    evaluator = ClusteringEvaluator(predictionCol="prediction", metricName="silhouette")
    best_k, best_score = 2, -1.0
    for k in k_range:
        km = KMeans(k=k, seed=42, featuresCol="scaled_features", predictionCol="prediction")
        pipeline_df = scaler.transform(assembler.transform(df))
        model = km.fit(pipeline_df)
        preds = model.transform(pipeline_df)
        score = evaluator.evaluate(preds)
        print(f"  k={k} silhouette={score:.4f} wssse={model.summary.trainingCost:.2f}")
        if score > best_score:
            best_score, best_k = score, k
    return best_k


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    print("Construyendo features de clientes...")
    features = build_features(spark).na.fill(0)

    feature_cols = [
        "frequency", "total_categories_bought", "unique_categories",
        "avg_basket_size", "recency_days", "active_days",
    ]
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_features")
    scaler = StandardScaler(inputCol="raw_features", outputCol="scaled_features", withStd=True, withMean=True)

    assembled = assembler.transform(features)
    scaler_model = scaler.fit(assembled)
    scaled = scaler_model.transform(assembled)

    print("Buscando K óptimo...")
    best_k = find_optimal_k(features, assembler, scaler_model)
    print(f"K óptimo: {best_k}")

    print(f"Entrenando KMeans con k={best_k}...")
    km = KMeans(k=best_k, seed=42, featuresCol="scaled_features", predictionCol="cluster")
    km_model = km.fit(scaled)
    km_model.write().overwrite().save(str(KMEANS_OUT))

    clusters = km_model.transform(scaled).select("customer_id", "cluster", *feature_cols)
    clusters.write.mode("overwrite").parquet(str(CLUSTERS_OUT))
    print(f"Clusters guardados: {clusters.count()} clientes")

    spark.stop()


if __name__ == "__main__":
    main()
