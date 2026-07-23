# Session Deployment Report

Fold dispersion is reported as median [IQR] and min--max. Standard deviation, when retained in JSON, measures between-capture heterogeneity and is not a score range.

## Local Baselines

| Experiment                                                               | Model   | Accuracy median [IQR]; min--max         | F1(mal) median [IQR]; min--max          |        Samples/s |
|--------------------------------------------------------------------------|---------|-----------------------------------------|-----------------------------------------|------------------|
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | RF      | 0.9878 [0.8212, 0.9946]; 0.4275--1.0000 | 0.9863 [0.7739, 0.9907]; 0.3807--1.0000 |  19757.4         |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | XGB     | 0.9592 [0.8078, 0.9914]; 0.4275--0.9946 | 0.9518 [0.7616, 0.9907]; 0.3807--0.9943 | 488692           |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | LGBM    | 0.9606 [0.8069, 0.9934]; 0.4275--0.9985 | 0.9535 [0.7607, 0.9956]; 0.3807--0.9974 | 399214           |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | CART    | 0.9606 [0.8078, 0.9977]; 0.4245--1.0000 | 0.9535 [0.7616, 0.9960]; 0.3764--1.0000 |      1.41281e+06 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | KNN     | 0.9647 [0.8025, 0.9977]; 0.4222--0.9980 | 0.9587 [0.7560, 0.9961]; 0.3755--0.9987 | 151977           |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | RF      | 0.9796 [0.8319, 0.9938]; 0.4275--1.0000 | 0.9774 [0.7845, 0.9893]; 0.3807--1.0000 |  17998.1         |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | XGB     | 0.9592 [0.8078, 0.9796]; 0.4275--0.9985 | 0.9518 [0.7616, 0.9865]; 0.3807--0.9974 | 474262           |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | LGBM    | 0.9592 [0.8069, 0.9868]; 0.4275--0.9985 | 0.9518 [0.7607, 0.9913]; 0.3807--0.9974 | 433716           |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | CART    | 0.9579 [0.8078, 0.9985]; 0.4230--1.0000 | 0.9501 [0.7616, 0.9974]; 0.3738--1.0000 |      1.46213e+06 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | KNN     | 0.8905 [0.8060, 0.9633]; 0.5174--0.9816 | 0.8419 [0.7594, 0.9571]; 0.5284--0.9876 | 212373           |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | RF      | 0.9946 [0.8381, 0.9969]; 0.4275--1.0000 | 0.9939 [0.7908, 0.9947]; 0.3807--1.0000 |  19365.4         |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | XGB     | 0.9592 [0.8078, 0.9776]; 0.4275--0.9985 | 0.9518 [0.7616, 0.9853]; 0.3807--0.9974 | 471358           |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | LGBM    | 0.9579 [0.8069, 0.9907]; 0.4275--0.9934 | 0.9502 [0.7607, 0.9839]; 0.3807--0.9956 | 434686           |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | CART    | 0.9579 [0.8078, 0.9961]; 0.4237--1.0000 | 0.9501 [0.7616, 0.9934]; 0.3751--1.0000 |      1.13459e+06 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | KNN     | 0.8928 [0.7927, 0.9688]; 0.5189--0.9829 | 0.8440 [0.7442, 0.9640]; 0.5292--0.9885 | 206633           |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | RF      | 0.9878 [0.8256, 0.9892]; 0.4275--0.9980 | 0.9812 [0.7778, 0.9860]; 0.3807--0.9987 |  20341.5         |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | XGB     | 0.9606 [0.8078, 0.9901]; 0.4275--0.9985 | 0.9535 [0.7616, 0.9934]; 0.3807--0.9974 | 478710           |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | LGBM    | 0.9592 [0.8069, 0.9921]; 0.4275--0.9985 | 0.9518 [0.7607, 0.9947]; 0.3807--0.9974 | 440253           |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | CART    | 0.9592 [0.8078, 0.9985]; 0.4252--1.0000 | 0.9518 [0.7616, 0.9974]; 0.3778--1.0000 |      1.36963e+06 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | KNN     | 0.8951 [0.7945, 0.9674]; 0.4162--0.9961 | 0.8472 [0.7425, 0.9628]; 0.3710--0.9974 | 176004           |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | RF      | 0.9592 [0.8452, 0.9800]; 0.4230--0.9882 | 0.9519 [0.7986, 0.9668]; 0.3748--0.9921 |  17942.6         |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | XGB     | 0.8774 [0.8016, 0.9552]; 0.4252--0.9928 | 0.8266 [0.7558, 0.9469]; 0.3788--0.9952 | 232815           |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | LGBM    | 0.8720 [0.8060, 0.9511]; 0.4275--0.9875 | 0.8203 [0.7599, 0.9429]; 0.3837--0.9917 | 439326           |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | CART    | 0.9565 [0.8060, 0.9892]; 0.4215--0.9987 | 0.9484 [0.7594, 0.9815]; 0.3742--0.9991 |      1.00965e+06 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | KNN     | 0.9538 [0.8310, 0.9938]; 0.4222--0.9980 | 0.9459 [0.7836, 0.9894]; 0.3755--0.9987 | 140340           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | RF      | 0.9606 [0.8452, 0.9769]; 0.4230--0.9895 | 0.9535 [0.7986, 0.9619]; 0.3748--0.9930 |  17976.1         |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | XGB     | 0.8782 [0.8016, 0.9565]; 0.4260--0.9829 | 0.8275 [0.7558, 0.9486]; 0.3801--0.9887 | 218313           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | LGBM    | 0.8751 [0.8034, 0.9565]; 0.4282--0.9829 | 0.8239 [0.7574, 0.9489]; 0.3841--0.9887 | 427371           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | CART    | 0.9592 [0.8060, 0.9915]; 0.4215--0.9928 | 0.9518 [0.7594, 0.9855]; 0.3742--0.9951 | 946297           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | KNN     | 0.9511 [0.8292, 0.9938]; 0.4230--0.9967 | 0.9427 [0.7818, 0.9894]; 0.3768--0.9978 | 127753           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | RF      | 0.9592 [0.8069, 0.9815]; 0.4237--0.9921 | 0.9519 [0.7607, 0.9693]; 0.3761--0.9947 |  19962.6         |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | XGB     | 0.8782 [0.8016, 0.9565]; 0.4252--0.9809 | 0.8275 [0.7558, 0.9486]; 0.3788--0.9874 | 214901           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | LGBM    | 0.8766 [0.8043, 0.9565]; 0.4260--0.9849 | 0.8257 [0.7582, 0.9489]; 0.3801--0.9900 | 454098           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | CART    | 0.9552 [0.8060, 0.9931]; 0.4215--0.9993 | 0.9467 [0.7594, 0.9881]; 0.3742--0.9996 | 946297           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | KNN     | 0.9538 [0.8310, 0.9838]; 0.4222--0.9849 | 0.9459 [0.7841, 0.9729]; 0.3755--0.9898 |  94218.6         |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | RF      | 0.9592 [0.8069, 0.9800]; 0.4237--0.9928 | 0.9519 [0.7607, 0.9667]; 0.3761--0.9952 |  19972.6         |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | XGB     | 0.8805 [0.8016, 0.9565]; 0.4245--0.9816 | 0.8302 [0.7558, 0.9486]; 0.3775--0.9878 | 205092           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | LGBM    | 0.9565 [0.8060, 0.9838]; 0.4290--0.9921 | 0.9489 [0.7599, 0.9728]; 0.3854--0.9947 | 404964           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | CART    | 0.9565 [0.8327, 0.9907]; 0.4207--0.9987 | 0.9486 [0.7854, 0.9841]; 0.3729--0.9991 | 973529           |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | KNN     | 0.9538 [0.8327, 0.9946]; 0.4222--0.9987 | 0.9459 [0.7854, 0.9908]; 0.3765--0.9991 |  96794.9         |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | RF      | 0.9606 [0.8514, 0.9884]; 0.4230--0.9993 | 0.9535 [0.8051, 0.9805]; 0.3727--0.9996 |  19187.7         |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | XGB     | 0.9592 [0.8078, 0.9829]; 0.4260--0.9846 | 0.9518 [0.7616, 0.9743]; 0.3781--0.9887 | 183384           |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | LGBM    | 0.9606 [0.8078, 0.9985]; 0.4267--1.0000 | 0.9535 [0.7616, 0.9974]; 0.3794--1.0000 | 307250           |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | CART    | 0.9579 [0.8078, 0.9977]; 0.4267--0.9993 | 0.9501 [0.7616, 0.9960]; 0.3794--0.9996 | 906622           |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | KNN     | 0.9538 [0.8238, 0.9938]; 0.4230--0.9987 | 0.9459 [0.7765, 0.9894]; 0.3768--0.9991 |  87139.5         |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | RF      | 0.9606 [0.8443, 0.9923]; 0.4237--0.9928 | 0.9535 [0.7977, 0.9869]; 0.3741--0.9952 |  18246           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | XGB     | 0.9592 [0.8078, 0.9835]; 0.4260--1.0000 | 0.9518 [0.7616, 0.9891]; 0.3781--1.0000 | 177061           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | LGBM    | 0.9606 [0.8069, 0.9985]; 0.4267--1.0000 | 0.9535 [0.7607, 0.9974]; 0.3794--1.0000 | 380290           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | CART    | 0.9579 [0.8078, 0.9977]; 0.5234--0.9993 | 0.9501 [0.7616, 0.9960]; 0.5329--0.9996 | 846436           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | KNN     | 0.9524 [0.8247, 0.9946]; 0.4230--0.9980 | 0.9444 [0.7779, 0.9908]; 0.3768--0.9987 | 118899           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | RF      | 0.9606 [0.8452, 0.9923]; 0.4252--0.9980 | 0.9535 [0.7986, 0.9869]; 0.3767--0.9987 |  17782.7         |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | XGB     | 0.9592 [0.8078, 0.9737]; 0.4260--0.9977 | 0.9518 [0.7616, 0.9827]; 0.3781--0.9960 | 189470           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | LGBM    | 0.9606 [0.8069, 0.9985]; 0.4260--0.9993 | 0.9535 [0.7607, 0.9974]; 0.3781--0.9996 | 354376           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | CART    | 0.9592 [0.8078, 0.9947]; 0.4252--0.9961 | 0.9518 [0.7616, 0.9934]; 0.3767--0.9965 | 844779           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | KNN     | 0.9538 [0.8292, 0.9854]; 0.4237--0.9987 | 0.9459 [0.7823, 0.9755]; 0.3771--0.9991 | 120990           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | RF      | 0.9606 [0.8434, 0.9923]; 0.4237--0.9961 | 0.9535 [0.7968, 0.9869]; 0.3741--0.9974 |  18174.4         |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | XGB     | 0.9592 [0.8078, 0.9737]; 0.4260--0.9869 | 0.9518 [0.7616, 0.9781]; 0.3781--0.9827 | 183751           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | LGBM    | 0.9606 [0.8069, 0.9892]; 0.4260--0.9993 | 0.9535 [0.7607, 0.9819]; 0.3781--0.9996 | 337928           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | CART    | 0.9579 [0.8078, 0.9977]; 0.4252--0.9993 | 0.9501 [0.7616, 0.9960]; 0.3767--0.9996 | 841806           |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | KNN     | 0.9538 [0.8247, 0.9938]; 0.4230--0.9987 | 0.9459 [0.7774, 0.9894]; 0.3768--0.9991 | 116111           |

