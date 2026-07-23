# Session Balanced Comparison Report

Fold dispersion is reported as median [IQR] and min--max. Standard deviation, when retained in JSON, measures between-capture heterogeneity and is not a score range.

## Local Baselines

| Experiment                                                             | Model   | Accuracy median [IQR]; min--max         | F1(mal) median [IQR]; min--max          |        Samples/s |
|------------------------------------------------------------------------|---------|-----------------------------------------|-----------------------------------------|------------------|
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | RF      | 0.9650 [0.8107, 0.9988]; 0.6554--1.0000 | 0.9637 [0.8409, 0.9988]; 0.4742--1.0000 |  13515.6         |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | XGB     | 0.9638 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9624 [0.8409, 1.0000]; 0.4714--1.0000 | 356621           |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | LGBM    | 0.9661 [0.8107, 0.9988]; 0.6542--1.0000 | 0.9649 [0.8409, 0.9988]; 0.4714--1.0000 | 331210           |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | CART    | 0.9673 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9662 [0.8409, 1.0000]; 0.4714--1.0000 |      1.11105e+06 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | KNN     | 0.9720 [0.8072, 0.9988]; 0.6402--1.0000 | 0.9712 [0.8374, 0.9988]; 0.4615--1.0000 | 105231           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | RF      | 0.9638 [0.8107, 0.9988]; 0.6554--1.0000 | 0.9624 [0.8409, 0.9988]; 0.4742--1.0000 |  14115           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | XGB     | 0.9638 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9624 [0.8409, 1.0000]; 0.4714--1.0000 | 315855           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | LGBM    | 0.9638 [0.8131, 0.9988]; 0.6542--1.0000 | 0.9624 [0.8425, 0.9988]; 0.4714--1.0000 | 327555           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | CART    | 0.8107 [0.6542, 0.9673]; 0.5327--0.9988 | 0.8409 [0.4714, 0.9662]; 0.1228--0.9988 | 899022           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | KNN     | 0.9661 [0.8084, 0.9708]; 0.6495--0.9965 | 0.9650 [0.8376, 0.9700]; 0.4681--0.9965 | 128023           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | RF      | 0.9638 [0.8107, 0.9988]; 0.6554--1.0000 | 0.9624 [0.8409, 0.9988]; 0.4742--1.0000 |  14416.3         |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | XGB     | 0.9661 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9649 [0.8409, 1.0000]; 0.4714--1.0000 | 319913           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | LGBM    | 0.9661 [0.8119, 1.0000]; 0.6542--1.0000 | 0.9649 [0.8417, 1.0000]; 0.4714--1.0000 | 292487           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | CART    | 0.9673 [0.8107, 0.9965]; 0.6542--1.0000 | 0.9662 [0.8409, 0.9965]; 0.4714--1.0000 | 973880           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | KNN     | 0.8107 [0.6519, 0.9650]; 0.5047--0.9953 | 0.8393 [0.4679, 0.9639]; 0.0230--0.9953 | 130238           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | RF      | 0.9661 [0.8107, 0.9988]; 0.6554--1.0000 | 0.9649 [0.8409, 0.9988]; 0.4742--1.0000 |  13619           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | XGB     | 0.9661 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9649 [0.8409, 1.0000]; 0.4714--1.0000 | 315561           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | LGBM    | 0.9661 [0.8143, 0.9988]; 0.6542--1.0000 | 0.9649 [0.8433, 0.9988]; 0.4714--1.0000 | 322942           |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | CART    | 0.9685 [0.8107, 0.9965]; 0.6530--1.0000 | 0.9674 [0.8409, 0.9965]; 0.4725--1.0000 |      1.01984e+06 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | KNN     | 0.9708 [0.8072, 0.9930]; 0.6449--0.9977 | 0.9699 [0.8371, 0.9930]; 0.4629--0.9977 | 165987           |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | RF      | 0.9720 [0.7874, 0.9907]; 0.7617--0.9953 | 0.9713 [0.8046, 0.9907]; 0.7300--0.9953 |   6300.5         |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | XGB     | 0.9626 [0.7734, 0.9907]; 0.7640--0.9953 | 0.9614 [0.8061, 0.9906]; 0.7069--0.9953 | 308558           |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | LGBM    | 0.9346 [0.8014, 0.9860]; 0.7570--0.9930 | 0.9300 [0.8015, 0.9862]; 0.7550--0.9930 | 207060           |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | CART    | 0.9673 [0.7617, 0.9883]; 0.7500--0.9883 | 0.9667 [0.8046, 0.9882]; 0.6748--0.9885 | 658107           |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | KNN     | 0.9556 [0.7944, 0.9556]; 0.7570--0.9860 | 0.9549 [0.7992, 0.9553]; 0.7486--0.9862 | 168457           |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | RF      | 0.9638 [0.8131, 0.9988]; 0.6542--0.9988 | 0.9624 [0.8425, 0.9988]; 0.4714--0.9988 |  12270.3         |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | XGB     | 0.9638 [0.8084, 0.9918]; 0.6589--0.9988 | 0.9624 [0.8389, 0.9919]; 0.4823--0.9988 | 162305           |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | LGBM    | 0.9603 [0.8096, 0.9942]; 0.6554--0.9988 | 0.9589 [0.8397, 0.9942]; 0.4742--0.9988 | 336910           |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | CART    | 0.9626 [0.8540, 0.9942]; 0.6694--0.9977 | 0.9612 [0.8721, 0.9942]; 0.5078--0.9977 | 686862           |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | KNN     | 0.9626 [0.8353, 0.9918]; 0.6519--0.9988 | 0.9613 [0.8577, 0.9918]; 0.4698--0.9988 | 108464           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | RF      | 0.9638 [0.8096, 0.9988]; 0.6530--0.9988 | 0.9624 [0.8394, 0.9988]; 0.4706--0.9988 |  13058.3         |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | XGB     | 0.9614 [0.8084, 0.9907]; 0.6624--0.9988 | 0.9601 [0.8389, 0.9907]; 0.4903--0.9988 | 146488           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | LGBM    | 0.9603 [0.8096, 0.9918]; 0.6542--0.9988 | 0.9589 [0.8397, 0.9919]; 0.4714--0.9988 | 321876           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | CART    | 0.9626 [0.8540, 0.9871]; 0.6682--0.9918 | 0.9612 [0.8721, 0.9870]; 0.5052--0.9918 | 651894           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | KNN     | 0.9626 [0.8376, 0.9930]; 0.6519--0.9977 | 0.9613 [0.8603, 0.9930]; 0.4698--0.9977 |  85117.7         |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | RF      | 0.9638 [0.8143, 0.9988]; 0.6542--0.9988 | 0.9624 [0.8433, 0.9988]; 0.4714--0.9988 |  14526.7         |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | XGB     | 0.9614 [0.8084, 0.9918]; 0.6624--0.9988 | 0.9601 [0.8389, 0.9919]; 0.4903--0.9988 | 124613           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | LGBM    | 0.9603 [0.8096, 0.9942]; 0.6554--0.9988 | 0.9589 [0.8397, 0.9942]; 0.4742--0.9988 | 327762           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | CART    | 0.9626 [0.8072, 0.9883]; 0.6682--0.9977 | 0.9612 [0.8374, 0.9882]; 0.5052--0.9977 | 675228           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | KNN     | 0.9626 [0.8388, 0.9918]; 0.6519--0.9988 | 0.9613 [0.8609, 0.9918]; 0.4698--0.9988 | 103715           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | RF      | 0.9638 [0.8143, 0.9988]; 0.6542--0.9988 | 0.9624 [0.8433, 0.9988]; 0.4714--0.9988 |  14325.6         |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | XGB     | 0.9614 [0.8084, 0.9907]; 0.6565--0.9988 | 0.9601 [0.8389, 0.9907]; 0.4769--0.9988 | 146228           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | LGBM    | 0.9603 [0.8096, 0.9930]; 0.6542--0.9988 | 0.9589 [0.8397, 0.9930]; 0.4714--0.9988 | 340989           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | CART    | 0.9614 [0.8084, 0.9860]; 0.6577--0.9965 | 0.9599 [0.8386, 0.9858]; 0.4814--0.9965 | 656565           |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | KNN     | 0.9626 [0.8388, 0.9942]; 0.6519--0.9988 | 0.9613 [0.8606, 0.9942]; 0.4698--0.9988 |  98549.4         |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | RF      | 0.9159 [0.8435, 0.9790]; 0.8154--0.9953 | 0.9082 [0.8646, 0.9788]; 0.7736--0.9953 |   6176.2         |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | XGB     | 0.9136 [0.8341, 0.9463]; 0.8154--0.9953 | 0.9059 [0.8566, 0.9446]; 0.7812--0.9953 | 244151           |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | LGBM    | 0.9136 [0.8481, 0.9533]; 0.8364--0.9953 | 0.9059 [0.8676, 0.9522]; 0.8148--0.9953 | 228606           |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | CART    | 0.9346 [0.8668, 0.9696]; 0.8411--0.9907 | 0.9307 [0.8607, 0.9693]; 0.8480--0.9907 | 641579           |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | KNN     | 0.9159 [0.8341, 0.9720]; 0.7477--0.9743 | 0.9095 [0.8577, 0.9726]; 0.6932--0.9742 | 168884           |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | RF      | 0.9638 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9624 [0.8409, 1.0000]; 0.4714--1.0000 |  13882.8         |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | XGB     | 0.9638 [0.8107, 0.9918]; 0.6554--1.0000 | 0.9624 [0.8409, 0.9919]; 0.4742--1.0000 | 134361           |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | LGBM    | 0.9638 [0.8107, 0.9977]; 0.6542--1.0000 | 0.9624 [0.8409, 0.9977]; 0.4714--1.0000 | 335275           |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | CART    | 0.9638 [0.8096, 0.9860]; 0.6589--0.9895 | 0.9624 [0.8397, 0.9858]; 0.4823--0.9895 | 628141           |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | KNN     | 0.9626 [0.8341, 0.9988]; 0.6519--0.9988 | 0.9613 [0.8571, 0.9988]; 0.4698--0.9988 |  94118           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | RF      | 0.9638 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9624 [0.8409, 1.0000]; 0.4714--1.0000 |  12248.1         |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | XGB     | 0.9638 [0.8107, 0.9918]; 0.6554--1.0000 | 0.9624 [0.8409, 0.9919]; 0.4742--1.0000 | 131300           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | LGBM    | 0.9638 [0.8119, 0.9977]; 0.6542--1.0000 | 0.9624 [0.8417, 0.9977]; 0.4714--1.0000 | 339676           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | CART    | 0.8107 [0.6600, 0.9638]; 0.5245--0.9930 | 0.8409 [0.4850, 0.9624]; 0.1015--0.9930 | 630999           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | KNN     | 0.9626 [0.8353, 0.9930]; 0.6519--0.9988 | 0.9613 [0.8583, 0.9930]; 0.4698--0.9988 |  86810.7         |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | RF      | 0.9638 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9624 [0.8409, 1.0000]; 0.4714--1.0000 |  14042.7         |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | XGB     | 0.9638 [0.8107, 0.9918]; 0.6554--1.0000 | 0.9624 [0.8409, 0.9919]; 0.4742--1.0000 | 128299           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | LGBM    | 0.9638 [0.8119, 1.0000]; 0.6542--1.0000 | 0.9624 [0.8417, 1.0000]; 0.4714--1.0000 | 244006           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | CART    | 0.9603 [0.8107, 0.9965]; 0.6600--0.9977 | 0.9586 [0.8409, 0.9965]; 0.4850--0.9977 | 595850           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | KNN     | 0.9650 [0.8341, 0.9977]; 0.6519--0.9988 | 0.9638 [0.8571, 0.9977]; 0.4698--0.9988 |  74144           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | RF      | 0.9638 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9624 [0.8409, 1.0000]; 0.4714--1.0000 |  13877.3         |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | XGB     | 0.9638 [0.8107, 0.9918]; 0.6554--1.0000 | 0.9624 [0.8409, 0.9919]; 0.4742--1.0000 | 130386           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | LGBM    | 0.9638 [0.8107, 1.0000]; 0.6542--1.0000 | 0.9624 [0.8409, 1.0000]; 0.4714--1.0000 | 296625           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | CART    | 0.8107 [0.6600, 0.9638]; 0.5257--0.9965 | 0.8409 [0.4850, 0.9624]; 0.1018--0.9965 | 607902           |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | KNN     | 0.9626 [0.8353, 0.9988]; 0.6519--0.9988 | 0.9613 [0.8580, 0.9988]; 0.4698--0.9988 |  90416.6         |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | RF      | 0.9556 [0.8645, 0.9930]; 0.8107--1.0000 | 0.9535 [0.8432, 0.9930]; 0.8409--1.0000 |   6822.2         |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | XGB     | 0.9463 [0.8294, 0.9930]; 0.8178--1.0000 | 0.9432 [0.8440, 0.9930]; 0.7944--1.0000 | 231887           |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | LGBM    | 0.9159 [0.8318, 0.9977]; 0.8318--1.0000 | 0.9082 [0.8548, 0.9977]; 0.7978--1.0000 | 207616           |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | CART    | 0.9626 [0.8551, 0.9953]; 0.7827--0.9977 | 0.9612 [0.8324, 0.9953]; 0.8215--0.9977 | 599324           |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | KNN     | 0.9182 [0.8037, 0.9696]; 0.7874--0.9720 | 0.9123 [0.8359, 0.9703]; 0.7347--0.9720 | 163304           |

