# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_dev_distractor_v1.json
- Mode: llm
- Records: 200
- Agents: react, reflexion
- Total Estimated Cost: $0.11733 USD ($0.25/1M tokens average)

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.74 | 0.92 | 0.18 |
| Avg attempts | 1 | 1.39 | 0.39 |
| Avg token estimate | 1881.49 | 2811.81 | 930.32 |
| Avg latency (ms) | 3768.1 | 7988.38 | 4220.28 |

## Failure modes
```json
{
  "react": {
    "none": 74,
    "wrong_final_answer": 26
  },
  "reflexion": {
    "none": 92,
    "wrong_final_answer": 8
  },
  "combined": {
    "none": 166,
    "wrong_final_answer": 34
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.

## Detailed Run Logs
| QID | Agent | Gold Answer | Predicted Answer | Correct? | Attempts | Tokens | Latency (ms) | Est. Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 5a713ea95542994082a3e6e4 | ReAct | Apalachees | Ais | ❌ | 1 | 2013 | 2845 | $0.0005033 |
| 5a713ea95542994082a3e6e4 | Reflexion | Apalachees | Ais | ❌ | 3 | 6996 | 13104 | $0.0017490 |
| 5a7166395542994082a3e814 | ReAct | Kansas Song | Kansas Song (We’re From Kansas) | ✅ | 1 | 2202 | 3522 | $0.0005505 |
| 5a7166395542994082a3e814 | Reflexion | Kansas Song | Kansas Song (We’re From Kansas) | ✅ | 1 | 2202 | 2112 | $0.0005505 |
| 5a722b8655429971e9dc9329 | ReAct | Barton Lee Hazlewood | Lee Hazlewood | ❌ | 1 | 1640 | 7176 | $0.0004100 |
| 5a722b8655429971e9dc9329 | Reflexion | Barton Lee Hazlewood | Barton Lee Hazlewood | ✅ | 3 | 5962 | 23385 | $0.0014905 |
| 5a7320565542991f9a20c61d | ReAct | Keith Bostic | Keith Bostic is younger than Jerry Glanville. | ✅ | 1 | 1972 | 2930 | $0.0004930 |
| 5a7320565542991f9a20c61d | Reflexion | Keith Bostic | Keith Bostic | ✅ | 1 | 1942 | 3873 | $0.0004855 |
| 5a74106b55429979e288289e | ReAct | Mumbai | Mumbai, Maharashtra | ✅ | 1 | 1687 | 4886 | $0.0004217 |
| 5a74106b55429979e288289e | Reflexion | Mumbai | Mumbai, Maharashtra | ✅ | 1 | 1687 | 2885 | $0.0004217 |
| 5a7571135542992d0ec05f98 | ReAct | New York City | New York City | ✅ | 1 | 1823 | 7522 | $0.0004557 |
| 5a7571135542992d0ec05f98 | Reflexion | New York City | New York City | ✅ | 1 | 1823 | 2387 | $0.0004557 |
| 5a75e05c55429976ec32bc5f | ReAct | 9,984 | 9,984 | ✅ | 1 | 2053 | 3672 | $0.0005132 |
| 5a75e05c55429976ec32bc5f | Reflexion | 9,984 | 9,984 | ✅ | 1 | 2053 | 2696 | $0.0005132 |
| 5a760ab65542994ccc918697 | ReAct | Nelson Rockefeller | Nelson Rockefeller | ✅ | 1 | 3092 | 2652 | $0.0007730 |
| 5a760ab65542994ccc918697 | Reflexion | Nelson Rockefeller | Nelson Rockefeller | ✅ | 1 | 3092 | 2226 | $0.0007730 |
| 5a7625e8554299109176e66a | ReAct | 1865 | 1865 | ✅ | 1 | 1552 | 3098 | $0.0003880 |
| 5a7625e8554299109176e66a | Reflexion | 1865 | 1865 | ✅ | 1 | 1554 | 2440 | $0.0003885 |
| 5a77152355429966f1a36c2e | ReAct | 821 | 821 | ✅ | 1 | 1310 | 2299 | $0.0003275 |
| 5a77152355429966f1a36c2e | Reflexion | 821 | 821 | ✅ | 1 | 1310 | 4573 | $0.0003275 |
| 5a7759fc5542993569682d60 | ReAct | Canary Islands, Spain | Teide National Park is located in Tenerife, and Garajonay National Park is located in La Gomera, both of which are part of the Canary Islands, Spain. | ✅ | 1 | 1695 | 3864 | $0.0004237 |
| 5a7759fc5542993569682d60 | Reflexion | Canary Islands, Spain | Teide National Park is located in Tenerife, and Garajonay National Park is located in La Gomera, both of which are part of the Canary Islands, Spain. | ✅ | 1 | 1695 | 3002 | $0.0004237 |
| 5a77724455429972597f153e | ReAct | Indianapolis Motor Speedway | Indianapolis Motor Speedway | ✅ | 1 | 1761 | 1993 | $0.0004402 |
| 5a77724455429972597f153e | Reflexion | Indianapolis Motor Speedway | Indianapolis Motor Speedway | ✅ | 1 | 1761 | 4149 | $0.0004402 |
| 5a77cb335542997042120b3a | ReAct | John John Florence | John John Florence | ✅ | 1 | 1331 | 2869 | $0.0003327 |
| 5a77cb335542997042120b3a | Reflexion | John John Florence | John John Florence | ✅ | 1 | 1331 | 2635 | $0.0003327 |
| 5a78bd9b554299078472774a | ReAct | British | British | ✅ | 1 | 1833 | 2423 | $0.0004582 |
| 5a78bd9b554299078472774a | Reflexion | British | British | ✅ | 1 | 1829 | 2643 | $0.0004572 |
| 5a79311755429970f5fffe67 | ReAct | 1962 | Masakazu Katsura | ❌ | 1 | 2304 | 4911 | $0.0005760 |
| 5a79311755429970f5fffe67 | Reflexion | 1962 | 1962 | ✅ | 2 | 4999 | 10811 | $0.0012497 |
| 5a7a0e1e5542990783324e1a | ReAct | Scotch Collie | Scotch Collie | ✅ | 1 | 2147 | 4586 | $0.0005368 |
| 5a7a0e1e5542990783324e1a | Reflexion | Scotch Collie | Scotch Collie | ✅ | 1 | 2147 | 3379 | $0.0005368 |
| 5a7bbb64554299042af8f7cc | ReAct | Terry Richardson | Annie Morton | ❌ | 1 | 1795 | 3557 | $0.0004487 |
| 5a7bbb64554299042af8f7cc | Reflexion | Terry Richardson | Annie Morton | ❌ | 3 | 6258 | 19569 | $0.0015645 |
| 5a7be2595542997c3ec972ac | ReAct | Adeline Virginia Woolf | Virginia Woolf | ❌ | 1 | 1625 | 2627 | $0.0004062 |
| 5a7be2595542997c3ec972ac | Reflexion | Adeline Virginia Woolf | Virginia Woolf | ✅ | 2 | 3693 | 7275 | $0.0009232 |
| 5a7cc50e554299452d57ba3e | ReAct | Letters to Cleo | Letters to Cleo | ✅ | 1 | 1916 | 3896 | $0.0004790 |
| 5a7cc50e554299452d57ba3e | Reflexion | Letters to Cleo | Letters to Cleo | ✅ | 1 | 1916 | 4157 | $0.0004790 |
| 5a7d54165542995f4f402256 | ReAct | Yellowcraig | Firth of Forth | ❌ | 1 | 1634 | 2554 | $0.0004085 |
| 5a7d54165542995f4f402256 | Reflexion | Yellowcraig | Yellowcraig | ✅ | 2 | 3697 | 9201 | $0.0009242 |
| 5a80721b554299485f5985ef | ReAct | World War II | World War II | ✅ | 1 | 1516 | 6552 | $0.0003790 |
| 5a80721b554299485f5985ef | Reflexion | World War II | World War II | ✅ | 1 | 1516 | 1867 | $0.0003790 |
| 5a80840f554299485f59863b | ReAct | Charmed | Charmed | ✅ | 1 | 1924 | 7453 | $0.0004810 |
| 5a80840f554299485f59863b | Reflexion | Charmed | Charmed | ✅ | 1 | 1924 | 2244 | $0.0004810 |
| 5a80b3a9554299485f5986cc | ReAct | Fairfax County | Fairfax County | ✅ | 1 | 1688 | 3891 | $0.0004220 |
| 5a80b3a9554299485f5986cc | Reflexion | Fairfax County | Fairfax County | ✅ | 1 | 1688 | 1937 | $0.0004220 |
| 5a8133725542995ce29dcbdb | ReAct | Robert Erskine Childers DSC | Robert Erskine Childers | ✅ | 1 | 1467 | 5506 | $0.0003667 |
| 5a8133725542995ce29dcbdb | Reflexion | Robert Erskine Childers DSC | Robert Erskine Childers | ✅ | 1 | 1467 | 4667 | $0.0003667 |
| 5a828c8355429966c78a6a50 | ReAct | Henry J. Kaiser | Henry J. Kaiser | ✅ | 1 | 1725 | 4725 | $0.0004312 |
| 5a828c8355429966c78a6a50 | Reflexion | Henry J. Kaiser | Henry J. Kaiser | ✅ | 1 | 1725 | 2262 | $0.0004312 |
| 5a835478554299123d8c20ed | ReAct | 250 million | The context does not provide specific sales figures for Roald Dahl's variation on a popular anecdote, "Mrs. Bixby and the Colonel's Coat." Therefore, the answer is not available. | ❌ | 1 | 1444 | 4562 | $0.0003610 |
| 5a835478554299123d8c20ed | Reflexion | 250 million | 250 million | ✅ | 3 | 5157 | 13796 | $0.0012893 |
| 5a8361b65542992ef85e22a0 | ReAct | International Boxing Hall of Fame | International Boxing Hall of Fame | ✅ | 1 | 2432 | 4223 | $0.0006080 |
| 5a8361b65542992ef85e22a0 | Reflexion | International Boxing Hall of Fame | International Boxing Hall of Fame | ✅ | 1 | 2432 | 1751 | $0.0006080 |
| 5a84c4135542994c784dda31 | ReAct | no | No, Yingkou is a prefecture-level city, while Fuding is a county-level city. | ✅ | 1 | 1187 | 3476 | $0.0002967 |
| 5a84c4135542994c784dda31 | Reflexion | no | No, Yingkou is a prefecture-level city, while Fuding is a county-level city. | ✅ | 1 | 1187 | 2859 | $0.0002967 |
| 5a85b2d95542997b5ce40028 | ReAct | Eenasul Fateh | Eenasul Fateh | ✅ | 1 | 2312 | 4057 | $0.0005780 |
| 5a85b2d95542997b5ce40028 | Reflexion | Eenasul Fateh | Eenasul Fateh | ✅ | 1 | 2312 | 2968 | $0.0005780 |
| 5a85ea095542994775f606a8 | ReAct | Animorphs | Animorphs | ✅ | 1 | 2040 | 2966 | $0.0005100 |
| 5a85ea095542994775f606a8 | Reflexion | Animorphs | Animorphs | ✅ | 1 | 2040 | 5782 | $0.0005100 |
| 5a85fb085542994775f606de | ReAct | Ronald Shusett | Ronald Shusett | ✅ | 1 | 1831 | 2241 | $0.0004577 |
| 5a85fb085542994775f606de | Reflexion | Ronald Shusett | Ronald Shusett | ✅ | 1 | 1831 | 2688 | $0.0004577 |
| 5a86ebac55429960ec39b6d6 | ReAct | Mondelez International, Inc. | Mondelez International | ✅ | 1 | 1692 | 2581 | $0.0004230 |
| 5a86ebac55429960ec39b6d6 | Reflexion | Mondelez International, Inc. | Mondelez International | ✅ | 1 | 1688 | 3448 | $0.0004220 |
| 5a877e5d5542993e715abf7d | ReAct | David Weissman | David Weissman | ✅ | 1 | 1731 | 2653 | $0.0004327 |
| 5a877e5d5542993e715abf7d | Reflexion | David Weissman | David Weissman | ✅ | 1 | 1731 | 3111 | $0.0004327 |
| 5a87ab905542996e4f3088c1 | ReAct | 3,677 seated | 3,677 seated | ✅ | 1 | 3410 | 2476 | $0.0008525 |
| 5a87ab905542996e4f3088c1 | Reflexion | 3,677 seated | 3,677 seated | ✅ | 1 | 3410 | 2526 | $0.0008525 |
| 5a87c13f5542996e4f30890c | ReAct | Rome | Rome | ✅ | 1 | 1865 | 1931 | $0.0004662 |
| 5a87c13f5542996e4f30890c | Reflexion | Rome | Rome | ✅ | 1 | 1863 | 4940 | $0.0004657 |
| 5a88658955429938390d3f47 | ReAct | Conscription | requiring only men to register for the draft | ❌ | 1 | 2484 | 4170 | $0.0006210 |
| 5a88658955429938390d3f47 | Reflexion | Conscription | conscription | ✅ | 2 | 5372 | 7779 | $0.0013430 |
| 5a8979f4554299669944a52e | ReAct | Ann | Ann | ✅ | 1 | 1542 | 1863 | $0.0003855 |
| 5a8979f4554299669944a52e | Reflexion | Ann | Ann | ✅ | 1 | 1542 | 2172 | $0.0003855 |
| 5a8a3e745542996c9b8d5e70 | ReAct | Arena of Khazan | Arena of Khazan | ✅ | 1 | 1694 | 3677 | $0.0004235 |
| 5a8a3e745542996c9b8d5e70 | Reflexion | Arena of Khazan | Arena of Khazan | ✅ | 1 | 1694 | 4314 | $0.0004235 |
| 5a8a43eb5542996c9b8d5e82 | ReAct | Marion, South Australia | Marion, South Australia | ✅ | 1 | 2209 | 2550 | $0.0005523 |
| 5a8a43eb5542996c9b8d5e82 | Reflexion | Marion, South Australia | Marion, South Australia | ✅ | 1 | 2209 | 2301 | $0.0005523 |
| 5a8b20335542996c9b8d5fb3 | ReAct | shortest player ever to play in the National Basketball Association | Muggsy Bogues | ❌ | 1 | 2371 | 4098 | $0.0005927 |
| 5a8b20335542996c9b8d5fb3 | Reflexion | shortest player ever to play in the National Basketball Association | Muggsy Bogues (shortest player in NBA history) | ✅ | 2 | 5240 | 13008 | $0.0013100 |
| 5a8b57f25542995d1e6f1371 | ReAct | yes | Yes | ✅ | 1 | 1640 | 4287 | $0.0004100 |
| 5a8b57f25542995d1e6f1371 | Reflexion | yes | Yes | ✅ | 1 | 1640 | 3235 | $0.0004100 |
| 5a8c7595554299585d9e36b6 | ReAct | Chief of Protocol | Shirley Temple Black | ❌ | 1 | 1826 | 2799 | $0.0004565 |
| 5a8c7595554299585d9e36b6 | Reflexion | Chief of Protocol | Chief of Protocol of the United States | ✅ | 3 | 6393 | 11823 | $0.0015982 |
| 5a8db19d5542994ba4e3dd00 | ReAct | yes | Yes | ✅ | 1 | 1805 | 3740 | $0.0004512 |
| 5a8db19d5542994ba4e3dd00 | Reflexion | yes | Yes | ✅ | 1 | 1805 | 2174 | $0.0004512 |
| 5a8e068b5542995085b37384 | ReAct | yes | Yes | ✅ | 1 | 1833 | 2414 | $0.0004582 |
| 5a8e068b5542995085b37384 | Reflexion | yes | Yes | ✅ | 1 | 1822 | 1954 | $0.0004555 |
| 5a8e0a005542995085b373a1 | ReAct | IT products and services | IT products and services | ✅ | 1 | 2090 | 2848 | $0.0005225 |
| 5a8e0a005542995085b373a1 | Reflexion | IT products and services | IT products and services | ✅ | 1 | 2090 | 2961 | $0.0005225 |
| 5a8e1027554299653c1aa15f | ReAct | 2009 Big 12 Conference | 2009, Big 12 Conference | ✅ | 1 | 1777 | 2084 | $0.0004442 |
| 5a8e1027554299653c1aa15f | Reflexion | 2009 Big 12 Conference | 2009, Big 12 Conference | ✅ | 1 | 1777 | 2689 | $0.0004442 |
| 5a8e3ea95542995a26add48d | ReAct | Greenwich Village, New York City | Greenwich Village, New York City | ✅ | 1 | 1824 | 2361 | $0.0004560 |
| 5a8e3ea95542995a26add48d | Reflexion | Greenwich Village, New York City | Greenwich Village, New York City | ✅ | 1 | 1818 | 3025 | $0.0004545 |
| 5a8ef2a75542995a26add583 | ReAct | 2000 | 2000 | ✅ | 1 | 1763 | 4362 | $0.0004408 |
| 5a8ef2a75542995a26add583 | Reflexion | 2000 | 2000 | ✅ | 1 | 1763 | 2139 | $0.0004408 |
| 5a8f4c8d554299458435d5a3 | ReAct | more than 70 countries | 70 | ❌ | 1 | 1593 | 7047 | $0.0003983 |
| 5a8f4c8d554299458435d5a3 | Reflexion | more than 70 countries | more than 70 countries | ✅ | 2 | 3600 | 6764 | $0.0009000 |
| 5ab29c24554299449642c932 | ReAct | yes | Yes | ✅ | 1 | 1818 | 2206 | $0.0004545 |
| 5ab29c24554299449642c932 | Reflexion | yes | Yes | ✅ | 1 | 1818 | 2508 | $0.0004545 |
| 5ab2d3df554299194fa9352c | ReAct | sovereignty | Ethiopian sovereignty | ✅ | 1 | 2423 | 2600 | $0.0006057 |
| 5ab2d3df554299194fa9352c | Reflexion | sovereignty | Ethiopian sovereignty. | ✅ | 1 | 2426 | 3102 | $0.0006065 |
| 5ab3b0bf5542992ade7c6e39 | ReAct | 1999 | 1999 | ✅ | 1 | 1971 | 2284 | $0.0004928 |
| 5ab3b0bf5542992ade7c6e39 | Reflexion | 1999 | 1999 | ✅ | 1 | 1971 | 2065 | $0.0004928 |
| 5ab3e45655429976abd1bcd4 | ReAct | the North Atlantic Conference | North Atlantic Conference | ✅ | 1 | 1790 | 2679 | $0.0004475 |
| 5ab3e45655429976abd1bcd4 | Reflexion | the North Atlantic Conference | North Atlantic Conference | ✅ | 1 | 1795 | 2441 | $0.0004487 |
| 5ab51dae5542991779162d82 | ReAct | no | No | ✅ | 1 | 1913 | 3229 | $0.0004782 |
| 5ab51dae5542991779162d82 | Reflexion | no | No | ✅ | 1 | 1913 | 1913 | $0.0004782 |
| 5ab56e32554299637185c594 | ReAct | no | Yes | ❌ | 1 | 3203 | 2637 | $0.0008007 |
| 5ab56e32554299637185c594 | Reflexion | no | Yes. | ❌ | 3 | 10515 | 19837 | $0.0026288 |
| 5ab6d09255429954757d337d | ReAct | from 1986 to 2013 | 1986 to 2013 | ✅ | 1 | 1455 | 5957 | $0.0003637 |
| 5ab6d09255429954757d337d | Reflexion | from 1986 to 2013 | 1986 to 2013 | ✅ | 1 | 1455 | 2949 | $0.0003637 |
| 5ab84bf555429916710eb01f | ReAct | 1,462 | 1,462 | ✅ | 1 | 1807 | 2617 | $0.0004518 |
| 5ab84bf555429916710eb01f | Reflexion | 1,462 | 1,462 | ✅ | 1 | 1807 | 4922 | $0.0004518 |
| 5ab859a955429934fafe6d7b | ReAct | Phil Spector | Phil Spector | ✅ | 1 | 2906 | 2544 | $0.0007265 |
| 5ab859a955429934fafe6d7b | Reflexion | Phil Spector | Phil Spector | ✅ | 1 | 2906 | 4208 | $0.0007265 |
| 5ab96ab755429970cfb8eacd | ReAct | Max Martin, Savan Kotecha and Ilya Salmanzadeh | Max Martin, Savan Kotecha, Ilya Salmanzadeh | ✅ | 1 | 1888 | 5603 | $0.0004720 |
| 5ab96ab755429970cfb8eacd | Reflexion | Max Martin, Savan Kotecha and Ilya Salmanzadeh | Max Martin, Savan Kotecha, Ilya Salmanzadeh | ✅ | 1 | 1888 | 4163 | $0.0004720 |
| 5aba5d2e55429901930fa799 | ReAct | Monica Lewinsky | Monica Lewinsky | ✅ | 1 | 2165 | 5418 | $0.0005412 |
| 5aba5d2e55429901930fa799 | Reflexion | Monica Lewinsky | Monica Lewinsky | ✅ | 1 | 2165 | 4826 | $0.0005412 |
| 5aba749055429901930fa7d8 | ReAct | director | Film director | ✅ | 1 | 1316 | 3064 | $0.0003290 |
| 5aba749055429901930fa7d8 | Reflexion | director | Film director | ✅ | 1 | 1316 | 2360 | $0.0003290 |
| 5aba7cfe554299232ef4a2fd | ReAct | Carabao Cup | Carabao Cup | ✅ | 1 | 1768 | 5029 | $0.0004420 |
| 5aba7cfe554299232ef4a2fd | Reflexion | Carabao Cup | Carabao Cup | ✅ | 1 | 1768 | 2543 | $0.0004420 |
| 5abbf698554299114383a0b5 | ReAct | English Electric Canberra | English Electric Canberra | ✅ | 1 | 2097 | 3067 | $0.0005242 |
| 5abbf698554299114383a0b5 | Reflexion | English Electric Canberra | English Electric Canberra | ✅ | 1 | 2090 | 1917 | $0.0005225 |
| 5abc0a5d5542993f40c73c64 | ReAct | no | No, "Freakonomics" is an American documentary, while "In the Realm of the Hackers" is an Australian documentary. | ❌ | 1 | 2222 | 4016 | $0.0005555 |
| 5abc0a5d5542993f40c73c64 | Reflexion | no | No | ✅ | 1 | 2145 | 3923 | $0.0005362 |
| 5abd259d55429924427fcf1a | ReAct | yes | Yes | ✅ | 1 | 837 | 2379 | $0.0002092 |
| 5abd259d55429924427fcf1a | Reflexion | yes | Yes | ✅ | 1 | 851 | 2865 | $0.0002127 |
| 5abd94525542992ac4f382d2 | ReAct | YG Entertainment | YG Entertainment | ✅ | 1 | 1822 | 2194 | $0.0004555 |
| 5abd94525542992ac4f382d2 | Reflexion | YG Entertainment | YG Entertainment | ✅ | 1 | 1823 | 2885 | $0.0004557 |
| 5abdf12255429976d4830a2f | ReAct | Bob Seger | Bob Seger | ✅ | 1 | 1899 | 4766 | $0.0004747 |
| 5abdf12255429976d4830a2f | Reflexion | Bob Seger | Bob Seger | ✅ | 1 | 1899 | 2038 | $0.0004747 |
| 5abf63f15542997ec76fd3ea | ReAct | October 1922 | 1922 | ❌ | 1 | 2425 | 3072 | $0.0006063 |
| 5abf63f15542997ec76fd3ea | Reflexion | October 1922 | October 1922 | ✅ | 3 | 8211 | 153516 | $0.0020527 |
| 5abfb3425542990832d3a1c0 | ReAct | The Conversation | The Conversation | ✅ | 1 | 1575 | 14607 | $0.0003938 |
| 5abfb3425542990832d3a1c0 | Reflexion | The Conversation | The Conversation | ✅ | 1 | 1575 | 3437 | $0.0003938 |
| 5ac1b8ee5542994d76dccedc | ReAct | Levni Yilmaz | Lev Yilmaz | ✅ | 1 | 2413 | 4823 | $0.0006032 |
| 5ac1b8ee5542994d76dccedc | Reflexion | Levni Yilmaz | Lev Yilmaz | ✅ | 1 | 2411 | 4408 | $0.0006027 |
| 5ac23ff0554299636651994d | ReAct | 2000 | March 14, 2000 | ✅ | 1 | 1918 | 2215 | $0.0004795 |
| 5ac23ff0554299636651994d | Reflexion | 2000 | March 14, 2000 | ✅ | 1 | 1919 | 13588 | $0.0004797 |
| 5ac2acff55429921a00ab02b | ReAct | Bill Murray | Nick Lachey | ❌ | 1 | 1827 | 2234 | $0.0004567 |
| 5ac2acff55429921a00ab02b | Reflexion | Bill Murray | Bill Murray | ✅ | 3 | 6368 | 12014 | $0.0015920 |
| 5ac3165c5542995ef918c10a | ReAct | John Waters | John Waters | ✅ | 1 | 1327 | 3922 | $0.0003317 |
| 5ac3165c5542995ef918c10a | Reflexion | John Waters | John Waters | ✅ | 1 | 1327 | 4092 | $0.0003317 |
| 5adbf0a255429947ff17385a | ReAct | no | No | ✅ | 1 | 1472 | 3773 | $0.0003680 |
| 5adbf0a255429947ff17385a | Reflexion | no | No | ✅ | 1 | 1472 | 2552 | $0.0003680 |
| 5adc53f75542996e6852530a | ReAct | no | Yes | ❌ | 1 | 1513 | 2349 | $0.0003783 |
| 5adc53f75542996e6852530a | Reflexion | no | Yes. | ❌ | 3 | 5421 | 11144 | $0.0013552 |
| 5adccd795542990d50227d2c | ReAct | Beijing | Beijing | ✅ | 1 | 1628 | 3799 | $0.0004070 |
| 5adccd795542990d50227d2c | Reflexion | Beijing | Beijing | ✅ | 1 | 1628 | 19450 | $0.0004070 |
| 5add61d65542995b365fab21 | ReAct | Organizations could come together to address global issues | World Summit of Nobel Peace Laureates | ❌ | 1 | 2596 | 3406 | $0.0006490 |
| 5add61d65542995b365fab21 | Reflexion | Organizations could come together to address global issues | World Summit of Nobel Peace Laureates | ❌ | 3 | 8797 | 16172 | $0.0021992 |
| 5adddccd5542997dc7907069 | ReAct | keyboard function keys | Siri Remote | ❌ | 1 | 2266 | 3477 | $0.0005665 |
| 5adddccd5542997dc7907069 | Reflexion | keyboard function keys | keyboard function keys | ✅ | 2 | 4977 | 7641 | $0.0012442 |
| 5adf37a95542995ec70e8f97 | ReAct | 1838 | 1838 | ✅ | 1 | 2255 | 1920 | $0.0005638 |
| 5adf37a95542995ec70e8f97 | Reflexion | 1838 | 1838 | ✅ | 1 | 2255 | 8079 | $0.0005638 |
| 5ae005b555429942ec259bec | ReAct | 1866 | 1866 | ✅ | 1 | 1554 | 2275 | $0.0003885 |
| 5ae005b555429942ec259bec | Reflexion | 1866 | 1866 | ✅ | 1 | 1554 | 2559 | $0.0003885 |
| 5ae0361155429925eb1afc2c | ReAct | Charles Eugène | Charles Nungesser and François Coli | ❌ | 1 | 1793 | 3457 | $0.0004482 |
| 5ae0361155429925eb1afc2c | Reflexion | Charles Eugène | Charles Nungesser | ❌ | 3 | 6398 | 22096 | $0.0015995 |
| 5ae0d4c9554299603e418468 | ReAct | 1969 until 1974 | 1969 to 1974 | ✅ | 1 | 2191 | 2193 | $0.0005477 |
| 5ae0d4c9554299603e418468 | Reflexion | 1969 until 1974 | 1969 to 1974 | ✅ | 1 | 2191 | 7014 | $0.0005477 |
| 5ae1f4cb554299234fd0436d | ReAct | 276,170 inhabitants | Strasbourg | ❌ | 1 | 1543 | 3974 | $0.0003857 |
| 5ae1f4cb554299234fd0436d | Reflexion | 276,170 inhabitants | 276,170 | ✅ | 2 | 3514 | 9040 | $0.0008785 |
| 5ae2070a5542994d89d5b313 | ReAct | Badly Drawn Boy | Wolf Alice | ❌ | 1 | 1564 | 2607 | $0.0003910 |
| 5ae2070a5542994d89d5b313 | Reflexion | Badly Drawn Boy | Badly Drawn Boy | ✅ | 3 | 5613 | 11303 | $0.0014032 |
| 5ae224da554299234fd043ee | ReAct | no | No | ✅ | 1 | 1562 | 2464 | $0.0003905 |
| 5ae224da554299234fd043ee | Reflexion | no | No | ✅ | 1 | 1561 | 2584 | $0.0003902 |
| 5ae22b8d554299234fd0440f | ReAct | World's Best Goalkeeper | Peter Schmeichel was voted the IFFHS World's Best Goalkeeper in 1992. | ✅ | 1 | 1773 | 2528 | $0.0004432 |
| 5ae22b8d554299234fd0440f | Reflexion | World's Best Goalkeeper | World's Best Goalkeeper | ✅ | 1 | 1715 | 5063 | $0.0004287 |
| 5ae2b770554299495565db0f | ReAct | March and April | March and April | ✅ | 1 | 1525 | 2860 | $0.0003812 |
| 5ae2b770554299495565db0f | Reflexion | March and April | March and April | ✅ | 1 | 1525 | 5949 | $0.0003812 |
| 5ae2dd2055429928c423950d | ReAct | Newport | Newport | ✅ | 1 | 1716 | 3950 | $0.0004290 |
| 5ae2dd2055429928c423950d | Reflexion | Newport | Newport | ✅ | 1 | 1716 | 2097 | $0.0004290 |
| 5ae32e125542991a06ce9946 | ReAct | 35,124 | 4,505 | ❌ | 1 | 1856 | 2092 | $0.0004640 |
| 5ae32e125542991a06ce9946 | Reflexion | 35,124 | 4,505 | ❌ | 3 | 6648 | 63707 | $0.0016620 |
| 5ae33c4d5542992f92d82262 | ReAct | William Jefferson Clinton | Bill Clinton | ✅ | 1 | 1511 | 2638 | $0.0003777 |
| 5ae33c4d5542992f92d82262 | Reflexion | William Jefferson Clinton | Bill Clinton | ✅ | 1 | 1512 | 1977 | $0.0003780 |
| 5ae37c765542992f92d822d4 | ReAct | Tromeo and Juliet | Tromeo and Juliet | ✅ | 1 | 2041 | 2190 | $0.0005102 |
| 5ae37c765542992f92d822d4 | Reflexion | Tromeo and Juliet | Tromeo and Juliet | ✅ | 1 | 2041 | 2346 | $0.0005102 |
| 5ae4a3265542995ad6573de5 | ReAct | Fujioka, Gunma | Japan | ❌ | 1 | 1656 | 2364 | $0.0004140 |
| 5ae4a3265542995ad6573de5 | Reflexion | Fujioka, Gunma | Fujioka, Gunma, Japan | ✅ | 2 | 3757 | 32799 | $0.0009392 |
| 5ae53b545542990ba0bbb23c | ReAct | Las Vegas Strip in Paradise | Flamingo Hotel, Las Vegas, Nevada | ❌ | 1 | 1347 | 3356 | $0.0003367 |
| 5ae53b545542990ba0bbb23c | Reflexion | Las Vegas Strip in Paradise | Las Vegas, Nevada | ❌ | 3 | 5047 | 19277 | $0.0012617 |
| 5ae5736e5542990ba0bbb2b3 | ReAct | April 1, 1949 | April 1, 1949 | ✅ | 1 | 2091 | 6720 | $0.0005227 |
| 5ae5736e5542990ba0bbb2b3 | Reflexion | April 1, 1949 | April 1, 1949 | ✅ | 1 | 2091 | 2548 | $0.0005227 |
| 5ae5aba0554299546bf82f17 | ReAct | Teen Titans Go! | Raven | ❌ | 1 | 1911 | 2968 | $0.0004777 |
| 5ae5aba0554299546bf82f17 | Reflexion | Teen Titans Go! | Teen Titans Go! | ✅ | 2 | 4271 | 6523 | $0.0010677 |
| 5ae6050f55429929b0807a5e | ReAct | Sonic | Tails | ❌ | 1 | 2010 | 21669 | $0.0005025 |
| 5ae6050f55429929b0807a5e | Reflexion | Sonic | Sonic the Hedgehog | ✅ | 2 | 4547 | 10213 | $0.0011367 |
| 5ae73acb5542991e8301cc07 | ReAct | Drifting | Drifting | ✅ | 1 | 1775 | 3312 | $0.0004437 |
| 5ae73acb5542991e8301cc07 | Reflexion | Drifting | Drifting | ✅ | 1 | 1769 | 2644 | $0.0004422 |
| 5ae7a8175542993210983ed8 | ReAct | Pedro Rodríguez | Pedro Rodríguez | ✅ | 1 | 1711 | 4619 | $0.0004277 |
| 5ae7a8175542993210983ed8 | Reflexion | Pedro Rodríguez | Pedro Rodríguez | ✅ | 1 | 1706 | 3717 | $0.0004265 |
| 5ae7ba7a5542993210983f12 | ReAct | Usher | Usher | ✅ | 1 | 2510 | 2168 | $0.0006275 |
| 5ae7ba7a5542993210983f12 | Reflexion | Usher | Usher | ✅ | 1 | 2510 | 5828 | $0.0006275 |
| 5ae7e1fc55429952e35ea9cc | ReAct | orange | Orange | ✅ | 1 | 1894 | 3045 | $0.0004735 |
| 5ae7e1fc55429952e35ea9cc | Reflexion | orange | Orange | ✅ | 1 | 1900 | 2310 | $0.0004750 |