## Local Held-Out-Family Folds

| Experiment                                                               | Model   |   Fold | Held-out family    |   Test N0 |   Test N1 |   Test prevalence |   Accuracy |   F1(mal) |
|--------------------------------------------------------------------------|---------|--------|--------------------|-----------|-----------|-------------------|------------|-----------|
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8212 |    0.7739 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9946 |    0.9907 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     1      |    1      |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9878 |    0.9863 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9946 |    0.9907 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9914 |    0.9943 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8069 |    0.7607 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9934 |    0.9956 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9977 |    0.996  |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     1      |    1      |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4245 |    0.3764 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8025 |    0.756  |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9977 |    0.9961 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.998  |    0.9987 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9647 |    0.9587 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment       | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4222 |    0.3755 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8319 |    0.7845 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9938 |    0.9893 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9796 |    0.9774 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9796 |    0.9865 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8069 |    0.7607 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9868 |    0.9913 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9579 |    0.9501 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.423  |    0.3738 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.806  |    0.7594 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.8905 |    0.8419 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9816 |    0.9876 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9633 |    0.9571 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_1p0s   | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.5174 |    0.5284 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8381 |    0.7908 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9969 |    0.9947 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9946 |    0.9939 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9776 |    0.9853 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8069 |    0.7607 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9907 |    0.9839 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9934 |    0.9956 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9579 |    0.9502 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9961 |    0.9934 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9579 |    0.9501 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4237 |    0.3751 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.7927 |    0.7442 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.8928 |    0.844  |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9829 |    0.9885 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9688 |    0.964  |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s   | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.5189 |    0.5292 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8256 |    0.7778 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9892 |    0.9812 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.998  |    0.9987 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9878 |    0.986  |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9901 |    0.9934 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8069 |    0.7607 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9921 |    0.9947 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3807 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4252 |    0.3778 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.7945 |    0.7425 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.8951 |    0.8472 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9961 |    0.9974 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9674 |    0.9628 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_30p0s  | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4162 |    0.371  |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8452 |    0.7986 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.98   |    0.9668 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9882 |    0.9921 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9519 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.423  |    0.3748 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8016 |    0.7558 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.8774 |    0.8266 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9928 |    0.9952 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9552 |    0.9469 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4252 |    0.3788 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.806  |    0.7599 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.872  |    0.8203 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9875 |    0.9917 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9511 |    0.9429 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4275 |    0.3837 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.806  |    0.7594 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9892 |    0.9815 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9987 |    0.9991 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9565 |    0.9484 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4215 |    0.3742 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.831  |    0.7836 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9938 |    0.9894 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.998  |    0.9987 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9538 |    0.9459 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment       | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4222 |    0.3755 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8452 |    0.7986 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9769 |    0.9619 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9895 |    0.993  |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.423  |    0.3748 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8016 |    0.7558 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.8782 |    0.8275 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9829 |    0.9887 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9565 |    0.9486 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.426  |    0.3801 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8034 |    0.7574 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.8751 |    0.8239 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9829 |    0.9887 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9565 |    0.9489 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4282 |    0.3841 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.806  |    0.7594 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9915 |    0.9855 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9928 |    0.9951 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4215 |    0.3742 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8292 |    0.7818 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9938 |    0.9894 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9967 |    0.9978 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9511 |    0.9427 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_1p0s   | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.423  |    0.3768 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8069 |    0.7607 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9815 |    0.9693 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9921 |    0.9947 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9519 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4237 |    0.3761 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8016 |    0.7558 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.8782 |    0.8275 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9809 |    0.9874 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9565 |    0.9486 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4252 |    0.3788 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8043 |    0.7582 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.8766 |    0.8257 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9849 |    0.99   |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9565 |    0.9489 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.426  |    0.3801 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.806  |    0.7594 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9931 |    0.9881 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9993 |    0.9996 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9552 |    0.9467 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4215 |    0.3742 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.831  |    0.7841 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9838 |    0.9729 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9849 |    0.9898 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9538 |    0.9459 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s   | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4222 |    0.3755 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8069 |    0.7607 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.98   |    0.9667 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9928 |    0.9952 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9519 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4237 |    0.3761 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8016 |    0.7558 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.8805 |    0.8302 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9816 |    0.9878 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9565 |    0.9486 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4245 |    0.3775 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.806  |    0.7599 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9838 |    0.9728 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9921 |    0.9947 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9565 |    0.9489 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.429  |    0.3854 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8327 |    0.7854 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9907 |    0.9841 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9987 |    0.9991 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9565 |    0.9486 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4207 |    0.3729 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8327 |    0.7854 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9946 |    0.9908 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9987 |    0.9991 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9538 |    0.9459 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_30p0s  | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4222 |    0.3765 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8514 |    0.8051 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9884 |    0.9805 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9993 |    0.9996 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.423  |    0.3727 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9846 |    0.9743 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9829 |    0.9887 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.426  |    0.3781 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     1      |    1      |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4267 |    0.3794 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9977 |    0.996  |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9993 |    0.9996 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9579 |    0.9501 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4267 |    0.3794 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8238 |    0.7765 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9938 |    0.9894 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9987 |    0.9991 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9538 |    0.9459 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment      | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.423  |    0.3768 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8443 |    0.7977 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9923 |    0.9869 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9928 |    0.9952 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4237 |    0.3741 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9835 |    0.9891 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.426  |    0.3781 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8069 |    0.7607 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4267 |    0.3794 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9977 |    0.996  |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9993 |    0.9996 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9579 |    0.9501 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.5234 |    0.5329 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8247 |    0.7779 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9946 |    0.9908 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.998  |    0.9987 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9524 |    0.9444 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_1p0s  | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.423  |    0.3768 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8452 |    0.7986 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9923 |    0.9869 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.998  |    0.9987 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4252 |    0.3767 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9977 |    0.996  |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9737 |    0.9827 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.426  |    0.3781 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8069 |    0.7607 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9985 |    0.9974 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9993 |    0.9996 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.426  |    0.3781 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9961 |    0.9934 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9947 |    0.9965 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4252 |    0.3767 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8292 |    0.7823 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9854 |    0.9755 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9987 |    0.9991 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9538 |    0.9459 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s  | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4237 |    0.3771 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | RF      |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8434 |    0.7968 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | RF      |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9923 |    0.9869 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | RF      |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9961 |    0.9974 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | RF      |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | RF      |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4237 |    0.3741 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | XGB     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | XGB     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9869 |    0.9781 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | XGB     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9737 |    0.9827 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | XGB     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9592 |    0.9518 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | XGB     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.426  |    0.3781 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | LGBM    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8069 |    0.7607 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | LGBM    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9892 |    0.9819 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | LGBM    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9993 |    0.9996 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | LGBM    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9606 |    0.9535 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | LGBM    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.426  |    0.3781 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | CART    |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8078 |    0.7616 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | CART    |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9977 |    0.996  |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | CART    |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9993 |    0.9996 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | CART    |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9579 |    0.9501 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | CART    |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.4252 |    0.3767 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | KNN     |      0 | BitCoinMiner       |       779 |       345 |            0.3069 |     0.8247 |    0.7774 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | KNN     |      1 | Dridex             |       918 |       379 |            0.2922 |     0.9938 |    0.9894 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | KNN     |      2 | Hancitor           |       383 |      1136 |            0.7479 |     0.9987 |    0.9991 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | KNN     |      3 | TrojanDownloader   |       410 |       326 |            0.4429 |     0.9538 |    0.9459 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_30p0s | KNN     |      4 | Website_5.8.88.175 |       333 |       991 |            0.7485 |     0.423  |    0.3768 |

