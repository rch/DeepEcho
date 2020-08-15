# Benchmarking DeepEcho

**DeepEcho** provides a benchmarking framework that allows users and developers to evaluate the
performance of the different models implemented in DeepEcho on a collection of real world
datasets.

## The Benchmarking process

The DeepEcho Benchmarking process has three main components:

### Datasets

We use the DeepEcho models to model and then sample a large collection of datasets of different
types. The collection of datasets can be found in the [deepecho-data bucket on S3](
http://deepecho-data.s3.amazonaws.com/index.html).

Most notably, many datasets from this collection are Time Series Classification datasets
downloaded from the [timeseriesclassification.com](http://www.timeseriesclassification.com/)
website.

This is the complete list of avilable datasets and some of their characteristics:

| dataset                   | size      |   entities |  data_columns |   max_sequence_len |
|---------------------------|-----------|------------|---------------|--------------------|
| Libras                    | 108.74 KB |        360 |             4 |                 45 |
| AtrialFibrillation        | 111.02 KB |         30 |             4 |                640 |
| BasicMotions              | 196.06 KB |         80 |             8 |                100 |
| ERing                     | 223.5 KB  |        300 |             6 |                 65 |
| RacketSports              | 235.39 KB |        303 |             8 |                 30 |
| Epilepsy                  | 439.75 KB |        275 |             5 |                206 |
| PenDigits                 | 441.87 KB |      10992 |             4 |                  8 |
| JapaneseVowels            | 475.01 KB |        640 |            14 |                 29 |
| StandWalkJump             | 504.3 KB  |         27 |             6 |               2500 |
| FingerMovements           | 764.23 KB |        416 |            30 |                 50 |
| EchoNASDAQ                | 968.61 KB |         19 |             8 |               9401 |
| Handwriting               | 1.38 MB   |       1000 |             5 |                152 |
| UWaveGestureLibrary       | 1.46 MB   |        440 |             5 |                315 |
| NATOPS                    | 1.78 MB   |        360 |            26 |                 51 |
| ArticularyWordRecognition | 1.93 MB   |        575 |            11 |                144 |
| Cricket                   | 3.13 MB   |        180 |             8 |               1197 |
| SelfRegulationSCP2        | 3.84 MB   |        380 |             9 |               1152 |
| LSST                      | 4.2 MB    |       4925 |             8 |                 36 |
| SelfRegulationSCP1        | 4.34 MB   |        561 |             8 |                896 |
| CharacterTrajectories     | 4.97 MB   |       2858 |             5 |                182 |
| HandMovementDirection     | 5.24 MB   |        234 |            12 |                400 |
| EthanolConcentration      | 10.75 MB  |        524 |             5 |               1751 |
| SpokenArabicDigits        | 15.81 MB  |       8798 |            15 |                 93 |
| Heartbeat                 | 28.25 MB  |        409 |            63 |                405 |
| PhonemeSpectra            | 50.42 MB  |       6668 |            13 |                217 |
| MotorImagery              | 70.96 MB  |        378 |            66 |               3000 |
| DuckDuckGeese             | 104.82 MB |        100 |          1347 |                270 |
| PEMS-SF                   | 110.03 MB |        440 |           965 |                144 |
| EigenWorms                | 128.72 MB |        259 |             8 |              17984 |
| InsectWingbeat            | 195.23 MB |      50000 |           202 |                 22 |
| FaceDetection             | 331.16 MB |       9414 |           146 |                 62 |

Further details more details about how the format in which these datasets are stored as well
as how to create yours, please [follow this tutorial](../tutorials/02_DeepEcho_Benchmark_Datasets.ipynb)

### Modeling and Sampling process

During our benchmarking process, we use the DeepEcho models to learn the distributions of
these TimeSeries datasets conditioned on the contextual values associated with each entity
found in the datasets.

Afterwards, we generate synthetic data for each one of these entities, which generates a
dataset of synthetic time series with exactly the same size and aspect as the original data.

### Metrics

After modeling the Time Series datasets and then sampling synthetic data for each one of the
entities found within it, we apply several metrics the evaluate how similar the generated data
is to the real one.

We currently implement four metrics:

* SDMetrics Overall Score: We use [SDMetrics](/sdv-dev/SDMetrics) to generate a report and then
  obtain the overall score from it. A larger score indicates that the synthetic data is higher
  quality.

* Random Forest Detection Score: We fit a TimeSeriesForestClassifier from [sktime](https://sktime.org/)
  with a mixture of real and synthetic time series, indicating it which one is which. Later on
  we try to use the learned model to distinguish real and synthetic data from a held out partition.

* LSTM Detection Score: We train a LSTM classifier to distinguish between real and synthetic time
  series. We evaluate the performance of the classifier on a held out partition and report the
  error rate (i.e. larger values indicate that the synthetic data is higher quality).

* Classification Score: We fit a TimeSeriesForestClassifier from [sktime](https://sktime.org/)
  with real and synthetic time series independently. Afterwards, we use both models to evaluate
  accuracy on real held out data and report the ratio between the performance of the synthetic
  model and the performance of the real model (i.e. larger values indicate that the synthetic
  data is higher quality).

## Benchmark Results

For every release we run the DeepEcho Becnhmark on all our models and datasets to produce a
compehensive table of results. These are the results obtained by the latest version of DeepEcho
using the following configuration:

- Models: `PARModel`
- Datasets: 16
- Maximum Entities: 300

> :warning: **NOTE**: This release was evaluated only on the first 16 datasets from the collection
shown above. The next releases will be evaluated on the complete the datasets.

| model    | dataset                   | fit_time   | sample_time   |   classification_score | classification_score_time   |   detection_score_lstm |   detection_score_rf | detection_score_time   |   sdmetrics_score | sdmetrics_score_time   |
|----------|---------------------------|------------|---------------|------------------------|-----------------------------|------------------------|----------------------|------------------------|-------------------|------------------------|
| PARModel | Libras                    | 00:01:51   | 00:00:22      |              0.147541  | 00:00:19                    |             0.126667   |           0.04       | 00:02:28               |         -0.351999 | 00:00:00               |
| PARModel | AtrialFibrillation        | 00:00:17   | 00:01:03      |            inf         | 00:00:07                    |             0.6        |           0.133333   | 00:32:11               |          0.322153 | 00:00:00               |
| PARModel | BasicMotions              | 00:01:22   | 00:00:29      |              1         | 00:00:12                    |             0.2        |           0.025      | 00:02:10               |         -1.99122  | 00:00:00               |
| PARModel | ERing                     | 00:03:28   | 00:00:51      |              0.493151  | 00:00:29                    |             0.0733333  |           0          | 00:04:40               |         -5.07133  | 00:00:00               |
| PARModel | RacketSports              | 00:05:08   | 00:00:33      |              0.528571  | 00:00:25                    |             0.08       |           0.0266667  | 00:01:33               |         -5.26812  | 00:00:00               |
| PARModel | Epilepsy                  | 00:02:28   | 00:02:28      |              1.01471   | 00:00:38                    |             0.34058    |           0.0362319  | 00:36:31               |         -0.203066 | 00:00:00               |
| PARModel | PenDigits                 | 00:01:55   | 00:00:04      |              0.464789  | 00:00:11                    |             0.0133333  |           0.0666667  | 00:00:20               |         -0.39169  | 00:00:00               |
| PARModel | FingerMovements           | 00:24:08   | 00:03:29      |              0.957447  | 00:01:08                    |             0.00666667 |           0          | 00:04:37               |       -319.162    | 00:00:01               |
| PARModel | Handwriting               | 00:02:47   | 00:01:51      |              0.0740741 | 00:00:43                    |             0          |           0          | 00:22:20               |         -2.18553  | 00:00:00               |
| PARModel | UWaveGestureLibrary       | 00:02:49   | 00:04:36      |              0.380282  | 00:00:55                    |             0.06       |           0.00666667 | 01:26:57               |         -3.0943   | 00:00:00               |
| PARModel | NATOPS                    | 00:20:27   | 00:03:09      |              0.910448  | 00:01:04                    |             0.0133333  |           0.0133333  | 00:04:05               |       -411.605    | 00:00:01               |
| PARModel | ArticularyWordRecognition | 00:07:46   | 00:03:44      |              0.352941  | 00:01:10                    |             0.0866667  |           0          | 00:21:05               |        -23.0411   | 00:00:00               |
| PARModel | Cricket                   | 00:03:33   | 00:24:12      |              0.840909  | 00:01:52                    |             0.0222222  |           0          | 12:28:40               |         -3.95943  | 00:00:01               |

Which contains:

* `model`: The name of the model that has been used.
* `dataset`: The name or path of the dataset.
* `fit_time`: Time, in seconds, that the training lasted.
* `sample_time`: Time, in seconds, that the sampling lasted.

And then, for each one of the metrics used:

* `<metric-name>`: Score obtained by the metric
* `<metric-name>_time`: Time, in seconds, that took to compute the metric.

## Running the Benchmarking

### Install

Before running the benchmarking process, you will have to follow this two steps in order to
install the package:

#### Python installation

In order to use the DeepEcho benchmarking framework you will need to install it using the
following command:

```bash
pip install deepecho-benchmark
```

### Running the Benchmarking using python

The user API for the DeepEcho Benchmarking is the `deepecho.benchmark.run_benchmark` function.

The simplest usage is to execute the `run_benchmark` function without any arguments:

```python
from deepecho.benchmark import run_benchmark

scores = run_benchmark()
```

> :warning: Be aware that that this command takes a lot of time to run on a single machine!

This will execute all the DeepEcho models on all the available datasets and evaluate them
using all the metrics, producing a table similar to the one shown above.

### Benchmark Arguments

The `run_benchmark` function has the following optional arguments:

- `models`: List of models to evaluate, passed as classes or model
  names or as a tuples containing the class and the keyword
  arguments. If not passed, all the available models are used.
- `datasets`: List of datasets in which to evaluate the model. They can be
  passed as dataset instances or as dataset names or paths. If not passed,
  all the available datasets are used.
- `metrics`: Dict of metrics to use for the evaluation. If not passed, all the
  available metrics are used.
- `max_entities`: Max number of entities to load per dataset. If not given, use the
  entire dataset.
- `distributed`: Whether to use `dask` for distributed computing. Defaults to `False`.
- `output_path`: Optionally store the results in a CSV in the given path.


## Kubernetes

Running the complete DeepEcho Benchmarking suite can take a long time when executing against all
our datasts. For this reason, it comes prepared to be executed distributedly over a dask cluster
created using Kubernetes. Check our [documentation](KUBERNETES.md)
on how to run on a kubernetes cluster.