## Local Held-Out-Family Folds

| Experiment                                                             | Model   |   Fold | Held-out family    |   Test N0 |   Test N1 |   Test prevalence |   Accuracy |   F1(mal) |
|------------------------------------------------------------------------|---------|--------|--------------------|-----------|-----------|-------------------|------------|-----------|
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.965  |    0.9637 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9661 |    0.9649 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9673 |    0.9662 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8072 |    0.8374 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.972  |    0.9712 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced       | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6402 |    0.4615 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8131 |    0.8425 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.5327 |    0.1228 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9673 |    0.9662 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8084 |    0.8376 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9965 |    0.9965 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9708 |    0.97   |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9661 |    0.965  |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_1p0s   | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6495 |    0.4681 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9661 |    0.9649 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8119 |    0.8417 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9661 |    0.9649 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9965 |    0.9965 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9673 |    0.9662 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8393 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9953 |    0.9953 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.5047 |    0.023  |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.965  |    0.9639 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s   | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6519 |    0.4679 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9661 |    0.9649 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9661 |    0.9649 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8143 |    0.8433 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9661 |    0.9649 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9965 |    0.9965 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9685 |    0.9674 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.653  |    0.4725 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8072 |    0.8371 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.993  |    0.993  |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9977 |    0.9977 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9708 |    0.9699 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_30p0s  | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6449 |    0.4629 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | RF      |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.7617 |    0.8046 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | RF      |      1 | Dridex             |       214 |       214 |               0.5 |     0.9953 |    0.9953 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | RF      |      2 | Hancitor           |       214 |       214 |               0.5 |     0.9907 |    0.9907 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | RF      |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.972  |    0.9713 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | RF      |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.7874 |    0.73   |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | XGB     |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.764  |    0.8061 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | XGB     |      1 | Dridex             |       214 |       214 |               0.5 |     0.9907 |    0.9906 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | XGB     |      2 | Hancitor           |       214 |       214 |               0.5 |     0.9953 |    0.9953 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | XGB     |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9626 |    0.9614 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | XGB     |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.7734 |    0.7069 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | LGBM    |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.757  |    0.8015 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | LGBM    |      1 | Dridex             |       214 |       214 |               0.5 |     0.993  |    0.993  |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | LGBM    |      2 | Hancitor           |       214 |       214 |               0.5 |     0.986  |    0.9862 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | LGBM    |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9346 |    0.93   |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | LGBM    |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.8014 |    0.755  |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | CART    |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.7617 |    0.8046 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | CART    |      1 | Dridex             |       214 |       214 |               0.5 |     0.9883 |    0.9882 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | CART    |      2 | Hancitor           |       214 |       214 |               0.5 |     0.9883 |    0.9885 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | CART    |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9673 |    0.9667 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | CART    |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.75   |    0.6748 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | KNN     |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.757  |    0.7992 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | KNN     |      1 | Dridex             |       214 |       214 |               0.5 |     0.9556 |    0.9553 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | KNN     |      2 | Hancitor           |       214 |       214 |               0.5 |     0.986  |    0.9862 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | KNN     |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9556 |    0.9549 |
| Session_packet_ablation_minimal_capture_disjoint_5fold_balanced        | KNN     |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.7944 |    0.7486 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8131 |    0.8425 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8084 |    0.8389 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9919 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6589 |    0.4823 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8096 |    0.8397 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9942 |    0.9942 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9603 |    0.9589 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.854  |    0.8721 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9942 |    0.9942 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9977 |    0.9977 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9612 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6694 |    0.5078 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8353 |    0.8577 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9918 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9613 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced       | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6519 |    0.4698 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8096 |    0.8394 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.653  |    0.4706 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8084 |    0.8389 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9907 |    0.9907 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9614 |    0.9601 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6624 |    0.4903 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8096 |    0.8397 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9919 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9603 |    0.9589 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.854  |    0.8721 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9918 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9871 |    0.987  |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9612 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6682 |    0.5052 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8376 |    0.8603 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.993  |    0.993  |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9977 |    0.9977 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9613 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_1p0s   | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6519 |    0.4698 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8143 |    0.8433 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8084 |    0.8389 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9919 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9614 |    0.9601 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6624 |    0.4903 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8096 |    0.8397 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9942 |    0.9942 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9603 |    0.9589 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8072 |    0.8374 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9977 |    0.9977 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9883 |    0.9882 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9612 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6682 |    0.5052 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8388 |    0.8609 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9918 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9613 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s   | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6519 |    0.4698 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8143 |    0.8433 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8084 |    0.8389 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9907 |    0.9907 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9614 |    0.9601 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6565 |    0.4769 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8096 |    0.8397 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     0.993  |    0.993  |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9603 |    0.9589 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8084 |    0.8386 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9965 |    0.9965 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.986  |    0.9858 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9614 |    0.9599 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6577 |    0.4814 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8388 |    0.8606 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9942 |    0.9942 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9613 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_30p0s  | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6519 |    0.4698 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | RF      |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.8435 |    0.8646 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | RF      |      1 | Dridex             |       214 |       214 |               0.5 |     0.9953 |    0.9953 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | RF      |      2 | Hancitor           |       214 |       214 |               0.5 |     0.979  |    0.9788 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | RF      |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9159 |    0.9082 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | RF      |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.8154 |    0.7736 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | XGB     |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.8341 |    0.8566 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | XGB     |      1 | Dridex             |       214 |       214 |               0.5 |     0.9953 |    0.9953 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | XGB     |      2 | Hancitor           |       214 |       214 |               0.5 |     0.9463 |    0.9446 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | XGB     |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9136 |    0.9059 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | XGB     |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.8154 |    0.7812 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | LGBM    |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.8481 |    0.8676 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | LGBM    |      1 | Dridex             |       214 |       214 |               0.5 |     0.9953 |    0.9953 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | LGBM    |      2 | Hancitor           |       214 |       214 |               0.5 |     0.9533 |    0.9522 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | LGBM    |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9136 |    0.9059 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | LGBM    |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.8364 |    0.8148 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | CART    |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.8411 |    0.8607 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | CART    |      1 | Dridex             |       214 |       214 |               0.5 |     0.9907 |    0.9907 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | CART    |      2 | Hancitor           |       214 |       214 |               0.5 |     0.9696 |    0.9693 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | CART    |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9346 |    0.9307 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | CART    |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.8668 |    0.848  |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | KNN     |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.8341 |    0.8577 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | KNN     |      1 | Dridex             |       214 |       214 |               0.5 |     0.972  |    0.9726 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | KNN     |      2 | Hancitor           |       214 |       214 |               0.5 |     0.9743 |    0.9742 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | KNN     |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9159 |    0.9095 |
| Session_packet_ablation_mercury_capture_disjoint_5fold_balanced        | KNN     |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.7477 |    0.6932 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9919 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9977 |    0.9977 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8096 |    0.8397 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9895 |    0.9895 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.986  |    0.9858 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6589 |    0.4823 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8341 |    0.8571 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9613 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced      | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6519 |    0.4698 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9919 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8119 |    0.8417 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9977 |    0.9977 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.993  |    0.993  |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.5245 |    0.1015 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.66   |    0.485  |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8353 |    0.8583 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.993  |    0.993  |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9613 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_1p0s  | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6519 |    0.4698 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9919 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8119 |    0.8417 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9965 |    0.9965 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9977 |    0.9977 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9603 |    0.9586 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.66   |    0.485  |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8341 |    0.8571 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9977 |    0.9977 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.965  |    0.9638 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s  | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6519 |    0.4698 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | RF      |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | RF      |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | RF      |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | RF      |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | RF      |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | XGB     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | XGB     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9918 |    0.9919 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | XGB     |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | XGB     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | XGB     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6554 |    0.4742 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | LGBM    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | LGBM    |      1 | Dridex             |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | LGBM    |      2 | Hancitor           |       428 |       428 |               0.5 |     1      |    1      |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | LGBM    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | LGBM    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6542 |    0.4714 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | CART    |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8107 |    0.8409 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | CART    |      1 | Dridex             |       428 |       428 |               0.5 |     0.9965 |    0.9965 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | CART    |      2 | Hancitor           |       428 |       428 |               0.5 |     0.5257 |    0.1018 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | CART    |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9638 |    0.9624 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | CART    |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.66   |    0.485  |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | KNN     |      0 | BitCoinMiner       |       428 |       428 |               0.5 |     0.8353 |    0.858  |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | KNN     |      1 | Dridex             |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | KNN     |      2 | Hancitor           |       428 |       428 |               0.5 |     0.9988 |    0.9988 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | KNN     |      3 | TrojanDownloader   |       428 |       428 |               0.5 |     0.9626 |    0.9613 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_30p0s | KNN     |      4 | Website_5.8.88.175 |       428 |       428 |               0.5 |     0.6519 |    0.4698 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | RF      |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.8107 |    0.8409 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | RF      |      1 | Dridex             |       214 |       214 |               0.5 |     1      |    1      |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | RF      |      2 | Hancitor           |       214 |       214 |               0.5 |     0.993  |    0.993  |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | RF      |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9556 |    0.9535 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | RF      |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.8645 |    0.8432 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | XGB     |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.8178 |    0.844  |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | XGB     |      1 | Dridex             |       214 |       214 |               0.5 |     1      |    1      |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | XGB     |      2 | Hancitor           |       214 |       214 |               0.5 |     0.993  |    0.993  |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | XGB     |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9463 |    0.9432 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | XGB     |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.8294 |    0.7944 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | LGBM    |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.8318 |    0.8548 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | LGBM    |      1 | Dridex             |       214 |       214 |               0.5 |     1      |    1      |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | LGBM    |      2 | Hancitor           |       214 |       214 |               0.5 |     0.9977 |    0.9977 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | LGBM    |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9159 |    0.9082 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | LGBM    |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.8318 |    0.7978 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | CART    |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.7827 |    0.8215 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | CART    |      1 | Dridex             |       214 |       214 |               0.5 |     0.9977 |    0.9977 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | CART    |      2 | Hancitor           |       214 |       214 |               0.5 |     0.9953 |    0.9953 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | CART    |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9626 |    0.9612 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | CART    |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.8551 |    0.8324 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | KNN     |      0 | BitCoinMiner       |       214 |       214 |               0.5 |     0.8037 |    0.8359 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | KNN     |      1 | Dridex             |       214 |       214 |               0.5 |     0.9696 |    0.9703 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | KNN     |      2 | Hancitor           |       214 |       214 |               0.5 |     0.972  |    0.972  |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | KNN     |      3 | TrojanDownloader   |       214 |       214 |               0.5 |     0.9182 |    0.9123 |
| Session_packet_ablation_combined_capture_disjoint_5fold_balanced       | KNN     |      4 | Website_5.8.88.175 |       214 |       214 |               0.5 |     0.7874 |    0.7347 |