## LLM Baselines

| Experiment                                                                     | Context   | Model   | Accuracy median [IQR]; min--max         | F1(mal) median [IQR]; min--max          |   Invalid |   Latency ms |   Tokens |
|--------------------------------------------------------------------------------|-----------|---------|-----------------------------------------|-----------------------------------------|-----------|--------------|----------|
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    | gpt-5.4 | 0.9273 [0.7636, 0.9636]; 0.7273--0.9636 | 0.8824 [0.7869, 0.9583]; 0.7273--0.9730 |         0 |       2439.6 |   2250.2 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | gpt-5.4 | 0.8000 [0.6909, 0.9636]; 0.5455--0.9818 | 0.7317 [0.2609, 0.9730]; 0.0000--0.9867 |         0 |       1989   |   2438.9 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    | gpt-5.4 | 0.7636 [0.4364, 0.9091]; 0.4182--1.0000 | 0.6977 [0.2791, 0.8571]; 0.2727--1.0000 |         0 |       1977.7 |   4068   |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | gpt-5.4 | 0.6182 [0.4364, 0.6364]; 0.3091--0.8545 | 0.2759 [0.0000, 0.3111]; 0.0000--0.7333 |         0 |       2004.9 |   4216.5 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    | gpt-5.4 | 0.7818 [0.6727, 0.9273]; 0.4000--0.9455 | 0.7143 [0.6897, 0.8824]; 0.1951--0.9189 |         0 |       1932.4 |   4274   |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    | gpt-5.4 | 0.5455 [0.3636, 0.6364]; 0.3455--0.8000 | 0.1000 [0.0000, 0.1860]; 0.0000--0.7027 |         0 |       1858.6 |   4069   |

