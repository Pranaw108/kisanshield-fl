# Federated Learning

| Path | Purpose |
|---|---|
| `simulation/` | Flower simulation: non-IID partitions (district split, Dirichlet α), FedAvg / FedProx / FedAdam, dropout and label-noise experiments |
| `server_app/` | Production Flower ServerApp: chosen strategy + SecAgg+ + differential privacy + robust aggregation |
| `attacks/` | Privacy and robustness tests: membership inference, gradient inversion, poisoning |

Clients train **only the classifier head** on top of a frozen backbone, so updates stay small (about 100 KB) and training fits on low-end phones.