## LLM Baselines

| Experiment                                                                   | Context   | Model   | Accuracy median [IQR]; min--max         | F1(mal) median [IQR]; min--max          |   Invalid |   Latency ms |   Tokens |
|------------------------------------------------------------------------------|-----------|---------|-----------------------------------------|-----------------------------------------|-----------|--------------|----------|
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    | gpt-5.4 | 0.5865 [0.5481, 0.9231]; 0.5000--0.9423 | 0.4946 [0.2951, 0.9167]; 0.0000--0.9388 |         0 |       1908.9 |   2607.6 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | gpt-5.4 | 0.6827 [0.4904, 0.7885]; 0.4615--0.8942 | 0.6972 [0.2535, 0.7925]; 0.0000--0.8842 |         0 |       1813.3 |   2783.5 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    | gpt-5.4 | 0.7788 [0.7500, 0.7885]; 0.6923--0.9808 | 0.7229 [0.6863, 0.7442]; 0.6667--0.9804 |         0 |       1798.9 |   4146.7 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | gpt-5.4 | 0.5962 [0.5673, 0.7308]; 0.5288--0.8462 | 0.6182 [0.5243, 0.6744]; 0.5055--0.8367 |         0 |       1875.2 |   4289.2 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    | gpt-5.4 | 0.8269 [0.8269, 0.8558]; 0.7692--1.0000 | 0.8352 [0.8085, 0.8393]; 0.7000--1.0000 |         0 |       1849.9 |   4295.6 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    | gpt-5.4 | 0.7019 [0.6538, 0.7596]; 0.4904--0.9615 | 0.7126 [0.6538, 0.7395]; 0.4045--0.9630 |         0 |       1822.9 |   4129.6 |