## LLM Family Coverage Audit

| Experiment                                                                     | Context   |   Families observed |   Malicious samples | Missing expected families   |
|--------------------------------------------------------------------------------|-----------|---------------------|---------------------|-----------------------------|
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    |                   5 |                 135 | none                        |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |                   5 |                 135 | none                        |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    |                   5 |                 135 | none                        |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |                   5 |                 135 | none                        |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    |                   5 |                 135 | none                        |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    |                   5 |                 135 | none                        |

## LLM Held-Out-Family Folds

| Experiment                                                                     | Context   |   Fold | Held-out family    |   Full N0 |   Full N1 |   Evaluated N0 |   Evaluated N1 |   Full prevalence |   Evaluated prevalence |   Accuracy |   F1(mal) |
|--------------------------------------------------------------------------------|-----------|--------|--------------------|-----------|-----------|----------------|----------------|-------------------|------------------------|------------|-----------|
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    |      0 | BitCoinMiner       |       779 |       345 |             35 |             20 |            0.3069 |                 0.3636 |     0.7273 |    0.7273 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    |      1 | Dridex             |       918 |       379 |             40 |             15 |            0.2922 |                 0.2727 |     0.9273 |    0.8824 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    |      2 | Hancitor           |       383 |      1136 |             18 |             37 |            0.7479 |                 0.6727 |     0.7636 |    0.7869 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    |      3 | TrojanDownloader   |       410 |       326 |             30 |             25 |            0.4429 |                 0.4545 |     0.9636 |    0.9583 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    |      4 | Website_5.8.88.175 |       333 |       991 |             17 |             38 |            0.7485 |                 0.6909 |     0.9636 |    0.973  |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      0 | BitCoinMiner       |       779 |       345 |             35 |             20 |            0.3069 |                 0.3636 |     0.6909 |    0.2609 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      1 | Dridex             |       918 |       379 |             40 |             15 |            0.2922 |                 0.2727 |     0.8    |    0.7317 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      2 | Hancitor           |       383 |      1136 |             18 |             37 |            0.7479 |                 0.6727 |     0.9636 |    0.973  |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      3 | TrojanDownloader   |       410 |       326 |             30 |             25 |            0.4429 |                 0.4545 |     0.5455 |    0      |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      4 | Website_5.8.88.175 |       333 |       991 |             17 |             38 |            0.7485 |                 0.6909 |     0.9818 |    0.9867 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    |      0 | BitCoinMiner       |       779 |       345 |             35 |             20 |            0.3069 |                 0.3636 |     0.9091 |    0.8571 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    |      1 | Dridex             |       918 |       379 |             40 |             15 |            0.2922 |                 0.2727 |     1      |    1      |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    |      2 | Hancitor           |       383 |      1136 |             18 |             37 |            0.7479 |                 0.6727 |     0.4364 |    0.2791 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    |      3 | TrojanDownloader   |       410 |       326 |             30 |             25 |            0.4429 |                 0.4545 |     0.7636 |    0.6977 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    |      4 | Website_5.8.88.175 |       333 |       991 |             17 |             38 |            0.7485 |                 0.6909 |     0.4182 |    0.2727 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      0 | BitCoinMiner       |       779 |       345 |             35 |             20 |            0.3069 |                 0.3636 |     0.6364 |    0      |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      1 | Dridex             |       918 |       379 |             40 |             15 |            0.2922 |                 0.2727 |     0.8545 |    0.7333 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      2 | Hancitor           |       383 |      1136 |             18 |             37 |            0.7479 |                 0.6727 |     0.3091 |    0      |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      3 | TrojanDownloader   |       410 |       326 |             30 |             25 |            0.4429 |                 0.4545 |     0.6182 |    0.2759 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    |      4 | Website_5.8.88.175 |       333 |       991 |             17 |             38 |            0.7485 |                 0.6909 |     0.4364 |    0.3111 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    |      0 | BitCoinMiner       |       779 |       345 |             35 |             20 |            0.3069 |                 0.3636 |     0.9455 |    0.9189 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    |      1 | Dridex             |       918 |       379 |             40 |             15 |            0.2922 |                 0.2727 |     0.9273 |    0.8824 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    |      2 | Hancitor           |       383 |      1136 |             18 |             37 |            0.7479 |                 0.6727 |     0.4    |    0.1951 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    |      3 | TrojanDownloader   |       410 |       326 |             30 |             25 |            0.4429 |                 0.4545 |     0.7818 |    0.7143 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    |      4 | Website_5.8.88.175 |       333 |       991 |             17 |             38 |            0.7485 |                 0.6909 |     0.6727 |    0.6897 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    |      0 | BitCoinMiner       |       779 |       345 |             35 |             20 |            0.3069 |                 0.3636 |     0.6364 |    0      |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    |      1 | Dridex             |       918 |       379 |             40 |             15 |            0.2922 |                 0.2727 |     0.8    |    0.7027 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    |      2 | Hancitor           |       383 |      1136 |             18 |             37 |            0.7479 |                 0.6727 |     0.3636 |    0.186  |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    |      3 | TrojanDownloader   |       410 |       326 |             30 |             25 |            0.4429 |                 0.4545 |     0.5455 |    0      |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    |      4 | Website_5.8.88.175 |       333 |       991 |             17 |             38 |            0.7485 |                 0.6909 |     0.3455 |    0.1    |

