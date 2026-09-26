# LAB067 — TRUE H4 VOLUME-MASS LOCATION + POC REJECTION

## Event outcomes

| period       | profile_state        |   N |   mean_ret_1h |   mean_ret_4h |   median_ret_4h |   mean_ret_8h |   mean_ret_12h |   mean_mfe_4h |   mean_mae_4h |   mean_rejected_side_share |   mean_opposite_side_share |
|:-------------|:---------------------|----:|--------------:|--------------:|----------------:|--------------:|---------------:|--------------:|--------------:|---------------------------:|---------------------------:|
| historical   | PROFILE_CONFIRMED    |  37 |   0.00100742  |  -0.00119534  |    -0.00155412  |   0.000354026 |   -0.000196413 |    0.0106424  |    0.00981419 |                   0.382736 |                   0.251858 |
| historical   | PROFILE_PARTIAL      |  62 |   0.00094517  |   0.000462271 |    -0.00218037  |   0.000100866 |    1.1728e-05  |    0.0131217  |    0.0110166  |                   0.290501 |                   0.320324 |
| historical   | PROFILE_CONTRADICTED |  55 |   0.000960002 |  -0.000772194 |     0.000344915 |  -0.00342486  |   -0.00552079  |    0.0104465  |    0.01081    |                   0.203924 |                   0.467428 |
| historical   | PROFILE_OTHER        |  67 |   0.00113641  |  -0.00156502  |    -0.00106481  |  -0.0021966   |   -0.000857089 |    0.0109361  |    0.0118871  |                   0.173955 |                   0.347779 |
| forward_2026 | PROFILE_CONFIRMED    |   4 |  -0.0010945   |  -0.00537989  |    -0.0031442   |  -0.0108331   |   -0.0148825   |    0.00387591 |    0.0090681  |                   0.390402 |                   0.253532 |
| forward_2026 | PROFILE_PARTIAL      |   9 |  -0.000972306 |   0.00341237  |     0.00411383  |   0.00346556  |    0.0042598   |    0.00730815 |    0.00445395 |                   0.290691 |                   0.335944 |
| forward_2026 | PROFILE_CONTRADICTED |   4 |   0.00017106  |  -0.00515979  |    -0.00484706  |  -0.0121545   |   -0.005002    |    0.00396776 |    0.00911807 |                   0.244647 |                   0.406821 |
| forward_2026 | PROFILE_OTHER        |   4 |  -0.00067392  |  -0.0101477   |    -0.00861742  |  -0.00609495  |   -0.0174458   |    0.00537155 |    0.0152092  |                   0.20703  |                   0.281458 |

## Primary checks

{
  "historical": {
    "confirmed_N": 37,
    "contradicted_N": 55,
    "confirmed_mean_ret4_gt_contradicted": false,
    "confirmed_median_ret4_gt_contradicted": false,
    "confirmed_mfe4_gt_contradicted": true,
    "confirmed_mae4_lt_contradicted": true,
    "sample_ok": true
  },
  "forward_2026": {
    "confirmed_N": 4,
    "contradicted_N": 4,
    "confirmed_mean_ret4_gt_contradicted": false,
    "confirmed_median_ret4_gt_contradicted": true,
    "confirmed_mfe4_gt_contradicted": false,
    "confirmed_mae4_lt_contradicted": true,
    "sample_ok": false
  }
}

Primary pattern repeats with adequate sample: **False**

## CF191g overlap

| period       | relation   | profile_state        |   N |        EV_R |          PF |       SumR |   mean_mfe60 |   mean_mae60 |
|:-------------|:-----------|:---------------------|----:|------------:|------------:|-----------:|-------------:|-------------:|
| historical   | SUPPORTIVE | PROFILE_CONFIRMED    |   6 |   0.296512  |   1.58881   |   1.77907  |     1.05406  |     0.672547 |
| historical   | SUPPORTIVE | PROFILE_PARTIAL      |   8 |  -0.114366  |   0.819089  |  -0.914924 |     1.16179  |     0.773406 |
| historical   | SUPPORTIVE | PROFILE_CONTRADICTED |   5 |   0.0335721 |   1.07961   |   0.16786  |     1.16206  |     1.11955  |
| historical   | SUPPORTIVE | PROFILE_OTHER        |  13 |  -0.146804  |   0.728698  |  -1.90846  |     0.654349 |     0.882011 |
| historical   | ADVERSE    | PROFILE_CONFIRMED    |   4 |  -0.680615  |   0.0986231 |  -2.72246  |     0.184868 |     1.91923  |
| historical   | ADVERSE    | PROFILE_PARTIAL      |   7 |   0.599856  |   2.8637    |   4.19899  |     1.32598  |     0.659967 |
| historical   | ADVERSE    | PROFILE_CONTRADICTED |  10 |   0.0117083 |   1.029     |   0.117083 |     1.17303  |     0.554102 |
| historical   | ADVERSE    | PROFILE_OTHER        |   6 |   2.10818   |   7.29524   |  12.6491   |     0.962356 |     0.493146 |
| forward_2026 | SUPPORTIVE | PROFILE_CONFIRMED    |   0 | nan         | nan         | nan        |   nan        |   nan        |
| forward_2026 | SUPPORTIVE | PROFILE_PARTIAL      |   1 |  -1.00855   |   0         |  -1.00855  |     0.556988 |     0.681809 |
| forward_2026 | SUPPORTIVE | PROFILE_CONTRADICTED |   0 | nan         | nan         | nan        |   nan        |   nan        |
| forward_2026 | SUPPORTIVE | PROFILE_OTHER        |   1 |  -1.00828   |   0         |  -1.00828  |     1.34883  |     0.365636 |
| forward_2026 | ADVERSE    | PROFILE_CONFIRMED    |   0 | nan         | nan         | nan        |   nan        |   nan        |
| forward_2026 | ADVERSE    | PROFILE_PARTIAL      |   0 | nan         | nan         | nan        |   nan        |   nan        |
| forward_2026 | ADVERSE    | PROFILE_CONTRADICTED |   0 | nan         | nan         | nan        |   nan        |   nan        |
| forward_2026 | ADVERSE    | PROFILE_OTHER        |   0 | nan         | nan         | nan        |   nan        |   nan        |