## LLM Family Coverage Audit

| Experiment                                                                   | Context   |   Families observed |   Malicious samples | Missing expected families   |
|------------------------------------------------------------------------------|-----------|---------------------|---------------------|-----------------------------|
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    |                   5 |                 260 | none                        |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |                   5 |                 260 | none                        |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    |                   5 |                 260 | none                        |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |                   5 |                 260 | none                        |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    |                   5 |                 260 | none                        |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    |                   5 |                 260 | none                        |

## LLM Held-Out-Family Folds

| Experiment                                                                   | Context   |   Fold | Held-out family    |   Full N0 |   Full N1 |   Evaluated N0 |   Evaluated N1 |   Full prevalence |   Evaluated prevalence |   Accuracy |   F1(mal) |
|------------------------------------------------------------------------------|-----------|--------|--------------------|-----------|-----------|----------------|----------------|-------------------|------------------------|------------|-----------|
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    |      0 | BitCoinMiner       |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.5481 |    0.4946 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    |      1 | Dridex             |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.9231 |    0.9167 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    |      2 | Hancitor           |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.5    |    0      |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    |      3 | TrojanDownloader   |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.9423 |    0.9388 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    |      4 | Website_5.8.88.175 |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.5865 |    0.2951 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      0 | BitCoinMiner       |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.6827 |    0.6972 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      1 | Dridex             |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.7885 |    0.7925 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      2 | Hancitor           |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.4615 |    0      |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      3 | TrojanDownloader   |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.8942 |    0.8842 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      4 | Website_5.8.88.175 |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.4904 |    0.2535 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    |      0 | BitCoinMiner       |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.7885 |    0.7442 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    |      1 | Dridex             |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.6923 |    0.6863 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    |      2 | Hancitor           |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.9808 |    0.9804 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    |      3 | TrojanDownloader   |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.7788 |    0.7229 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    |      4 | Website_5.8.88.175 |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.75   |    0.6667 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      0 | BitCoinMiner       |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.5288 |    0.5243 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      1 | Dridex             |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.5962 |    0.6182 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      2 | Hancitor           |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.8462 |    0.8367 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      3 | TrojanDownloader   |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.7308 |    0.6744 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    |      4 | Website_5.8.88.175 |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.5673 |    0.5055 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    |      0 | BitCoinMiner       |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.8269 |    0.8393 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    |      1 | Dridex             |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.8269 |    0.8085 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    |      2 | Hancitor           |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     1      |    1      |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    |      3 | TrojanDownloader   |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.8558 |    0.8352 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    |      4 | Website_5.8.88.175 |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.7692 |    0.7    |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    |      0 | BitCoinMiner       |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.7019 |    0.7395 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    |      1 | Dridex             |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.6538 |    0.6538 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    |      2 | Hancitor           |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.9615 |    0.963  |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    |      3 | TrojanDownloader   |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.7596 |    0.7126 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    |      4 | Website_5.8.88.175 |       428 |       428 |             52 |             52 |               0.5 |                    0.5 |     0.4904 |    0.4045 |