## LLM Malicious-Family Coverage

| Experiment                                                                     | Context   | Malware family     |   Samples |   Detection rate |   Invalid |
|--------------------------------------------------------------------------------|-----------|--------------------|-----------|------------------|-----------|
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    | BitCoinMiner       |        20 |           1      |         0 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    | Dridex             |        15 |           1      |         0 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    | Hancitor           |        37 |           0.6486 |         0 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    | TrojanDownloader   |        25 |           0.92   |         0 |
| Session_session_sequence_minimal_capture_disjoint_5fold_deployment_memory      | memory    | Website_5.8.88.175 |        38 |           0.9474 |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | BitCoinMiner       |        20 |           0.15   |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | Dridex             |        15 |           1      |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | Hancitor           |        37 |           0.973  |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | TrojanDownloader   |        25 |           0      |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | Website_5.8.88.175 |        38 |           0.9737 |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    | BitCoinMiner       |        20 |           0.75   |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    | Dridex             |        15 |           1      |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    | Hancitor           |        37 |           0.1622 |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    | TrojanDownloader   |        25 |           0.6    |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_deployment_memory      | memory    | Website_5.8.88.175 |        38 |           0.1579 |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | BitCoinMiner       |        20 |           0      |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | Dridex             |        15 |           0.7333 |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | Hancitor           |        37 |           0      |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | TrojanDownloader   |        25 |           0.16   |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_deployment_5p0s_memory  | memory    | Website_5.8.88.175 |        38 |           0.1842 |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    | BitCoinMiner       |        20 |           0.85   |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    | Dridex             |        15 |           1      |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    | Hancitor           |        37 |           0.1081 |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    | TrojanDownloader   |        25 |           0.6    |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_deployment_memory     | memory    | Website_5.8.88.175 |        38 |           0.5263 |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    | BitCoinMiner       |        20 |           0      |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    | Dridex             |        15 |           0.8667 |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    | Hancitor           |        37 |           0.1081 |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    | TrojanDownloader   |        25 |           0      |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_deployment_5p0s_memory | memory    | Website_5.8.88.175 |        38 |           0.0526 |         0 |

