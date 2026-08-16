# Reserving triangle data

Public actuarial reserving datasets used for TabPFN experiments.

## Files

- `clrd.csv` — CAS Loss Reserving Database extract, insurer-level Schedule P-style observations with accident year, development year, incurred loss, cumulative paid loss, premium, and line of business.
- `clrd2025.csv` — newer CLRD extract with the same general structure and updated reserve field names.
- `raa.csv` — compact paid-loss run-off triangle commonly shipped with the Python `chainladder` package.
- `genins.csv` — compact general-insurance cumulative loss triangle from the `chainladder` package.
- `auto.csv` — compact auto-insurance triangle with development, origin, incurred, paid, and line-of-business fields.

## Sources

The files were downloaded from the public `casact/chainladder-python` repository:

- https://github.com/casact/chainladder-python/tree/main/chainladder/utils/data
- https://raw.githubusercontent.com/casact/chainladder-python/main/chainladder/utils/data/clrd.csv
- https://raw.githubusercontent.com/casact/chainladder-python/main/chainladder/utils/data/clrd2025.csv
- https://raw.githubusercontent.com/casact/chainladder-python/main/chainladder/utils/data/raa.csv
- https://raw.githubusercontent.com/casact/chainladder-python/main/chainladder/utils/data/genins.csv
- https://raw.githubusercontent.com/casact/chainladder-python/main/chainladder/utils/data/auto.csv

These are raw research inputs. Check the upstream repository and CAS terms before redistribution or publication.