## LLM Malicious-Family Coverage

| Experiment                                                                   | Context   | Malware family     |   Samples |   Detection rate |   Invalid |
|------------------------------------------------------------------------------|-----------|--------------------|-----------|------------------|-----------|
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    | BitCoinMiner       |        52 |           0.4423 |         0 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    | Dridex             |        52 |           0.8462 |         0 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    | Hancitor           |        52 |           0      |         0 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    | TrojanDownloader   |        52 |           0.8846 |         0 |
| Session_session_sequence_minimal_capture_disjoint_5fold_balanced_memory      | memory    | Website_5.8.88.175 |        52 |           0.1731 |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | BitCoinMiner       |        52 |           0.7308 |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | Dridex             |        52 |           0.8077 |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | Hancitor           |        52 |           0      |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | TrojanDownloader   |        52 |           0.8077 |         0 |
| Session_behavior_window_minimal_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | Website_5.8.88.175 |        52 |           0.1731 |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    | BitCoinMiner       |        52 |           0.6154 |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    | Dridex             |        52 |           0.6731 |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    | Hancitor           |        52 |           0.9615 |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    | TrojanDownloader   |        52 |           0.5769 |         0 |
| Session_session_sequence_mercury_capture_disjoint_5fold_balanced_memory      | memory    | Website_5.8.88.175 |        52 |           0.5    |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | BitCoinMiner       |        52 |           0.5192 |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | Dridex             |        52 |           0.6538 |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | Hancitor           |        52 |           0.7885 |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | TrojanDownloader   |        52 |           0.5577 |         0 |
| Session_behavior_window_mercury_capture_disjoint_5fold_balanced_5p0s_memory  | memory    | Website_5.8.88.175 |        52 |           0.4423 |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    | BitCoinMiner       |        52 |           0.9038 |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    | Dridex             |        52 |           0.7308 |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    | Hancitor           |        52 |           1      |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    | TrojanDownloader   |        52 |           0.7308 |         0 |
| Session_session_sequence_combined_capture_disjoint_5fold_balanced_memory     | memory    | Website_5.8.88.175 |        52 |           0.5385 |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    | BitCoinMiner       |        52 |           0.8462 |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    | Dridex             |        52 |           0.6538 |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    | Hancitor           |        52 |           1      |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    | TrojanDownloader   |        52 |           0.5962 |         0 |
| Session_behavior_window_combined_capture_disjoint_5fold_balanced_5p0s_memory | memory    | Website_5.8.88.175 |        52 |           0.3462 |         0 |