## Unsupported Protocol Cells

| Experiment                                                         | Suite         | Fail-closed reason                                                 |
|--------------------------------------------------------------------|---------------|--------------------------------------------------------------------|
| Session_packet_ablation_minimal_capture_disjoint_5fold_deployment  | session_local | Deployment validation fold 0 has support 177/60, below minimum=100 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_deployment  | session_local | Deployment validation fold 0 has support 177/60, below minimum=100 |
| Session_packet_ablation_combined_capture_disjoint_5fold_deployment | session_local | Deployment validation fold 0 has support 177/60, below minimum=100 |

## Paired Differences

| Comparison   | Candidate - reference   | Model   | Sample unit      |   Pairs | Accuracy delta median [IQR]   |
|--------------|-------------------------|---------|------------------|---------|-------------------------------|
| feature_set  | mercury - minimal       | RF      | session_sequence |       5 | -0.0118 [-0.0146, -0.0045]    |
| feature_set  | combined - minimal      | RF      | session_sequence |       5 | -0.0045 [-0.0062, -0.0007]    |
| feature_set  | combined - mercury      | RF      | session_sequence |       5 | 0.0062 [0.0014, 0.0085]       |
| feature_set  | mercury - minimal       | XGB     | session_sequence |       5 | -0.0041 [-0.0062, -0.0023]    |
| feature_set  | combined - minimal      | XGB     | session_sequence |       5 | -0.0015 [-0.0086, 0.0000]     |
| feature_set  | combined - mercury      | XGB     | session_sequence |       5 | 0.0041 [0.0008, 0.0062]       |
| feature_set  | mercury - minimal       | LGBM    | session_sequence |       5 | -0.0059 [-0.0095, -0.0009]    |
| feature_set  | combined - minimal      | LGBM    | session_sequence |       5 | 0.0000 [0.0000, 0.0009]       |
| feature_set  | combined - mercury      | LGBM    | session_sequence |       5 | 0.0095 [0.0018, 0.0125]       |
| feature_set  | mercury - minimal       | CART    | session_sequence |       5 | -0.0030 [-0.0041, -0.0018]    |
| feature_set  | combined - minimal      | CART    | session_sequence |       5 | 0.0000 [-0.0007, 0.0000]      |
| feature_set  | combined - mercury      | CART    | session_sequence |       5 | 0.0018 [0.0014, 0.0053]       |
| feature_set  | mercury - minimal       | KNN     | session_sequence |       5 | 0.0000 [-0.0039, 0.0000]      |
| feature_set  | combined - minimal      | KNN     | session_sequence |       5 | 0.0007 [-0.0039, 0.0008]      |
| feature_set  | combined - mercury      | KNN     | session_sequence |       5 | 0.0000 [0.0000, 0.0007]       |
| feature_set  | mercury - minimal       | RF      | behavior_window  |       5 | -0.0105 [-0.0170, -0.0045]    |
| feature_set  | combined - minimal      | RF      | behavior_window  |       5 | -0.0038 [-0.0072, -0.0015]    |
| feature_set  | combined - mercury      | RF      | behavior_window  |       5 | 0.0008 [0.0000, 0.0033]       |
| feature_set  | mercury - minimal       | XGB     | behavior_window  |       5 | -0.0027 [-0.0062, -0.0015]    |
| feature_set  | combined - minimal      | XGB     | behavior_window  |       5 | 0.0000 [0.0000, 0.0015]       |
| feature_set  | combined - mercury      | XGB     | behavior_window  |       5 | 0.0027 [0.0007, 0.0062]       |
| feature_set  | mercury - minimal       | LGBM    | behavior_window  |       5 | -0.0036 [-0.0039, -0.0027]    |
| feature_set  | combined - minimal      | LGBM    | behavior_window  |       5 | 0.0000 [0.0000, 0.0014]       |
| feature_set  | combined - mercury      | LGBM    | behavior_window  |       5 | 0.0041 [0.0036, 0.0171]       |
| feature_set  | mercury - minimal       | CART    | behavior_window  |       5 | -0.0018 [-0.0069, -0.0015]    |
| feature_set  | combined - minimal      | CART    | behavior_window  |       5 | 0.0000 [-0.0007, 0.0000]      |
| feature_set  | combined - mercury      | CART    | behavior_window  |       5 | 0.0062 [0.0018, 0.0066]       |
| feature_set  | mercury - minimal       | KNN     | behavior_window  |       5 | 0.0151 [-0.0122, 0.0231]      |
| feature_set  | combined - minimal      | KNN     | behavior_window  |       5 | 0.0165 [-0.0109, 0.0187]      |
| feature_set  | combined - mercury      | KNN     | behavior_window  |       5 | 0.0008 [0.0000, 0.0013]       |
| feature_set  | mercury - minimal       | RF      | behavior_window  |       5 | -0.0154 [-0.0311, -0.0079]    |
| feature_set  | combined - minimal      | RF      | behavior_window  |       5 | -0.0023 [-0.0046, -0.0020]    |
| feature_set  | combined - mercury      | RF      | behavior_window  |       5 | 0.0059 [0.0015, 0.0108]       |
| feature_set  | mercury - minimal       | XGB     | behavior_window  |       5 | -0.0027 [-0.0062, -0.0023]    |
| feature_set  | combined - minimal      | XGB     | behavior_window  |       5 | -0.0008 [-0.0015, 0.0000]     |
| feature_set  | combined - mercury      | XGB     | behavior_window  |       5 | 0.0027 [0.0008, 0.0062]       |
| feature_set  | mercury - minimal       | LGBM    | behavior_window  |       5 | -0.0027 [-0.0086, -0.0015]    |
| feature_set  | combined - minimal      | LGBM    | behavior_window  |       5 | 0.0027 [0.0000, 0.0059]       |
| feature_set  | combined - mercury      | LGBM    | behavior_window  |       5 | 0.0041 [0.0027, 0.0145]       |
| feature_set  | mercury - minimal       | CART    | behavior_window  |       5 | -0.0023 [-0.0027, -0.0018]    |
| feature_set  | combined - minimal      | CART    | behavior_window  |       5 | 0.0000 [0.0000, 0.0014]       |
| feature_set  | combined - mercury      | CART    | behavior_window  |       5 | 0.0031 [0.0018, 0.0038]       |
| feature_set  | mercury - minimal       | KNN     | behavior_window  |       5 | 0.0020 [-0.0149, 0.0383]      |
| feature_set  | combined - minimal      | KNN     | behavior_window  |       5 | 0.0158 [-0.0149, 0.0365]      |
| feature_set  | combined - mercury      | KNN     | behavior_window  |       5 | 0.0015 [0.0000, 0.0015]       |
| feature_set  | mercury - minimal       | RF      | behavior_window  |       5 | -0.0093 [-0.0187, -0.0053]    |
| feature_set  | combined - minimal      | RF      | behavior_window  |       5 | -0.0020 [-0.0038, 0.0031]     |
| feature_set  | combined - mercury      | RF      | behavior_window  |       5 | 0.0033 [0.0014, 0.0123]       |
| feature_set  | mercury - minimal       | XGB     | behavior_window  |       5 | -0.0062 [-0.0086, -0.0041]    |
| feature_set  | combined - minimal      | XGB     | behavior_window  |       5 | -0.0015 [-0.0116, -0.0014]    |
| feature_set  | combined - mercury      | XGB     | behavior_window  |       5 | 0.0027 [0.0015, 0.0062]       |
| feature_set  | mercury - minimal       | LGBM    | behavior_window  |       5 | -0.0009 [-0.0027, 0.0000]     |
| feature_set  | combined - minimal      | LGBM    | behavior_window  |       5 | 0.0000 [-0.0015, 0.0014]      |
| feature_set  | combined - mercury      | LGBM    | behavior_window  |       5 | 0.0041 [0.0009, 0.0054]       |
| feature_set  | mercury - minimal       | CART    | behavior_window  |       5 | -0.0027 [-0.0045, -0.0013]    |
| feature_set  | combined - minimal      | CART    | behavior_window  |       5 | -0.0007 [-0.0008, 0.0000]     |
| feature_set  | combined - mercury      | CART    | behavior_window  |       5 | 0.0014 [0.0007, 0.0045]       |
| feature_set  | mercury - minimal       | KNN     | behavior_window  |       5 | 0.0060 [0.0026, 0.0383]       |
| feature_set  | combined - minimal      | KNN     | behavior_window  |       5 | 0.0068 [0.0026, 0.0302]       |
| feature_set  | combined - mercury      | KNN     | behavior_window  |       5 | 0.0000 [-0.0008, 0.0000]      |
| algorithm    | CART - RF               |         | session_sequence |       5 | -0.0030 [-0.0133, 0.0000]     |
| algorithm    | KNN - RF                |         | session_sequence |       5 | -0.0053 [-0.0187, -0.0020]    |
| algorithm    | LGBM - RF               |         | session_sequence |       5 | -0.0066 [-0.0142, 0.0000]     |
| algorithm    | XGB - RF                |         | session_sequence |       5 | -0.0086 [-0.0133, 0.0000]     |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0045 [-0.0217, 0.0000]     |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0184 [-0.0258, -0.0163]    |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | -0.0132 [-0.0204, 0.0000]     |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0204 [-0.0204, 0.0000]     |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0038 [-0.0302, -0.0008]    |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0258 [-0.0454, -0.0171]    |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | -0.0066 [-0.0311, -0.0062]    |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0224 [-0.0302, 0.0000]     |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0023 [-0.0178, 0.0020]     |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0204 [-0.0311, -0.0113]    |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | -0.0059 [-0.0187, 0.0000]     |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0079 [-0.0178, 0.0000]     |
| algorithm    | CART - RF               |         | session_sequence |       5 | -0.0015 [-0.0027, 0.0093]     |
| algorithm    | KNN - RF                |         | session_sequence |       5 | -0.0008 [-0.0054, 0.0099]     |
| algorithm    | LGBM - RF               |         | session_sequence |       5 | -0.0082 [-0.0391, -0.0007]    |
| algorithm    | XGB - RF                |         | session_sequence |       5 | -0.0041 [-0.0436, 0.0023]     |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0014 [-0.0015, 0.0033]     |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | 0.0000 [-0.0095, 0.0072]      |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | -0.0066 [-0.0418, -0.0041]    |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0066 [-0.0436, -0.0041]    |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0009 [-0.0023, 0.0072]     |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0015 [-0.0054, 0.0023]     |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | -0.0027 [-0.0072, -0.0027]    |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0053 [-0.0112, -0.0027]    |
| algorithm    | CART - RF               |         | behavior_window  |       5 | 0.0059 [-0.0027, 0.0108]      |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | 0.0059 [-0.0015, 0.0146]      |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | -0.0007 [-0.0009, 0.0039]     |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0053 [-0.0112, -0.0027]    |
| algorithm    | CART - RF               |         | session_sequence |       5 | 0.0000 [-0.0027, 0.0038]      |
| algorithm    | KNN - RF                |         | session_sequence |       5 | -0.0007 [-0.0068, 0.0000]     |
| algorithm    | LGBM - RF               |         | session_sequence |       5 | 0.0007 [0.0000, 0.0038]       |
| algorithm    | XGB - RF                |         | session_sequence |       5 | -0.0039 [-0.0165, -0.0014]    |
| algorithm    | CART - RF               |         | behavior_window  |       5 | 0.0054 [-0.0027, 0.0066]      |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0008 [-0.0082, 0.0023]     |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0030 [0.0000, 0.0062]       |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0014 [-0.0092, 0.0023]     |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0014 [-0.0033, 0.0000]     |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0068 [-0.0069, -0.0015]    |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0008 [0.0000, 0.0013]       |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0014 [-0.0244, 0.0008]     |
| algorithm    | CART - RF               |         | behavior_window  |       5 | 0.0015 [-0.0027, 0.0033]      |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0008 [-0.0068, 0.0015]     |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0000 [-0.0031, 0.0023]      |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0054 [-0.0224, -0.0014]    |