## Paired Differences

| Comparison   | Candidate - reference   | Model   | Sample unit      |   Pairs | Accuracy delta median [IQR]   |
|--------------|-------------------------|---------|------------------|---------|-------------------------------|
| feature_set  | mercury - minimal       | RF      | session_sequence |       5 | -0.0012 [-0.0012, 0.0000]     |
| feature_set  | combined - minimal      | RF      | session_sequence |       5 | 0.0000 [-0.0012, 0.0000]      |
| feature_set  | combined - mercury      | RF      | session_sequence |       5 | 0.0000 [0.0000, 0.0012]       |
| feature_set  | mercury - minimal       | XGB     | session_sequence |       5 | -0.0012 [-0.0023, 0.0000]     |
| feature_set  | combined - minimal      | XGB     | session_sequence |       5 | 0.0000 [0.0000, 0.0000]       |
| feature_set  | combined - mercury      | XGB     | session_sequence |       5 | 0.0000 [0.0000, 0.0012]       |
| feature_set  | mercury - minimal       | LGBM    | session_sequence |       5 | -0.0012 [-0.0047, -0.0012]    |
| feature_set  | combined - minimal      | LGBM    | session_sequence |       5 | 0.0000 [-0.0012, 0.0000]      |
| feature_set  | combined - mercury      | LGBM    | session_sequence |       5 | 0.0012 [0.0012, 0.0035]       |
| feature_set  | mercury - minimal       | CART    | session_sequence |       5 | -0.0023 [-0.0047, 0.0152]     |
| feature_set  | combined - minimal      | CART    | session_sequence |       5 | -0.0035 [-0.0105, -0.0012]    |
| feature_set  | combined - mercury      | CART    | session_sequence |       5 | -0.0105 [-0.0117, -0.0047]    |
| feature_set  | mercury - minimal       | KNN     | session_sequence |       5 | -0.0012 [-0.0070, 0.0117]     |
| feature_set  | combined - minimal      | KNN     | session_sequence |       5 | 0.0000 [-0.0012, 0.0117]      |
| feature_set  | combined - mercury      | KNN     | session_sequence |       5 | 0.0000 [0.0000, 0.0000]       |
| feature_set  | mercury - minimal       | RF      | behavior_window  |       5 | -0.0012 [-0.0012, 0.0000]     |
| feature_set  | combined - minimal      | RF      | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| feature_set  | combined - mercury      | RF      | behavior_window  |       5 | 0.0012 [0.0012, 0.0012]       |
| feature_set  | mercury - minimal       | XGB     | behavior_window  |       5 | -0.0023 [-0.0023, -0.0012]    |
| feature_set  | combined - minimal      | XGB     | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| feature_set  | combined - mercury      | XGB     | behavior_window  |       5 | 0.0012 [0.0012, 0.0023]       |
| feature_set  | mercury - minimal       | LGBM    | behavior_window  |       5 | -0.0035 [-0.0035, -0.0012]    |
| feature_set  | combined - minimal      | LGBM    | behavior_window  |       5 | 0.0000 [-0.0012, 0.0000]      |
| feature_set  | combined - mercury      | LGBM    | behavior_window  |       5 | 0.0023 [0.0012, 0.0035]       |
| feature_set  | mercury - minimal       | CART    | behavior_window  |       5 | 0.0140 [-0.0047, 0.0432]      |
| feature_set  | combined - minimal      | CART    | behavior_window  |       5 | -0.0035 [-0.0058, 0.0000]     |
| feature_set  | combined - mercury      | CART    | behavior_window  |       5 | -0.0082 [-0.0432, 0.0012]     |
| feature_set  | mercury - minimal       | KNN     | behavior_window  |       5 | 0.0023 [-0.0035, 0.0269]      |
| feature_set  | combined - minimal      | KNN     | behavior_window  |       5 | 0.0023 [0.0023, 0.0222]       |
| feature_set  | combined - mercury      | KNN     | behavior_window  |       5 | 0.0000 [-0.0023, 0.0000]      |
| feature_set  | mercury - minimal       | RF      | behavior_window  |       5 | 0.0000 [-0.0012, 0.0000]      |
| feature_set  | combined - minimal      | RF      | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| feature_set  | combined - mercury      | RF      | behavior_window  |       5 | 0.0000 [0.0000, 0.0012]       |
| feature_set  | mercury - minimal       | XGB     | behavior_window  |       5 | -0.0023 [-0.0047, -0.0012]    |
| feature_set  | combined - minimal      | XGB     | behavior_window  |       5 | 0.0000 [-0.0023, 0.0000]      |
| feature_set  | combined - mercury      | XGB     | behavior_window  |       5 | 0.0012 [0.0000, 0.0023]       |
| feature_set  | mercury - minimal       | LGBM    | behavior_window  |       5 | -0.0023 [-0.0058, -0.0012]    |
| feature_set  | combined - minimal      | LGBM    | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| feature_set  | combined - mercury      | LGBM    | behavior_window  |       5 | 0.0023 [0.0012, 0.0035]       |
| feature_set  | mercury - minimal       | CART    | behavior_window  |       5 | -0.0035 [-0.0047, 0.0012]     |
| feature_set  | combined - minimal      | CART    | behavior_window  |       5 | 0.0000 [-0.0023, 0.0000]      |
| feature_set  | combined - mercury      | CART    | behavior_window  |       5 | -0.0012 [-0.0023, 0.0035]     |
| feature_set  | mercury - minimal       | KNN     | behavior_window  |       5 | 0.0000 [-0.0023, 0.0280]      |
| feature_set  | combined - minimal      | KNN     | behavior_window  |       5 | 0.0023 [0.0000, 0.0234]       |
| feature_set  | combined - mercury      | KNN     | behavior_window  |       5 | 0.0000 [0.0000, 0.0023]       |
| feature_set  | mercury - minimal       | RF      | behavior_window  |       5 | -0.0012 [-0.0012, 0.0000]     |
| feature_set  | combined - minimal      | RF      | behavior_window  |       5 | 0.0000 [-0.0012, 0.0000]      |
| feature_set  | combined - mercury      | RF      | behavior_window  |       5 | 0.0000 [0.0000, 0.0012]       |
| feature_set  | mercury - minimal       | XGB     | behavior_window  |       5 | -0.0023 [-0.0047, -0.0012]    |
| feature_set  | combined - minimal      | XGB     | behavior_window  |       5 | 0.0000 [-0.0023, 0.0000]      |
| feature_set  | combined - mercury      | XGB     | behavior_window  |       5 | 0.0012 [0.0012, 0.0023]       |
| feature_set  | mercury - minimal       | LGBM    | behavior_window  |       5 | -0.0047 [-0.0058, -0.0012]    |
| feature_set  | combined - minimal      | LGBM    | behavior_window  |       5 | 0.0000 [-0.0023, 0.0000]      |
| feature_set  | combined - mercury      | LGBM    | behavior_window  |       5 | 0.0012 [0.0012, 0.0035]       |
| feature_set  | mercury - minimal       | CART    | behavior_window  |       5 | -0.0023 [-0.0070, 0.0000]     |
| feature_set  | combined - minimal      | CART    | behavior_window  |       5 | 0.0000 [-0.0047, 0.0000]      |
| feature_set  | combined - mercury      | CART    | behavior_window  |       5 | 0.0023 [0.0000, 0.0023]       |
| feature_set  | mercury - minimal       | KNN     | behavior_window  |       5 | 0.0012 [0.0012, 0.0070]       |
| feature_set  | combined - minimal      | KNN     | behavior_window  |       5 | 0.0058 [0.0012, 0.0070]       |
| feature_set  | combined - mercury      | KNN     | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| feature_set  | mercury - minimal       | RF      | packet_ablation  |       5 | 0.0000 [-0.0117, 0.0280]      |
| feature_set  | combined - minimal      | RF      | packet_ablation  |       5 | 0.0047 [0.0023, 0.0491]       |
| feature_set  | combined - mercury      | RF      | packet_ablation  |       5 | 0.0140 [0.0047, 0.0397]       |
| feature_set  | mercury - minimal       | XGB     | packet_ablation  |       5 | 0.0047 [-0.0491, 0.0421]      |
| feature_set  | combined - minimal      | XGB     | packet_ablation  |       5 | 0.0093 [-0.0023, 0.0537]      |
| feature_set  | combined - mercury      | XGB     | packet_ablation  |       5 | 0.0140 [0.0047, 0.0327]       |
| feature_set  | mercury - minimal       | LGBM    | packet_ablation  |       5 | 0.0023 [-0.0210, 0.0350]      |
| feature_set  | combined - minimal      | LGBM    | packet_ablation  |       5 | 0.0117 [0.0070, 0.0304]       |
| feature_set  | combined - mercury      | LGBM    | packet_ablation  |       5 | 0.0023 [-0.0047, 0.0047]      |
| feature_set  | mercury - minimal       | CART    | packet_ablation  |       5 | 0.0023 [-0.0187, 0.0794]      |
| feature_set  | combined - minimal      | CART    | packet_ablation  |       5 | 0.0093 [0.0070, 0.0210]       |
| feature_set  | combined - mercury      | CART    | packet_ablation  |       5 | 0.0070 [-0.0117, 0.0257]      |
| feature_set  | mercury - minimal       | KNN     | packet_ablation  |       5 | -0.0117 [-0.0397, 0.0164]     |
| feature_set  | combined - minimal      | KNN     | packet_ablation  |       5 | -0.0070 [-0.0140, 0.0140]     |
| feature_set  | combined - mercury      | KNN     | packet_ablation  |       5 | -0.0023 [-0.0023, 0.0023]     |
| algorithm    | CART - RF               |         | session_sequence |       5 | 0.0000 [0.0000, 0.0012]       |
| algorithm    | KNN - RF                |         | session_sequence |       5 | 0.0000 [-0.0035, 0.0000]      |
| algorithm    | LGBM - RF               |         | session_sequence |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | XGB - RF                |         | session_sequence |       5 | 0.0000 [-0.0012, 0.0000]      |
| algorithm    | CART - RF               |         | behavior_window  |       5 | 0.0000 [-0.0012, 0.0000]      |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0023 [-0.0058, -0.0023]    |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | CART - RF               |         | behavior_window  |       5 | 0.0000 [-0.0012, 0.0000]      |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0035 [-0.0035, 0.0000]     |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0012 [0.0000, 0.0012]       |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0012]       |
| algorithm    | CART - RF               |         | behavior_window  |       5 | 0.0000 [-0.0023, 0.0000]      |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0035 [-0.0058, -0.0023]    |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | CART - RF               |         | packet_ablation  |       5 | -0.0047 [-0.0070, -0.0023]    |
| algorithm    | KNN - RF                |         | packet_ablation  |       5 | -0.0047 [-0.0164, -0.0047]    |
| algorithm    | LGBM - RF               |         | packet_ablation  |       5 | -0.0047 [-0.0047, -0.0023]    |
| algorithm    | XGB - RF                |         | packet_ablation  |       5 | -0.0047 [-0.0093, 0.0023]     |
| algorithm    | CART - RF               |         | session_sequence |       5 | -0.0012 [-0.0012, 0.0152]     |
| algorithm    | KNN - RF                |         | session_sequence |       5 | -0.0012 [-0.0023, 0.0000]     |
| algorithm    | LGBM - RF               |         | session_sequence |       5 | -0.0035 [-0.0035, 0.0000]     |
| algorithm    | XGB - RF                |         | session_sequence |       5 | 0.0000 [-0.0047, 0.0000]      |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0012 [-0.0070, 0.0152]     |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0012 [-0.0012, -0.0012]    |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0000 [-0.0035, 0.0000]      |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0012 [-0.0023, 0.0000]     |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0012 [-0.0070, -0.0012]    |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0012 [-0.0023, 0.0000]     |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | -0.0035 [-0.0047, 0.0000]     |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0023 [-0.0058, 0.0000]     |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0023 [-0.0058, -0.0023]    |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0012 [-0.0023, 0.0000]     |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | -0.0035 [-0.0047, 0.0000]     |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | -0.0023 [-0.0058, 0.0000]     |
| algorithm    | CART - RF               |         | packet_ablation  |       5 | -0.0023 [-0.0047, 0.0187]     |
| algorithm    | KNN - RF                |         | packet_ablation  |       5 | -0.0093 [-0.0234, -0.0047]    |
| algorithm    | LGBM - RF               |         | packet_ablation  |       5 | 0.0000 [-0.0023, 0.0047]      |
| algorithm    | XGB - RF                |         | packet_ablation  |       5 | -0.0023 [-0.0093, 0.0000]     |
| algorithm    | CART - RF               |         | session_sequence |       5 | -0.0012 [-0.0105, 0.0000]     |
| algorithm    | KNN - RF                |         | session_sequence |       5 | -0.0012 [-0.0012, -0.0012]    |
| algorithm    | LGBM - RF               |         | session_sequence |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | XGB - RF                |         | session_sequence |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | CART - RF               |         | behavior_window  |       5 | 0.0000 [-0.0070, 0.0000]      |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0012 [-0.0023, -0.0012]    |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | CART - RF               |         | behavior_window  |       5 | -0.0023 [-0.0035, 0.0000]     |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0012 [-0.0023, 0.0012]     |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | CART - RF               |         | behavior_window  |       5 | 0.0000 [-0.0035, 0.0000]      |
| algorithm    | KNN - RF                |         | behavior_window  |       5 | -0.0012 [-0.0012, -0.0012]    |
| algorithm    | LGBM - RF               |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | XGB - RF                |         | behavior_window  |       5 | 0.0000 [0.0000, 0.0000]       |
| algorithm    | CART - RF               |         | packet_ablation  |       5 | -0.0023 [-0.0093, 0.0023]     |
| algorithm    | KNN - RF                |         | packet_ablation  |       5 | -0.0304 [-0.0374, -0.0210]    |
| algorithm    | LGBM - RF               |         | packet_ablation  |       5 | 0.0000 [-0.0327, 0.0047]      |
| algorithm    | XGB - RF                |         | packet_ablation  |       5 | 0.0000 [-0.0093, 0.0000]      |
